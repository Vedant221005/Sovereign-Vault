from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt, get_jwt_identity, jwt_required

from app.extensions import db, limiter
from app.models import TokenBlocklist, User
from app.services.log_service import log_action
from app.utils.validators import validate_password, validate_username

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not validate_username(username):
        return jsonify({"error": "Invalid username format"}), 400
    if not validate_password(password):
        return jsonify({"error": "Password must be at least 8 characters with letters and numbers"}), 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"error": "Username already exists"}), 409

    user = User(username=username, role="user")
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    log_action(user.id, "register_success")

    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        log_action(None, f"login_failed_unknown_user:{username}")
        return jsonify({"error": "Invalid credentials"}), 401

    if user.is_locked:
        log_action(user.id, "login_blocked_locked_account")
        return jsonify({"error": "Account is locked after 5 failed attempts"}), 423

    if not user.check_password(password):
        user.failed_attempts += 1
        db.session.commit()
        log_action(user.id, "login_failed_bad_password")

        if user.is_locked:
            return jsonify({"error": "Account is locked after 5 failed attempts"}), 423

        return jsonify({"error": "Invalid credentials"}), 401

    user.failed_attempts = 0
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
    )
    refresh_token = create_refresh_token(identity=str(user.id))

    log_action(user.id, "login_success")

    return jsonify({"access_token": token, "refresh_token": refresh_token}), 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh_access_token():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({"error": "User not found"}), 404

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "username": user.username},
    )

    log_action(user.id, "token_refresh_success")

    return jsonify({"access_token": access_token}), 200


@auth_bp.post("/logout")
@jwt_required()
def logout():
    user_id = int(get_jwt_identity())
    jwt_data = get_jwt()
    jti = jwt_data.get("jti")
    token_type = jwt_data.get("type", "access")

    if not jti:
        return jsonify({"error": "Invalid token"}), 401

    already_revoked = db.session.query(TokenBlocklist.id).filter_by(jti=jti).first()
    if not already_revoked:
        db.session.add(TokenBlocklist(jti=jti, token_type=token_type))
        db.session.commit()

    log_action(user_id, f"logout_success:{token_type}")

    return jsonify({"message": "Token revoked"}), 200
