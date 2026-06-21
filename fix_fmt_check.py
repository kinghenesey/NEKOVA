# NEKOVA — Fix nekova fmt / nekova check bugs
# Run with: python fix_fmt_check.py
import os

def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  [ok] {path}")

print("=" * 60)
print("NEKOVA - Fix nekova fmt / nekova check bugs")
print("=" * 60)

# ── FIX 1: main.py — register 'fmt' and 'check' as valid commands ──
print("\n[1/2] Patching main.py command dispatch...")
path = "main.py"
c = read(path)

old = (
    '    commands = {\n'
    '        "run", "test", "build", "new", "info", "clean",\n'
    '        "export", "package", "publish", "deploy", "repl",\n'
    '        "marketplace", "debug", "ide", "format", "notebook",\n'
    '        "compile",\n'
    '    }'
)
new = (
    '    commands = {\n'
    '        "run", "test", "build", "new", "info", "clean",\n'
    '        "export", "package", "publish", "deploy", "repl",\n'
    '        "marketplace", "debug", "ide", "format", "notebook",\n'
    '        "compile", "fmt", "check",\n'
    '    }'
)

if old in c:
    write(path, c.replace(old, new, 1))
    print("  [ok] Added 'fmt' and 'check' to recognized commands set")
else:
    print("  [skip] Pattern not found — may already be fixed")

# ── FIX 2: checker.py — exclude stdlib builtins from unused-var check ──
print("\n[2/2] Patching nekova/cli/checker.py...")
path = "nekova/cli/checker.py"
c = read(path)

old = (
    '    def _check_unused(self):\n'
    '        """Warn about variables defined but never used."""\n'
    '        for name, line in self.scope.defined.items():\n'
    '            if name in _BUILTINS:\n'
    '                continue\n'
    '            if name in self.scope.tasks:\n'
    '                continue'
)
new = (
    '    def _check_unused(self):\n'
    '        """Warn about variables defined but never used."""\n'
    '        # Stdlib functions pre-seeded into scope must never be\n'
    '        # reported as unused -- they are builtins, not user variables.\n'
    '        _STDLIB_PRESEEDED = {\n'
    '            "connect", "uuid", "token", "hash",\n'
    '            "json_encode", "json_decode",\n'
    '            "env_get", "env_set", "recall",\n'
    '        }\n'
    '        for name, line in self.scope.defined.items():\n'
    '            if name in _BUILTINS:\n'
    '                continue\n'
    '            if name in _STDLIB_PRESEEDED:\n'
    '                continue\n'
    '            if name in self.scope.tasks:\n'
    '                continue'
)

if old in c:
    write(path, c.replace(old, new, 1))
    print("  [ok] Fixed phantom unused-variable warnings for stdlib builtins")
else:
    print("  [skip] Pattern not found — may already be fixed")

# ── VERIFY ───────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Verifying fixes...")
print("=" * 60)

import subprocess, sys
env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'

# Create a test file with no stdlib usage
test_content = (
    'let x=5\n'
    'let y =10\n'
    'show x+y\n'
)
with open("_fmt_check_test.nk", "w", encoding="utf-8") as f:
    f.write(test_content)

print("\nTesting 'nekova fmt'...")
r1 = subprocess.run(["nekova", "fmt", "_fmt_check_test.nk"],
                     capture_output=True, text=True, encoding='utf-8',
                     errors='replace', env=env)
print(r1.stdout[-300:] if r1.stdout else r1.stderr[-300:])

print("\nTesting 'nekova check'...")
r2 = subprocess.run(["nekova", "check", "_fmt_check_test.nk"],
                     capture_output=True, text=True, encoding='utf-8',
                     errors='replace', env=env)
print(r2.stdout[-500:] if r2.stdout else r2.stderr[-500:])

os.remove("_fmt_check_test.nk")

print("\nRunning full test suite...")
r3 = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                     capture_output=True, text=True, encoding='utf-8',
                     errors='replace', env=env)
print(r3.stdout[-300:] if r3.stdout else "")

print("\n" + "=" * 60)
if "json_encode" not in (r2.stdout or "") and "'fmt' is not a NEKOVA file" not in (r1.stdout or ""):
    print("Both bugs fixed successfully!")
    print("\nNext steps:")
    print("  git add -A")
    print('  git commit -m "fix: register fmt/check commands, exclude stdlib builtins from unused-var check"')
    print("  git push")
else:
    print("Please review the output above — one or both fixes may need manual review.")