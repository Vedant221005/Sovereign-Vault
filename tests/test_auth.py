def test_register_and_login_success(client, register_user, login_user):
    register = register_user("alice", "Password123")
    assert register.status_code == 201

    login = login_user("alice", "Password123")
    assert login.status_code == 200
    assert "access_token" in login.get_json()
    assert "refresh_token" in login.get_json()


def test_account_locks_after_five_failed_attempts(client, register_user, login_user):
    register_user("bob", "Password123")

    for _ in range(5):
        response = login_user("bob", "WrongPass9")

    assert response.status_code == 423
    assert "locked" in response.get_json()["error"].lower()

    blocked_login = login_user("bob", "Password123")
    assert blocked_login.status_code == 423
