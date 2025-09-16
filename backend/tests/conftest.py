import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.db.session import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db_engine():
    """Create a test database engine using SQLite in memory."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_db_session(test_db_engine):
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client(test_db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_azure_client():
    """Mock Azure AI client for testing without external dependencies."""
    mock = AsyncMock()
    mock.run_single_turn = AsyncMock()
    return mock


@pytest.fixture
def mock_doc_store_plugin():
    """Mock document store plugin for testing without file dependencies."""
    mock = Mock()
    mock.list_documents = Mock(return_value=[])
    mock.search_documents = Mock(return_value=[])
    mock.read_document_tables = Mock(return_value=[])
    return mock


@pytest.fixture
def sample_applicant_data():
    """Provide sample applicant data for testing."""
    return {
        "id": 1,
        "name": "Test Applicant",
        "email": "test@example.com",
        "status": "pending"
    }


@pytest.fixture
def sample_assessment_data():
    """Provide sample assessment data for testing."""
    return {
        "id": 1,
        "name": "Test Assessment",
        "description": "Test assessment description",
        "target_class": "UPPER_SECOND"
    }