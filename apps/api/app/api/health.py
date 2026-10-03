from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def readiness() -> JSONResponse:
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        expected = ScriptDirectory.from_config(config).get_current_head()
        with get_engine().connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            vector = connection.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            ).scalar_one()
        if revision != expected or not vector:
            return unavailable()
    except (SQLAlchemyError, ValueError):
        return unavailable()
    return JSONResponse({"status": "ok"})


def unavailable() -> JSONResponse:
    return JSONResponse(
        {"error": {"code": "DATABASE_UNAVAILABLE", "message": "Database is not ready."}},
        status_code=503,
    )
