from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.context_search import router as context_router
from app.api.documents import router as documents_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.manual_state import router as manual_state_router
from app.api.meetings import router as meetings_router
from app.api.projects import router as projects_router
from app.api.relevance import router as relevance_router
from app.domain.errors import ProjectNotFound, WorkspaceUnavailable
from app.domain.manual_state import StateError

app = FastAPI(title="ProjectPulse API", version="0.1.0")
app.include_router(health_router)
app.include_router(events_router)
app.include_router(relevance_router)
app.include_router(meetings_router)
app.include_router(context_router)
app.include_router(documents_router)
app.include_router(projects_router)
app.include_router(manual_state_router)


@app.exception_handler(StateError)
def state_error(request: Request, error: StateError) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": error.code, "message": error.message}}, status_code=error.status
    )


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
