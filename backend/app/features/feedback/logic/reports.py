from sqlalchemy.orm import Session

from app.features.feedback.models import FeedbackReport


def get_reports(db: Session, user_id: int, limit: int = 20):
    return (db.query(FeedbackReport)
            .filter(FeedbackReport.user_id == user_id)
            .order_by(FeedbackReport.created_at.desc())
            .limit(limit).all())


def get_report(db: Session, report_id: int, user_id: int):
    r = db.query(FeedbackReport).filter(
        FeedbackReport.id == report_id, FeedbackReport.user_id == user_id).first()
    if not r:
        raise ValueError("Report not found.")
    return r


def mark_read(db: Session, report_id: int, user_id: int):
    r = db.query(FeedbackReport).filter(
        FeedbackReport.id == report_id, FeedbackReport.user_id == user_id).first()
    if r:
        r.is_read = True
        db.commit()


def unread_count(db: Session, user_id: int) -> int:
    return db.query(FeedbackReport).filter(
        FeedbackReport.user_id == user_id, FeedbackReport.is_read.is_(False)).count()
