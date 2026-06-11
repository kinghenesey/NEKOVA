# =============================================================
# NEKOVA UI Framework — Package Init
# =============================================================
# Makes the UI module importable from anywhere like:
#   from ui import load_ui_module

from nekova.ui.ui_module import load
from nekova.ui.components import (
    UIApp, Page, Title, Text, Button,
    Input, Image, Divider, Space, Card, Row
)
from nekova.ui.renderer import HTMLRenderer


def load_ui_module() -> dict:
    """Load all UI functions into the NEKOVA environment."""
    return load()
