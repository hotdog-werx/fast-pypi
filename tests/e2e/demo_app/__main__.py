import uvicorn

from fast_pypi.pypi.package_rbac import (
    set_project_rbac_decision_func,
)

from .app import allow_hot_dog, demo_app

if __name__ == '__main__':
    set_project_rbac_decision_func(allow_hot_dog)
    uvicorn.run(app=demo_app, port=8100)
