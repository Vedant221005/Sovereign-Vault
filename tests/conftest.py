from pathlib import Path

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-at-least-thirty-two-bytes")
    monkeypatch.setenv("FERNET_KEY", "Q8v5hYfQmGPOkWq7MwmFHz4sJQ2UTWyxlL6ZSnM4M9Q=")
    monkeypatch.setenv("ENCRYPTED_STORAGE_DIR", str(tmp_path / "encrypted"))
    monkeypatch.setenv("MAX_FILE_SIZE", "1048576")
    monkeypatch.setenv("RATELIMIT_ENABLED", "false")

    flask_app = create_app()
    flask_app.config.update(TESTING=True)

    with flask_app.app_context():
        db.drop_all()
        db.create_all()

    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def register_user(client):
    def _register(username: str, password: str):
        return client.post(
            "/register",
            json={"username": username, "password": password},
        )

    return _register


@pytest.fixture()
def login_user(client):
    def _login(username: str, password: str):
        return client.post(
            "/login",
            json={"username": username, "password": password},
        )

    return _login


@pytest.fixture()
def auth_header():
    def _header(token: str):
        return {"Authorization": f"Bearer {token}"}

    return _header
