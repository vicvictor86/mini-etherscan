from sqlalchemy.orm import declarative_base
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from functools import partial
import pytest
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extension import app


SQLALCHEMY_DATABASE_URI = "postgresql://{}:{}@{}:{}/{}".format(
    os.getenv("DB_USER"),
    os.getenv("DB_PASSWORD"),
    os.getenv("DB_HOST"),
    os.getenv("DB_PORT"),
    os.getenv("DB_DATABASE_NAME"),
)

Base = declarative_base()

engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_size=10,
    max_overflow=10,
    json_serializer=partial(json.dumps, ensure_ascii=False),
)


@pytest.fixture(autouse=True, scope="session")
def db_engine():
    Base.metadata.create_all(engine)

    yield engine

    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
    )()

    all_tables = session_local.execute(
        text(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' AND tableowner = 'postgres';"
        )
    )

    tables_to_ignore = ["alembic_version", "users"]
    for table in all_tables:
        if table[0] not in tables_to_ignore:
            # Clean the tables
            session_local.execute(text(f"TRUNCATE TABLE {table[0]} CASCADE;"))
            session_local.commit()

    session_local.close()


@pytest.fixture(autouse=True, scope="function")
def db_session(db_engine):
    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
        expire_on_commit=False,
    )()

    yield session_local  # every test will get a new db session

    session_local.rollback()

    session_local.close()


@pytest.fixture
def test_client():
    """A test client for the app."""
    with TestClient(app) as test_client:
        yield test_client
