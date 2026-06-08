# =============================================================
# NEKOVA Web Framework — Package Init
# =============================================================
# Makes the web module importable from anywhere like:
#   from web import load_web_module

from web.web_module import load
from web.server import NEKOVAServer
from web.router import Router
from web.request import NEKOVARequest
from web.response import (
    NEKOVAResponse, text_response,
    json_response, html_response, error_response
)


def load_web_module() -> dict:
    """Load all web functions into the NEKOVA environment."""
    return load()