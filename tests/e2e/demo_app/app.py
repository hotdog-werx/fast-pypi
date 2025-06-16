from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from fast_pypi.pypi.package_rbac import ProjectRBACDecisionInput
from fast_pypi.pypi.router import pep503_router


async def allow_hot_dog(rbac_input: ProjectRBACDecisionInput) -> bool:
    """Check if the request has Basic Auth with username 'hot' and password 'dog'."""
    import base64
    import binascii

    auth_header = rbac_input.request.headers.get('Authorization', '')
    if not auth_header.startswith('Basic '):
        return False

    try:
        auth_decoded = base64.b64decode(auth_header[6:].encode()).decode()
        username, password = auth_decoded.split(':', 1)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False

    # Ignore hardcoded credentials warning - this is a test
    return username == 'hot' and password == 'dog'  # noqa: S105


async def healthcheck() -> PlainTextResponse:
    """Healthcheck endpoint to verify the service is running."""
    return PlainTextResponse('ok')


demo_app = FastAPI()
demo_app.include_router(router=pep503_router, prefix='/fast-pypi')
demo_app.add_api_route(
    path='/healthz',
    endpoint=healthcheck,
    methods=['GET'],
    response_class=PlainTextResponse,
)
