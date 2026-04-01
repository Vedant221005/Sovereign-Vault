from app.extensions import db
from app.models import AuditLog


def log_action(user_id: int | None, action: str) -> None:
    log_entry = AuditLog(user_id=user_id, action=action)
    db.session.add(log_entry)
    db.session.commit()
