import logging

from config_file import credentials_match, ensure_config, load_config
from tests.conftest import csrf_from, sign_in


def test_config_stores_bcrypt_hash_only(tmp_path):
    path = tmp_path / "config.json"
    ensure_config(path, rounds=4)
    text = path.read_text(encoding="utf-8")
    assert "monitor-demo" not in text
    config = load_config(path)
    assert config["username"] == "admin"
    assert credentials_match(config, "admin", "monitor-demo")
    assert not credentials_match(config, "admin", "other-password")
    assert not credentials_match(config, "other", "monitor-demo")


def test_valid_login(client):
    response = sign_in(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    page = client.get("/")
    assert page.status_code == 200
    assert b"Server list" in page.data


def test_invalid_login_stays_on_the_form(client, caplog):
    caplog.set_level(logging.DEBUG)
    page = client.get("/login")
    token = csrf_from(page.get_data(as_text=True))
    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "wrong-password-value",
            "csrf_token": token,
        },
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert body.count("Sign-in failed.") == 1
    assert "wrong-password-value" not in body
    assert "wrong-password-value" not in caplog.text
    assert "incorrect password" not in body.lower()
    follow = client.get("/")
    assert follow.status_code == 302
    assert follow.headers["Location"].endswith("/login")


def test_sign_out(client):
    sign_in(client)
    page = client.get("/")
    token = csrf_from(page.get_data(as_text=True))
    response = client.post("/logout", data={"csrf_token": token})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    again = client.get("/servers")
    assert again.status_code == 302
    assert again.headers["Location"].endswith("/login")


def test_signed_out_requests_redirect(client):
    for path in ("/", "/servers", "/servers/abc", "/api/servers", "/api/servers/abc"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_session_cookie_is_httponly_and_lax(client):
    response = client.get("/login")
    cookies = " ".join(response.headers.getlist("Set-Cookie"))
    assert "HttpOnly" in cookies
    assert "SameSite=Lax" in cookies
    assert "monitor-demo" not in cookies
