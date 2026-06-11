# =============================================================
# NEKOVA Deploy — Cloud Deployment Engine
# =============================================================
# Deploys NEKOVA apps to cloud providers.
#
# Supported targets:
#   1. Railway  (railway.app — free tier)
#   2. Bundle   (zip file + instructions — always works)
#
# Usage:
#   from deploy.cloud import CloudDeployer
#   deployer = CloudDeployer()
#   result = deployer.deploy("examples/web_demo.NEKOVA")

import os
import sys
import json
import shutil
import subprocess
import tempfile
from datetime import datetime


class CloudDeployer:
    """
    Deploys NEKOVA applications to cloud providers.
    """

    def __init__(self):
        self.railway_available = self._check_railway()

    def _check_railway(self) -> bool:
        """Check if Railway CLI is installed."""
        try:
            result = subprocess.run(
                ["railway", "--version"],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def deploy(self, filepath: str,
               target: str = "auto") -> dict:
        """
        Deploy an NEKOVA file to the cloud.
        Returns a dict with deployment info.
        """
        if not os.path.isfile(filepath):
            raise FileNotFoundError(
                f"File not found: '{filepath}'"
            )

        print(f"📦 Preparing deployment for '{filepath}'...")

        # Build the deployment bundle
        from deploy.bundle import AppBundler
        bundler = AppBundler()
        bundle_dir = bundler.bundle(filepath)

        # Choose deployment target
        if target == "railway" or (
            target == "auto" and self.railway_available
        ):
            return self._deploy_railway(
                bundle_dir, filepath)
        else:
            return self._deploy_bundle(
                bundle_dir, filepath)

    def _deploy_railway(self, bundle_dir: str,
                        filepath: str) -> dict:
        """Deploy to Railway.app."""
        print("🚂 Deploying to Railway...")

        try:
            # Initialize Railway project
            result = subprocess.run(
                ["railway", "init"],
                cwd=bundle_dir,
                capture_output=True, text=True
            )

            # Deploy
            result = subprocess.run(
                ["railway", "up"],
                cwd=bundle_dir,
                capture_output=True, text=True,
                timeout=120
            )

            if result.returncode == 0:
                # Extract URL from output
                url = self._extract_url(result.stdout)
                return {
                    "status":   "success",
                    "provider": "railway",
                    "url":      url,
                    "bundle":   bundle_dir,
                }
            else:
                # Fall back to bundle
                return self._deploy_bundle(
                    bundle_dir, filepath)

        except Exception as e:
            return self._deploy_bundle(
                bundle_dir, filepath)

    def _deploy_bundle(self, bundle_dir: str,
                       filepath: str) -> dict:
        """
        Create a deployable zip bundle.
        Works everywhere — no cloud account needed.
        """
        print("📦 Creating deployment bundle...")

        # Create zip file
        app_name = os.path.splitext(
            os.path.basename(filepath))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name  = f"{app_name}_deploy_{timestamp}"
        zip_path  = shutil.make_archive(
            zip_name, "zip", bundle_dir)

        # Move to deploy/ folder
        os.makedirs("deploy/output", exist_ok=True)
        final_path = os.path.join(
            "deploy/output", os.path.basename(zip_path))
        shutil.move(zip_path, final_path)

        # Generate deployment instructions
        instructions = self._generate_instructions(
            app_name, final_path)

        instructions_path = os.path.join(
            "deploy/output",
            f"{app_name}_deploy_instructions.txt")

        with open(instructions_path, "w") as f:
            f.write(instructions)

        return {
            "status":       "bundled",
            "provider":     "local",
            "bundle_path":  final_path,
            "instructions": instructions_path,
            "app_name":     app_name,
        }

    def _extract_url(self, output: str) -> str:
        """Extract deployment URL from Railway output."""
        for line in output.split("\n"):
            if "https://" in line:
                for word in line.split():
                    if word.startswith("https://"):
                        return word
        return "https://your-app.railway.app"

    def _generate_instructions(self, app_name: str,
                                bundle_path: str) -> str:
        """Generate deployment instructions."""
        return f"""
NEKOVA App Deployment Instructions
=================================
App: {app_name}
Bundle: {bundle_path}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

OPTION 1 — Deploy to Railway (Free):
--------------------------------------
1. Install Railway CLI:
   npm install -g @railway/cli

2. Login to Railway:
   railway login

3. Extract the bundle zip file

4. Navigate to the extracted folder:
   cd {app_name}_bundle

5. Deploy:
   railway init
   railway up

6. Your app will be live at: https://your-app.railway.app

OPTION 2 — Deploy to Render (Free):
--------------------------------------
1. Go to https://render.com and create an account
2. Click "New Web Service"
3. Upload the contents of the bundle zip
4. Set build command: pip install -r requirements.txt
5. Set start command: python main.py app.NEKOVA
6. Click "Create Web Service"

OPTION 3 — Run Locally:
--------------------------------------
1. Extract the bundle zip
2. Install dependencies:
   pip install -r requirements.txt
3. Run:
   python main.py {app_name}.NEKOVA

Bundle contents:
- {app_name}.NEKOVA     Your NEKOVA application
- main.py             NEKOVA runtime entry point
- requirements.txt    Python dependencies
- Procfile            Railway/Heroku process file
- README.md           Setup instructions
"""
