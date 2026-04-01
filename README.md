# Secure File Storage with IAM - Full Project Guide
<img width="954" height="507" alt="1" src="https://github.com/user-attachments/assets/2665bde5-6bca-491b-8e8b-4772b4546e09" />
<img width="960" height="509" alt="2" src="https://github.com/user-attachments/assets/a0e1a79c-9171-4b59-a512-2b1be9edcb47" />
<img width="960" height="509" alt="3" src="https://github.com/user-attachments/assets/70c6ea01-f351-4230-9de7-0e4b9cd9215e" />
<img width="960" height="510" alt="4" src="https://github.com/user-attachments/assets/c7439b70-b794-4da2-aeac-2c01d305dbb3" />


## 1. Project Summary

This project is a Flask-based secure file storage system with identity and access management (IAM).

Core capabilities:
- User registration and login with password hashing
- JWT access and refresh token authentication
- Token revocation (blocklist) on logout
- Role-based access control (user/admin)
- Encrypted file upload and secure download
- Ownership and admin authorization checks
- Admin user management (role update, unlock, delete)
- Audit logging of security-relevant actions
- Browser-based frontend for user and admin workflows
- Automated tests for authentication, files, and admin/token flows

---

## 2. Tech Stack

Backend:
- Flask 3
- Flask-SQLAlchemy
- Flask-JWT-Extended
- Flask-Bcrypt
- Flask-Limiter
- cryptography (Fernet)
- psycopg3 (for PostgreSQL/Neon)

Frontend:
- Server-rendered HTML template
- Tailwind CSS via CDN
- Vanilla JavaScript

Testing:
- pytest

Dependencies are pinned in `requirements.txt`.

---

## 3. High-Level Architecture

### App Factory Pattern
- `app/__init__.py` exposes `create_app()`.
- Environment variables are loaded with `python-dotenv`.
- Flask extensions are initialized via `app/extensions.py`.
- Blueprints from `app/routes/` are registered.
- Database tables are created with `db.create_all()`.

### Extension Wiring
`app/extensions.py` defines singleton extension objects:
- `db` for SQLAlchemy
- `bcrypt` for password hashing
- `jwt` for JWT lifecycle
- `limiter` for request throttling

### Blueprints
- `auth_bp` in `app/routes/auth_routes.py`
- `admin_bp` in `app/routes/admin_routes.py`
- `file_bp` in `app/routes/file_routes.py`

### Data Models
Defined in `app/models/`:
- `User`
- `StoredFile`
- `AuditLog`
- `TokenBlocklist`

---

## 4. Database Schema and Model Responsibilities

### User (`users`)
Fields:
- `id` (PK)
- `username` (unique, indexed)
- `password` (bcrypt hash)
- `role` (`user` or `admin`)
- `failed_attempts` (used for account lockout)
- `created_at`

Behavior:
- `set_password(raw_password)` stores bcrypt hash
- `check_password(raw_password)` verifies hash
- `is_locked` property returns `failed_attempts >= 5`

### StoredFile (`files`)
Fields:
- `id` (PK)
- `filename` (original safe name)
- `owner_id` (FK -> users.id)
- `encrypted_path` (filesystem path to encrypted blob)
- `created_at`
- `last_downloaded_at`

Behavior:
- Belongs to a `User` through `owner` relationship

### AuditLog (`logs`)
Fields:
- `id` (PK)
- `user_id` (nullable FK -> users.id)
- `action` (string event code/message)
- `timestamp`

### TokenBlocklist (`token_blocklist`)
Fields:
- `id` (PK)
- `jti` (JWT ID, unique)
- `token_type` (`access` or `refresh`)
- `created_at`

Purpose:
- Any token whose `jti` exists in this table is treated as revoked.

---

## 5. Security Model

### Authentication
- Login returns:
  - `access_token`
  - `refresh_token`
- Access token includes role and username claims.

### Authorization
- Route-level JWT checks via `@jwt_required()`.
- Role checks via middleware decorator `role_required()` in `app/middleware/authz.py`.
- File operations enforce owner-or-admin policy.

### Token Revocation
- `/logout` stores token `jti` in `token_blocklist`.
- JWT callback (`token_in_blocklist_loader`) rejects revoked tokens.

### Password Security
- Passwords are hashed with bcrypt (never stored in plaintext).
- Password validation requires at least 8 chars with letters and numbers.

### Brute-force Protection
- `/login` is rate-limited to `10 per minute`.
- User accounts lock after 5 failed password attempts.

### Encryption at Rest
- File content is encrypted with Fernet before writing to disk.
- Decryption happens only during authorized download.

### Upload Validation
Upload path validates:
- file key exists in multipart form
- non-empty filename
- safe filename (`secure_filename`)
- extension allowlist
- MIME allowlist
- non-empty content
- max file size

---

## 6. Runtime Configuration

Configured in `app/config.py` and overridden in `create_app()` from environment values.

Key env vars:
- `DATABASE_URL`
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `JWT_ACCESS_TOKEN_MINUTES`
- `JWT_REFRESH_TOKEN_DAYS`
- `FERNET_KEY`
- `ENCRYPTED_STORAGE_DIR`
- `MAX_FILE_SIZE`
- `ALLOWED_FILE_EXTENSIONS`
- `ALLOWED_MIME_TYPES`
- `RATELIMIT_STORAGE_URI`
- `RATELIMIT_ENABLED`
- `ADMIN_USERNAME` (optional default admin bootstrap)
- `ADMIN_PASSWORD` (required to create default admin if missing)
- `DB_POOL_RECYCLE_SECONDS` (for Postgres pooled connection recycling)

### Postgres/Neon Connection Resilience
In `app/__init__.py` for PostgreSQL URLs:
- `pool_pre_ping=True`
- `pool_recycle` configurable (default 300 seconds)

The JWT blocklist DB lookup also has one retry path after disposing stale engine connections.

---

## 7. API Endpoints

### Public/Auth
- `POST /register`
- `POST /login`
- `POST /refresh` (requires refresh token)
- `POST /logout` (requires JWT)

### User/Admin Shared File Operations (JWT required)
- `GET /files`
- `POST /upload`
- `GET /download/<file_id>`
- `DELETE /file/<file_id>`

### Admin-only User Management
- `GET /users`
- `PATCH /users/<user_id>/role`
- `POST /users/<user_id>/unlock`
- `DELETE /users/<user_id>`

### Utility Routes
- `GET /` serves frontend (`index.html`)
- `GET /health` returns `{ "status": "ok" }`

---

## 8. Request/Flow Walkthrough

### Registration Flow
1. Client sends username/password to `/register`.
2. Username/password format validated.
3. User uniqueness checked.
4. Password hashed and saved.
5. Audit event written.

### Login Flow
1. Client sends credentials to `/login`.
2. User fetched and lock state checked.
3. Password verified.
4. Failed attempts updated on failure.
5. On success: attempts reset and both tokens issued.
6. Audit event written.

### Refresh Flow
1. Client sends refresh token to `/refresh`.
2. User is resolved by token identity.
3. New access token generated with current role/username.

### Logout Flow
1. JWT `jti` extracted.
2. `jti` inserted into blocklist (if not already present).
3. Future requests with that token are rejected.

### File Upload Flow
1. Authenticated request with multipart file.
2. Extension, MIME, and size validations.
3. File bytes encrypted via Fernet.
4. Encrypted bytes written under storage directory.
5. Metadata persisted in DB.
6. Audit event written.

### File Download Flow
1. Authenticated request with `file_id`.
2. Ownership/admin authorization check.
3. Encrypted blob read from storage path.
4. Decrypt in memory.
5. Update `last_downloaded_at`.
6. Stream file as attachment.

---

## 9. Frontend Behavior

Frontend files:
- `app/templates/index.html`
- `app/static/app.js`
- `app/static/styles.css`

### UI Features
- Auth screen for login and optional register panel
- Session bar with username and role
- User dashboard for upload/list/download/delete own files
- Admin dashboard with tabs:
  - users management
  - all-files overview

### Session Handling in Browser
`app/static/app.js` stores in localStorage:
- `access_token`
- `refresh_token`
- `username`
- `role`

On API 401 responses (except auth endpoints), frontend attempts `/refresh` once and retries original request.

### Frontend/Backend ID Handling
- IDs are still used internally by frontend for route calls (download/delete/role/unlock).
- ID columns were removed from visible frontend tables.

---

## 10. Storage Layout

Typical layout:
- `storage/encrypted/` contains encrypted binary blobs
- DB row in `files` maps original filename to encrypted file path

Encrypted data is opaque at rest and only decrypted for authorized download requests.

---

## 11. Error Handling

Global handlers in `app/__init__.py` include:
- 400 -> `Bad request`
- 404 -> `Not found`
- 413 -> `File exceeds allowed size`
- 429 -> `Too many requests`
- 500 -> `Internal server error`

Note:
- Route-level validation often returns more specific messages before global handlers apply.

---

## 12. Testing Strategy

Test suite in `tests/` covers major flows.

### Test Setup (`tests/conftest.py`)
- Uses temp SQLite database per test session
- Sets test secrets and Fernet key
- Uses temp encrypted storage path
- Disables rate limiting for deterministic tests

### Auth Tests (`tests/test_auth.py`)
- Register/login success
- Account lock after five failed attempts

### File Tests (`tests/test_files.py`)
- User upload/list own files
- Non-owner download forbidden
- Admin can access all files

### Admin and Token Tests (`tests/test_admin_and_tokens.py`)
- Refresh token flow
- Logout revokes access token
- Admin role update, unlock, and delete user

---

## 13. How to Run

From project root:

1. Create and activate virtual environment
2. Install dependencies
3. Configure `.env`
4. Start app:

```bash
python run.py
```

App defaults:
- URL: `http://127.0.0.1:5000`
- Host/port from `run.py`: `0.0.0.0:5000`

Run tests:

```bash
pytest -q
```

---

## 14. Important Operational Notes

- Ensure `FERNET_KEY` is configured, otherwise encryption/decryption fails.
- For production, move limiter storage from in-memory to a shared backend (for example Redis).
- Keep `.env` out of source control.
- If using Neon/PostgreSQL and seeing intermittent SSL disconnects, tune `DB_POOL_RECYCLE_SECONDS` lower (for example 120).
- `create_app()` includes a compatibility migration for `files.last_downloaded_at` if missing.

---

## 15. Directory Purpose Reference

- `app/config.py`: base configuration defaults
- `app/extensions.py`: Flask extension singletons
- `app/middleware/`: custom request authorization decorators
- `app/models/`: SQLAlchemy models
- `app/routes/`: API endpoints grouped by domain
- `app/services/`: encryption and audit logging services
- `app/utils/`: input validators
- `app/templates/`: HTML template(s)
- `app/static/`: JS and CSS assets
- `storage/encrypted/`: encrypted file blobs
- `instance/`: local instance artifacts (if used)
- `tests/`: pytest suite
- `run.py`: application entrypoint

