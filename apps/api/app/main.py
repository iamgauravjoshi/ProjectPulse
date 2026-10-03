from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.domain.errors import ProjectNotFound, WorkspaceUnavailable

app = FastAPI(title="ContextBoard API", version="0.1.0")
app.include_router(health_router)
app.include_router(projects_router)


@app.exception_handler(WorkspaceUnavailable)
def workspace_unavailable(request: Request, error: WorkspaceUnavailable) -> JSONResponse:
    return JSONResponse(
        {
            "error": {
                "code": "WORKSPACE_UNAVAILABLE",
                "message": "Workspace is temporarily unavailable.",
            }
        },
        status_code=503,
    )


@app.exception_handler(ProjectNotFound)
def project_not_found(request: Request, error: ProjectNotFound) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": "PROJECT_NOT_FOUND", "message": "Project not found."}}, status_code=404
    )
