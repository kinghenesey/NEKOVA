# =============================================================
# NEKOVA — Apply All Fixes Script
# =============================================================
# Run this from your project root:
#   C:\Users\HomePC\Desktop\NEKOVA>
#
# Usage:
#   .\apply_fixes.ps1
#
# If you get a "running scripts is disabled" error, first run:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# =============================================================

Write-Host "=== NEKOVA Fix Script — Starting ===" -ForegroundColor Cyan

# -------------------------------------------------------------
# 1. Fix bare 'from config import' across entire nekova/ package
# -------------------------------------------------------------
Write-Host "[1/9] Fixing 'from config import' -> 'from nekova.config import'..." -ForegroundColor Yellow
Get-ChildItem -Path nekova -Filter *.py -Recurse | ForEach-Object {
    (Get-Content $_.FullName -Raw) -replace 'from config import', 'from nekova.config import' |
        Set-Content $_.FullName -Encoding UTF8 -NoNewline
}

# -------------------------------------------------------------
# 2. Fix bare 'from lexer import' / 'from parser...' / 'from interpreter...'
# -------------------------------------------------------------
Write-Host "[2/9] Fixing lexer/parser/interpreter imports inside nekova/..." -ForegroundColor Yellow
Get-ChildItem -Path nekova -Filter *.py -Recurse | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $content = $content -replace 'from lexer import', 'from nekova.lexer import'
    $content = $content -replace 'from parser\.parser import', 'from nekova.parser.parser import'
    $content = $content -replace 'from parser\.nodes import', 'from nekova.parser.nodes import'
    $content = $content -replace 'from interpreter\.interpreter import', 'from nekova.interpreter.interpreter import'
    $content = $content -replace 'from stdlib import', 'from nekova.stdlib import'
    $content = $content -replace 'from compiler\.transpiler import', 'from nekova.compiler.transpiler import'
    $content = $content -replace 'from web\.response import', 'from nekova.web.response import'
    $content = $content -replace 'from marketplace import', 'from nekova.marketplace import'
    $content = $content -replace 'from deploy\.bundle import', 'from nekova.deploy.bundle import'
    $content = $content -replace 'from deploy\.exporter import', 'from nekova.deploy.exporter import'
    $content = $content -replace 'from deploy\.packager import', 'from nekova.deploy.packager import'
    $content = $content -replace 'from deploy\.publisher import', 'from nekova.deploy.publisher import'
    $content = $content -replace 'from deploy\.cloud import', 'from nekova.deploy.cloud import'
    Set-Content $_.FullName -Value $content -Encoding UTF8 -NoNewline
}

# -------------------------------------------------------------
# 3. Fix all test files (tests/test_phase*.py)
# -------------------------------------------------------------
Write-Host "[3/9] Fixing test file imports..." -ForegroundColor Yellow
Get-ChildItem -Path tests -Filter "test_phase*.py" | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $content = $content -replace 'from config import', 'from nekova.config import'
    $content = $content -replace 'from lexer import', 'from nekova.lexer import'
    $content = $content -replace 'from lexer\.token_types import', 'from nekova.lexer.token_types import'
    $content = $content -replace 'from parser\.parser import', 'from nekova.parser.parser import'
    $content = $content -replace 'from parser\.nodes import', 'from nekova.parser.nodes import'
    $content = $content -replace 'from interpreter\.interpreter import', 'from nekova.interpreter.interpreter import'
    $content = $content -replace 'from ai\.providers', 'from nekova.ai.providers'
    $content = $content -replace 'from packages import', 'from nekova.packages import'
    $content = $content -replace 'from cli\.package_manager import', 'from nekova.cli.package_manager import'
    Set-Content $_.FullName -Value $content -Encoding UTF8 -NoNewline
}

# -------------------------------------------------------------
# 4. Fix test_phase1.py — wrong .nekova extension in temp files
# -------------------------------------------------------------
Write-Host "[4/9] Fixing .nekova -> NEKOVA_EXTENSION in test_phase1.py..." -ForegroundColor Yellow
(Get-Content tests/test_phase1.py -Raw) -replace '\.mkstemp\(suffix="\.nekova"\)', '.mkstemp(suffix=NEKOVA_EXTENSION)' |
    Set-Content tests/test_phase1.py -Encoding UTF8 -NoNewline

# -------------------------------------------------------------
# 5. Fix test_phase4.py and test_phase5.py — NEKOVA has 6 letters, not 4
# -------------------------------------------------------------
Write-Host "[5/9] Fixing NEKOVA-length test expectations (6, not 4/AION)..." -ForegroundColor Yellow

$p4 = Get-Content tests/test_phase4.py -Raw
$old4 = "    def test_length(self):`r`n        output = run('show length(`"NEKOVA`")')`r`n        self.assertEqual(output, `"4`")"
$new4 = "    def test_length(self):`r`n        output = run('show length(`"NEKOVA`")')`r`n        self.assertEqual(output, `"6`")"
$p4 = $p4.Replace($old4, $new4)
Set-Content tests/test_phase4.py -Value $p4 -Encoding UTF8 -NoNewline

$p5 = Get-Content tests/test_phase5.py -Raw
$oldReverse = "    def test_reverse(self):`r`n        output = run('use text\nshow reverse(`"NEKOVA`")')`r`n        self.assertEqual(output, `"NOIA`")"
$newReverse = "    def test_reverse(self):`r`n        output = run('use text\nshow reverse(`"NEKOVA`")')`r`n        self.assertEqual(output, `"AVOKEN`")"
$p5 = $p5.Replace($oldReverse, $newReverse)

$oldLength = "    def test_length(self):`r`n        output = run('use text\nshow length(`"NEKOVA`")')`r`n        self.assertEqual(output, `"4`")"
$newLength = "    def test_length(self):`r`n        output = run('use text\nshow length(`"NEKOVA`")')`r`n        self.assertEqual(output, `"6`")"
$p5 = $p5.Replace($oldLength, $newLength)
Set-Content tests/test_phase5.py -Value $p5 -Encoding UTF8 -NoNewline

# -------------------------------------------------------------
# 6. Fix myproject/NEKOVA.json — wrong extension
# -------------------------------------------------------------
Write-Host "[6/9] Fixing myproject/NEKOVA.json extension..." -ForegroundColor Yellow
if (Test-Path myproject/NEKOVA.json) {
    (Get-Content myproject/NEKOVA.json -Raw) -replace 'src/main\.nekova', 'src/main.nk' |
        Set-Content myproject/NEKOVA.json -Encoding UTF8 -NoNewline
}

# -------------------------------------------------------------
# 7. Rewrite nekova/parser/__init__.py (dedupe + add missing exports)
# -------------------------------------------------------------
Write-Host "[7/9] Rewriting nekova/parser/__init__.py..." -ForegroundColor Yellow
$parserInit = @'
# =============================================================
# NEKOVA Parser - Package Init
# =============================================================
# Makes the parser importable from anywhere like:
#   from nekova.parser import Parser

from nekova.parser.parser import Parser, ParseError
from nekova.parser.nodes import (
    Node, Program, IntegerLiteral, FloatLiteral, StringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral, DictLiteral,
    IndexExpression, MethodCall, Identifier, BinaryOp, UnaryOp,
    AssignStatement, ShowStatement, ThinkStatement, PipelineStatement,
    ModelStatement, ParallelStatement, MemoryStatement, SandboxStatement,
    PipelineDefStatement, RunPipelineStatement, IfStatement,
    RepeatStatement, WhileStatement, TryStatement, ForStatement,
    TaskStatement, ReturnStatement, UseStatement, ImportStatement,
    CallExpression
)
'@
Set-Content nekova/parser/__init__.py -Value $parserInit -Encoding UTF8

# -------------------------------------------------------------
# 8. Replace .gitignore with cleaned version
# -------------------------------------------------------------
Write-Host "[8/9] Replacing .gitignore..." -ForegroundColor Yellow
$gitignore = @'
# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd

# Virtual environment
venv/

# NEKOVA installed packages (generated files)
packages/auth.py
packages/random.py
packages/validation.py
packages/colors.py
packages/charts.py
packages/registry.json

# Environment variables (API keys)
.env

# VS Code
.vscode/

# OS files
.DS_Store
Thumbs.db

# Build artifacts
dist/
*.egg-info/
build/

# Runtime-generated files
project_ideas.db
generated_image.png
*.NEKOVAmem/
.NEKOVAmem/

# VS Code extension
nekova-vscode/node_modules/
nekova-vscode/*.vsix
nekova-vscode/out/
nekova-vscode/.vscode-test/
'@
Set-Content .gitignore -Value $gitignore -Encoding UTF8

# -------------------------------------------------------------
# 9. Create the missing tests/test_phase6.py
# -------------------------------------------------------------
Write-Host "[9/9] Creating tests/test_phase6.py..." -ForegroundColor Yellow
$phase6 = @'
# =============================================================
# NEKOVA - Phase 6 Tests (Control Flow & Data Structures)
# =============================================================
# Run with: python tests/test_phase6.py
#
# Covers features that exist in the interpreter but were not
# yet covered by Phase 4 or Phase 5: while loops, for loops,
# try/catch error handling, and list/dict literals.

import sys
import os
import unittest
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(source: str) -> str:
    """Helper - run NEKOVA source and capture printed output."""
    tokens      = Lexer(source).tokenize()
    program     = Parser(tokens).parse()
    interpreter = Interpreter()

    captured   = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured

    try:
        interpreter.execute(program)
    finally:
        sys.stdout = old_stdout

    return captured.getvalue().strip()


class TestWhileLoops(unittest.TestCase):

    def test_while_basic(self):
        source = (
            'i = 0\n'
            'while i < 3:\n'
            '    show i\n'
            '    i = i + 1\n'
        )
        self.assertEqual(run(source), "0\n1\n2")

    def test_while_never_runs(self):
        source = (
            'i = 5\n'
            'while i < 3:\n'
            '    show i\n'
        )
        self.assertEqual(run(source), "")


class TestForLoops(unittest.TestCase):

    def test_for_over_list(self):
        source = (
            'items = ["a", "b", "c"]\n'
            'for item in items:\n'
            '    show item\n'
        )
        self.assertEqual(run(source), "a\nb\nc")

    def test_for_with_numbers(self):
        source = (
            'nums = [1, 2, 3]\n'
            'total = 0\n'
            'for n in nums:\n'
            '    total = total + n\n'
            'show total\n'
        )
        self.assertEqual(run(source), "6")


class TestTryCatch(unittest.TestCase):

    def test_try_no_error(self):
        source = (
            'try:\n'
            '    show "ok"\n'
            'catch err:\n'
            '    show "failed"\n'
        )
        self.assertEqual(run(source), "ok")

    def test_try_with_error(self):
        source = (
            'try:\n'
            '    x = 1 / 0\n'
            '    show "unreachable"\n'
            'catch err:\n'
            '    show "caught"\n'
        )
        self.assertEqual(run(source), "caught")


class TestListLiterals(unittest.TestCase):

    def test_list_index(self):
        source = (
            'items = [10, 20, 30]\n'
            'show items[1]\n'
        )
        self.assertEqual(run(source), "20")

    def test_list_length(self):
        source = (
            'items = [1, 2, 3, 4]\n'
            'show length(items)\n'
        )
        self.assertEqual(run(source), "4")


class TestDictLiterals(unittest.TestCase):

    def test_dict_access(self):
        source = (
            'person = {"name": "Emmanuel", "age": 25}\n'
            'show person["name"]\n'
        )
        self.assertEqual(run(source), "Emmanuel")


if __name__ == "__main__":
    unittest.main()
'@
Set-Content tests/test_phase6.py -Value $phase6 -Encoding UTF8

# -------------------------------------------------------------
# 10. Remove redundant setup.cfg, untrack generated files
# -------------------------------------------------------------
Write-Host "[10/10] Cleaning up setup.cfg and generated files..." -ForegroundColor Yellow
if (Test-Path setup.cfg) { Remove-Item setup.cfg }
if (Test-Path generated_image.png) { git rm --cached generated_image.png 2>$null; Remove-Item generated_image.png -ErrorAction SilentlyContinue }
if (Test-Path project_ideas.db) { git rm --cached project_ideas.db 2>$null; Remove-Item project_ideas.db -ErrorAction SilentlyContinue }
git rm -r --cached __pycache__ 2>$null
Get-ChildItem -Path . -Filter __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# -------------------------------------------------------------
# 11. Add py-modules to pyproject.toml (so nekova_cli works for non-editable installs)
# -------------------------------------------------------------
Write-Host "[11/11] Updating pyproject.toml with py-modules..." -ForegroundColor Yellow
$pyproject = Get-Content pyproject.toml -Raw
if ($pyproject -notmatch '\[tool\.setuptools\]') {
    $pyproject = $pyproject -replace '(\[tool\.setuptools\.packages\.find\][^\[]*)', "`$1`r`n[tool.setuptools]`r`npy-modules = [`"main`", `"runner`", `"nekova_cli`", `"repl`", `"debugger`", `"notebook`", `"formatter`"]`r`n"
    Set-Content pyproject.toml -Value $pyproject -Encoding UTF8 -NoNewline
}

Write-Host ""
Write-Host "=== All fixes applied! ===" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  pip install -e ."
Write-Host "  python tests/test_phase1.py"
Write-Host "  python tests/test_phase2.py"
Write-Host "  python tests/test_phase3.py"
Write-Host "  python tests/test_phase4.py"
Write-Host "  python tests/test_phase5.py"
Write-Host "  python tests/test_phase6.py"
Write-Host "  python tests/test_phase7.py"
Write-Host "  python tests/test_phase8.py"
