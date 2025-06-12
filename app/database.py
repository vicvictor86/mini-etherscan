from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from functools import partial
from sqlalchemy import text
from alembic.config import Config
from alembic import command
import json
import os

SQLALCHEMY_DATABASE_URI = "postgresql://{}:{}@{}:{}/{}".format(
    os.getenv("DB_USER"),
    os.getenv("DB_PASSWORD"),
    os.getenv("DB_HOST"),
    os.getenv("DB_PORT"),
    os.getenv("DB_DATABASE_NAME"),
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_size=10,
    max_overflow=10,
    json_serializer=partial(json.dumps, ensure_ascii=False),
)

# Create the engine and base class for declarative models
Base = declarative_base()

# Create a session factory
SessionLocal = sessionmaker(bind=engine)

# Create tables if they don't exist yet
# Ensure models are imported before calling this!
Base.metadata.create_all(engine)

# Dependency for session management (using context manager)

if os.getenv("ENV") == "E2E":
    with engine.connect() as connection:
        # If VECTOR doesn't exist error show up, execute this command in the database directly
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "../alembic.ini"))
    command.upgrade(alembic_cfg, "head")


def get_db():
    """Dependency for getting a new session with proper handling."""
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Commit the transaction
    except SQLAlchemyError as e:
        db.rollback()  # Rollback in case of an error
        raise e  # Re-raise the error to handle it further up the stack
    finally:
        db.close()  # Close the session when done
