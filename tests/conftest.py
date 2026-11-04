import re

import pytest

from app import create_app
from config_file import ensure_config
from tests.samples import OkCollector


@pytest.fixture
def clock():
    class Clock:
        def __init__(self):
            self.now = 1_700_000_000.0

        def __call__(self):
            return self.now

        def advance(self, seconds):
            self.now += seconds

    return Clock()


@pytest.fixture
def make_app(tmp_path, clock):
    def _make(collector=None):
        config_path = tmp_path / "config.json"
        inventory_path = tmp_path / "inventory.json"
        ensure_config(config_path, rounds=4)
        application = create_app(
            config_path,
            inventory_path,
            secret_key="test-secret-key",
            collector=collector if collector is not None else OkCollector(),
            clock=clock,
        )
        application.config["TESTING"] = True
        return application

    return _make


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_from(html):
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match
    return match.group(1)


def sign_in(client, username="admin", password="monitor-demo"):
    page = client.get("/login")
    token = csrf_from(page.get_data(as_text=True))
    return client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token},
    )
