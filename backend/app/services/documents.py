"""Shared document ownership, presentation and ingestion services.

Routers depend on this module instead of importing other routers. Callers can
use commit=False to include ingestion in a larger, atomic transaction.
"""

from pathlib import Path
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models import Document, User
from .processing import process_document
from .demo import guest_quota


def owned(db: Session, user: User, document_id: int) -> Document:
    doc = db.query(Document).filter_by(id=document_id, user_id=user.id).first()
    if not doc:
        raise HTTPException(404, "Document not found / الملف غير موجود")
    return doc


def brief(doc: Document) -> dict:
    return {
        "id": doc.id,
        "title": doc.title,
        "created_at": doc.created_at,
        "size": doc.size,
        "pages": len(set(c["page"] for c in doc.chunks)),
        "chunks": len(doc.chunks),
    }


def save_document(
    db: Session, user: User, filename: str, data: bytes, *, commit: bool = True, trusted: bool = False
) -> dict:
    guest_quota(db, user, Document, 10)
    try:
        chunks, study = process_document(filename, data, trusted=trusted)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception:
        raise HTTPException(422, "Could not read this file. Check its format / تعذرت قراءة الملف، تحققي من الصيغة")
    doc = Document(
        user_id=user.id,
        title=Path(filename.replace("\\", "/")).name[:255],
        chunks=chunks,
        study=study,
        size=len(data),
    )
    db.add(doc)
    if commit:
        db.commit()
    else:
        db.flush()
    return brief(doc)
