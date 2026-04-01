from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.middleware.authz import role_required
from app.models import User
from app.services.log_service import log_action

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/users")
@role_required("admin")
def list_users():
    users = User.query.order_by(User.id.asc()).all()
    return (
        jsonify(
            [
                {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "failed_attempts": user.failed_attempts,
                }
                for user in users
            ]
        ),
        200,
    )


@admin_bp.patch("/users/<int:user_id>/role")
@role_required("admin")
def update_user_role(user_id: int):
    payload = request.get_json(silent=True) or {}
    role = (payload.get("role") or "").strip().lower()
    if role not in {"admin", "user"}:
        return jsonify({"error": "Role must be admin or user"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.role = role
    db.session.commit()

    actor_id = int(get_jwt_identity())
    log_action(actor_id, f"admin_update_role:user_id={user_id},role={role}")

    return jsonify({"message": "User role updated"}), 200


@admin_bp.post("/users/<int:user_id>/unlock")
@role_required("admin")
def unlock_user(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.failed_attempts = 0
    db.session.commit()

    actor_id = int(get_jwt_identity())
    log_action(actor_id, f"admin_unlock_user:user_id={user_id}")

    return jsonify({"message": "User unlocked"}), 200


@admin_bp.delete("/users/<int:user_id>")
@role_required("admin")
def delete_user(user_id: int):
    actor_id = int(get_jwt_identity())
    if actor_id == user_id:
        return jsonify({"error": "Admin cannot delete own account"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()

    log_action(actor_id, f"admin_delete_user:user_id={user_id}")

    return jsonify({"message": "User deleted"}), 200
