"""Local sign-in config.

The demo password is hashed into config.json. The plain password is not
written to the file and is not logged.
"""

import json
import os
from pathlib import Path

import bcrypt

DEMO_USERNAME = "admin"
DEMO_PASSWORD = "monitor-demo"


class ConfigError(Exception):
    """The sign-in config is missing or unreadable."""


def write_private_json(path, payload):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    os.chmod(temporary, 0o600)
    os.replace(temporary, destination)


def ensure_config(path, rounds=12):
    """Write config.json when it is missing.

    Existing files are left as they are so a changed hash is kept.
    """
    destination = Path(path)
    if destination.exists():
        return
    password_hash = bcrypt.hashpw(
        DEMO_PASSWORD.encode("utf-8"),
        bcrypt.gensalt(rounds=rounds),
    ).decode("ascii")
    payload = {
        "username": DEMO_USERNAME,
        "password_hash": password_hash,
    }
    write_private_json(destination, json.dumps(payload, indent=2) + "\n")


def load_config(path):
    destination = Path(path)
    try:
        data = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError("The sign-in config could not be read.") from None
    if not isinstance(data, dict):
        raise ConfigError("The sign-in config could not be read.")
    username = data.get("username")
    password_hash = data.get("password_hash")
    if not isinstance(username, str) or not isinstance(password_hash, str):
        raise ConfigError("The sign-in config could not be read.")
    return {"username": username, "password_hash": password_hash}


def credentials_match(config, username, password):
    """Compare the submitted password to the stored bcrypt hash.

    The hash is checked even when the username does not match.
    """
    if not isinstance(password, str):
        password = ""
    try:
        hash_ok = bcrypt.checkpw(
            password.encode("utf-8"),
            config["password_hash"].encode("ascii"),
        )
    except (ValueError, TypeError, UnicodeError):
        return False
    if not isinstance(username, str):
        return False
    return username == config["username"] and hash_ok
