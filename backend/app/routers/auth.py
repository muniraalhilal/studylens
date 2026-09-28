import os
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models import LoginSession, User, GuestProfile
from ..schemas import Credentials, Registration
from ..services.demo import DEMO_SECONDS, cleanup_expired_guests
from ..database import ROOT
from ..services.documents import save_document
from ..security import current_user, hash_password, token_hash, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


def public(user, db):
    guest = db.get(GuestProfile, user.id)
    return {
        "id": user.id,
        "name": user.name,
        "email": None if guest else user.email,
        "is_demo": guest is not None,
        "expires_at": guest.expires if guest else None,
    }


def login_session(user, db, response):
    token = secrets.token_urlsafe(32)
    guest = db.get(GuestProfile, user.id)
    expiry = guest.expires if guest else int(time.time()) + 604800
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires=expiry))
    db.commit()
    response.set_cookie(
        "studylens_session",
        token,
        httponly=True,
        samesite="strict",
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        max_age=max(0, expiry - int(time.time())),
    )
    return public(user, db)


@router.post("/register", status_code=201)
def register(body: Registration, response: Response, db: Session = Depends(get_db)):
    if os.getenv("PUBLIC_DEMO_ONLY", "false").lower() == "true":
        raise HTTPException(403, "Use the demo button / استخدمي زر الدخول التجريبي")
    user = User(email=body.email, name=body.name.strip() or "Student", password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered / البريد مسجل مسبقًا")
    return login_session(user, db, response)


@router.post("/login")
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    if os.getenv("PUBLIC_DEMO_ONLY", "false").lower() == "true":
        raise HTTPException(403, "Use the demo button / استخدمي زر الدخول التجريبي")
    user = db.query(User).filter_by(email=body.email).first()
    if not user or db.get(GuestProfile, user.id) or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials / بيانات الدخول غير صحيحة")
    return login_session(user, db, response)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    db.query(LoginSession).filter_by(token_hash=token_hash(request.cookies.get("studylens_session", ""))).delete()
    db.commit()
    response.delete_cookie("studylens_session")


@router.get("/me")
def me(user=Depends(current_user), db: Session = Depends(get_db)):
    return public(user, db)


@router.post("/demo")
def demo(request: Request, response: Response, db: Session = Depends(get_db)):
    """Create an isolated 24-hour guest session, or resume the current identity."""
    existing = db.get(LoginSession, token_hash(request.cookies.get("studylens_session", "")))
    if existing and existing.expires > time.time():
        user = db.get(User, existing.user_id)
        if user:
            return public(user, db)
    cleanup_expired_guests(db)
    # Random, unguessable identity with a password deliberately unusable for login.
    user = User(email=f"{secrets.token_hex(20)}@demo.invalid", name="Demo explorer", password_hash="!guest")
    db.add(user)
    db.flush()
    db.add(GuestProfile(user_id=user.id, expires=int(time.time()) + DEMO_SECONDS))
    for path in sorted((ROOT / "samples").glob("*.txt")):
        save_document(db, user, path.name, path.read_bytes(), commit=False, trusted=True)
    return login_session(user, db, response)
