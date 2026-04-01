from datetime import datetime, timezone

from app.extensions import db


class StoredFile(db.Model):
    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    encrypted_path = db.Column(db.String(512), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_downloaded_at = db.Column(db.DateTime, nullable=True)

    owner = db.relationship("User", back_populates="files")
