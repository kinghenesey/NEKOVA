# =============================================================
# NEKOVA CLI — Deployment Commands
# =============================================================
# Handles all deployment commands:
#   python main.py export <file.aion>
#   python main.py package <project_dir>
#   python main.py publish <package.aionpkg>
#   python main.py deploy <file.aion>

import os
from config import Color
from cli import (print_success, print_error,
                 print_info, print_separator)


def cmd_export(filepath: str,
               output_dir: str = "dist") -> bool:
    """Export an NEKOVA file to HTML and script formats."""
    if not filepath:
        print_error(
            "Please provide a file to export.\n"
            "  Usage: python main.py export app.aion"
        )
        return False

    if not os.path.isfile(filepath):
        print_error(f"File not found: '{filepath}'")
        return False

    print()
    print(f"{Color.CYAN}{Color.BOLD}"
          f"  NEKOVA Exporter{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print()
    print_info(f"Exporting '{filepath}'...")
    print()

    try:
        from deploy.exporter import Exporter
        exporter = Exporter(filepath)

        # Export to HTML
        html_path = exporter.to_html(output_dir)

        # Export to script
        script_path = exporter.to_script(output_dir)

        # Export to package
        pkg_path = exporter.to_package(output_dir)

        print()
        print_separator()
        print_success(f"Export complete! Files in '{output_dir}/'")
        print()
        print(f"  {Color.DIM}HTML:    {html_path}{Color.RESET}")
        print(f"  {Color.DIM}Script:  {script_path}{Color.RESET}")
        print(f"  {Color.DIM}Package: {pkg_path}{Color.RESET}")
        print()
        return True

    except Exception as e:
        print_error(f"Export failed: {e}")
        return False


def cmd_package(project_dir: str = ".",
                output_dir: str = "dist") -> bool:
    """Package an NEKOVA project."""
    print()
    print(f"{Color.CYAN}{Color.BOLD}"
          f"  NEKOVA Packager{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print()

    try:
        from deploy.packager import Packager
        packager = Packager(project_dir)
        pkg_path = packager.build(output_dir)

        print()
        print_success(
            f"Package ready: '{pkg_path}'")
        return True

    except Exception as e:
        print_error(f"Packaging failed: {e}")
        return False


def cmd_publish(pkg_path: str) -> bool:
    """Publish an NEKOVA package to the local registry."""
    if not pkg_path:
        print_error(
            "Please provide a package to publish.\n"
            "  Usage: python main.py publish "
            "dist/myapp-1.0.0.aionpkg"
        )
        return False

    print()
    print(f"{Color.CYAN}{Color.BOLD}"
          f"  NEKOVA Publisher{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print()

    try:
        from deploy.publisher import Publisher
        publisher = Publisher()
        success   = publisher.publish_local(pkg_path)

        if success:
            print()
            # Show all published packages
            packages = publisher.list_published()
            print(f"  {Color.DIM}Registry contains "
                  f"{len(packages)} package(s)"
                  f"{Color.RESET}")
        return success

    except Exception as e:
        print_error(f"Publish failed: {e}")
        return False


def cmd_deploy(filepath: str) -> bool:
    """
    Full deployment pipeline:
    export → package → publish
    """
    if not filepath:
        print_error(
            "Please provide a file to deploy.\n"
            "  Usage: python main.py deploy app.aion"
        )
        return False

    print()
    print(f"{Color.CYAN}{Color.BOLD}"
          f"  NEKOVA Deployment Pipeline{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print()
    print_info(
        f"Deploying '{filepath}'...")
    print()

    # Step 1: Export
    print(f"  {Color.BOLD}Step 1/3{Color.RESET} "
          f"— Exporting...")
    export_ok = cmd_export(filepath, "dist")
    if not export_ok:
        return False

    # Step 2: Package
    print()
    print(f"  {Color.BOLD}Step 2/3{Color.RESET} "
          f"— Packaging...")
    package_ok = cmd_package(".", "dist")
    if not package_ok:
        return False

    # Step 3: Publish
    print()
    print(f"  {Color.BOLD}Step 3/3{Color.RESET} "
          f"— Publishing...")
    name = os.path.splitext(
        os.path.basename(filepath))[0]

    # Find the package file
    dist_dir = "dist"
    pkg_file = None
    if os.path.exists(dist_dir):
        for f in os.listdir(dist_dir):
            if f.endswith(".aionpkg"):
                pkg_file = os.path.join(dist_dir, f)
                break

    if pkg_file:
        publish_ok = cmd_publish(pkg_file)
    else:
        print_error("No package file found to publish.")
        return False

    print()
    print_separator()
    print_success(
        f"'{filepath}' deployed successfully!")
    print()
    print(f"  {Color.DIM}Output directory: dist/{Color.RESET}")
    print()
    return True

def cmd_deploy_cloud(filepath: str) -> bool:
    """
    Deploy an NEKOVA app to the cloud.
    Usage: python main.py deploy cloud app.aion
    """
    if not filepath:
        print_error(
            "Please provide a file to deploy.\n"
            "  Usage: python main.py deploy cloud app.aion"
        )
        return False

    if not os.path.isfile(filepath):
        print_error(f"File not found: '{filepath}'")
        return False

    print()
    print(f"{Color.CYAN}{Color.BOLD}"
          f"  NEKOVA Cloud Deployment{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print()

    try:
        from deploy.cloud import CloudDeployer
        deployer = CloudDeployer()
        result   = deployer.deploy(filepath)

        print()
        print_separator()

        if result["status"] == "success":
            print_success("App deployed successfully!")
            print()
            print(f"  {Color.CYAN}🌐 URL: "
                  f"{result['url']}{Color.RESET}")

        elif result["status"] == "bundled":
            print_success("Deployment bundle created!")
            print()
            print(f"  {Color.CYAN}📦 Bundle: "
                  f"{result['bundle_path']}{Color.RESET}")
            print(f"  {Color.CYAN}📄 Instructions: "
                  f"{result['instructions']}{Color.RESET}")
            print()
            print(f"  {Color.DIM}Next steps:{Color.RESET}")
            print(f"  {Color.DIM}1. Open the instructions file{Color.RESET}")
            print(f"  {Color.DIM}2. Follow the Railway or Render steps{Color.RESET}")
            print(f"  {Color.DIM}3. Your app will be live in minutes{Color.RESET}")

        print()
        return True

    except Exception as e:
        print_error(f"Cloud deployment failed: {e}")
        return False