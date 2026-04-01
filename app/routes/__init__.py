from app.routes.admin_routes import admin_bp
from app.routes.auth_routes import auth_bp
from app.routes.file_routes import file_bp

__all__ = ["auth_bp", "admin_bp", "file_bp"]
