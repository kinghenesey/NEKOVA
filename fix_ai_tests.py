# NEKOVA — Fix AI test failures caused by suspended/missing API keys
# Run with: python fix_ai_tests.py
import os

def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  [ok] {path}")

print("=" * 60)
print("NEKOVA — Fix AI Test Failures")
print("=" * 60)

# ── FIX 1: gemini.py — better error for suspended/invalid keys ──
print("\n[1/2] Patching nekova/ai/providers/gemini.py ...")
path = "nekova/ai/providers/gemini.py"
c = read(path)

old = (
    "        except Exception as e:\n"
    "            raise RuntimeError(\n"
    "                f\"Gemini API error: {str(e)}\\n\"\n"
    "                f\"  Check your API key and try again.\"\n"
    "            )"
)
new = (
    "        except Exception as e:\n"
    "            err = str(e)\n"
    "            if '403' in err or 'PERMISSION_DENIED' in err or 'suspended' in err.lower():\n"
    "                raise RuntimeError(\n"
    "                    \"Gemini API key is suspended or invalid.\\n\"\n"
    "                    \"  Get a new free key at: https://aistudio.google.com\\n\"\n"
    "                    \"  Then update GEMINI_API_KEY in your .env file.\"\n"
    "                )\n"
    "            raise RuntimeError(\n"
    "                f\"Gemini API error: {err}\\n\"\n"
    "                f\"  Check your API key and try again.\"\n"
    "            )"
)

if old in c:
    write(path, c.replace(old, new, 1))
    print("  [ok] Added suspended key detection")
else:
    print("  [skip] Pattern not found — may already be patched")

# ── FIX 2: test_phase7.py — force mock provider in TestAIInNEKOVA ──
print("\n[2/2] Patching tests/test_phase7.py to force mock in AI tests ...")
path = "tests/test_phase7.py"
c = read(path)

# Check what the run() helper looks like
run_start = c.find("def run(")
print(f"  Current run() helper (first 200 chars):")
print("  " + c[run_start:run_start+200].replace("\n", "\n  "))

# Add os.environ override at the top of the file if not already there
if "NEKOVA_FORCE_MOCK" not in c and "force_mock" not in c.lower():
    # Inject after the last import line
    import_end = 0
    for i, line in enumerate(c.split('\n')):
        if line.startswith('import ') or line.startswith('from '):
            import_end = c.find('\n', sum(len(l)+1 for l in c.split('\n')[:i]))

    # Find the TestAIInNEKOVA class and add setUp to force mock
    old_class = "class TestAIInNEKOVA(unittest.TestCase):"
    new_class = (
        "class TestAIInNEKOVA(unittest.TestCase):\n"
        "\n"
        "    def setUp(self):\n"
        "        \"\"\"Force mock provider so tests never hit real APIs.\"\"\"\n"
        "        import os\n"
        "        os.environ['NEKOVA_AI_PROVIDER'] = 'mock'\n"
        "\n"
        "    def tearDown(self):\n"
        "        import os\n"
        "        os.environ.pop('NEKOVA_AI_PROVIDER', None)\n"
    )
    if old_class in c:
        c = c.replace(old_class, new_class, 1)
        write(path, c)
        print("  [ok] Added setUp/tearDown to force mock provider")
    else:
        print("  [skip] TestAIInNEKOVA class not found with expected name")
else:
    print("  [skip] Mock forcing already present")

# ── FIX 3: Check if ai_module.py respects NEKOVA_AI_PROVIDER env var ──
print("\n[3/3] Checking nekova/ai/ai_module.py for env override support ...")
path = "nekova/ai/ai_module.py"
c = read(path)

if "NEKOVA_AI_PROVIDER" not in c:
    # Find where the provider is selected and add env override
    old_load = "def load(self):"
    if old_load in c:
        # Find the provider selection logic
        provider_line = None
        for line in c.split('\n'):
            if 'get_provider' in line or 'select_provider' in line or 'MockProvider' in line:
                provider_line = line
                break
        print(f"  Provider selection line: {provider_line}")
        print("  Adding NEKOVA_AI_PROVIDER environment variable support...")

        # Add env override at the top of load()
        old_load_body = "def load(self):\n"
        idx = c.find(old_load_body)
        if idx != -1:
            # Find next line after def load(self):
            next_line_idx = c.find('\n', idx) + 1
            insertion = (
                "        import os\n"
                "        # Allow tests/CI to force a specific provider\n"
                "        _forced = os.environ.get('NEKOVA_AI_PROVIDER')\n"
                "        if _forced:\n"
                "            from nekova.ai.providers import get_provider\n"
                "            provider = get_provider(_forced)\n"
                "            _print_provider_info(provider)\n"
                "            return self._build_functions(provider)\n"
                "\n"
            )
            c = c[:next_line_idx] + insertion + c[next_line_idx:]
            write(path, c)
            print("  [ok] Added NEKOVA_AI_PROVIDER env override to ai_module.load()")
        else:
            print("  [skip] Could not find load() body")
    else:
        print("  [skip] No load() method found")
else:
    print("  [skip] NEKOVA_AI_PROVIDER already supported")

# ── VERIFY ──────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Running test_phase7.py ...")
print("=" * 60)

import subprocess, sys
env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'
env.pop('GEMINI_API_KEY', None)   # Remove suspended key for this test run

r = subprocess.run(
    [sys.executable, '-m', 'pytest', 'tests/test_phase7.py', '-q'],
    capture_output=True, text=True, encoding='utf-8', errors='replace',
    env=env
)
print(r.stdout[-2000:] if len(r.stdout) > 2000 else r.stdout)
if r.returncode == 0:
    print("\n All phase7 tests passing!")
    print("\nNext steps:")
    print("  1. Remove your suspended GEMINI_API_KEY from .env")
    print("  2. Get a new free key at: https://aistudio.google.com")
    print("  3. git add -A && git commit -m 'fix: handle suspended Gemini key, force mock in AI tests'")
    print("  4. git push")
else:
    print("\nSome tests still failing — paste output for diagnosis.")