from inventory import add_server, load_servers, remove_server, validate_new_server


def _fields(**overrides):
    fields = {
        "name": "web",
        "host": "192.0.2.10",
        "port": "22",
        "username": "monitor",
        "password": "stored-secret",
        "key_path": "",
    }
    fields.update(overrides)
    return fields


def test_missing_inventory_file_loads_as_empty(tmp_path):
    assert load_servers(tmp_path / "inventory.json") == []


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "inventory.json"
    secret = "stored-secret"
    added = add_server(path, _fields(password=secret, key_path="/keys/demo"))
    loaded = load_servers(path)
    assert len(loaded) == 1
    assert loaded[0]["id"] == added["id"]
    assert loaded[0]["name"] == "web"
    assert loaded[0]["host"] == "192.0.2.10"
    assert loaded[0]["port"] == 22
    assert loaded[0]["username"] == "monitor"
    assert loaded[0]["password"] == secret
    assert loaded[0]["key_path"] == "/keys/demo"


def test_remove_drops_one_entry_and_leaves_the_other(tmp_path):
    path = tmp_path / "inventory.json"
    first = add_server(path, _fields(name="alpha", host="192.0.2.11"))
    second = add_server(path, _fields(name="beta", host="192.0.2.12"))
    remaining = remove_server(path, first["id"])
    assert [item["id"] for item in remaining] == [second["id"]]
    assert load_servers(path)[0]["name"] == "beta"


def test_validate_accepts_password_or_key_and_rejects_gaps():
    cleaned, errors = validate_new_server(_fields(port=""))
    assert errors == []
    assert cleaned["port"] == 22
    assert cleaned["password"] == "stored-secret"

    keyed, key_errors = validate_new_server(
        _fields(password="", key_path="/keys/demo")
    )
    assert key_errors == []
    assert keyed["key_path"] == "/keys/demo"
    assert keyed["password"] == ""

    cases = [
        ("name", "Display name is required."),
        ("host", "Hostname or IP is required."),
        ("username", "SSH username is required."),
    ]
    for field, message in cases:
        _cleaned, field_errors = validate_new_server(_fields(**{field: "  "}))
        assert message in field_errors

    _cleaned, neither = validate_new_server(_fields(password="", key_path=""))
    assert "Enter a password or a private key path." in neither

    _cleaned, bad_port = validate_new_server(_fields(port="0"))
    assert "SSH port must be a number from 1 to 65535." in bad_port
