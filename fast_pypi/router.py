import mimetypes
from pathlib import Path
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse

from .backend import ProjectFileExistsError
from .get_backend import get_backend_from_env
from .logging import logger
from .package_rbac import (
    ProjectRBACDecisionInput,
    get_project_rbac_decision_func,
)

templates = Jinja2Templates(
    directory=Path(__file__).parent / 'templates',
)
pep503_router = APIRouter()


async def _check_and_raise_project_rbac(rbac_input: ProjectRBACDecisionInput) -> None:
    """Check and raise an exception if the project RBAC decision is not allowed.

    Args:
        rbac_input: Input for the RBAC decision function.

    Raises:
        HTTPException: If the RBAC decision is not allowed.
    """
    decision = await get_project_rbac_decision_func()(rbac_input)
    if not decision:
        logger.warning(
            'rbac_check_failed',
            extra={
                'operation_type': rbac_input.operation_type,
                'project_name': rbac_input.project_name,
                'request_method': rbac_input.request.method,
                'request_path': rbac_input.request.url.path,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You do not have permission to access this project.',
        )


@pep503_router.get('/simple/', response_class=HTMLResponse)
async def get_simple_index(request: Request) -> HTMLResponse:
    """A simple endpoint to test the router.

    Returns:
        HTMLResponse: A simple HTML response listing all projects.
    """
    # Check RBAC for the read operation on the simple root
    await _check_and_raise_project_rbac(
        ProjectRBACDecisionInput(
            operation_type='read',
            project_name=None,  # None for root
            request=request,
        ),
    )

    backend = get_backend_from_env()
    return templates.TemplateResponse(
        request=request,
        name='simple_index.html',
        context={
            'project_names': await backend.list_projects(),
        },
    )


@pep503_router.get('/simple/{project_name}/', response_class=HTMLResponse)
async def get_project_simple_index(request: Request, project_name: str) -> HTMLResponse:
    """A simple endpoint to test the router."""
    # Check RBAC for the read operation on the simple root
    await _check_and_raise_project_rbac(
        ProjectRBACDecisionInput(
            operation_type='read',
            project_name=project_name,
            request=request,
        ),
    )

    backend = get_backend_from_env()
    project_files = await backend.list_files_for_project(
        project_name,
    )
    return templates.TemplateResponse(
        request=request,
        name='simple_index_project.html',
        context={
            'project_name': project_name,
            'project_files': project_files,
        },
    )


@pep503_router.get('/artifacts/{project_name}/{version}/{filename}')
async def get_project_artifact(
    request: Request,
    project_name: str,
    version: str,
    filename: str,
) -> Response:
    """Get a specific artifact for a project."""
    # Check RBAC for the read operation on the simple root
    await _check_and_raise_project_rbac(
        ProjectRBACDecisionInput(
            operation_type='read',
            project_name=project_name,
            request=request,
        ),
    )

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
    sha256_digest: str
    protocol_version: Literal['1']
    metadata_version: str
    name: str
    version: str
    filetype: Literal['sdist', 'bdist_wheel']
    pyversion: str
    author_email: str
    description: str
    description_content_type: str
    license_expression: str
    requires_python: str
    content: UploadFile


@pep503_router.post('/upload/', status_code=status.HTTP_201_CREATED)
async def upload_project_file(
    request: Request,
    body: Annotated[UploadFormData, Form()],
) -> None:
    """Upload a project file to the server."""
    # Check RBAC for the read operation on the simple root
    await _check_and_raise_project_rbac(
        ProjectRBACDecisionInput(
            operation_type='write',
            project_name=body.name,
            request=request,
        ),
    )

    backend = get_backend_from_env()

    if not body.content.filename:
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


@pep503_router.delete('/delete/{project_name}/{version}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_version(
    request: Request,
    project_name: str,
    version: str,
) -> None:
    """Delete a specific version of a project."""
    # Check RBAC for the delete operation on the simple root
    await _check_and_raise_project_rbac(
        ProjectRBACDecisionInput(
            operation_type='delete',
            project_name=project_name,
            request=request,
        ),
    )

    backend = get_backend_from_env()
    result = await backend.delete_project_version(
        project_name=project_name,
        version=version,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Project {project_name} version {version} not found.',
        )

    logger.info(
        'project_version_deleted',
        extra={
            'project_name': project_name,
            'version': version,
        },
    )
