"""Small deployment configuration boundary; secrets remain environment-only."""

import os
from urllib.parse import urlsplit


def app_origin() -> str:
    value = os.getenv("APP_ORIGIN") or os.getenv("RENDER_EXTERNAL_URL") or "http://127.0.0.1:8000"
    value = value.rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("APP_ORIGIN must be one exact HTTP(S) origin without a path")
    return value


def validate_hosted_configuration(database_url: str) -> None:
    if os.getenv("RENDER", "").lower() != "true":
        return
    if not database_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Hosted deployment requires a persistent PostgreSQL DATABASE_URL")
    if not app_origin().startswith("https://"):
        raise RuntimeError("Hosted deployment requires an HTTPS origin")
    if os.getenv("COOKIE_SECURE", "").lower() != "true":
        raise RuntimeError("Hosted deployment requires COOKIE_SECURE=true")
