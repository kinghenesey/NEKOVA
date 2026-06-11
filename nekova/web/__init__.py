# =============================================================
# NEKOVA Web Framework — Package Init
# =============================================================
# Makes the web module importable from anywhere like:
#   from web import load_web_module

from nekova.web.web_module import load
from nekova.web.server import NEKOVAServer
from nekova.web.router import Router
from nekova.web.request import NEKOVARequest
from nekova.web.response import (
    NEKOVAResponse, text_response,
    json_response, html_response, error_response
)


def load_web_module() -> dict:
    """Load all web functions into the NEKOVA environment."""
    return load()
