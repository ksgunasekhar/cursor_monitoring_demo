"""Local server inventory.

SSH passwords and key paths are stored only in the inventory file.
"""

import json
import uuid
from pathlib import Path

from config_file import write_private_json


class InventoryError(Exception):
    """The inventory file is unreadable."""


def load_servers(path):
    destination = Path(path)
    if not destination.exists():
        return []
    try:
        data = json.loads(destination.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise InventoryError("The inventory file could not be read.") from None
    if not isinstance(data, list):
        raise InventoryError("The inventory file could not be read.")
    return data


def save_servers(path, servers):
    write_private_json(path, json.dumps(servers, indent=2) + "\n")


def add_server(path, fields):
    servers = load_servers(path)
    entry = {
        "id": uuid.uuid4().hex,
        "name": fields["name"],
        "host": fields["host"],
        "port": int(fields["port"]),
        "username": fields["username"],
        "password": fields.get("password") or "",
        "key_path": fields.get("key_path") or "",
    }
    servers.append(entry)
    save_servers(path, servers)
    return entry


def remove_server(path, server_id):
    servers = [item for item in load_servers(path) if item.get("id") != server_id]
    save_servers(path, servers)
    return servers


def _text(form, key):
    value = form.get(key, "")
    if not isinstance(value, str):
        return ""
    return value.strip()


def validate_new_server(form):
    """Return a cleaned server dict, or field errors.

    A server needs a display name, host, and username, plus a password
    or a private key path.
    """
    name = _text(form, "name")
    host = _text(form, "host")
    username = _text(form, "username")
    password = form.get("password", "")
    if not isinstance(password, str):
        password = ""
    key_path = _text(form, "key_path")
    port_raw = _text(form, "port")
    errors = []
    if not name:
        errors.append("Display name is required.")
    if not host:
        errors.append("Hostname or IP is required.")
    if not username:
        errors.append("SSH username is required.")
    if port_raw == "":
        port = 22
    else:
        try:
            port = int(port_raw)
        except (TypeError, ValueError):
            port = None
        if port is None or port < 1 or port > 65535:
            errors.append("SSH port must be a number from 1 to 65535.")
    if password == "" and key_path == "":
        errors.append("Enter a password or a private key path.")
    if errors:
        return None, errors
    return {
        "name": name,
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "key_path": key_path,
    }, []
