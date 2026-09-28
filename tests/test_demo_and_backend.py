"""Regression coverage for real, isolated demo sessions and backend invariants."""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import User, GuestProfile, LoginSession, Document, Quiz, Review
from backend.app.security import token_hash


def enter(client):
    response = client.post("/api/auth/demo")
    assert response.status_code == 200, response.text
    assert response.json()["is_demo"] is True
    assert response.json()["email"] is None
    return response.json()


def test_demo_without_credentials_and_resume(client):
    identity = enter(client)
    assert 86000 < identity["expires_at"] - time.time() <= 86400
    documents = client.get("/api/documents").json()
    assert len(documents) == 2
    assert client.post("/api/auth/demo").json()["id"] == identity["id"]
    assert client.get("/api/documents").json() == documents
    with SessionLocal() as db:
        assert db.query(User).count() == 1
        assert db.query(LoginSession).count() == 1
        session = db.query(LoginSession).one()
        assert session.token_hash != client.cookies.get("studylens_session")
        assert session.token_hash == token_hash(client.cookies.get("studylens_session"))
    assert client.get("/api/auth/me").json()["is_demo"]


def test_guest_isolation_every_protected_resource(client):
    a = enter(client)
    document = client.get("/api/documents").json()[0]
    quiz = client.post(f"/api/documents/{document['id']}/quizzes").json()
    with TestClient(app) as visitor:
        b = enter(visitor)
        assert a["id"] != b["id"]
        assert not {d["id"] for d in visitor.get("/api/documents").json()} & {document["id"]}
        did = document["id"]
        checks = [
            ("get", f"/api/documents/{did}", None),
            ("delete", f"/api/documents/{did}", None),
            ("post", f"/api/documents/{did}/ask", {"question": "المفتاح الأساسي"}),
            ("post", f"/api/documents/{did}/reviews", {"card_index": 0, "rating": "known"}),
            ("post", f"/api/documents/{did}/quizzes", None),
            ("post", f"/api/quizzes/{quiz['id']}/submit", {"answers": [0] * len(quiz["questions"])}),
        ]
        for method, url, body in checks:
            response = getattr(visitor, method)(url, **({"json": body} if body else {}))
            assert response.status_code == 404, (url, response.text)
        assert visitor.get("/api/progress").json()["quizzes"] == 0
    assert client.get(f"/api/documents/{document['id']}").status_code == 200


def test_logout_revokes_guest_cookie(client):
    enter(client)
    old = client.cookies.get("studylens_session")
    client.post("/api/auth/logout")
    client.cookies.set("studylens_session", old)
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/documents").status_code == 401
    client.cookies.clear()
    enter(client)
    assert client.get("/api/progress").json()["quizzes"] == 0


def test_expired_guest_cleanup_preserves_real_users(account):
    registered = account.get("/api/auth/me").json()["id"]
    account.post("/api/auth/logout")
    guest = enter(account)
    did = account.get("/api/documents").json()[0]["id"]
    account.post(f"/api/documents/{did}/quizzes")
    account.post(f"/api/documents/{did}/reviews", json={"card_index": 0, "rating": "known"})
    with SessionLocal() as db:
        db.query(GuestProfile).filter_by(user_id=guest["id"]).update({"expires": 0})
        db.query(LoginSession).filter_by(user_id=guest["id"]).update({"expires": 0})
        db.commit()
    assert account.get("/api/auth/me").status_code == 401
    account.cookies.clear()
    enter(account)
    with SessionLocal() as db:
        assert db.get(User, registered) is not None
        assert db.query(Quiz).count() == 0
        assert db.query(Review).count() == 0
        assert db.query(GuestProfile).count() == 1
        assert db.query(Document).count() == 2


def test_demo_does_not_replace_registered_session(account):
    before = account.get("/api/auth/me").json()
    response = account.post("/api/auth/demo")
    assert response.json()["id"] == before["id"]
    assert response.json()["is_demo"] is False


def test_public_demo_mode_disallows_password_accounts(client, monkeypatch):
    monkeypatch.setenv("PUBLIC_DEMO_ONLY", "true")
    assert client.get("/api/config").json() == {"public_demo_only": True}
    creds = {"email": "friend@example.com", "password": "good-password", "name": "Friend"}
    assert client.post("/api/auth/register", json=creds).status_code == 403
    assert client.post("/api/auth/login", json=creds).status_code == 403
    enter(client)
    assert len(client.get("/api/documents").json()) == 2


def test_secure_cookie_and_wrong_origin(client, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    response = client.post("/api/auth/demo")
    assert "Secure" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert client.post("/api/auth/demo", headers={"origin": "https://other.example"}).status_code == 403
    monkeypatch.setenv("APP_ORIGIN", "https://studylens.example")
    assert client.post("/api/auth/demo", headers={"origin": "https://studylens.example"}).status_code == 200


def test_forged_session(client):
    client.cookies.set("studylens_session", "made-up-token")
    assert client.get("/api/documents").status_code == 401
    assert client.get("/api/progress").status_code == 401


def test_exact_scoring_and_concurrent_duplicate_submission(client):
    enter(client)
    did = client.get("/api/documents").json()[0]["id"]
    quiz = client.post(f"/api/documents/{did}/quizzes").json()
    with SessionLocal() as db:
        answers = [q["correct"] for q in db.get(Quiz, quiz["id"]).questions]
    cookie = client.cookies.get("studylens_session")

    def submit():
        with TestClient(app) as other:
            other.cookies.set("studylens_session", cookie)
            return other.post(f"/api/quizzes/{quiz['id']}/submit", json={"answers": answers})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert next(r for r in results if r.status_code == 200).json()["score"] == 100
    assert client.get("/api/progress").json()["quizzes"] == 1
    assert client.get("/api/progress").json()["average"] == 100


@pytest.mark.parametrize("answer", [True, "1", 1.5, -1, 999])
def test_invalid_quiz_answer_types(client, answer):
    enter(client)
    did = client.get("/api/documents").json()[0]["id"]
    quiz = client.post(f"/api/documents/{did}/quizzes").json()
    response = client.post(f"/api/quizzes/{quiz['id']}/submit", json={"answers": [answer] * len(quiz["questions"])})
    assert response.status_code == 422
    assert client.get("/api/progress").json()["quizzes"] == 0


def test_guest_limits_and_sample_idempotency(client):
    guest = enter(client)
    did = client.get("/api/documents").json()[0]["id"]
    for _ in range(3):
        assert len(client.post("/api/documents/samples").json()) == 2
    with SessionLocal() as db:
        source = db.get(Document, did)
        for i in range(8):
            db.add(Document(user_id=guest["id"], title=f"copy{i}", chunks=source.chunks, study=source.study))
        for _ in range(30):
            db.add(Quiz(user_id=guest["id"], document_id=did, questions=source.study["questions"]))
        for _ in range(100):
            db.add(Review(user_id=guest["id"], document_id=did, card_index=0, rating="known"))
        db.commit()
    assert client.post("/api/documents", files={"file": ("notes.txt", b"x" * 100)}).status_code == 429
    assert client.post(f"/api/documents/{did}/quizzes").status_code == 429
    assert client.post(f"/api/documents/{did}/reviews", json={"card_index": 0, "rating": "known"}).status_code == 429


def test_actual_streamed_body_limit(client):
    def parts():
        for _ in range(12):
            yield b"x" * (1024 * 1024)

    response = client.post("/api/auth/demo", content=parts(), headers={"content-type": "application/octet-stream"})
    assert response.status_code == 413
    with SessionLocal() as db:
        assert db.query(User).count() == 0


def test_parser_timeout_does_not_create_document(client):
    import subprocess

    enter(client)
    with patch("backend.app.services.processing.subprocess.run", side_effect=subprocess.TimeoutExpired("parser", 15)):
        response = client.post("/api/documents", files={"file": ("notes.txt", b"x" * 100)})
    assert response.status_code == 422 and "timed out" in response.json()["detail"]
    assert len(client.get("/api/documents").json()) == 2


def test_guest_creation_atomic_on_failure(client):
    with patch("backend.app.routers.auth.save_document", side_effect=RuntimeError("sample failure")):
        with pytest.raises(RuntimeError):
            client.post("/api/auth/demo")
    with SessionLocal() as db:
        assert db.query(User).count() == 0
        assert db.query(GuestProfile).count() == 0
        assert db.query(LoginSession).count() == 0


def test_citations_and_empty_question(client):
    enter(client)
    docs = client.get("/api/documents").json()
    english = next(d for d in docs if "Computer" in d["title"])
    did = english["id"]
    detail = client.get(f"/api/documents/{did}").json()
    answer = client.post(f"/api/documents/{did}/ask", json={"question": "TCP delivery"}).json()
    assert answer["found"]
    for citation in answer["sources"]:
        original = next(c for c in detail["source"] if c["id"] == citation["id"])
        assert citation["page"] == original["page"]
        assert all(sentence in original["text"] for sentence in citation["text"].splitlines())
    assert client.post(f"/api/documents/{did}/ask", json={"question": "   "}).status_code == 422


def test_delete_cascades_only_owner_data(client):
    enter(client)
    docs = client.get("/api/documents").json()
    did = docs[0]["id"]
    client.post(f"/api/documents/{did}/quizzes")
    client.post(f"/api/documents/{did}/reviews", json={"card_index": 0, "rating": "again"})
    assert client.delete(f"/api/documents/{did}").status_code == 204
    assert client.get(f"/api/documents/{docs[1]['id']}").status_code == 200
    with SessionLocal() as db:
        assert db.query(Quiz).filter_by(document_id=did).count() == 0
        assert db.query(Review).filter_by(document_id=did).count() == 0
    assert client.get("/api/progress").json()["reviews"] == 0


def test_sample_batch_rolls_back_when_second_file_fails(account):
    """A failed sample import must not leave a half-created library."""
    from backend.app.services.documents import save_document as real_save

    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("second sample unavailable")
        return real_save(*args, **kwargs)

    with patch("backend.app.routers.documents.save_document", side_effect=fail_second):
        with pytest.raises(RuntimeError):
            account.post("/api/documents/samples")
    assert account.get("/api/documents").json() == []
    assert len(account.post("/api/documents/samples").json()) == 2
