from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, HTTPException, Request, status
from fastapi.params import Depends as DependsClass

from fast_pypi.logger import logger

from .utils import infer_project_name_from_request

OperationType = Literal['read', 'write', 'delete']


@dataclass
class ProjectRBACDecisionInput:
    """Input for project RBAC decision."""

    operation_type: OperationType
    project_name: str | None
    request: Request


class PackageNotAuthorizedException(HTTPException):
    """Exception raised when a user is not authorized to perform an operation on a project.

    Args:
        rbac_input: Input for the RBAC decision function.
    """

    def __init__(self, rbac_input: ProjectRBACDecisionInput) -> None:
        detail = (
            f'You do not have permission to perform {rbac_input.operation_type} on project {rbac_input.project_name}.'
        )
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def _project_decision_noop(
    _: ProjectRBACDecisionInput,
) -> bool:
    """No-op decision function for project RBAC.

    Args:
        input: Input for the decision function.

    Returns:
        bool: Always returns True.
    """
    return True


__project_decision_func: Callable[[ProjectRBACDecisionInput], Awaitable[bool]] = _project_decision_noop


def get_project_rbac_decision_func() -> Callable[[ProjectRBACDecisionInput], Awaitable[bool]]:
    """Get the project RBAC decision function.

    Returns:
        Callable[[ProjectRBACDecisionInput], Awaitable[bool]]: The project RBAC decision function.
    """
    return __project_decision_func


def set_project_rbac_decision_func(
    func: Callable[[ProjectRBACDecisionInput], Awaitable[bool]],
) -> None:
    """Set the project RBAC decision function.

    Args:
        func: The new project RBAC decision function.
    """
    global __project_decision_func  # noqa: PLW0603
    __project_decision_func = func


def reset_project_rbac_decision_func() -> None:
    """Reset the project RBAC decision function to the no-op function."""
    set_project_rbac_decision_func(_project_decision_noop)


async def check_and_raise_project_rbac(rbac_input: ProjectRBACDecisionInput) -> None:
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
        raise PackageNotAuthorizedException(rbac_input)


class _PackageRbacDependency:
    """Dependency for applying package RBAC to requests.

    Args:
        operation_type: The type of operation being performed (read, write, delete).
    """

    _operation_type: OperationType

    def __init__(self, operation_type: OperationType) -> None:
        self._operation_type = operation_type

    async def __call__(self, request: Request) -> None:
        """Apply the package RBAC dependency."""
        await check_and_raise_project_rbac(
            rbac_input=ProjectRBACDecisionInput(
                operation_type=self._operation_type,
                project_name=await infer_project_name_from_request(request),
                request=request,
            ),
        )


def package_rbac_dependency(operation_type: OperationType) -> DependsClass:
    """Create a dependency for package RBAC authorization.

    Args:
        operation_type: The type of operation being performed (read, write, delete).

    Returns:
        A FastAPI dependency that checks RBAC permissions for the specified
            operation type.
    """
    return Depends(  # pyright: ignore[reportAny]
        _PackageRbacDependency(operation_type=operation_type),
    )
