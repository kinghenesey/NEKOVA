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