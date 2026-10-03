from logging.config import fileConfig

from alembic import context

from app.config import get_settings
from app.db import models  # noqa: F401 -- register models for schema comparison
from app.db.base import Base
from app.db.session import create_database_engine

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
database_url = get_settings().database_url
if not database_url:
    raise ValueError("DATABASE_URL is required for migrations")

if context.is_offline_mode():
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_database_engine(database_url)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
