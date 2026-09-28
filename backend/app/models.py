from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from .database import Base


def now():
    return datetime.now(timezone.utc).isoformat()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(254), unique=True, nullable=False)
    name = Column(String(80), nullable=False)
    password_hash = Column(String(256), nullable=False)


class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires = Column(Integer, nullable=False)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    created_at = Column(String(40), default=now)
    chunks = Column(JSON, nullable=False)
    study = Column(JSON, nullable=False)
    size = Column(Integer, default=0)


class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    questions = Column(JSON, nullable=False)
    answers = Column(JSON, nullable=True)
    score = Column(Integer, nullable=True)
    created_at = Column(String(40), default=now)


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    card_index = Column(Integer, nullable=False)
    rating = Column(String(12), nullable=False)
    created_at = Column(String(40), default=now)


class GuestProfile(Base):
    """Temporary, isolated demo identity; existing users need no schema migration."""

    __tablename__ = "guest_profiles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    expires = Column(Integer, nullable=False, index=True)
