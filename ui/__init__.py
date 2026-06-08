# =============================================================
# NEKOVA UI Framework — Package Init
# =============================================================
# Makes the UI module importable from anywhere like:
#   from ui import load_ui_module

from ui.ui_module import load
from ui.components import (
    UIApp, Page, Title, Text, Button,
    Input, Image, Divider, Space, Card, Row
)
from ui.renderer import HTMLRenderer


def load_ui_module() -> dict:
    """Load all UI functions into the NEKOVA environment."""
    return load()