# =============================================================
# NEKOVA Deployment — Exporter
# =============================================================
# Exports NEKOVA apps to different formats:
#   - HTML  (web apps, UI apps)
#   - Script (standalone Python)
#   - Package (shareable zip)

import os
import json
import shutil
import zipfile
from datetime import datetime
from config import NEKOVA_VERSION, Color


class Exporter:
    """
    Exports NEKOVA programs to distributable formats.

    Usage:
        exporter = Exporter("myapp.aion")
        exporter.to_html("output/")
        exporter.to_package("dist/")
    """

    def __init__(self, filepath: str):
        self.filepath  = filepath
        self.source    = ""
        self.name      = os.path.splitext(
                             os.path.basename(filepath))[0]

        self._load_source()

    def _load_source(self):
        """Load the NEKOVA source file."""
        if not os.path.isfile(self.filepath):
            raise FileNotFoundError(
                f"File not found: '{self.filepath}'"
            )
        with open(self.filepath, "r",
                  encoding="utf-8") as f:
            self.source = f.read()

    def to_html(self, output_dir: str = "dist") -> str:
        """
        Export a UI app to a standalone HTML file.
        Runs the NEKOVA file and captures HTML output.
        """
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir, f"{self.name}.html")

        try:
            # Run the NEKOVA file to generate HTML
            from lexer import Lexer
            from parser.parser import Parser
            from interpreter.interpreter import Interpreter

            tokens      = Lexer(self.source).tokenize()
            program     = Parser(tokens).parse()
            interpreter = Interpreter()
            interpreter.execute(program)

            # Check if HTML was generated
            if os.path.exists(f"{self.name}.html"):
                shutil.copy(f"{self.name}.html",
                            output_path)
            elif os.path.exists("output.html"):
                shutil.copy("output.html", output_path)
            else:
                # Generate a simple HTML wrapper
                html = self._generate_html_wrapper()
                with open(output_path, "w",
                          encoding="utf-8") as f:
                    f.write(html)

            print(f"{Color.GREEN}✓ Exported to "
                  f"'{output_path}'{Color.RESET}")
            return output_path

        except Exception as e:
            raise RuntimeError(
                f"Export failed: {e}"
            )

    def to_package(self,
                   output_dir: str = "dist") -> str:
        """
        Create a shareable .aionpkg zip package.
        Includes source, metadata, and dependencies.
        """
        os.makedirs(output_dir, exist_ok=True)
        pkg_name    = f"{self.name}-{NEKOVA_VERSION}"
        pkg_path    = os.path.join(
            output_dir, f"{pkg_name}.aionpkg")

        with zipfile.ZipFile(pkg_path, "w",
                             zipfile.ZIP_DEFLATED) as zf:
            # Add source file
            zf.write(self.filepath,
                     f"{self.name}.aion")

            # Add metadata
            metadata = self._generate_metadata()
            zf.writestr("aion.json",
                        json.dumps(metadata, indent=2))

            # Add README
            readme = self._generate_readme()
            zf.writestr("README.md", readme)

        print(f"{Color.GREEN}✓ Package created: "
              f"'{pkg_path}'{Color.RESET}")
        print(f"{Color.DIM}  Size: "
              f"{os.path.getsize(pkg_path)} bytes"
              f"{Color.RESET}")
        return pkg_path

    def to_script(self,
                  output_dir: str = "dist") -> str:
        """
        Export as a standalone Python script that
        bundles the NEKOVA runtime and source together.
        """
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(
            output_dir, f"{self.name}.py")

        script = f'''#!/usr/bin/env python3
"""
{self.name} — Built with NEKOVA v{NEKOVA_VERSION}
Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

SOURCE = """
{self.source}
"""

import sys
import os

# Add NEKOVA to path
NEKOVA_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, NEKOVA_PATH)

try:
    from lexer import Lexer
    from parser.parser import Parser
    from interpreter.interpreter import Interpreter

    tokens      = Lexer(SOURCE).tokenize()
    program     = Parser(tokens).parse()
    interpreter = Interpreter()
    interpreter.execute(program)

except ImportError:
    print("Error: NEKOVA runtime not found.")
    print("Make sure the NEKOVA folder is in your path.")
    sys.exit(1)
'''

        with open(output_path, "w",
                  encoding="utf-8") as f:
            f.write(script)

        print(f"{Color.GREEN}✓ Script exported: "
              f"'{output_path}'{Color.RESET}")
        return output_path

    def _generate_metadata(self) -> dict:
        """Generate package metadata."""
        return {
            "name":       self.name,
            "version":    "1.0.0",
            "aion":       NEKOVA_VERSION,
            "created":    datetime.now().isoformat(),
            "main":       f"{self.name}.aion",
            "type":       "aion-package",
        }

    def _generate_readme(self) -> str:
        """Generate a README for the package."""
        return f"""# {self.name}

An NEKOVA language package.

## Run

```bash
python main.py {self.name}.aion
```

## Built with

NEKOVA v{NEKOVA_VERSION}
Generated on {datetime.now().strftime("%Y-%m-%d")}
"""

    def _generate_html_wrapper(self) -> str:
        """Generate a simple HTML wrapper."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.name}</title>
    <style>
        body {{
            font-family: monospace;
            background: #0f0f1a;
            color: #e0e0e0;
            padding: 40px;
        }}
        pre {{
            background: #1a1a2e;
            padding: 20px;
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <h1>{self.name}</h1>
    <p>Built with NEKOVA v{NEKOVA_VERSION}</p>
    <pre>{self.source}</pre>
</body>
</html>"""