# =============================================================
# NEKOVA Web Framework — Request Object
# =============================================================
# Represents an incoming HTTP request.
# Wraps Flask's request object in an NEKOVA-friendly way.

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class NEKOVARequest:
    """
    Represents an incoming HTTP request.

    Attributes:
        method   — GET, POST, PUT, DELETE
        path     — URL path e.g. '/hello'
        params   — URL query parameters e.g. ?name=Emmanuel
        body     — request body (for POST/PUT)
        headers  — request headers
        json     — parsed JSON body (if Content-Type is JSON)
    """
    method:  str                  = "GET"
    path:    str                  = "/"
    params:  Dict[str, str]       = field(default_factory=dict)
    body:    str                  = ""
    headers: Dict[str, str]       = field(default_factory=dict)
    json:    Dict[str, Any]       = field(default_factory=dict)

    def get_param(self, key: str, default: str = "") -> str:
        """Get a URL query parameter by name."""
        return self.params.get(key, default)

    def get_json(self, key: str, default=None):
        """Get a JSON body field by name."""
        return self.json.get(key, default)

    def is_get(self) -> bool:
        return self.method == "GET"

    def is_post(self) -> bool:
        return self.method == "POST"

    def __repr__(self):
        return f"Request({self.method} {self.path})"


def from_flask_request(flask_request) -> NEKOVARequest:
    """Convert a Flask request to an NEKOVARequest."""
    try:
        json_data = flask_request.get_json(silent=True) or {}
    except Exception:
        json_data = {}

    return NEKOVARequest(
        method=flask_request.method,
        path=flask_request.path,
        params=dict(flask_request.args),
        body=flask_request.get_data(as_text=True),
        headers=dict(flask_request.headers),
        json=json_data,
    )