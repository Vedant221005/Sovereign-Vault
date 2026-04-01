import os

from dotenv import load_dotenv
from flask import Flask, current_app, jsonify, render_template
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.config import Config
from app.extensions import bcrypt, db, jwt, limiter
from app.models import TokenBlocklist
from app.routes import admin_bp, auth_bp, file_bp


def create_app() -> Flask:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", Config.SQLALCHEMY_DATABASE_URI)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    engine_options = {}
    if database_url.startswith("postgresql"):
        engine_options = {
            # Prevent stale SSL pooled connections from causing request-time failures.
            "pool_pre_ping": True,
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", "300")),
        }

    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", app.config["SECRET_KEY"]),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", app.config["JWT_SECRET_KEY"]),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_ENGINE_OPTIONS=engine_options,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_FILE_SIZE", str(app.config["MAX_CONTENT_LENGTH"]))),
        RATELIMIT_STORAGE_URI=os.getenv("RATELIMIT_STORAGE_URI", app.config["RATELIMIT_STORAGE_URI"]),
        RATELIMIT_ENABLED=os.getenv("RATELIMIT_ENABLED", "true").lower() == "true",
        ALLOWED_FILE_EXTENSIONS={
            ext.strip().lower()
            for ext in os.getenv("ALLOWED_FILE_EXTENSIONS", "txt,pdf,doc,docx").split(",")
            if ext.strip()
        },
        ALLOWED_MIME_TYPES={
            mime.strip().lower()
            for mime in os.getenv(
                "ALLOWED_MIME_TYPES",
                "text/plain,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ).split(",")
            if mime.strip()
        },
        JWT_ACCESS_TOKEN_EXPIRES=Config.JWT_ACCESS_TOKEN_EXPIRES,
        JWT_REFRESH_TOKEN_EXPIRES=Config.JWT_REFRESH_TOKEN_EXPIRES,
    )

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(file_bp)

    @app.get("/")
    def index_page():
        return render_template("index.html")

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"}), 200

    @jwt.token_in_blocklist_loader
    def is_token_revoked(_jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        if not jti:
            return True
        try:
            return db.session.query(TokenBlocklist.id).filter_by(jti=jti).first() is not None
        except OperationalError:
            # Retry once after resetting pool/session for transient dropped SSL connections.
            db.session.remove()
            db.engine.dispose()
            try:
                return db.session.query(TokenBlocklist.id).filter_by(jti=jti).first() is not None
            except OperationalError:
                current_app.logger.exception("Token blocklist check failed after retry")
                # Fail closed if blocklist check cannot be performed.
                return True

    @app.errorhandler(400)
    def handle_bad_request(_err):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(404)
    def handle_not_found(_err):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(413)
    def handle_payload_too_large(_err):
        return jsonify({"error": "File exceeds allowed size"}), 413

    @app.errorhandler(429)
    def handle_rate_limited(_err):
        return jsonify({"error": "Too many requests"}), 429

    @app.errorhandler(500)
    def handle_server_error(_err):
        return jsonify({"error": "Internal server error"}), 500

    with app.app_context():
        db.create_all()
        _ensure_schema_compatibility()
        _ensure_default_admin()

    return app


def _ensure_default_admin() -> None:
    from app.models import User

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD")

    admin = User.query.filter_by(username=admin_username).first()
    if admin:
        return

    if not admin_password:
        return

    admin = User(username=admin_username, role="admin")
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.commit()


def _ensure_schema_compatibility() -> None:
    inspector = inspect(db.engine)
    file_columns = {column["name"] for column in inspector.get_columns("files")}
    if "last_downloaded_at" not in file_columns:
        db.session.execute(text("ALTER TABLE files ADD COLUMN last_downloaded_at TIMESTAMP NULL"))
        db.session.commit()
