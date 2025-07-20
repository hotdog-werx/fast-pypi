import mimetypes
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Body,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse, RedirectResponse

from fast_pypi.backends import ProjectFileExistsError
from fast_pypi.config import FastPypiConfig
from fast_pypi.get_backend import get_backend_from_env
from fast_pypi.logger import logger

from .package_rbac import package_rbac_dependency

templates = Jinja2Templates(
    directory=Path(__file__).parent / 'templates',
)
pep503_router = APIRouter()


@pep503_router.get(
    '/simple/',
    response_class=HTMLResponse,
    dependencies=[package_rbac_dependency('read')],
    include_in_schema=False,
)
async def get_simple_index(request: Request) -> HTMLResponse:
    """A simple endpoint to test the router.

    Returns:
        HTMLResponse: A simple HTML response listing all projects.
    """
    backend = get_backend_from_env()
    return templates.TemplateResponse(
        request=request,
        name='simple_index.html',
        context={
            'project_names': await backend.list_projects(),
        },
    )


async def handle_project_not_found(
    project_name: str,
) -> RedirectResponse:
    """Handle the case where a project is not found."""
    cfg = FastPypiConfig.from_env()
    if cfg.fallback_enabled:
        fallback_url = cfg.fallback_url.rstrip('/')
        return RedirectResponse(
            url=f'{fallback_url}/{project_name}/',
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f'Project {project_name} not found.',
    )


@pep503_router.get(
    '/simple/{project_name}/',
    response_model=None,
    dependencies=[package_rbac_dependency('read')],
    include_in_schema=False,
)
async def get_project_simple_index(request: Request, project_name: str) -> HTMLResponse | RedirectResponse:
    """A simple endpoint to test the router."""
    backend = get_backend_from_env()
    project_files = await backend.list_files_for_project(
        project_name,
    )
    if not project_files:
        return await handle_project_not_found(project_name)
    return templates.TemplateResponse(
        request=request,
        name='simple_index_project.html',
        context={
            'project_name': project_name,
            'project_files': [(f.version, f.filename) for f in project_files],
        },
    )


@pep503_router.get(
    '/artifacts/{project_name}/{version}/{filename}',
    dependencies=[package_rbac_dependency('read')],
)
async def get_project_artifact(
    project_name: str,
    version: str,
    filename: str,
) -> Response:
    """Get a specific artifact for a project."""
    backend = get_backend_from_env()
    file_contents = await backend.get_file_contents(
        project_name=project_name,
        version=version,
        filename=filename,
    )
    if not file_contents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'File {filename} for project {project_name} not found.',
        )

    mime_type = mimetypes.guess_type(file_contents.filename)
    return Response(
        content=file_contents.content,
        media_type=mime_type[0] or 'application/octet-stream',
        headers={
            'Content-Disposition': f'attachment; filename="{file_contents.filename}"',
            **({'Content-Encoding': mime_type[1]} if mime_type[1] else {}),  # If there's encoding (e.g gzip)
        },
    )


class UploadFormData(BaseModel):
    """Form data for uploading a package file."""

    action: Annotated[Literal['file_upload'], Field(alias=':action')]
    sha256_digest: str | None = None
    protocol_version: Literal['1']
    metadata_version: str
    name: str
    version: str
    filetype: Literal['sdist', 'bdist_wheel']
    pyversion: str | None = None
    author_email: str | None = None
    description: str | None = None
    description_content_type: str | None = None
    license_expression: str | None = None
    requires_python: str | None = None
    content: Annotated[UploadFile, File()]


@pep503_router.post(
    '/upload/',
    status_code=status.HTTP_201_CREATED,
    dependencies=[package_rbac_dependency('write')],
)
async def upload_project_file(
    body: Annotated[UploadFormData, Form(media_type='multipart/form-data')],
) -> None:
    """Upload a project file to the server."""
    backend = get_backend_from_env()

    if not body.content.filename:  # pragma: no cover
        logger.warning(
            'upload_file_missing_filename',
            extra={
                'project_name': body.name,
                'version': body.version,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Filename is required.',
        )

    try:
        await backend.upload_file(
            project_name=body.name,
            version=body.version,
            filename=body.content.filename,
            file_content=await body.content.read(),
            sha256_digest=body.sha256_digest,
        )
    except ProjectFileExistsError as e:
        logger.warning(
            'project_file_exists',
            extra={
                'project_name': body.name,
                'file_name': body.content.filename,
                'version': body.version,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'File {body.content.filename} for project {body.name} already exists.',
        ) from e


@pep503_router.get(
    '/projects/',
    dependencies=[package_rbac_dependency('read')],
)
async def list_projects() -> Sequence[str]:
    """List all projects."""
    backend = get_backend_from_env()
    return await backend.list_projects()


@pep503_router.get(
    '/projects/{project_name}/versions/',
    dependencies=[package_rbac_dependency('read')],
)
async def list_project_versions(project_name: str) -> Sequence[str]:
    """List all versions for a specific project."""
    backend = get_backend_from_env()
    project_versions = await backend.list_project_versions(project_name)
    if not project_versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Project {project_name} not found.',
        )
    return project_versions


@pep503_router.post(
    '/projects/{project_name}/delete-versions/',
    status_code=status.HTTP_200_OK,
    dependencies=[package_rbac_dependency('delete')],
)
async def delete_project_versions(
    _: Request,
    project_name: str,
    versions: Annotated[list[str], Body()],
) -> Sequence[str]:
    """Delete a specific version of a project."""
    backend = get_backend_from_env()
    deleted_versions: list[str] = []
    for version in versions:
        deleted = await backend.delete_project_version(
            project_name=project_name,
            version=version,
        )
        if deleted:
            deleted_versions.append(version)

    logger.info(
        'project_versions_deleted',
        extra={
            'project_name': project_name,
            'versions': deleted_versions,
        },
    )
    return deleted_versions
