# =============================================================
# NEKOVA Deployment — Packager
# =============================================================
# Creates distributable NEKOVA project packages.
#
# A package includes:
#   - All .nekova source files
#   - Dependencies (stdlib modules used)
#   - Configuration (nekova.json)
#   - README and documentation
#   - Examples

import os
import json
import shutil
import zipfile
from datetime import datetime
from config import NEKOVA_VERSION, Color


class Packager:
    """
    Creates distributable NEKOVA packages from projects.

    Usage:
        packager = Packager("myproject/")
        packager.build("dist/")
    """

    def __init__(self, project_dir: str = "."):
        self.project_dir = project_dir
        self.config      = self._load_config()
        self.name        = self.config.get(
                               "name", "nekova-project")
        self.version     = self.config.get(
                               "version", "1.0.0")

    def build(self, output_dir: str = "dist") -> str:
        """
        Build a complete project package.
        Returns path to the created package.
        """
        os.makedirs(output_dir, exist_ok=True)

        pkg_name = f"{self.name}-{self.version}"
        pkg_path = os.path.join(
            output_dir, f"{pkg_name}.nekovapkg")

        print(f"{Color.CYAN}  Packaging "
              f"'{self.name}'...{Color.RESET}")

        with zipfile.ZipFile(pkg_path, "w",
                             zipfile.ZIP_DEFLATED) as zf:

            # Add all .nekova files
            nekova_files = self._find_nekova_files()
            for filepath in nekova_files:
                arcname = os.path.relpath(
                    filepath, self.project_dir)
                zf.write(filepath, arcname)
                print(f"{Color.DIM}  + {arcname}"
                      f"{Color.RESET}")

            # Add config
            config = self._generate_config()
            zf.writestr("nekova.json",
                        json.dumps(config, indent=2))

            # Add README if exists
            readme_path = os.path.join(
                self.project_dir, "README.md")
            if os.path.exists(readme_path):
                zf.write(readme_path, "README.md")
            else:
                zf.writestr("README.md",
                            self._generate_readme())

            # Add manifest
            manifest = self._generate_manifest(
                nekova_files)
            zf.writestr("MANIFEST.json",
                        json.dumps(manifest, indent=2))

        size = os.path.getsize(pkg_path)
        print(f"{Color.GREEN}✓ Package built: "
              f"'{pkg_path}' "
              f"({size} bytes){Color.RESET}")

        return pkg_path

    def install_from_package(self,
                             pkg_path: str,
                             target_dir: str = "."):
        """
        Install an .nekovapkg package.
        Extracts to target directory.
        """
        if not os.path.exists(pkg_path):
            raise FileNotFoundError(
                f"Package not found: '{pkg_path}'"
            )

        print(f"{Color.CYAN}  Installing "
              f"'{pkg_path}'...{Color.RESET}")

        with zipfile.ZipFile(pkg_path, "r") as zf:
            # Read manifest
            try:
                manifest = json.loads(
                    zf.read("MANIFEST.json"))
                name = manifest.get("name", "package")
            except Exception:
                name = os.path.basename(pkg_path)

            # Extract to target
            install_dir = os.path.join(
                target_dir, name)
            os.makedirs(install_dir, exist_ok=True)
            zf.extractall(install_dir)

        print(f"{Color.GREEN}✓ Installed to "
              f"'{install_dir}'{Color.RESET}")
        return install_dir

    def _find_nekova_files(self) -> list:
        """Find all .nekova files in the project."""
        nekova_files = []
        for root, dirs, files in os.walk(
                self.project_dir):
            # Skip hidden and cache dirs
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d != "__pycache__"
                and d != "venv"
                and d != "dist"
            ]
            for f in files:
                if f.endswith(".nekova"):
                    nekova_files.append(
                        os.path.join(root, f))
        return nekova_files

    def _load_config(self) -> dict:
        """Load project config from nekova.json."""
        config_path = os.path.join(
            self.project_dir, "nekova.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
        return {}

    def _generate_config(self) -> dict:
        """Generate package config."""
        return {
            "name":      self.name,
            "version":   self.version,
            "nekova":      NEKOVA_VERSION,
            "built":     datetime.now().isoformat(),
            "type":      "nekova-package",
            "main":      self.config.get(
                             "main", "main.nekova"),
        }

    def _generate_manifest(self,
                           files: list) -> dict:
        """Generate package manifest."""
        return {
            "name":     self.name,
            "version":  self.version,
            "nekova":     NEKOVA_VERSION,
            "files":    [
                os.path.relpath(f, self.project_dir)
                for f in files
            ],
            "created":  datetime.now().isoformat(),
        }

    def _generate_readme(self) -> str:
        """Generate default README."""
        return f"""# {self.name}

Version {self.version} — Built with NEKOVA v{NEKOVA_VERSION}

## Run

```bash
python main.py {self.config.get('main', 'main.nekova')}
```
"""