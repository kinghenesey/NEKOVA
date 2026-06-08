# =============================================================
# NEKOVA UI Framework — UI Module
# =============================================================
# This is what gets loaded when you write "use ui" in NEKOVA.
# It exposes all UI building functions to your NEKOVA programs.
#
# Usage in NEKOVA:
#   use ui
#   ui_page("Home")
#   ui_title("Welcome to NEKOVA")
#   ui_text("Build beautiful apps")
#   ui_button("Get Started", "Dashboard")
#   ui_save("app.html")

import os
from ui.components import (
    UIApp, Page, Title, Text, Button,
    Input, Image, Divider, Space, Card, Row
)
from ui.renderer import HTMLRenderer


# Global app state — holds the current UI being built
_current_app  = None
_current_page = None


def load() -> dict:
    """
    Returns all UI functions to be loaded
    into the NEKOVA environment when 'use ui' is called.
    """
    return {
        # App management
        "ui_app":      _ui_app,
        "ui_page":     _ui_page,
        "ui_save":     _ui_save,
        "ui_preview":  _ui_preview,

        # Components
        "ui_title":    _ui_title,
        "ui_text":     _ui_text,
        "ui_button":   _ui_button,
        "ui_input":    _ui_input,
        "ui_image":    _ui_image,
        "ui_divider":  _ui_divider,
        "ui_space":    _ui_space,
        "ui_card_start":  _ui_card_start,
        "ui_card_end":    _ui_card_end,
        "ui_row_start":   _ui_row_start,
        "ui_row_end":     _ui_row_end,
    }


# ----------------------------------------------------------
# App & page management
# ----------------------------------------------------------

def _ui_app(name: str):
    """Create a new UI application."""
    global _current_app, _current_page
    _current_app  = UIApp(name=str(name))
    _current_page = None
    return name


def _ui_page(name: str):
    """Create a new page and make it current."""
    global _current_app, _current_page

    if _current_app is None:
        _current_app = UIApp(name="NEKOVA App")

    page = Page(name=str(name))
    _current_app.add_page(page)
    _current_page = page
    return name


def _ui_save(filepath: str = "output.html"):
    """Render the UI app and save it to an HTML file."""
    global _current_app

    if _current_app is None:
        raise RuntimeError(
            "No UI app defined.\n"
            "  Call ui_app('MyApp') first."
        )

    if not _current_app.pages:
        raise RuntimeError(
            "No pages defined.\n"
            "  Call ui_page('Home') to create a page."
        )

    renderer = HTMLRenderer(_current_app)
    renderer.save(str(filepath))

    from config import Color
    print(f"{Color.GREEN}✓ UI saved to '{filepath}'{Color.RESET}")
    print(f"{Color.DIM}  Open it in your browser to see your app!{Color.RESET}")
    return filepath


def _ui_preview():
    """Save and open the UI in the default browser."""
    import webbrowser
    filepath = "preview.html"
    _ui_save(filepath)
    abs_path = os.path.abspath(filepath)
    webbrowser.open(f"file://{abs_path}")
    return filepath


# ----------------------------------------------------------
# Component builders
# ----------------------------------------------------------

def _ui_title(text: str):
    """Add a title to the current page."""
    _require_page()
    _current_page.add(Title(text=str(text)))
    return text


def _ui_text(content: str):
    """Add a text paragraph to the current page."""
    _require_page()
    _current_page.add(Text(content=str(content)))
    return content


def _ui_button(label: str, goto: str = None):
    """Add a button to the current page."""
    _require_page()
    _current_page.add(Button(
        label=str(label),
        goto=str(goto) if goto else None
    ))
    return label


def _ui_input(placeholder: str, name: str = "input"):
    """Add an input field to the current page."""
    _require_page()
    _current_page.add(Input(
        placeholder=str(placeholder),
        name=str(name)
    ))
    return name


def _ui_image(src: str, alt: str = ""):
    """Add an image to the current page."""
    _require_page()
    _current_page.add(Image(src=str(src), alt=str(alt)))
    return src


def _ui_divider():
    """Add a horizontal divider to the current page."""
    _require_page()
    _current_page.add(Divider())


def _ui_space(size: int = 1):
    """Add vertical space to the current page."""
    _require_page()
    _current_page.add(Space(size=int(size)))


def _ui_card_start():
    """Start a card container."""
    _require_page()
    card = Card()
    _current_page.add(card)
    # Temporarily redirect additions to the card
    _current_page._card_stack = getattr(
        _current_page, '_card_stack', [])
    _current_page._card_stack.append(card)


def _ui_card_end():
    """End a card container."""
    _require_page()
    if hasattr(_current_page, '_card_stack'):
        if _current_page._card_stack:
            _current_page._card_stack.pop()


def _ui_row_start():
    """Start a row container."""
    _require_page()
    row = Row()
    _current_page.add(row)


def _ui_row_end():
    """End a row container."""
    pass  # rows are self-closing for now


# ----------------------------------------------------------
# Helper
# ----------------------------------------------------------

def _require_page():
    """Ensure a page exists before adding components."""
    global _current_page
    if _current_page is None:
        # Auto-create a default page
        _ui_page("Home")