"""Read-only SSH collector.

Host and username are connection arguments. Commands are constants.
Remote stderr is discarded so it cannot reach the page.
"""

import logging
import os
import socket
import time

import paramiko

logging.getLogger("paramiko").setLevel(logging.WARNING)

CONNECT_TIMEOUT = 8
COMMAND_TIMEOUT = 8
SAMPLE_GAP_SECONDS = 1

CAT_STAT = "cat /proc/stat"
CAT_MEMINFO = "cat /proc/meminfo"
CAT_NETDEV = "cat /proc/net/dev"
SS_WITH_PROCESS = "ss -H -lntup"
SS_FALLBACK = "ss -H -lntu"

# Fixed read-only commands. Nothing here writes, installs, or restarts.
COMMANDS = (
    CAT_STAT,
    CAT_MEMINFO,
    CAT_NETDEV,
    SS_WITH_PROCESS,
    SS_FALLBACK,
)


class AuthFailed(Exception):
    """SSH rejected the username, password, or key."""


class Unreachable(Exception):
    """The host could not be reached, or the attempt timed out."""


def collect_with_session(session, sleeper=time.sleep):
    """Run the fixed command list on an already connected session."""
    try:
        _code, stat_first = session.run(CAT_STAT, COMMAND_TIMEOUT)
        sleeper(SAMPLE_GAP_SECONDS)
        _code, stat_second = session.run(CAT_STAT, COMMAND_TIMEOUT)
        _code, meminfo = session.run(CAT_MEMINFO, COMMAND_TIMEOUT)
        _code, netdev = session.run(CAT_NETDEV, COMMAND_TIMEOUT)
        code, ports = session.run(SS_WITH_PROCESS, COMMAND_TIMEOUT)
        if code != 0:
            # Process names are often denied. Fall back to sockets only.
            code, ports = session.run(SS_FALLBACK, COMMAND_TIMEOUT)
        if code != 0:
            ports = ""
        return {
            "stat_first": stat_first,
            "stat_second": stat_second,
            "meminfo": meminfo,
            "netdev": netdev,
            "ports": ports,
        }
    finally:
        session.close()


class ParamikoSession:
    def __init__(self, client_factory=None):
        self._client_factory = client_factory or paramiko.SSHClient
        self.client = None

    def connect(self, *, host, port, username, password, key_path, timeout):
        if key_path and not os.path.isfile(key_path):
            raise AuthFailed()
        client = self._client_factory()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=host,
                port=int(port),
                username=username,
                password=password,
                key_filename=key_path,
                timeout=timeout,
                auth_timeout=timeout,
                banner_timeout=timeout,
                look_for_keys=False,
                allow_agent=False,
            )
        except paramiko.AuthenticationException:
            client.close()
            raise AuthFailed() from None
        except (socket.timeout, TimeoutError, OSError, paramiko.SSHException):
            client.close()
            raise Unreachable() from None
        self.client = client

    def run(self, command, timeout):
        if command not in COMMANDS:
            raise Unreachable()
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            stdin.close()
            text = stdout.read().decode("utf-8", errors="replace")
            stderr.read()
            code = stdout.channel.recv_exit_status()
        except (socket.timeout, TimeoutError, OSError, paramiko.SSHException):
            raise Unreachable() from None
        return code, text

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None


class ParamikoCollector:
    def __init__(self, client_factory=None, sleeper=time.sleep):
        self._client_factory = client_factory
        self._sleeper = sleeper

    def read(self, *, host, port, username, password, key_path):
        session = ParamikoSession(client_factory=self._client_factory)
        session.connect(
            host=host,
            port=port,
            username=username,
            password=password or None,
            key_path=key_path or None,
            timeout=CONNECT_TIMEOUT,
        )
        return collect_with_session(session, sleeper=self._sleeper)
