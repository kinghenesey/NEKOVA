# =============================================================
# NEKOVA UI Framework — HTML Renderer
# =============================================================
# Converts a UIApp component tree into a full HTML file.
#
# Process:
#   UIApp → pages → components → HTML elements → full page
#
# The output is a single self-contained HTML file with:
#   - Modern responsive design
#   - Clean typography
#   - Page navigation (multi-page support)
#   - Mobile friendly layout

from ui.components import (
    UIApp, Page, Title, Text, Button, Input,
    Image, Divider, Space, Card, Row, Component
)


class HTMLRenderer:
    """
    Renders a UIApp into a complete HTML file.

    Usage:
        renderer = HTMLRenderer(app)
        html     = renderer.render()
        renderer.save("output.html")
    """

    def __init__(self, app: UIApp):
        self.app = app

    def render(self) -> str:
        """Render the entire app to an HTML string."""
        pages_html = self._render_pages()
        nav_html   = self._render_nav()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.app.name}</title>
    <style>
        {self._styles()}
    </style>
</head>
<body>
    {nav_html}
    <main class="container">
        {pages_html}
    </main>
    <script>
        {self._scripts()}
    </script>
</body>
</html>"""

    def save(self, filepath: str):
        """Save rendered HTML to a file."""
        html = self.render()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

    # ----------------------------------------------------------
    # Page rendering
    # ----------------------------------------------------------

    def _render_pages(self) -> str:
        """Render all pages."""
        if not self.app.pages:
            return "<p>No pages defined.</p>"

        html = ""
        for i, page in enumerate(self.app.pages):
            active = "active" if i == 0 else ""
            html += f"""
        <section class="page {active}" id="page-{page.name}">
            {self._render_components(page.children)}
        </section>"""

        return html

    def _render_nav(self) -> str:
        """Render navigation bar if multiple pages exist."""
        if len(self.app.pages) <= 1:
            return ""

        links = ""
        for i, page in enumerate(self.app.pages):
            active = "active" if i == 0 else ""
            links += (f'<a href="#" class="nav-link {active}" '
                      f'onclick="showPage(\'{page.name}\')">'
                      f'{page.name}</a>')

        return f"""
    <nav class="navbar">
        <div class="nav-brand">{self.app.name}</div>
        <div class="nav-links">{links}</div>
    </nav>"""

    def _render_components(self, components: list) -> str:
        """Render a list of components to HTML."""
        html = ""
        for component in components:
            html += self._render_component(component)
        return html

    def _render_component(self, component: Component) -> str:
        """Route a component to its matching render method."""
        method_name = f"_render_{type(component).__name__.lower()}"
        method      = getattr(self, method_name, None)

        if method is None:
            return f"<!-- Unknown component: {type(component).__name__} -->"

        return method(component)

    # ----------------------------------------------------------
    # Component renderers
    # ----------------------------------------------------------

    def _render_title(self, c: Title) -> str:
        return f'<h1 class="nekova-title">{c.text}</h1>\n'

    def _render_text(self, c: Text) -> str:
        return f'<p class="nekova-text">{c.content}</p>\n'

    def _render_button(self, c: Button) -> str:
        if c.goto:
            onclick = f"showPage('{c.goto}')"
        else:
            onclick = ""
        return (f'<button class="nekova-button" '
                f'onclick="{onclick}">{c.label}</button>\n')

    def _render_input(self, c: Input) -> str:
        return (f'<input class="nekova-input" '
                f'type="text" '
                f'placeholder="{c.placeholder}" '
                f'name="{c.name}">\n')

    def _render_image(self, c: Image) -> str:
        return (f'<img class="nekova-image" '
                f'src="{c.src}" '
                f'alt="{c.alt}">\n')

    def _render_divider(self, c: Divider) -> str:
        return '<hr class="nekova-divider">\n'

    def _render_space(self, c: Space) -> str:
        height = c.size * 20
        return f'<div style="height:{height}px"></div>\n'

    def _render_card(self, c: Card) -> str:
        inner = self._render_components(c.children)
        return f'<div class="nekova-card">{inner}</div>\n'

    def _render_row(self, c: Row) -> str:
        inner = self._render_components(c.children)
        return f'<div class="nekova-row">{inner}</div>\n'

    # ----------------------------------------------------------
    # Styles
    # ----------------------------------------------------------

    def _styles(self) -> str:
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont,
                         'Segoe UI', sans-serif;
            background: #0f0f1a;
            color: #e0e0e0;
            min-height: 100vh;
        }

        /* Navigation */
        .navbar {
            background: #1a1a2e;
            border-bottom: 1px solid #2a2a4a;
            padding: 16px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .nav-brand {
            font-size: 1.2rem;
            font-weight: 700;
            color: #00d4ff;
            letter-spacing: 2px;
        }

        .nav-links {
            display: flex;
            gap: 24px;
        }

        .nav-link {
            color: #888;
            text-decoration: none;
            font-size: 0.9rem;
            transition: color 0.2s;
        }

        .nav-link:hover,
        .nav-link.active {
            color: #00d4ff;
        }

        /* Container */
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 48px 24px;
        }

        /* Pages */
        .page {
            display: none;
        }

        .page.active {
            display: block;
        }

        /* Components */
        .nekova-title {
            font-size: 2.5rem;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 16px;
            line-height: 1.2;
        }

        .nekova-text {
            font-size: 1.1rem;
            color: #a0a0b0;
            margin-bottom: 16px;
            line-height: 1.6;
        }

        .nekova-button {
            background: linear-gradient(135deg, #00d4ff, #0088cc);
            color: white;
            border: none;
            padding: 12px 28px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            margin: 8px 8px 8px 0;
            transition: transform 0.2s, opacity 0.2s;
        }

        .nekova-button:hover {
            transform: translateY(-2px);
            opacity: 0.9;
        }

        .nekova-input {
            width: 100%;
            background: #1a1a2e;
            border: 1px solid #2a2a4a;
            color: #e0e0e0;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 1rem;
            margin-bottom: 16px;
            outline: none;
            transition: border-color 0.2s;
        }

        .nekova-input:focus {
            border-color: #00d4ff;
        }

        .nekova-image {
            max-width: 100%;
            border-radius: 8px;
            margin-bottom: 16px;
        }

        .nekova-divider {
            border: none;
            border-top: 1px solid #2a2a4a;
            margin: 24px 0;
        }

        .nekova-card {
            background: #1a1a2e;
            border: 1px solid #2a2a4a;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 16px;
        }

        .nekova-row {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            margin-bottom: 16px;
            align-items: center;
        }

        /* Footer */
        .nekova-footer {
            text-align: center;
            padding: 32px;
            color: #444;
            font-size: 0.8rem;
        }
        """

    # ----------------------------------------------------------
    # Scripts
    # ----------------------------------------------------------

    def _scripts(self) -> str:
        return """
        function showPage(name) {
            // Hide all pages
            document.querySelectorAll('.page').forEach(p => {
                p.classList.remove('active');
            });

            // Remove active from all nav links
            document.querySelectorAll('.nav-link').forEach(l => {
                l.classList.remove('active');
            });

            // Show target page
            const target = document.getElementById('page-' + name);
            if (target) {
                target.classList.add('active');
            }

            // Activate nav link
            document.querySelectorAll('.nav-link').forEach(l => {
                if (l.textContent === name) {
                    l.classList.add('active');
                }
            });
        }
        """