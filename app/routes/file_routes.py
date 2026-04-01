import os
import uuid
from datetime import timezone
from io import BytesIO

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import StoredFile
from app.services.crypto_service import decrypt_bytes, encrypt_bytes, get_storage_dir
from app.services.log_service import log_action

file_bp = Blueprint("file", __name__)


def _to_utc_iso(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in allowed_extensions


@file_bp.get("/files")
@jwt_required()
def list_files():
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")

    if role == "admin":
        files = StoredFile.query.order_by(StoredFile.id.asc()).all()
    else:
        files = StoredFile.query.filter_by(owner_id=user_id).order_by(StoredFile.id.asc()).all()

    return (
        jsonify(
            [
                {
                    "id": file.id,
                    "filename": file.filename,
                    "owner_id": file.owner_id,
                    "owner_username": file.owner.username if file.owner else "unknown",
                    "encrypted_string": file.encrypted_path,
                    "created_at": _to_utc_iso(file.created_at),
                    "last_downloaded_at": _to_utc_iso(file.last_downloaded_at),
                }
                for file in files
            ]
        ),
        200,
    )


@file_bp.post("/upload")
@jwt_required()
def upload_file():
    user_id = int(get_jwt_identity())
    allowed_extensions = set(current_app.config.get("ALLOWED_FILE_EXTENSIONS", set()))
    allowed_mime_types = set(current_app.config.get("ALLOWED_MIME_TYPES", set()))
    max_size = int(current_app.config.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))

    if "file" not in request.files:
        return jsonify({"error": "File is required"}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "Invalid file"}), 400

    safe_name = secure_filename(uploaded_file.filename)
    if not safe_name:
        return jsonify({"error": "Invalid filename"}), 400

    if not _is_allowed_file(safe_name, allowed_extensions):
        return jsonify({"error": "Unsupported file type"}), 400

    content_type = (uploaded_file.content_type or "").lower()
    if content_type and content_type not in allowed_mime_types:
        return jsonify({"error": "Unsupported mime type"}), 400

    try:
        raw_data = uploaded_file.read()
        if not raw_data:
            return jsonify({"error": "File is empty"}), 400
        if len(raw_data) > max_size:
            return jsonify({"error": "File exceeds allowed size"}), 400
        encrypted_data = encrypt_bytes(raw_data)
    except RuntimeError:
        return jsonify({"error": "Encryption service unavailable"}), 500

    unique_name = f"{uuid.uuid4().hex}.bin"
    storage_file = get_storage_dir() / unique_name

    with open(storage_file, "wb") as fh:
        fh.write(encrypted_data)

    stored = StoredFile(
        filename=safe_name,
        owner_id=user_id,
        encrypted_path=str(storage_file),
    )

    db.session.add(stored)
    db.session.commit()

    log_action(user_id, f"file_upload_success:file_id={stored.id}")

    return jsonify({"message": "File uploaded securely", "file_id": stored.id}), 201


@file_bp.get("/download/<int:file_id>")
@jwt_required()
def download_file(file_id: int):
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")
    file_record = db.session.get(StoredFile, file_id)

    if not file_record:
        return jsonify({"error": "File not found"}), 404

    if role != "admin" and file_record.owner_id != user_id:
        log_action(user_id, f"file_download_forbidden:file_id={file_id}")
        return jsonify({"error": "Forbidden"}), 403

    if not os.path.exists(file_record.encrypted_path):
        return jsonify({"error": "Stored file is missing"}), 404

    with open(file_record.encrypted_path, "rb") as fh:
        encrypted_data = fh.read()

    try:
        decrypted_data = decrypt_bytes(encrypted_data)
    except RuntimeError:
        return jsonify({"error": "Encryption service unavailable"}), 500
    except Exception:
        return jsonify({"error": "Unable to decrypt file"}), 500

    from datetime import datetime, timezone

    file_record.last_downloaded_at = datetime.now(timezone.utc)
    db.session.commit()

    log_action(user_id, f"file_download_success:file_id={file_id}")

    return send_file(
        BytesIO(decrypted_data),
        as_attachment=True,
        download_name=file_record.filename,
        mimetype="application/octet-stream",
    )


@file_bp.delete("/file/<int:file_id>")
@jwt_required()
def delete_file(file_id: int):
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")
    file_record = db.session.get(StoredFile, file_id)

    if not file_record:
        return jsonify({"error": "File not found"}), 404

    if role != "admin" and file_record.owner_id != user_id:
        log_action(user_id, f"file_delete_forbidden:file_id={file_id}")
        return jsonify({"error": "Forbidden"}), 403

    if os.path.exists(file_record.encrypted_path):
        os.remove(file_record.encrypted_path)

    db.session.delete(file_record)
    db.session.commit()

    log_action(user_id, f"file_delete_success:file_id={file_id}")

    return jsonify({"message": "File deleted"}), 200
