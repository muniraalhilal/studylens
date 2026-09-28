"""Guest lifecycle and explicit quotas for the public, no-signup demo."""

import time
from fastapi import HTTPException
from ..models import GuestProfile, User, LoginSession, Document, Quiz, Review

DEMO_SECONDS = 24 * 60 * 60


def cleanup_expired_guests(db):
    expired = [row[0] for row in db.query(GuestProfile.user_id).filter(GuestProfile.expires <= int(time.time())).all()]
    if expired:
        for model in (Review, Quiz, Document, LoginSession, GuestProfile):
            db.query(model).filter(model.user_id.in_(expired)).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_(expired)).delete(synchronize_session=False)
    db.query(LoginSession).filter(LoginSession.expires <= int(time.time())).delete(synchronize_session=False)


def guest_quota(db, user, model, limit):
    if db.get(GuestProfile, user.id) and db.query(model).filter_by(user_id=user.id).count() >= limit:
        raise HTTPException(429, "Demo limit reached / وصلتِ للحد المسموح في الجلسة التجريبية")
