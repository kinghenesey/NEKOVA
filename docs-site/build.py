#!/usr/bin/env python3
"""
NEKOVA Docs — Site Generator
=============================
Usage:
    python build.py            # build the site into output/
    python build.py --serve    # build, then serve on http://localhost:8000

To add a page:
    1. Write a markdown file under content/<category>/<name>.md
       with frontmatter:
           ---
           title: My Page Title
           lede: One-sentence summary shown under the title.
           ---
           ## A heading
           Regular markdown content...
    2. Add one entry to content/nav.yaml pointing at the file.
    3. Run this script again.

That's the entire workflow — no HTML or CSS editing required to
add, remove, or reorder documentation pages.
"""
import os
import re
import shutil
import sys
import html
import yaml
import markdown
import frontmatter
from jinja2 import Environment, FileSystemLoader

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(ROOT, "content")
TEMPLATES_DIR = os.path.join(ROOT, "templates")
STATIC_DIR = os.path.join(ROOT, "static")
OUTPUT_DIR = os.path.join(ROOT, "output")


# ----------------------------------------------------------------------
# NEKOVA syntax highlighting for ```nekova fenced code blocks.
# Regex-based on purpose (no external grammar dependency for the
# build) but keyword lists are pulled to match the real lexer's
# keyword table, not guessed.
# ----------------------------------------------------------------------
AI_KEYWORDS = (
    "think|remember|recall|speak|listen|imagine|watch|every|observe|mock|"
    "retry|fallback|model|autonomous|parallel|pipeline|fetch|shape|stream"
)
DECL_KEYWORDS = (
    "task|func|let|const|enum|async|await|class|object|error|schema|save|"
    "use|import|from|init|prompt"
)
CTRL_KEYWORDS = (
    "if|else|elif|repeat|while|for|in|return|break|continue|try|catch|"
    "finally|raise|pass|match|when|yield|with|global|assert|is|not|and|or|"
    "show|route|serve"
)
CONST_KEYWORDS = "true|false|null"


def highlight_nekova(code: str) -> str:
    """Tokenize a NEKOVA snippet into spans for theme.css's .tok-* classes."""
    placeholders = []

    def stash(match, css_class):
        token = f"\x00PH{len(placeholders)}PH\x00"
        placeholders.append((token, css_class, match.group(0)))
        return token

    # 1. Pull out comments and strings first so keyword matching never
    #    reaches inside them.
    code = re.sub(r"#.*", lambda m: stash(m, "tok-com"), code)
    code = re.sub(
        r'f?"""[\s\S]*?"""|f?\'\'\'[\s\S]*?\'\'\'|f?"[^"\n]*"|f?\'[^\'\n]*\'',
        lambda m: stash(m, "tok-str"),
        code,
    )

    # 2. Escape remaining HTML-sensitive characters.
    code = html.escape(code)

    # 3. Keywords — all four categories matched in a SINGLE regex pass.
    #    Sequential passes are a trap here: injecting <span class="tok-ai">
    #    for 'think' introduces the literal word "class" into the output,
    #    which a later pass for declaration keywords (which includes
    #    'class') would then re-match and corrupt. One combined pattern
    #    with named groups avoids re-scanning already-substituted HTML.
    combined = re.compile(
        rf"\b(?P<ai>{AI_KEYWORDS})\b"
        rf"|\b(?P<const>{CONST_KEYWORDS})\b"
        rf"|\b(?P<decl>{DECL_KEYWORDS})\b"
        rf"|\b(?P<ctrl>{CTRL_KEYWORDS})\b"
        rf"|\b(?P<num>\d+\.?\d*)\b"
    )

    def kw_repl(m):
        if m.group("ai"):    return f'<span class="tok-ai">{m.group("ai")}</span>'
        if m.group("const"): return f'<span class="tok-const">{m.group("const")}</span>'
        if m.group("decl"):  return f'<span class="tok-decl">{m.group("decl")}</span>'
        if m.group("ctrl"):  return f'<span class="tok-kw">{m.group("ctrl")}</span>'
        if m.group("num"):   return f'<span class="tok-num">{m.group("num")}</span>'
        return m.group(0)

    code = combined.sub(kw_repl, code)

    # 4. Restore strings/comments (escaped + wrapped) now that keyword
    #    substitution is safely done.
    for token, css_class, original in placeholders:
        escaped = html.escape(original)
        code = code.replace(token, f'<span class="{css_class}">{escaped}</span>')

    return code


def render_fenced_code(md_html: str) -> str:
    """
    Post-process python-markdown's fenced-code output:
    <pre><code class="language-nekova">...</code></pre>
    -> apply highlight_nekova() to the raw text inside, add glow-border.
    """
    pattern = re.compile(
        r'<pre><code class="language-nekova">([\s\S]*?)</code></pre>'
    )

    def repl(m):
        raw = html.unescape(m.group(1))
        highlighted = highlight_nekova(raw)
        return f'<pre class="glow-border"><code>{highlighted}</code></pre>'

    md_html = pattern.sub(repl, md_html)

    # Any other fenced block (bash, text, etc.) still gets the glow
    # border for visual consistency, just no token highlighting.
    md_html = re.sub(
        r'<pre>(?!<code>)?<code class="language-(\w+)">',
        r'<pre class="glow-border"><code class="language-\1">',
        md_html,
    )
    return md_html


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s]+", "-", slug)


def extract_toc(md_html: str):
    """Pull h2/h3 headings out of rendered HTML, inject ids, return a
    (modified_html, toc_list) pair for the right-hand mini-TOC."""
    toc = []
    seen = {}

    def repl(m):
        level = int(m.group(1))
        inner = m.group(2)
        text = re.sub(r"<[^>]+>", "", inner)
        base_id = slugify(text)
        n = seen.get(base_id, 0)
        seen[base_id] = n + 1
        heading_id = base_id if n == 0 else f"{base_id}-{n}"
        toc.append({"level": level, "text": text, "id": heading_id})
        return f'<h{level} id="{heading_id}">{inner}</h{level}>'

    md_html = re.sub(r"<h([23])>(.*?)</h\1>", repl, md_html)
    return md_html, toc


def load_nav():
    with open(os.path.join(CONTENT_DIR, "nav.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def flatten_nav(nav):
    """Returns (grouped_for_sidebar, linear_list_for_prev_next)."""
    grouped = []
    linear = []
    for group in nav:
        items = []
        for item in group["items"]:
            href = "docs/" + item["file"].replace(".md", ".html")
            entry = {"title": item["title"], "href": href, "file": item["file"],
                      "group_label": group["label"]}
            items.append(entry)
            linear.append(entry)
        grouped.append({"label": group["label"], "items": items})
    return grouped, linear


def build():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    nav = load_nav()
    grouped_nav, linear_nav = flatten_nav(nav)

    md_converter = markdown.Markdown(
        extensions=["fenced_code", "tables", "sane_lists", "attr_list"]
    )

    # --- Build each documentation page ---
    for i, entry in enumerate(linear_nav):
        src_path = os.path.join(CONTENT_DIR, entry["file"])
        if not os.path.exists(src_path):
            print(f"  [skip] {entry['file']} listed in nav.yaml but not found")
            continue

        post = frontmatter.load(src_path)
        md_converter.reset()
        body_html = md_converter.convert(post.content)
        body_html = render_fenced_code(body_html)
        body_html, toc = extract_toc(body_html)

        prev_page = linear_nav[i - 1] if i > 0 else None
        next_page = linear_nav[i + 1] if i < len(linear_nav) - 1 else None

        out_rel = entry["href"]
        depth = out_rel.count("/")
        root_prefix = "../" * depth

        html_out = env.get_template("page.html").render(
            root=root_prefix,
            nav=grouped_nav,
            current_href=entry["href"],
            group_label=entry["group_label"],
            page_title=post.get("title", entry["title"]),
            page_description=post.get("lede", ""),
            lede=post.get("lede", ""),
            content=body_html,
            toc=toc,
            prev_page=prev_page,
            next_page=next_page,
        )

        out_path = os.path.join(OUTPUT_DIR, out_rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_out)

    # --- Build the landing page ---
    home_html = env.get_template("home.html").render(
        root="",
        page_title="NEKOVA — The AI-Native Programming Language",
        page_description="NEKOVA is a programming language with AI reasoning "
                          "built into its grammar. Built in Nigeria.",
    )
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(home_html)

    # --- Copy static assets ---
    shutil.copytree(STATIC_DIR, os.path.join(OUTPUT_DIR, "static"))

    print(f"Built {len(linear_nav)} documentation pages + landing page")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import http.server
        import socketserver

        os.chdir(OUTPUT_DIR)
        PORT = 8000
        with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
            print(f"Serving at http://localhost:{PORT}")
            httpd.serve_forever()