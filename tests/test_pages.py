from pathlib import Path

from inventory import add_server
from ssh_client import Unreachable
from tests.conftest import csrf_from, sign_in
from tests.samples import outputs


SECRET = "pw-do-not-show"
KEY_PATH = "/keys/do-not-show"


def _add(app, name, host, password=SECRET, key_path=""):
    return add_server(
        app.config["INVENTORY_PATH"],
        {
            "name": name,
            "host": host,
            "port": 22,
            "username": "monitor",
            "password": password,
            "key_path": key_path,
        },
    )


def _post_server(client, token, **fields):
    payload = {
        "csrf_token": token,
        "name": fields.get("name", "web"),
        "host": fields.get("host", "192.0.2.20"),
        "port": fields.get("port", "22"),
        "username": fields.get("username", "monitor"),
        "password": fields.get("password", SECRET),
        "key_path": fields.get("key_path", ""),
    }
    return client.post("/servers", data=payload)


def test_add_accepts_password_or_key_and_rejects_gaps(client):
    sign_in(client)
    page = client.get("/servers")
    token = csrf_from(page.get_data(as_text=True))

    missing_name = _post_server(client, token, name="", password=SECRET)
    body = missing_name.get_data(as_text=True)
    assert "Display name is required." in body
    assert SECRET not in body

    token = csrf_from(body)
    missing_host = _post_server(client, token, host="  ")
    assert "Hostname or IP is required." in missing_host.get_data(as_text=True)

    token = csrf_from(missing_host.get_data(as_text=True))
    missing_user = _post_server(client, token, username="")
    assert "SSH username is required." in missing_user.get_data(as_text=True)

    token = csrf_from(missing_user.get_data(as_text=True))
    neither = _post_server(client, token, password="", key_path="")
    assert "Enter a password or a private key path." in neither.get_data(as_text=True)

    token = csrf_from(neither.get_data(as_text=True))
    accepted = _post_server(client, token, name="alpha", password=SECRET, key_path="")
    assert accepted.status_code == 302
    saved = client.get("/servers")
    saved_body = saved.get_data(as_text=True)
    assert "alpha" in saved_body
    assert SECRET not in saved_body
    assert "Password" in saved_body

    token = csrf_from(saved_body)
    with_key = _post_server(
        client,
        token,
        name="beta",
        password="",
        key_path=KEY_PATH,
    )
    assert with_key.status_code == 302
    listed = client.get("/servers").get_data(as_text=True)
    assert "beta" in listed
    assert KEY_PATH not in listed


def test_remove_drops_one_server_without_ssh(make_app):
    class Guard:
        def read(self, **_kwargs):
            raise AssertionError("remove must not open SSH")

    application = make_app(Guard())
    client = application.test_client()
    first = _add(application, "alpha", "192.0.2.21")
    second = _add(application, "beta", "192.0.2.22")
    sign_in(client)
    page = client.get("/servers")
    token = csrf_from(page.get_data(as_text=True))
    response = client.post(
        f"/servers/{first['id']}/remove",
        data={"csrf_token": token},
    )
    assert response.status_code == 302
    body = client.get("/servers").get_data(as_text=True)
    assert "alpha" not in body
    assert "beta" in body
    assert second["id"] in body


def test_remove_requires_a_session_and_csrf(make_app):
    application = make_app()
    first = _add(application, "alpha", "192.0.2.23")
    outsider = application.test_client()
    blocked = outsider.post(f"/servers/{first['id']}/remove", data={"csrf_token": "nope"})
    assert blocked.status_code == 302
    assert blocked.headers["Location"].endswith("/login")

    client = application.test_client()
    sign_in(client)
    rejected = client.post(f"/servers/{first['id']}/remove", data={"csrf_token": "nope"})
    assert rejected.status_code == 400
    still_there = client.get("/servers").get_data(as_text=True)
    assert "alpha" in still_there


def test_list_links_two_servers_and_hides_secrets(app, client):
    first = _add(app, "alpha", "192.0.2.31", password=SECRET, key_path="")
    second = _add(app, "beta", "192.0.2.32", password="", key_path=KEY_PATH)
    sign_in(client)
    body = client.get("/").get_data(as_text=True)
    assert f'/servers/{first["id"]}' in body
    assert f'/servers/{second["id"]}' in body
    assert "alpha" in body
    assert "beta" in body
    assert "192.0.2.31" in body
    assert SECRET not in body
    assert KEY_PATH not in body


def test_list_shows_ok_and_failed_servers(make_app):
    class HostCollector:
        def read(self, *, host, **_kwargs):
            if host == "down.example":
                raise RuntimeError("password=should-not-leak")
            return outputs()

    application = make_app(HostCollector())
    _add(application, "good", "ok.example")
    _add(application, "bad", "down.example")
    client = application.test_client()
    sign_in(client)
    body = client.get("/").get_data(as_text=True)
    assert "good" in body
    assert "bad" in body
    assert ">ok<" in body
    assert ">unreachable<" in body
    assert "50.0%" in body
    assert "25.0%" in body
    assert "should-not-leak" not in body


def test_detail_renders_each_block(app, client):
    server = _add(app, "web", "192.0.2.40")
    sign_in(client)
    body = client.get(f"/servers/{server['id']}").get_data(as_text=True)
    assert "web" in body
    assert "192.0.2.40" in body
    assert ">ok<" in body
    assert "50.0%" in body
    assert "25.0%" in body
    assert "eth0" in body
    assert "4.0 KiB" in body
    assert "2.0 KiB" in body
    assert "<td>lo</td>" not in body
    assert "tcp" in body
    assert "sshd" in body
    assert "udp" in body
    assert "53" in body
    assert SECRET not in body
    for control in ("Restart", "Kill", "Shell"):
        assert control not in body


def test_empty_output_and_down_host_show_messages(make_app, clock):
    class Flip:
        def __init__(self):
            self.calls = 0

        def read(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return {
                    "stat_first": "",
                    "stat_second": "",
                    "meminfo": "",
                    "netdev": "",
                    "ports": "",
                }
            raise Unreachable()

    application = make_app(Flip())
    server = _add(application, "web", "192.0.2.41")
    client = application.test_client()
    sign_in(client)
    first = client.get(f"/servers/{server['id']}").get_data(as_text=True)
    assert "No CPU data." in first
    assert "No memory data." in first
    assert "No network data." in first
    assert "No listening ports." in first
    clock.advance(15)
    second = client.get(f"/servers/{server['id']}").get_data(as_text=True)
    assert "unreachable" in second
    assert "The host could not be reached." in second


def test_json_requires_a_session_and_matches_the_page(app, client):
    server = _add(app, "web", "192.0.2.50")
    signed_out = app.test_client()
    for path in ("/api/servers", f"/api/servers/{server['id']}"):
        blocked = signed_out.get(path)
        assert blocked.status_code == 302
        assert blocked.headers["Location"].endswith("/login")

    sign_in(client)
    page = client.get("/")
    listing = client.get("/api/servers")
    payload = listing.get_json()
    assert listing.status_code == 200
    row = payload["servers"][0]
    assert set(row) == {
        "id",
        "name",
        "host",
        "status",
        "message",
        "cpu_percent",
        "cpu_text",
        "memory_percent",
        "memory_text",
        "last_success",
        "last_success_text",
    }
    html = page.get_data(as_text=True)
    assert row["cpu_text"] in html
    assert row["memory_text"] in html
    assert row["status"] in html
    raw = listing.get_data(as_text=True)
    assert SECRET not in raw
    assert "key_path" not in raw
    assert "password" not in raw

    detail_page = client.get(f"/servers/{server['id']}")
    detail = client.get(f"/api/servers/{server['id']}")
    server_payload = detail.get_json()["server"]
    detail_html = detail_page.get_data(as_text=True)
    assert server_payload["cpu_text"] in detail_html
    assert server_payload["memory_text"] in detail_html
    assert server_payload["network"][0]["name"] in detail_html
    assert server_payload["ports"][0]["process"] in detail_html
    detail_raw = detail.get_data(as_text=True)
    assert SECRET not in detail_raw
    assert "key_path" not in detail_raw


def test_reload_shows_the_sample_and_script_polls_every_15_seconds(app, client):
    server = _add(app, "web", "192.0.2.60")
    sign_in(client)
    first = client.get(f"/servers/{server['id']}").get_data(as_text=True)
    assert "50.0%" in first
    assert "refresh.js" in first
    assert "Rates appear after two samples about 15 seconds apart." in first
    script = Path(app.root_path) / "static" / "refresh.js"
    assert "15000" in script.read_text(encoding="utf-8")


def test_second_sample_shows_a_network_rate(make_app, clock):
    class Growing:
        def __init__(self):
            self.calls = 0

        def read(self, **_kwargs):
            self.calls += 1
            return outputs(rx=15360 * self.calls, tx=15360 * self.calls)

    application = make_app(Growing())
    server = _add(application, "web", "192.0.2.61")
    client = application.test_client()
    sign_in(client)
    first = client.get(f"/servers/{server['id']}").get_data(as_text=True)
    assert "—" in first
    clock.advance(15)
    second = client.get(f"/servers/{server['id']}").get_data(as_text=True)
    assert "1.0 KiB/s" in second


def test_failed_poll_keeps_the_last_success_on_the_page(make_app, clock):
    class Flip:
        def __init__(self):
            self.calls = 0

        def read(self, **_kwargs):
            self.calls += 1
            if self.calls > 1:
                raise Unreachable()
            return outputs()

    application = make_app(Flip())
    server = _add(application, "web", "192.0.2.62")
    client = application.test_client()
    sign_in(client)
    first = client.get("/").get_data(as_text=True)
    assert ">ok<" in first
    clock.advance(15)
    second = client.get("/").get_data(as_text=True)
    assert ">unreachable<" in second
    assert "50.0%" in second
    assert "25.0%" in second
    assert "The host could not be reached." not in second or "unreachable" in second
