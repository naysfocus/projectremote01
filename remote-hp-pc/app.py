"""Remote HP — entry point Flask v1.50 with Android Controller API."""
from __future__ import annotations

import os

from flask import Flask, jsonify, redirect, render_template, request, url_for

from database.db import init_db
from services.remote_server_client import RemoteServerClient
from services.device_connection import WirelessAdbManager

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

init_db()
remote_server_client = RemoteServerClient()
wireless_adb_manager = WirelessAdbManager()
app.extensions["remote_server_client"] = remote_server_client
app.extensions["wireless_adb_manager"] = wireless_adb_manager

from routes.devices import devices_bp
from routes.accounts import accounts_bp
from routes.upload import upload_bp
from routes.history import history_bp
from routes.settings import settings_bp
from routes.remote_auth import remote_auth_bp
from routes.pairing import pairing_bp
from routes.mobile import mobile_bp

app.register_blueprint(devices_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(history_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(remote_auth_bp)
app.register_blueprint(pairing_bp)
app.register_blueprint(mobile_bp)


@app.before_request
def require_remote_server_access():
    allowed_prefixes = ("/static/", "/api/remote-auth/")
    if request.path == "/activation" or request.path.startswith(allowed_prefixes):
        return None
    client = app.extensions["remote_server_client"]
    if client.is_allowed():
        return None
    if request.path.startswith("/api/"):
        status = client.public_status()
        return jsonify({"error": status["message"], "remote_auth_status": status["status"]}), 423
    return redirect(url_for("remote_auth.activation_page"))


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.path.startswith("/api/mobile/") or request.path.startswith("/api/pairing"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    remote_server_client.start()
    wireless_adb_manager.start()
    print("=" * 62)
    host = (os.environ.get("REMOTE_HP_BIND") or "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.environ.get("REMOTE_HP_PORT") or "5001")
    print(f"  Remote HP v1.50 berjalan di http://{host}:{port}")
    print("  Aktivasi & sesi dikelola oleh https://remote.darda.uk")
    print("  (tekan Ctrl+C untuk berhenti)")
    print("=" * 62)
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
    finally:
        wireless_adb_manager.shutdown()
        remote_server_client.shutdown()
