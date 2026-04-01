from io import BytesIO

from app.extensions import db
from app.models import User


def _promote_user_to_admin(username: str):
    user = User.query.filter_by(username=username).first()
    user.role = "admin"
    db.session.commit()


def _upload_sample(client, token: str, auth_header):
    return client.post(
        "/upload",
        headers=auth_header(token),
        data={"file": (BytesIO(b"hello secure world"), "note.txt", "text/plain")},
        content_type="multipart/form-data",
    )


def test_user_can_upload_and_list_own_files(client, app, register_user, login_user, auth_header):
    register_user("charlie", "Password123")
    token = login_user("charlie", "Password123").get_json()["access_token"]

    upload = _upload_sample(client, token, auth_header)
    assert upload.status_code == 201

    listed = client.get("/files", headers=auth_header(token))
    assert listed.status_code == 200
    payload = listed.get_json()
    assert len(payload) == 1
    assert payload[0]["filename"] == "note.txt"


def test_forbidden_download_for_non_owner(client, app, register_user, login_user, auth_header):
    register_user("owner", "Password123")
    owner_token = login_user("owner", "Password123").get_json()["access_token"]
    upload = _upload_sample(client, owner_token, auth_header)
    file_id = upload.get_json()["file_id"]

    register_user("otheruser", "Password123")
    other_token = login_user("otheruser", "Password123").get_json()["access_token"]

    forbidden = client.get(f"/download/{file_id}", headers=auth_header(other_token))
    assert forbidden.status_code == 403


def test_admin_can_access_all_files(client, app, register_user, login_user, auth_header):
    register_user("admin1", "Password123")
    with app.app_context():
        _promote_user_to_admin("admin1")

    admin_token = login_user("admin1", "Password123").get_json()["access_token"]

    register_user("owner2", "Password123")
    owner_token = login_user("owner2", "Password123").get_json()["access_token"]
    upload = _upload_sample(client, owner_token, auth_header)
    file_id = upload.get_json()["file_id"]

    downloaded = client.get(f"/download/{file_id}", headers=auth_header(admin_token))
    assert downloaded.status_code == 200
    assert downloaded.data == b"hello secure world"
