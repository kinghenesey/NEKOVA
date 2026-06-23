# =============================================================
# NEKOVA Package Manager — CLI Interface  (Phase 11)
# =============================================================

import os
import sys
import json

from nekova.config import Color
from nekova.cli    import print_success, print_error, print_info, print_warning
from nekova.packages import (
    BUILTIN_PACKAGES, load_registry, save_registry,
    is_installed, PACKAGES_DIR, search_packages,
)

_BOLD  = f"{Color.BOLD}"
_DIM   = f"{Color.DIM}"
_GREEN = f"{Color.GREEN}"
_RED   = "\x1b[38;5;196m"
_GOLD  = "\x1b[38;5;172m"
_CYAN  = f"{Color.CYAN}"
_RESET = f"{Color.RESET}"


# ── install ───────────────────────────────────────────────────

def install_package(name: str) -> bool:
    """
    Install a package by name.
    Returns True if successful.
    """
    name = name.strip().lower()

    if is_installed(name):
        print_warning(f"'{name}' is already installed.")
        return True

    if name not in BUILTIN_PACKAGES:
        # Try fuzzy suggestion
        close = [k for k in BUILTIN_PACKAGES if name in k or k in name]
        msg = f"Package '{name}' was not found in the NEKOVA registry."
        if close:
            msg += f"\n  Did you mean: {', '.join(close)}?"
        else:
            available = ", ".join(sorted(BUILTIN_PACKAGES.keys()))
            msg += f"\n  Available packages: {available}"
        print_error(msg)
        return False

    package = BUILTIN_PACKAGES[name]

    # Install any Python dependencies first
    py_deps = package.get("requires", [])
    for dep in py_deps:
        if not _pip_available(dep):
            print_info(f"Installing Python dependency: {dep}")
            ret = os.system(f"{sys.executable} -m pip install {dep} -q")
            if ret != 0:
                print_warning(
                    f"Could not install '{dep}' automatically.\n"
                    f"  Run manually:  pip install {dep}"
                )

    # Generate the package module
    if not _create_package_module(name, package):
        return False

    # Update registry
    registry = load_registry()
    registry[name] = {
        "name":        package["name"],
        "version":     package["version"],
        "description": package["description"],
        "category":    package.get("category", ""),
        "installed":   True,
    }
    save_registry(registry)

    print_success(
        f"Installed '{name}' v{package['version']} — "
        f"{package['description']}"
    )
    print_info(f"Use it in NEKOVA with:  use {name}")
    return True


def install_from_toml(toml_path: str = "nekova.toml") -> bool:
    """
    Read [dependencies] from nekova.toml and install all listed packages.
    Returns True if all succeeded.
    """
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            print_error(
                "Cannot read nekova.toml — install tomli:\n"
                "  pip install tomli"
            )
            return False

    if not os.path.exists(toml_path):
        print_error(f"No {toml_path} found in this directory.")
        return False

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    packages = (config
                .get("dependencies", {})
                .get("packages", []))

    if not packages:
        print_info("No dependencies listed in nekova.toml.")
        return True

    all_ok = True
    for pkg in packages:
        ok = install_package(pkg)
        if not ok:
            all_ok = False

    return all_ok


# ── uninstall ─────────────────────────────────────────────────

def uninstall_package(name: str) -> bool:
    """Uninstall a package by name."""
    name = name.strip().lower()

    if not is_installed(name):
        print_error(f"'{name}' is not installed.")
        return False

    # Remove module file
    module_path = os.path.join(PACKAGES_DIR, f"{name}.py")
    if os.path.exists(module_path):
        os.remove(module_path)

    # Update registry
    registry = load_registry()
    registry.pop(name, None)
    save_registry(registry)

    print_success(f"Uninstalled '{name}' successfully.")
    return True


# ── search ────────────────────────────────────────────────────

def search(query: str) -> bool:
    """Search the package registry."""
    results = search_packages(query)

    print()
    print(f"{_CYAN}{_BOLD}  NEKOVA Package Search: '{query}'{_RESET}")
    print(f"  {_DIM}{'─' * 44}{_RESET}")

    if not results:
        print(f"  {_DIM}No packages found matching '{query}'.{_RESET}")
        print(f"  {_DIM}Try: nekova search all  to see everything.{_RESET}")
        print()
        return True

    installed = load_registry()
    for name, info in results:
        _print_package_row(name, info, name in installed)

    print(f"  {_DIM}{len(results)} package(s) found.{_RESET}")
    print()
    return True


# ── list ──────────────────────────────────────────────────────

def list_packages(category: str = None) -> bool:
    """Display all available packages, optionally filtered by category."""
    available = BUILTIN_PACKAGES
    installed = load_registry()

    if category:
        available = {k: v for k, v in available.items()
                     if v.get("category", "") == category}

    # Group by category
    categories = {}
    for name, info in available.items():
        cat = info.get("category", "other")
        categories.setdefault(cat, []).append((name, info))

    print()
    print(f"{_CYAN}{_BOLD}  NEKOVA Package Registry{_RESET}")
    print(f"  {_DIM}{'─' * 44}{_RESET}")
    print()

    for cat, pkgs in sorted(categories.items()):
        print(f"  {_BOLD}{cat.upper()}{_RESET}")
        for name, info in sorted(pkgs):
            _print_package_row(name, info, name in installed)
        print()

    total      = len(available)
    inst_count = sum(1 for n in available if n in installed)
    print(f"  {_DIM}{inst_count}/{total} packages installed"
          f"  ·  nekova install <name>{_RESET}")
    print()
    return True


def _print_package_row(name, info, is_inst):
    status = (f"{_GREEN}✓ installed{_RESET}"
              if is_inst else
              f"{_DIM}  available{_RESET}")
    version = info["version"]
    desc    = info["description"]
    fns     = info.get("functions", [])
    fn_str  = ", ".join(fns[:3])
    if len(fns) > 3:
        fn_str += f" +{len(fns)-3} more"

    print(f"  {_BOLD}{name:<16}{_RESET}"
          f"{_DIM}v{version:<8}{_RESET}"
          f"{status}")
    print(f"  {'':16}{_DIM}{desc}{_RESET}")
    if fn_str:
        print(f"  {'':16}{_DIM}→ {fn_str}{_RESET}")
    print()


# ── publish ───────────────────────────────────────────────────

def publish_package(directory: str = ".") -> bool:
    """
    Package a NEKOVA project for publishing.
    Reads nekova.toml, bundles .nk files, creates a .nkpkg archive.
    """
    import zipfile, datetime

    toml_path = os.path.join(directory, "nekova.toml")
    if not os.path.exists(toml_path):
        print_error(
            f"No nekova.toml found in '{directory}'.\n"
            "  Run  nekova new <name>  to scaffold a project."
        )
        return False

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(toml_path, "rb") as f:
            config = tomllib.load(f)
    except Exception as e:
        print_error(f"Could not read nekova.toml: {e}")
        return False

    proj    = config.get("project", {})
    name    = proj.get("name", "unnamed")
    version = proj.get("version", "0.1.0")
    author  = proj.get("author", "unknown")

    pkg_name = f"{name}-{version}.nkpkg"
    pkg_path = os.path.join(directory, pkg_name)

    print_info(f"Building package: {pkg_name}")

    try:
        with zipfile.ZipFile(pkg_path, "w",
                             zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            manifest = {
                "name":       name,
                "version":    version,
                "author":     author,
                "built_at":   datetime.datetime.utcnow().isoformat(),
                "nekova_version": "1.2.0",
            }
            zf.writestr("manifest.json",
                        json.dumps(manifest, indent=2))

            # Add nekova.toml
            zf.write(toml_path,
                     arcname="nekova.toml")

            # Add all .nk files
            nk_count = 0
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs
                           if not d.startswith(".")
                           and d not in ("__pycache__",
                                         ".git", "dist",
                                         "build")]
                for fname in files:
                    if fname.endswith(".nk"):
                        fpath  = os.path.join(root, fname)
                        arcname = os.path.relpath(fpath, directory)
                        zf.write(fpath, arcname=arcname)
                        nk_count += 1

    except Exception as e:
        print_error(f"Failed to create package: {e}")
        return False

    size_kb = os.path.getsize(pkg_path) / 1024
    print_success(
        f"Package created: {pkg_name}  "
        f"({nk_count} files, {size_kb:.1f} KB)"
    )
    print()
    print(f"  {_DIM}To publish to the NEKOVA registry:{_RESET}")
    print(f"  {_DIM}  nekova publish {pkg_name}{_RESET}")
    print(f"  {_DIM}  (Registry publishing coming in NEKOVA v1.3){_RESET}")
    print()
    return True


# ── info ──────────────────────────────────────────────────────

def package_info(name: str) -> bool:
    """Show detailed info about a single package."""
    name = name.strip().lower()

    if name not in BUILTIN_PACKAGES:
        print_error(f"Package '{name}' not found.")
        return False

    info      = BUILTIN_PACKAGES[name]
    installed = is_installed(name)

    print()
    print(f"  {_BOLD}{_CYAN}{info['name']}{_RESET}  "
          f"{_DIM}v{info['version']}{_RESET}")
    print(f"  {info['description']}")
    print()
    print(f"  {_DIM}Author:    {info.get('author', 'NEKOVA Core Team')}{_RESET}")
    print(f"  {_DIM}Category:  {info.get('category', 'general')}{_RESET}")
    status = f"{_GREEN}Installed{_RESET}" if installed else f"{_GOLD}Not installed{_RESET}"
    print(f"  {_DIM}Status:    {_RESET}{status}")
    print()

    fns = info.get("functions", [])
    if fns:
        print(f"  {_BOLD}Functions:{_RESET}")
        for fn in fns:
            print(f"  {_DIM}  · {fn}(){_RESET}")
        print()

    requires = info.get("requires", [])
    if requires:
        print(f"  {_DIM}Python deps: {', '.join(requires)}{_RESET}")
        print()

    if not installed:
        print(f"  Install with:  {_BOLD}nekova install {name}{_RESET}")
    else:
        print(f"  Use in NEKOVA: {_BOLD}use {name}{_RESET}")
    print()
    return True


# ── helpers ───────────────────────────────────────────────────

def _pip_available(package_name: str) -> bool:
    """Check if a Python package is already importable."""
    import importlib.util
    return importlib.util.find_spec(package_name) is not None


def _create_package_module(name: str, package: dict) -> bool:
    """Write the package module file into packages/."""
    os.makedirs(PACKAGES_DIR, exist_ok=True)
    module_path = os.path.join(PACKAGES_DIR, f"{name}.py")
    try:
        content = _generate_module_code(name, package)
        with open(module_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print_error(f"Failed to create package module: {e}")
        return False


def _generate_module_code(name: str, package: dict) -> str:
    """Dispatch to the right generator."""
    generators = {
        "charts":     _gen_charts,
        "auth":       _gen_auth,
        "validation": _gen_validation,
        "colors":     _gen_colors,
        "random":     _gen_random,
        "requests":   _gen_requests,
        "openai":     _gen_openai,
        "stripe":     _gen_stripe,
        "sendmail":   _gen_sendmail,
        "csv":        _gen_csv,
        "slug":       _gen_slug,
    }
    gen = generators.get(name)
    if gen:
        return gen()
    return (f"# NEKOVA Package — {name}\n"
            f"def load() -> dict:\n    return {{}}\n")


# ══ Module generators ════════════════════════════════════════

def _gen_charts() -> str:
    return '''# NEKOVA Package — charts
def load() -> dict:
    return {
        "bar_chart":  _bar_chart,
        "line_chart": _line_chart,
        "pie_chart":  _pie_chart,
    }

def _bar_chart(data: list, width: int = 20):
    if not data: return ""
    max_val = max(data) if max(data) > 0 else 1
    lines = []
    for i, val in enumerate(data):
        bar = "#" * int((val / max_val) * int(width))
        lines.append(f"  {i+1:>2} | {bar} {val}")
    return "\\n".join(lines)

def _line_chart(data: list, width: int = 40):
    if not data: return ""
    max_val = max(data) if max(data) > 0 else 1
    min_val = min(data)
    height  = 10
    lines   = []
    for row in range(height, -1, -1):
        line = ""
        for val in data:
            normalized = (val - min_val) / (max_val - min_val + 0.001)
            line += "o" if int(normalized * height) >= row else " "
        lines.append(f"  |{line}")
    lines.append(f"  +{'─' * len(data)}")
    return "\\n".join(lines)

def _pie_chart(data: dict):
    if not data: return ""
    total = sum(data.values())
    lines = ["  Pie Chart:"]
    for label, val in data.items():
        pct = (val / total) * 100 if total > 0 else 0
        bar = "#" * int(pct / 5)
        lines.append(f"  {label:<12} | {bar} {pct:.1f}%")
    return "\\n".join(lines)
'''


def _gen_auth() -> str:
    return '''# NEKOVA Package — auth
import hashlib, secrets

def load() -> dict:
    return {
        "hash_password":  _hash_password,
        "check_password": _check_password,
        "generate_token": _generate_token,
    }

def _hash_password(password: str) -> str:
    salt   = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + str(password)).encode()).hexdigest()
    return f"{salt}:{hashed}"

def _check_password(password: str, hashed: str) -> bool:
    try:
        salt, hash_val = hashed.split(":")
        check = hashlib.sha256((salt + str(password)).encode()).hexdigest()
        return secrets.compare_digest(check, hash_val)
    except Exception:
        return False

def _generate_token(length: int = 32) -> str:
    return secrets.token_hex(int(length))
'''


def _gen_validation() -> str:
    return r'''# NEKOVA Package — validation
import re

def load() -> dict:
    return {
        "is_email":           _is_email,
        "is_phone":           _is_phone,
        "is_url":             _is_url,
        "is_strong_password": _is_strong_password,
    }

def _is_email(v: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", str(v)))

def _is_phone(v: str) -> bool:
    return bool(re.match(r"^\+?[0-9]{7,15}$", str(v).replace(" ", "")))

def _is_url(v: str) -> bool:
    return bool(re.match(r"^https?://[^\s/$.?#].[^\s]*$", str(v)))

def _is_strong_password(v: str) -> bool:
    s = str(v)
    return (len(s) >= 8 and any(c.isupper() for c in s)
            and any(c.islower() for c in s)
            and any(c.isdigit() for c in s))
'''


def _gen_colors() -> str:
    return '''# NEKOVA Package — colors
def load() -> dict:
    return {
        "red":    lambda t: f"\\033[91m{t}\\033[0m",
        "green":  lambda t: f"\\033[92m{t}\\033[0m",
        "yellow": lambda t: f"\\033[93m{t}\\033[0m",
        "blue":   lambda t: f"\\033[94m{t}\\033[0m",
        "bold":   lambda t: f"\\033[1m{t}\\033[0m",
        "dim":    lambda t: f"\\033[2m{t}\\033[0m",
    }
'''


def _gen_random() -> str:
    return '''# NEKOVA Package — random
import importlib
_r = importlib.import_module("random")

def load() -> dict:
    return {
        "random_int":    lambda a, b: _r.randint(int(a), int(b)),
        "random_float":  lambda a, b: _r.uniform(float(a), float(b)),
        "random_choice": lambda lst: _r.choice(lst),
        "shuffle":       lambda lst: _r.sample(lst, len(lst)),
        "random_token":  lambda n=8: "".join(
            _r.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=int(n))),
    }
'''


def _gen_requests() -> str:
    return '''# NEKOVA Package — requests
# Simple HTTP client wrapping the requests library

def load() -> dict:
    return {
        "http_get":     _get,
        "http_post":    _post,
        "http_put":     _put,
        "http_delete":  _delete,
        "http_headers": _default_headers,
    }

def _get(url: str, headers: dict = None, params: dict = None):
    """
    Send a GET request.
    Returns a dict with: status, body, json, headers, ok
    """
    import requests as _req
    try:
        r = _req.get(str(url), headers=headers or {},
                     params=params or {}, timeout=30)
        return _wrap(r)
    except Exception as e:
        return _error(str(e))

def _post(url: str, data=None, json_data=None, headers: dict = None):
    """Send a POST request with optional body or JSON."""
    import requests as _req
    try:
        kw = {"headers": headers or {}, "timeout": 30}
        if json_data is not None:
            kw["json"] = json_data
        elif data is not None:
            kw["data"] = data
        r = _req.post(str(url), **kw)
        return _wrap(r)
    except Exception as e:
        return _error(str(e))

def _put(url: str, data=None, json_data=None, headers: dict = None):
    import requests as _req
    try:
        kw = {"headers": headers or {}, "timeout": 30}
        if json_data is not None:
            kw["json"] = json_data
        elif data is not None:
            kw["data"] = data
        r = _req.put(str(url), **kw)
        return _wrap(r)
    except Exception as e:
        return _error(str(e))

def _delete(url: str, headers: dict = None):
    import requests as _req
    try:
        r = _req.delete(str(url), headers=headers or {}, timeout=30)
        return _wrap(r)
    except Exception as e:
        return _error(str(e))

def _default_headers(content_type: str = "application/json",
                     auth_token: str = None) -> dict:
    h = {"Content-Type": content_type}
    if auth_token:
        h["Authorization"] = f"Bearer {auth_token}"
    return h

def _wrap(r) -> dict:
    json_body = None
    try:
        json_body = r.json()
    except Exception:
        pass
    return {
        "status":  r.status_code,
        "ok":      r.ok,
        "body":    r.text,
        "json":    json_body,
        "headers": dict(r.headers),
    }

def _error(msg: str) -> dict:
    return {"status": 0, "ok": False, "body": msg,
            "json": None, "headers": {}}
'''


def _gen_openai() -> str:
    return '''# NEKOVA Package — openai
# OpenAI GPT integration

def load() -> dict:
    return {
        "gpt_chat":     _chat,
        "gpt_complete": _complete,
        "gpt_embed":    _embed,
        "gpt_image":    _image,
        "gpt_models":   _models,
    }

def _get_client():
    import os
    try:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable not set.\\n"
                "  Set it with:  env_set(\\"OPENAI_API_KEY\\", \\"sk-...\\")"
            )
        return OpenAI(api_key=api_key)
    except ImportError:
        raise RuntimeError(
            "openai package not installed.\\n"
            "  Run:  pip install openai"
        )

def _chat(prompt: str, model: str = "gpt-4o-mini",
          system: str = None) -> str:
    """Send a chat message and return the reply text."""
    client = _get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": str(system)})
    messages.append({"role": "user", "content": str(prompt)})
    resp = client.chat.completions.create(
        model=str(model), messages=messages
    )
    return resp.choices[0].message.content

def _complete(prompt: str, model: str = "gpt-3.5-turbo-instruct",
              max_tokens: int = 256) -> str:
    """Legacy completion endpoint."""
    client = _get_client()
    resp = client.completions.create(
        model=str(model),
        prompt=str(prompt),
        max_tokens=int(max_tokens)
    )
    return resp.choices[0].text.strip()

def _embed(text: str,
           model: str = "text-embedding-3-small") -> list:
    """Get embedding vector for text."""
    client = _get_client()
    resp = client.embeddings.create(
        model=str(model), input=str(text)
    )
    return resp.data[0].embedding

def _image(prompt: str, size: str = "1024x1024",
           model: str = "dall-e-3") -> str:
    """Generate an image URL from a text prompt."""
    client = _get_client()
    resp = client.images.generate(
        model=str(model),
        prompt=str(prompt),
        size=str(size),
        n=1,
    )
    return resp.data[0].url

def _models() -> list:
    """List available OpenAI models."""
    client = _get_client()
    models = client.models.list()
    return [m.id for m in models.data]
'''


def _gen_stripe() -> str:
    return '''# NEKOVA Package — stripe
# Stripe payments integration

def load() -> dict:
    return {
        "stripe_charge":       _charge,
        "stripe_customer":     _customer,
        "stripe_subscription": _subscription,
        "stripe_refund":       _refund,
    }

def _get_stripe():
    import os
    try:
        import stripe as _stripe
        api_key = os.environ.get("STRIPE_SECRET_KEY", "")
        if not api_key:
            raise RuntimeError(
                "STRIPE_SECRET_KEY environment variable not set."
            )
        _stripe.api_key = api_key
        return _stripe
    except ImportError:
        raise RuntimeError("stripe package not installed. Run: pip install stripe")

def _charge(amount: int, currency: str = "usd",
            description: str = "", source: str = None) -> dict:
    """
    Create a payment charge.
    amount: amount in smallest currency unit (cents for USD)
    """
    s = _get_stripe()
    try:
        charge = s.Charge.create(
            amount=int(amount),
            currency=str(currency),
            description=str(description),
            source=source or "tok_visa",
        )
        return {"id": charge.id, "status": charge.status,
                "amount": charge.amount, "ok": True}
    except Exception as e:
        return {"id": None, "status": "failed", "ok": False,
                "error": str(e)}

def _customer(email: str, name: str = None,
              metadata: dict = None) -> dict:
    s = _get_stripe()
    try:
        cust = s.Customer.create(
            email=str(email),
            name=str(name) if name else None,
            metadata=metadata or {},
        )
        return {"id": cust.id, "email": cust.email, "ok": True}
    except Exception as e:
        return {"id": None, "ok": False, "error": str(e)}

def _subscription(customer_id: str, price_id: str) -> dict:
    s = _get_stripe()
    try:
        sub = s.Subscription.create(
            customer=str(customer_id),
            items=[{"price": str(price_id)}],
        )
        return {"id": sub.id, "status": sub.status, "ok": True}
    except Exception as e:
        return {"id": None, "ok": False, "error": str(e)}

def _refund(charge_id: str, amount: int = None) -> dict:
    s = _get_stripe()
    try:
        kw = {"charge": str(charge_id)}
        if amount is not None:
            kw["amount"] = int(amount)
        ref = s.Refund.create(**kw)
        return {"id": ref.id, "status": ref.status, "ok": True}
    except Exception as e:
        return {"id": None, "ok": False, "error": str(e)}
'''


def _gen_sendmail() -> str:
    return '''# NEKOVA Package — sendmail
# Send emails via SMTP

import smtplib, os
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart

def load() -> dict:
    return {
        "send_email":      _send,
        "send_html_email": _send_html,
        "email_template":  _template,
    }

def _smtp_config() -> dict:
    return {
        "host":     os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port":     int(os.environ.get("SMTP_PORT", "587")),
        "user":     os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
    }

def _send(to: str, subject: str, body: str,
          from_addr: str = None) -> dict:
    """Send a plain-text email."""
    cfg  = _smtp_config()
    msg  = MIMEText(str(body), "plain")
    msg["Subject"] = str(subject)
    msg["From"]    = from_addr or cfg["user"]
    msg["To"]      = str(to)
    return _dispatch(msg, str(to), cfg)

def _send_html(to: str, subject: str, html: str,
               from_addr: str = None) -> dict:
    """Send an HTML email."""
    cfg  = _smtp_config()
    msg  = MIMEMultipart("alternative")
    msg["Subject"] = str(subject)
    msg["From"]    = from_addr or cfg["user"]
    msg["To"]      = str(to)
    msg.attach(MIMEText(str(html), "html"))
    return _dispatch(msg, str(to), cfg)

def _dispatch(msg, to: str, cfg: dict) -> dict:
    try:
        if not cfg["user"] or not cfg["password"]:
            raise RuntimeError(
                "SMTP credentials not set.\\n"
                "  Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD"
            )
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], to, msg.as_string())
        return {"ok": True, "to": to}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _template(name: str, variables: dict = None) -> str:
    """Simple string template with {{variable}} substitution."""
    templates = {
        "welcome":     "Welcome to {{app}}, {{name}}! Your account is ready.",
        "reset":       "Hi {{name}}, click here to reset your password: {{link}}",
        "invoice":     "Invoice #{{number}} for {{amount}} is due on {{date}}.",
        "newsletter":  "Hello {{name}},\\n\\n{{content}}\\n\\nBest,\\n{{sender}}",
    }
    t = templates.get(str(name), str(name))
    if variables:
        for k, v in variables.items():
            t = t.replace("{{" + str(k) + "}}", str(v))
    return t
'''


def _gen_csv() -> str:
    return '''# NEKOVA Package — csv
import csv as _csv
import os

def load() -> dict:
    return {
        "csv_read":      _read,
        "csv_write":     _write,
        "csv_append":    _append,
        "csv_to_dict":   _to_dict,
        "csv_from_dict": _from_dict,
        "csv_filter":    _filter_rows,
        "csv_columns":   _columns,
    }

def _read(filepath: str, has_header: bool = True) -> list:
    """Read a CSV file. Returns list of rows (list of strings)."""
    rows = []
    with open(str(filepath), "r", encoding="utf-8", newline="") as f:
        reader = _csv.reader(f)
        if has_header:
            next(reader, None)   # skip header
        for row in reader:
            rows.append(row)
    return rows

def _write(filepath: str, rows: list,
           headers: list = None) -> bool:
    """Write rows to a CSV file, overwriting if it exists."""
    try:
        with open(str(filepath), "w", encoding="utf-8",
                  newline="") as f:
            w = _csv.writer(f)
            if headers:
                w.writerow(headers)
            for row in rows:
                w.writerow(row if isinstance(row, list) else [row])
        return True
    except Exception:
        return False

def _append(filepath: str, row: list) -> bool:
    """Append a single row to an existing CSV file."""
    try:
        with open(str(filepath), "a", encoding="utf-8",
                  newline="") as f:
            _csv.writer(f).writerow(row)
        return True
    except Exception:
        return False

def _to_dict(filepath: str) -> list:
    """Read a CSV with header row into a list of dicts."""
    results = []
    with open(str(filepath), "r", encoding="utf-8", newline="") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            results.append(dict(row))
    return results

def _from_dict(filepath: str, data: list,
               fieldnames: list = None) -> bool:
    """Write a list of dicts to a CSV file."""
    if not data:
        return False
    try:
        fields = fieldnames or list(data[0].keys())
        with open(str(filepath), "w", encoding="utf-8",
                  newline="") as f:
            w = _csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(data)
        return True
    except Exception:
        return False

def _filter_rows(filepath: str, column: int,
                 value: str) -> list:
    """Return rows where column index equals value."""
    rows = _read(filepath, has_header=False)
    return [r for r in rows
            if len(r) > int(column)
            and r[int(column)] == str(value)]

def _columns(filepath: str) -> list:
    """Return the header row (column names) of a CSV file."""
    with open(str(filepath), "r", encoding="utf-8", newline="") as f:
        reader = _csv.reader(f)
        return next(reader, [])
'''


def _gen_slug() -> str:
    return r'''# NEKOVA Package — slug
import re, html

def load() -> dict:
    return {
        "slugify":          _slugify,
        "truncate":         _truncate,
        "word_count":       _word_count,
        "capitalize_words": _capitalize_words,
        "strip_html":       _strip_html,
    }

def _slugify(text: str, separator: str = "-") -> str:
    """Convert text to a URL-friendly slug."""
    t = str(text).lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_-]+", str(separator), t)
    t = re.sub(r"^-+|-+$", "", t)
    return t

def _truncate(text: str, max_len: int = 100,
              suffix: str = "...") -> str:
    t = str(text)
    n = int(max_len)
    if len(t) <= n:
        return t
    return t[:n - len(suffix)].rstrip() + suffix

def _word_count(text: str) -> int:
    return len(str(text).split())

def _capitalize_words(text: str) -> str:
    return " ".join(w.capitalize() for w in str(text).split())

def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", str(text))
    return html.unescape(clean).strip()
'''