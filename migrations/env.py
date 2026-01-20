import sys
import os
from logging.config import fileConfig
from os.path import abspath, dirname
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- Alembic and project setup ---

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add the project's root directory to the Python path.
# This allows Alembic to find our application's modules (e.g., models).
project_root = dirname(dirname(abspath(__file__)))
sys.path.insert(0, project_root)

# --- Model Metadata ---
# Import the Base from our application and all the models that use it.
# This is crucial for Alembic's autogenerate feature to work.
from src.database.connection import Base
from src.models.user_model import User
from src.models.alert_history_model import AlertHistory
from src.models.driving_session_model import DrivingSession
from src.models.user_settings_model import UserSettings

# The target_metadata is what Alembic compares against the database
# to find differences and generate migration scripts.
target_metadata = Base.metadata

# --- Database URL Configuration ---
# Load environment variables directly from the .env file
load_dotenv(os.path.join(project_root, '.env'))

def get_database_url():
    """Constructs database URL from environment variables."""
    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME")

    if not db_name:
        raise ValueError("DB_NAME environment variable is not set.")

    return f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# Set the constructed URL for SQLAlchemy to use.
# This overrides the dummy URL in alembic.ini
config.set_main_option('sqlalchemy.url', get_database_url())


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
