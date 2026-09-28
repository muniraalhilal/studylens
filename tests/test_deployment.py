import pytest
from backend.app.config import app_origin, validate_hosted_configuration


def test_render_origin_without_wildcards(monkeypatch):
    monkeypatch.delenv("APP_ORIGIN", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://studylens-example.onrender.com")
    assert app_origin() == "https://studylens-example.onrender.com"
    monkeypatch.setenv("APP_ORIGIN", "https://custom.example/")
    assert app_origin() == "https://custom.example"


@pytest.mark.parametrize("origin", ["https://example.com/path", "*", "https://example.com?x=1", "ftp://example.com"])
def test_reject_invalid_origin(monkeypatch, origin):
    monkeypatch.setenv("APP_ORIGIN", origin)
    with pytest.raises(ValueError):
        app_origin()


def test_hosted_server_rejects_ephemeral_storage(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("APP_ORIGIN", "https://example.onrender.com")
    monkeypatch.setenv("COOKIE_SECURE", "true")
    with pytest.raises(RuntimeError, match="persistent PostgreSQL"):
        validate_hosted_configuration("sqlite:///data.db")
    validate_hosted_configuration("postgresql+psycopg://test:password@localhost/test")


def test_hosted_server_requires_secure_cookie(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("APP_ORIGIN", "https://example.onrender.com")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        validate_hosted_configuration("postgresql+psycopg://test:password@localhost/test")
