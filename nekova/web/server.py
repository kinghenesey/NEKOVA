# =============================================================
# NEKOVA Web Framework — Server
# =============================================================
import os
import sys
from nekova.web.router import Router
from nekova.web.request import from_flask_request
from nekova.web.response import NEKOVAResponse


class NEKOVAServer:
    def __init__(self, name: str = "NEKOVA App"):
        self.name   = name
        self.router = Router()
        self._app   = None

    def start(self, port: int = 8000, debug: bool = False):
        self._setup_flask()

        print()
        print("  \033[96m\033[1mNEKOVA Web Server\033[0m")
        print(f"  {'─' * 40}")
        print(f"  \033[92m✓ Server running at http://localhost:{port}\033[0m")
        print("  Press Ctrl+C to stop")
        print()

        for route in self.router.get_routes():
            methods = ', '.join(route.methods)
            print(f"  → {methods:<6} {route.path}")
        print()

        import logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        self._app.run(
            host="127.0.0.1",
            port=int(port),
            debug=debug,
            use_reloader=False
        )

    def _setup_flask(self):
        from flask import Flask, request as flask_request

        self._app = Flask(self.name)

        @self._app.route("/", defaults={"path": ""})
        @self._app.route("/<path:path>", methods=[
            "GET", "POST", "PUT", "DELETE", "PATCH"
        ])
        def handle_all(path):
            from flask import Response as FlaskResponse
            nekova_request  = from_flask_request(flask_request)
            nekova_response = self.router.handle(nekova_request)
            return FlaskResponse(
                response=nekova_response.body,
                status=nekova_response.status,
                headers=nekova_response.headers,
                content_type=nekova_response.content_type,
            )

    def __repr__(self):
        return f"NEKOVAServer({self.name})"