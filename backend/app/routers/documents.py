from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from ..database import get_db, ROOT
from ..models import Document, Quiz, Review
from ..schemas import Question, CardReview
from ..security import current_user
from ..services.study import retrieve
from ..services.documents import owned, brief, save_document
from ..services.demo import guest_quota

router = APIRouter(prefix="/documents", tags=["Documents & study"])


@router.get("")
def listing(db: Session = Depends(get_db), user=Depends(current_user)):
    return [brief(d) for d in db.query(Document).filter_by(user_id=user.id).order_by(Document.id.desc()).all()]


@router.post("", status_code=201)
def upload(file: UploadFile, db: Session = Depends(get_db), user=Depends(current_user)):
    guest_quota(db, user, Document, 10)
    data = file.file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Maximum file size is 10 MB / الحد الأقصى 10 ميجابايت")
    return save_document(db, user, file.filename or "untitled", data)


@router.post("/samples", status_code=201)
def samples(db: Session = Depends(get_db), user=Depends(current_user)):
    created = []
    for path in sorted((ROOT / "samples").glob("*.txt")):
        existing = db.query(Document).filter_by(user_id=user.id, title=path.name).first()
        created.append(
            brief(existing)
            if existing
            else save_document(db, user, path.name, path.read_bytes(), commit=False, trusted=True)
        )
    db.commit()
    return created


@router.get("/{document_id}")
def detail(document_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    d = owned(db, user, document_id)
    return {
        **brief(d),
        "summary": d.study["summary"],
        "cards": d.study["cards"],
        "mode": d.study["mode"],
        "source": d.chunks,
    }


@router.delete("/{document_id}", status_code=204)
def delete(document_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    doc = owned(db, user, document_id)
    db.query(Quiz).filter_by(document_id=doc.id, user_id=user.id).delete()
    db.query(Review).filter_by(document_id=doc.id, user_id=user.id).delete()
    db.delete(doc)
    db.commit()


@router.post("/{document_id}/ask")
def ask(document_id: int, body: Question, db: Session = Depends(get_db), user=Depends(current_user)):
    return retrieve(body.question, owned(db, user, document_id).chunks)


@router.post("/{document_id}/reviews", status_code=201)
def review(document_id: int, body: CardReview, db: Session = Depends(get_db), user=Depends(current_user)):
    d = owned(db, user, document_id)
    if body.card_index >= len(d.study["cards"]):
        raise HTTPException(422, "Invalid card / بطاقة غير صالحة")
    guest_quota(db, user, Review, 100)
    db.add(Review(user_id=user.id, document_id=d.id, **body.model_dump()))
    db.commit()
    return {"saved": True}
