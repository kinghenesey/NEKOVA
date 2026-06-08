# =============================================================
# NEKOVA UI Framework — Components
# =============================================================
# Every UI element in NEKOVA is a Component.
# Components form a tree that gets rendered to HTML.
#
# Example tree:
#   Page("Home")
#   ├── Title("Welcome")
#   ├── Text("Hello world")
#   └── Button("Click me", goto="Dashboard")

from dataclasses import dataclass, field
from typing import List, Optional


class Component:
    """Base class for all NEKOVA UI components."""
    pass


@dataclass
class Title(Component):
    """
    A large heading.
    Usage in NEKOVA:  title "Welcome to NEKOVA"
    """
    text: str

    def __repr__(self):
        return f"Title({repr(self.text)})"


@dataclass
class Text(Component):
    """
    A paragraph of text.
    Usage in NEKOVA:  text "Hello world"
    """
    content: str

    def __repr__(self):
        return f"Text({repr(self.content)})"


@dataclass
class Button(Component):
    """
    A clickable button.
    Usage in NEKOVA:
        button "Get Started":
            go Dashboard
    """
    label:  str
    goto:   Optional[str] = None
    action: Optional[str] = None

    def __repr__(self):
        return f"Button({repr(self.label)}, goto={self.goto})"


@dataclass
class Input(Component):
    """
    A text input field.
    Usage in NEKOVA:  input "Enter your name" as name
    """
    placeholder: str
    name:        str = "input"

    def __repr__(self):
        return f"Input({repr(self.placeholder)})"


@dataclass
class Image(Component):
    """
    An image.
    Usage in NEKOVA:  image "logo.png" alt "NEKOVA Logo"
    """
    src: str
    alt: str = ""

    def __repr__(self):
        return f"Image({repr(self.src)})"


@dataclass
class Divider(Component):
    """
    A horizontal divider line.
    Usage in NEKOVA:  divider
    """
    def __repr__(self):
        return "Divider()"


@dataclass
class Space(Component):
    """
    Vertical spacing.
    Usage in NEKOVA:  space
    """
    size: int = 1

    def __repr__(self):
        return f"Space({self.size})"


@dataclass
class Card(Component):
    """
    A card container with children.
    Usage in NEKOVA:
        card:
            title "Hello"
            text "World"
    """
    children: List[Component] = field(default_factory=list)

    def __repr__(self):
        return f"Card({len(self.children)} children)"


@dataclass
class Row(Component):
    """
    A horizontal row of components.
    Usage in NEKOVA:
        row:
            button "Yes"
            button "No"
    """
    children: List[Component] = field(default_factory=list)

    def __repr__(self):
        return f"Row({len(self.children)} children)"


@dataclass
class Page(Component):
    """
    A full page — the top-level UI component.
    Usage in NEKOVA:
        page Home:
            title "Welcome"
            text "Hello"
    """
    name:     str
    children: List[Component] = field(default_factory=list)

    def add(self, component: Component):
        self.children.append(component)

    def __repr__(self):
        return f"Page({self.name}, {len(self.children)} components)"


@dataclass
class UIApp(Component):
    """
    The root UI application — contains all pages.
    """
    name:  str
    pages: List[Page] = field(default_factory=list)

    def add_page(self, page: Page):
        self.pages.append(page)

    def get_page(self, name: str) -> Optional[Page]:
        for page in self.pages:
            if page.name == name:
                return page
        return None

    def __repr__(self):
        return f"UIApp({self.name}, {len(self.pages)} pages)"