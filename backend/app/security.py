import hashlib
import hmac
import secrets
import time
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .database import get_db
from .models import LoginSession, User


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    if "$" not in stored:
        return False
    salt, expected = stored.split("$")
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, expected)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("studylens_session", "")
    session = db.get(LoginSession, token_hash(token))
    if not session or session.expires <= time.time():
        raise HTTPException(401, "Please sign in / يرجى تسجيل الدخول")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Please sign in / يرجى تسجيل الدخول")
    return user
