"""
Fixtures compartidos para los tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Cliente HTTP para tests de API (usa httpx internamente)."""
    return TestClient(app)


@pytest.fixture
def db_session_transactional():
    """
    Sesión SQLAlchemy enlazada a una transacción que hace ROLLBACK al terminar el test.
    Evita dejar datos de prueba en la base (requiere MySQL/local configurado como en desarrollo).
    """
    from app.database import engine

    connection = engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(text("SELECT 1"))
    except Exception as e:
        transaction.rollback()
        connection.close()
        pytest.skip(f"Base de datos no disponible para pruebas E2E: {e}")
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client_transactional_db(db_session_transactional):
    """
    TestClient con get_db sobrescrito para usar la sesión transaccional (rollback al acabar).
    """
    from app.database import get_db

    def override_get_db():
        yield db_session_transactional

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
