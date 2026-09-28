from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Document, Quiz, Review
from ..schemas import Submission
from ..security import current_user
from ..services.documents import owned
from ..services.demo import guest_quota

router = APIRouter(tags=["Quizzes & progress"])


@router.post("/documents/{document_id}/quizzes", status_code=201)
def start(document_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    doc = owned(db, user, document_id)
    guest_quota(db, user, Quiz, 30)
    questions = doc.study["questions"]
    if not questions:
        raise HTTPException(422, "More varied text is needed to create a quiz / نحتاج نصًا أكثر تنوعًا لإنشاء اختبار")
    quiz = Quiz(user_id=user.id, document_id=doc.id, questions=questions)
    db.add(quiz)
    db.commit()
    return {"id": quiz.id, "questions": [{"prompt": q["prompt"], "options": q["options"]} for q in questions]}


@router.post("/quizzes/{quiz_id}/submit")
def submit(quiz_id: int, body: Submission, db: Session = Depends(get_db), user=Depends(current_user)):
    quiz = db.query(Quiz).filter_by(id=quiz_id, user_id=user.id).with_for_update().first()
    if not quiz:
        raise HTTPException(404, "Quiz not found / الاختبار غير موجود")
    if quiz.answers is not None:
        raise HTTPException(409, "Quiz already submitted / تم تسليم الاختبار مسبقًا")
    if len(body.answers) != len(quiz.questions) or any(
        a < 0 or a >= len(q["options"]) for a, q in zip(body.answers, quiz.questions)
    ):
        raise HTTPException(422, "Answer every question / أجيبي عن كل الأسئلة")
    score = round(100 * sum(a == q["correct"] for a, q in zip(body.answers, quiz.questions)) / len(quiz.questions))
    # Compare-and-set prevents concurrent double submissions, including on SQLite.
    changed = (
        db.query(Quiz)
        .filter(Quiz.id == quiz.id, Quiz.score.is_(None))
        .update({"answers": body.answers, "score": score}, synchronize_session=False)
    )
    if not changed:
        db.rollback()
        raise HTTPException(409, "Quiz already submitted / تم تسليم الاختبار مسبقًا")
    db.commit()
    return {"score": score, "questions": quiz.questions, "answers": body.answers}


@router.get("/progress")
def progress(db: Session = Depends(get_db), user=Depends(current_user)):
    quizzes = db.query(Quiz).filter(Quiz.user_id == user.id, Quiz.score.is_not(None)).order_by(Quiz.id.desc()).all()
    documents = db.query(Document).filter_by(user_id=user.id).all()
    titles = {d.id: d.title for d in documents}
    reviews = db.query(Review).filter_by(user_id=user.id).all()
    return {
        "documents": len(documents),
        "quizzes": len(quizzes),
        "average": round(sum(q.score for q in quizzes) / len(quizzes)) if quizzes else 0,
        "reviews": len(reviews),
        "history": [
            {"id": q.id, "title": titles.get(q.document_id, ""), "score": q.score, "created_at": q.created_at}
            for q in quizzes[:30]
        ],
    }
