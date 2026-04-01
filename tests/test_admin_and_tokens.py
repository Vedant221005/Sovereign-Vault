from app.extensions import db
from app.models import User


def _promote_user_to_admin(username: str):
    user = User.query.filter_by(username=username).first()
    user.role = "admin"
    db.session.commit()


def test_refresh_token_flow(client, register_user, login_user, auth_header):
    register_user("refreshuser", "Password123")
    login = login_user("refreshuser", "Password123")
    assert login.status_code == 200

    refresh_token = login.get_json()["refresh_token"]
    refreshed = client.post("/refresh", headers=auth_header(refresh_token))
    assert refreshed.status_code == 200
    assert "access_token" in refreshed.get_json()


def test_logout_revokes_access_token(client, register_user, login_user, auth_header):
    register_user("logoutuser", "Password123")
    login = login_user("logoutuser", "Password123")
    access_token = login.get_json()["access_token"]

    logout = client.post("/logout", headers=auth_header(access_token))
    assert logout.status_code == 200

    files = client.get("/files", headers=auth_header(access_token))
    assert files.status_code == 401


def test_admin_can_manage_users(client, app, register_user, login_user, auth_header):
    register_user("boss", "Password123")
    register_user("worker", "Password123")

    with app.app_context():
        _promote_user_to_admin("boss")
        worker = User.query.filter_by(username="worker").first()
        worker.failed_attempts = 5
        db.session.commit()
        worker_id = worker.id

    admin_token = login_user("boss", "Password123").get_json()["access_token"]

    role_update = client.patch(
        f"/users/{worker_id}/role",
        headers=auth_header(admin_token),
        json={"role": "admin"},
    )
    assert role_update.status_code == 200

    unlock = client.post(f"/users/{worker_id}/unlock", headers=auth_header(admin_token))
    assert unlock.status_code == 200

    with app.app_context():
        worker = db.session.get(User, worker_id)
        assert worker.role == "admin"
        assert worker.failed_attempts == 0

    delete_resp = client.delete(f"/users/{worker_id}", headers=auth_header(admin_token))
    assert delete_resp.status_code == 200

    with app.app_context():
        worker = db.session.get(User, worker_id)
        assert worker is None
