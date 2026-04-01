import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-env")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-jwt-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///secure_storage.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_FILE_SIZE", 2 * 1024 * 1024))
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    ALLOWED_FILE_EXTENSIONS = {
        ext.strip().lower()
        for ext in os.getenv("ALLOWED_FILE_EXTENSIONS", "txt,pdf,doc,docx").split(",")
        if ext.strip()
    }
    ALLOWED_MIME_TYPES = {
        mime.strip().lower()
        for mime in os.getenv(
            "ALLOWED_MIME_TYPES",
            "text/plain,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ).split(",")
        if mime.strip()
    }
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_DAYS", "7")))
