import os
import secrets
import sys
import threading
import time
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for

from config_file import ConfigError, credentials_match, ensure_config, load_config
from inventory import InventoryError, add_server, load_servers, remove_server, validate_new_server
from poller import refresh_servers
from present import present_detail, present_list_row
from ssh_client import ParamikoCollector


def create_app(config_path, inventory_path, secret_key, collector=None, clock=None):
    app = Flask(__name__)
    app.secret_key = secret_key
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["CONFIG_PATH"] = str(config_path)
    app.config["INVENTORY_PATH"] = str(inventory_path)
    app.config["COLLECTOR"] = collector if collector is not None else ParamikoCollector()
    app.config["CLOCK"] = clock if clock is not None else time.time
    app.config["SAMPLE_STORE"] = {}
    app.config["POLL_LOCK"] = threading.Lock()

    def csrf_token():
        token = session.get("_csrf")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf"] = token
        return token

    def verify_csrf():
        sent = request.form.get("csrf_token", "")
        expected = session.get("_csrf", "")
        if not isinstance(sent, str) or not isinstance(expected, str) or not expected:
            abort(400, description="The form expired. Reload the page and try again.")
        if not secrets.compare_digest(sent, expected):
            abort(400, description="The form expired. Reload the page and try again.")

    @app.context_processor
    def inject_csrf():
        return {"csrf_token": csrf_token}

    @app.before_request
    def require_session():
        if request.endpoint in {"login", "static", "favicon"}:
            return None
        if not session.get("user"):
            return redirect(url_for("login"))
        return None

    @app.get("/favicon.ico")
    def favicon():
        return ("", 204)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("user") and request.method == "GET":
            return redirect(url_for("server_list"))
        error = None
        if request.method == "POST":
            verify_csrf()
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            try:
                config = load_config(app.config["CONFIG_PATH"])
                matched = credentials_match(config, username, password)
            except ConfigError:
                matched = False
            if matched:
                session.clear()
                session["user"] = config["username"]
                session["_csrf"] = secrets.token_urlsafe(32)
                return redirect(url_for("server_list"))
            error = "Sign-in failed."
        return render_template("login.html", error=error)

    @app.post("/logout")
    def logout():
        verify_csrf()
        session.clear()
        return redirect(url_for("login"))

    def load_inventory():
        try:
            return load_servers(app.config["INVENTORY_PATH"]), None
        except InventoryError:
            return [], "The inventory file could not be read."

    def poll_inventory(servers):
        with app.config["POLL_LOCK"]:
            return refresh_servers(
                servers,
                app.config["COLLECTOR"],
                app.config["SAMPLE_STORE"],
                app.config["CLOCK"](),
            )

    @app.get("/")
    def server_list():
        servers, error = load_inventory()
        rows = [] if error else poll_inventory(servers)
        return render_template(
            "list.html",
            servers=[present_list_row(row) for row in rows],
            error=error,
        )

    @app.get("/api/servers")
    def servers_json():
        servers, error = load_inventory()
        if error:
            return jsonify({"error": error, "servers": []})
        rows = poll_inventory(servers)
        return jsonify({"servers": [present_list_row(row) for row in rows]})

    @app.route("/servers", methods=["GET", "POST"])
    def servers_page():
        errors = []
        values = _blank_form()
        if request.method == "POST":
            verify_csrf()
            cleaned, errors = validate_new_server(request.form)
            if cleaned and not errors:
                try:
                    add_server(app.config["INVENTORY_PATH"], cleaned)
                except InventoryError:
                    errors = ["The inventory file could not be read."]
                else:
                    return redirect(url_for("servers_page"))
            values = {
                "name": request.form.get("name", ""),
                "host": request.form.get("host", ""),
                "port": request.form.get("port", ""),
                "username": request.form.get("username", ""),
                "key_path": request.form.get("key_path", ""),
            }
        saved, load_error = load_inventory()
        public = [_public_inventory(item) for item in saved]
        return render_template(
            "servers.html",
            errors=errors,
            values=values,
            servers=public,
            load_error=load_error,
        )

    @app.post("/servers/<server_id>/remove")
    def remove_server_route(server_id):
        verify_csrf()
        try:
            remove_server(app.config["INVENTORY_PATH"], server_id)
        except InventoryError:
            return redirect(url_for("servers_page"))
        with app.config["POLL_LOCK"]:
            app.config["SAMPLE_STORE"].pop(server_id, None)
        return redirect(url_for("servers_page"))

    def sample_for(server_id):
        servers, error = load_inventory()
        if error:
            return None, error, False
        if not any(item["id"] == server_id for item in servers):
            return None, None, False
        rows = poll_inventory(servers)
        sample = next((row for row in rows if row["id"] == server_id), None)
        return sample, None, True

    @app.get("/servers/<server_id>")
    def server_detail(server_id):
        sample, error, found = sample_for(server_id)
        if error:
            return render_template("detail.html", server=None, error=error)
        if not found or sample is None:
            abort(404)
        return render_template("detail.html", server=present_detail(sample), error=None)

    @app.get("/api/servers/<server_id>")
    def server_json(server_id):
        sample, error, found = sample_for(server_id)
        if error:
            return jsonify({"error": error})
        if not found or sample is None:
            abort(404)
        return jsonify({"server": present_detail(sample)})

    return app


def _blank_form():
    return {"name": "", "host": "", "port": "22", "username": "", "key_path": ""}


def _public_inventory(item):
    if item.get("key_path"):
        auth = "Key"
    else:
        auth = "Password"
    return {
        "id": item["id"],
        "name": item["name"],
        "host": item["host"],
        "port": item["port"],
        "username": item["username"],
        "auth": auth,
    }


def main():
    root = Path(__file__).resolve().parent
    config_path = root / "config.json"
    inventory_path = root / "inventory.json"
    ensure_config(config_path)
    secret = os.environ.get("FLASK_SECRET_KEY")
    if not secret:
        sys.stderr.write("Set FLASK_SECRET_KEY in the environment before starting.\n")
        sys.exit(1)
    application = create_app(config_path, inventory_path, secret)
    application.run(host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
