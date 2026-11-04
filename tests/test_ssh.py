import socket

import paramiko
import pytest

from ssh_client import (
    CAT_MEMINFO,
    CAT_NETDEV,
    CAT_STAT,
    COMMANDS,
    COMMAND_TIMEOUT,
    CONNECT_TIMEOUT,
    SS_FALLBACK,
    SS_WITH_PROCESS,
    AuthFailed,
    ParamikoCollector,
    ParamikoSession,
    Unreachable,
)


class FakeBuffer:
    def __init__(self, payload, code=0):
        self.payload = payload
        self.channel = self
        self.code = code

    def read(self):
        return self.payload

    def recv_exit_status(self):
        return self.code

    def close(self):
        return None


class FakeClient:
    def __init__(self, fail=None, ss_code=0):
        self.fail = fail
        self.ss_code = ss_code
        self.commands = []
        self.timeouts = []
        self.kwargs = None
        self.closed = False
        self.stats = [
            b"cpu  100 0 0 300 0 0 0 0\n",
            b"cpu  200 0 50 450 0 0 0 0\n",
        ]

    def set_missing_host_key_policy(self, _policy):
        return None

    def connect(self, **kwargs):
        self.kwargs = kwargs
        if self.fail == "auth":
            raise paramiko.AuthenticationException("password=should-not-leak")
        if self.fail == "timeout":
            raise socket.timeout("password=should-not-leak")

    def exec_command(self, command, timeout=None):
        self.commands.append(command)
        self.timeouts.append(timeout)
        if self.fail == "command-timeout":
            raise socket.timeout("password=should-not-leak")
        if command == CAT_STAT:
            payload = self.stats.pop(0)
            code = 0
        elif command == SS_WITH_PROCESS:
            payload = b"tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n"
            code = self.ss_code
        elif command == SS_FALLBACK:
            payload = b"tcp LISTEN 0 128 127.0.0.1:22 0.0.0.0:*\n"
            code = 0
        else:
            payload = b"ok\n"
            code = 0
        stdout = FakeBuffer(payload, code)
        stderr = FakeBuffer(b"password=should-not-leak")
        return FakeBuffer(b""), stdout, stderr

    def close(self):
        self.closed = True


def _collector(fail=None, ss_code=0, gaps=None):
    client = FakeClient(fail=fail, ss_code=ss_code)

    def factory():
        return client

    def sleeper(seconds):
        if gaps is not None:
            gaps.append(seconds)

    return client, ParamikoCollector(client_factory=factory, sleeper=sleeper)


def test_success_runs_only_fixed_commands():
    gaps = []
    client, collector = _collector(gaps=gaps)
    result = collector.read(
        host="INJECT.example",
        port=22,
        username="INJECT-user",
        password="secret-value",
        key_path=None,
    )
    assert client.commands == [CAT_STAT, CAT_STAT, CAT_MEMINFO, CAT_NETDEV, SS_WITH_PROCESS]
    assert all(command in COMMANDS for command in client.commands)
    assert "INJECT" not in " ".join(client.commands)
    assert client.kwargs["hostname"] == "INJECT.example"
    assert client.kwargs["username"] == "INJECT-user"
    assert client.kwargs["timeout"] == CONNECT_TIMEOUT
    assert client.timeouts == [8, 8, 8, 8, 8]
    assert gaps == [1]
    assert "should-not-leak" not in " ".join(result.values())
    assert "cpu  100" in result["stat_first"]
    assert client.closed


def test_authentication_failure():
    _client, collector = _collector(fail="auth")
    with pytest.raises(AuthFailed) as caught:
        collector.read(
            host="h",
            port=22,
            username="u",
            password="secret-value",
            key_path=None,
        )
    assert "should-not-leak" not in str(caught.value)


def test_timeout():
    _client, collector = _collector(fail="timeout")
    with pytest.raises(Unreachable) as caught:
        collector.read(
            host="h",
            port=22,
            username="u",
            password=None,
            key_path=None,
        )
    assert "should-not-leak" not in str(caught.value)


def test_ss_falls_back_when_process_names_are_denied():
    client, collector = _collector(ss_code=1)
    result = collector.read(
        host="h",
        port=22,
        username="u",
        password=None,
        key_path=None,
    )
    assert client.commands[-2:] == [SS_WITH_PROCESS, SS_FALLBACK]
    assert "127.0.0.1:22" in result["ports"]
    assert "should-not-leak" not in result["ports"]


def test_missing_key_file_is_auth_failed(tmp_path):
    collector = ParamikoCollector(sleeper=lambda _seconds: None)
    with pytest.raises(AuthFailed):
        collector.read(
            host="h",
            port=22,
            username="u",
            password=None,
            key_path=str(tmp_path / "missing-key"),
        )


def test_session_rejects_commands_outside_the_list():
    client = FakeClient()
    session = ParamikoSession(client_factory=lambda: client)
    session.connect(
        host="h",
        port=22,
        username="u",
        password=None,
        key_path=None,
        timeout=CONNECT_TIMEOUT,
    )
    with pytest.raises(Unreachable):
        session.run("reboot", COMMAND_TIMEOUT)
