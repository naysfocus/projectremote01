from __future__ import annotations

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

remote_auth_bp = Blueprint("remote_auth", __name__)


def _client():
    return current_app.extensions["remote_server_client"]


@remote_auth_bp.get("/activation")
def activation_page():
    status = _client().public_status()
    if status["allowed"]:
        return redirect(url_for("index"))
    return render_template("activation.html", status=status)


@remote_auth_bp.get("/api/remote-auth/status")
def auth_status():
    return jsonify(_client().public_status())


@remote_auth_bp.post("/api/remote-auth/activate")
def activate():
    data = request.get_json(silent=True) or {}
    result = _client().activate(str(data.get("code") or ""))
    return jsonify(result), (200 if result.get("ok") else 400)


@remote_auth_bp.post("/api/remote-auth/retry")
def retry():
    result = _client().retry()
    return jsonify(result), (200 if result.get("ok") else 409)
