# =============================================================
# NEKOVA Deployment — Publisher
# =============================================================
# Publishes NEKOVA packages to registries.
#
# Currently supports:
#   - Local registry (always available)
#   - GitHub (via git commands)
#   - Future: NEKOVA Cloud Registry
#
# This lays the foundation for a future NEKOVA package
# ecosystem where developers share their modules.

import os
import json
import shutil
from datetime import datetime
from config import NEKOVA_VERSION, Color


# Local registry path
LOCAL_REGISTRY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "packages", "registry"
)


class Publisher:
    """
    Publishes NEKOVA packages to registries.

    Usage:
        publisher = Publisher()
        publisher.publish("dist/myapp-1.0.0.nekovapkg")
    """

    def __init__(self):
        self.registry_path = os.path.abspath(
            LOCAL_REGISTRY)
        os.makedirs(self.registry_path, exist_ok=True)

    def publish_local(self, pkg_path: str) -> bool:
        """
        Publish a package to the local registry.
        Makes it available for others on this machine.
        """
        if not os.path.exists(pkg_path):
            raise FileNotFoundError(
                f"Package not found: '{pkg_path}'"
            )

        pkg_name = os.path.basename(pkg_path)
        dest     = os.path.join(
            self.registry_path, pkg_name)

        # Copy package to registry
        shutil.copy2(pkg_path, dest)

        # Update registry index
        self._update_index(pkg_path, pkg_name)

        print(f"{Color.GREEN}✓ Published '{pkg_name}' "
              f"to local registry{Color.RESET}")
        print(f"{Color.DIM}  Location: "
              f"{self.registry_path}{Color.RESET}")
        return True

    def publish_github(self,
                       pkg_path: str,
                       repo: str = "") -> bool:
        """
        Publish by pushing to GitHub.
        Requires git to be configured.
        """
        import subprocess

        print(f"{Color.CYAN}  Publishing to "
              f"GitHub...{Color.RESET}")

        try:
            # Add and commit
            subprocess.run(
                ["git", "add", pkg_path],
                check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m",
                 f"Publish {os.path.basename(pkg_path)}"],
                check=True, capture_output=True
            )
            subprocess.run(
                ["git", "push"],
                check=True, capture_output=True
            )

            print(f"{Color.GREEN}✓ Published to "
                  f"GitHub{Color.RESET}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"{Color.YELLOW}⚠ Git publish "
                  f"failed: {e}{Color.RESET}")
            return False

    def list_published(self) -> list:
        """List all locally published packages."""
        packages = []
        if not os.path.exists(self.registry_path):
            return packages

        for f in os.listdir(self.registry_path):
            if f.endswith(".nekovapkg"):
                path = os.path.join(
                    self.registry_path, f)
                size = os.path.getsize(path)
                packages.append({
                    "name": f,
                    "size": size,
                    "path": path,
                })

        return packages

    def unpublish(self, pkg_name: str) -> bool:
        """Remove a package from the local registry."""
        pkg_path = os.path.join(
            self.registry_path, pkg_name)

        if not os.path.exists(pkg_path):
            print(f"{Color.RED}✗ Package "
                  f"'{pkg_name}' not found "
                  f"in registry{Color.RESET}")
            return False

        os.remove(pkg_path)
        self._update_index_remove(pkg_name)

        print(f"{Color.GREEN}✓ Unpublished "
              f"'{pkg_name}'{Color.RESET}")
        return True

    def _update_index(self, pkg_path: str,
                      pkg_name: str):
        """Update the registry index file."""
        index_path = os.path.join(
            self.registry_path, "index.json")

        index = self._load_index()
        index[pkg_name] = {
            "name":      pkg_name,
            "published": datetime.now().isoformat(),
            "size":      os.path.getsize(pkg_path),
            "nekova":      NEKOVA_VERSION,
        }

        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)

    def _update_index_remove(self, pkg_name: str):
        """Remove a package from the index."""
        index_path = os.path.join(
            self.registry_path, "index.json")

        index = self._load_index()
        if pkg_name in index:
            del index[pkg_name]

        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)

    def _load_index(self) -> dict:
        """Load the registry index."""
        index_path = os.path.join(
            self.registry_path, "index.json")

        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                return json.load(f)
        return {}

    def __repr__(self):
        packages = self.list_published()
        return (f"Publisher("
                f"{len(packages)} packages published)")