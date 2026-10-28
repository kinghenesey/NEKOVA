# =============================================================
# NEKOVA Web Framework — Response Object
# =============================================================
# Represents an outgoing HTTP response.
# Makes it easy to send text, JSON, or HTML back to the browser.

import json
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class NEKOVAResponse:
    """
    Represents an outgoing HTTP response.

    Attributes:
        body        — response content
        status      — HTTP status code (200, 404, 500 etc.)
        headers     — response headers
        content_type — type of content being sent
    """
    body:         str             = ""
    status:       int             = 200
    headers:      Dict[str, str]  = field(default_factory=dict)
    content_type: str             = "text/plain"

    def __repr__(self):
        return f"Response({self.status}, {self.content_type})"


def check_status(status) -> int:
    """Return `status` if it is a valid HTTP status code, else raise."""
    if (isinstance(status, bool) or not isinstance(status, int)
            or not 100 <= status <= 599):
        raise ValueError(
            f"status must be a whole number from 100 to 599, got {status!r}")
    return status


def respond(status, body="", headers=None) -> NEKOVAResponse:
    """
    Build a response from a status, a body and optional headers.
    This is the `respond(...)` function NEKOVA programs call, and it works
    anywhere - including inside middleware, where the route-body helpers
    (text, json, html) are not in scope.

        respond(404, "not found")                  plain text
        respond(201, {"id": 7})                    JSON (dict or list)
        respond(401, "no", {"WWW-Authenticate": "Bearer"})
    """
    try:
        code = check_status(status)
    except ValueError as e:
        raise ValueError(f"respond: {e}") from None
    if isinstance(body, (dict, list)):
        response = json_response(body, code)
    else:
        response = text_response("" if body is None else body, code)
    if headers is not None:
        if not isinstance(headers, dict):
            raise ValueError("respond: headers must be a dict of name: value")
        for name, value in headers.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise ValueError("respond: header names and values must be "
                                 "strings")
            if any(c in name + value for c in "\r\n\0"):
                raise ValueError("respond: headers must not contain line "
                                 "breaks")
            response.headers[name] = value
    return response


def text_response(content: str, status: int = 200) -> NEKOVAResponse:
    """Create a plain text response."""
    return NEKOVAResponse(
        body=str(content),
        status=status,
        content_type="text/plain"
    )


def json_response(data: Any, status: int = 200) -> NEKOVAResponse:
    """Create a JSON response."""
    if isinstance(data, str):
        body = data
    else:
        body = json.dumps(data, indent=2)

    return NEKOVAResponse(
        body=body,
        status=status,
        content_type="application/json"
    )


def html_response(content: str, status: int = 200) -> NEKOVAResponse:
    """Create an HTML response."""
    return NEKOVAResponse(
        body=str(content),
        status=status,
        content_type="text/html"
    )


def error_response(message: str, status: int = 400) -> NEKOVAResponse:
    """Create an error response."""
    body = json.dumps({
        "error":   message,
        "status":  status,
    })
    return NEKOVAResponse(
        body=body,
        status=status,
        content_type="application/json"
    )


def not_found_response(path: str) -> NEKOVAResponse:
    """Create a 404 not found response."""
    return error_response(
        f"Route '{path}' not found.",
        status=404
    )