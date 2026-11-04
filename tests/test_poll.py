import threading
import time

from poller import refresh_servers, poll_server
from ssh_client import AuthFailed, Unreachable
from tests.samples import outputs


class Scripted:
    def __init__(self, exc=None, marker=None):
        self.exc = exc
        self.marker = marker

    def read(self, **_kwargs):
        if self.exc is not None:
            raise self.exc
        return outputs()


def _server(name="web", host="192.0.2.10"):
    return {
        "id": "server-1",
        "name": name,
        "host": host,
        "port": 22,
        "username": "monitor",
        "password": "stored-secret",
        "key_path": "",
    }


def test_poll_ok_unreachable_and_auth_failed():
    server = _server()
    ok = poll_server(server, Scripted(), None, now=1_700_000_000)
    assert ok["status"] == "ok"
    assert ok["cpu_percent"] == 50.0
    assert ok["last_success"]
    assert "stored-secret" not in str(ok["message"])

    denied = poll_server(server, Scripted(exc=AuthFailed()), ok, now=1_700_000_100)
    assert denied["status"] == "auth failed"
    assert denied["message"] == "Authentication failed."
    assert denied["last_success"] == ok["last_success"]
    assert denied["cpu_percent"] == 50.0

    down = poll_server(
        server,
        Scripted(exc=RuntimeError("password=should-not-leak")),
        ok,
        now=1_700_000_200,
    )
    assert down["status"] == "unreachable"
    assert down["message"] == "The host could not be reached."
    assert down["last_success"] == ok["last_success"]
    assert "should-not-leak" not in str(down)

    timed_out = poll_server(server, Scripted(exc=Unreachable()), None, now=1_700_000_300)
    assert timed_out["status"] == "unreachable"
    assert timed_out["last_success"] is None


def test_network_rate_uses_the_previous_sample():
    server = _server()

    class Growing:
        def __init__(self):
            self.calls = 0

        def read(self, **_kwargs):
            self.calls += 1
            return outputs(rx=1000 * self.calls, tx=500 * self.calls)

    collector = Growing()
    first = poll_server(server, collector, None, now=1000)
    assert first["network"][0]["rx_rate"] is None
    second = poll_server(server, collector, first, now=1015)
    assert second["network"][0]["rx_rate"] == round(1000 / 15, 1)
    assert second["network"][0]["tx_rate"] == round(500 / 15, 1)


def test_a_failed_host_does_not_stop_the_other():
    peak = {"value": 0, "active": 0}
    lock = threading.Lock()

    class Collector:
        def read(self, *, host, **_kwargs):
            with lock:
                peak["active"] += 1
                peak["value"] = max(peak["value"], peak["active"])
            try:
                time.sleep(0.4)
                if host == "down.example":
                    raise RuntimeError("password=should-not-leak")
                return outputs()
            finally:
                with lock:
                    peak["active"] -= 1

    servers = [
        _server(name="good", host="ok.example"),
        _server(name="bad", host="down.example"),
    ]
    servers[1]["id"] = "server-2"
    rows = refresh_servers(servers, Collector(), {}, now=1_700_000_000)
    by_host = {row["host"]: row for row in rows}
    assert by_host["ok.example"]["status"] == "ok"
    assert by_host["ok.example"]["cpu_percent"] == 50.0
    assert by_host["down.example"]["status"] == "unreachable"
    assert "should-not-leak" not in str(by_host["down.example"])
    assert peak["value"] == 2
