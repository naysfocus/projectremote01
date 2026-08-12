from __future__ import annotations

import json
from base64 import b64decode, b64encode
from typing import Literal

import itsdangerous
from itsdangerous.exc import BadSignature
from starlette.datastructures import MutableHeaders, Secret
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class DynamicSessionMiddleware:
    """Signed cookie session with a Secure flag chosen per request.

    In ``auto`` mode HTTPS requests receive Secure cookies, while direct HTTP
    access over Tailscale can still be used as a recovery path.
    """

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str | Secret,
        session_cookie: str = "session",
        max_age: int | None = 14 * 24 * 60 * 60,
        path: str = "/",
        same_site: Literal["lax", "strict", "none"] = "lax",
        secure_mode: Literal["auto", "always", "never"] = "auto",
        domain: str | None = None,
    ) -> None:
        self.app = app
        self.signer = itsdangerous.TimestampSigner(str(secret_key))
        self.session_cookie = session_cookie
        self.max_age = max_age
        self.path = path
        self.same_site = same_site
        self.secure_mode = secure_mode
        self.domain = domain

    @staticmethod
    def _forwarded_proto(scope: Scope) -> str:
        for key, value in scope.get("headers", []):
            if key.lower() == b"x-forwarded-proto":
                return value.decode("latin-1").split(",", 1)[0].strip().lower()
        return ""

    def _is_secure(self, scope: Scope) -> bool:
        if self.secure_mode == "always":
            return True
        if self.secure_mode == "never":
            return False
        return scope.get("scheme") == "https" or self._forwarded_proto(scope) == "https"

    def _security_flags(self, scope: Scope) -> str:
        flags = f"httponly; samesite={self.same_site}"
        if self._is_secure(scope):
            flags += "; secure"
        if self.domain is not None:
            flags += f"; domain={self.domain}"
        return flags

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        initial_session_was_empty = True
        if self.session_cookie in connection.cookies:
            data = connection.cookies[self.session_cookie].encode("utf-8")
            try:
                data = self.signer.unsign(data, max_age=self.max_age)
                scope["session"] = json.loads(b64decode(data))
                initial_session_was_empty = False
            except BadSignature:
                scope["session"] = {}
        else:
            scope["session"] = {}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                flags = self._security_flags(scope)
                if scope["session"]:
                    data = b64encode(json.dumps(scope["session"]).encode("utf-8"))
                    data = self.signer.sign(data)
                    headers = MutableHeaders(scope=message)
                    max_age = f"Max-Age={self.max_age}; " if self.max_age else ""
                    headers.append(
                        "Set-Cookie",
                        f"{self.session_cookie}={data.decode('utf-8')}; path={self.path}; {max_age}{flags}",
                    )
                elif not initial_session_was_empty:
                    headers = MutableHeaders(scope=message)
                    headers.append(
                        "Set-Cookie",
                        f"{self.session_cookie}=null; path={self.path}; expires=Thu, 01 Jan 1970 00:00:00 GMT; {flags}",
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)
