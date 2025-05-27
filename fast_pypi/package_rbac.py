from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import Request


@dataclass
class ProjectRBACDecisionInput:
    """Input for project RBAC decision."""

    operation_type: Literal['read', 'write', 'delete']
    project_name: str | None
    request: Request


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
