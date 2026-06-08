# =============================================================
# NEKOVA Language — Notebook System
# =============================================================
# A Jupyter-like notebook for NEKOVA.
# Runs in the browser with cells that can be executed
# independently while sharing the same interpreter state.
#
# Usage:
#   python main.py notebook
#   python main.py notebook examples/demo_notebook.aion

import os
import sys
import json
from io import StringIO
from flask import Flask, request, jsonify, send_from_directory
from config import NEKOVA_VERSION, Color


# ── Notebook cell types ───────────────────────────────────────

class Cell:
    """A single notebook cell."""
    def __init__(self, cell_id: int,
                 code: str = "",
                 cell_type: str = "code"):
        self.id       = cell_id
        self.code     = code
        self.type     = cell_type
        self.output   = ""
        self.error    = None
        self.executed = False

    def to_dict(self) -> dict:
        return {
            "id":       self.id,
            "code":     self.code,
            "type":     self.type,
            "output":   self.output,
            "error":    self.error,
            "executed": self.executed,
        }


class Notebook:
    """
    An NEKOVA notebook with multiple cells sharing state.
    """

    def __init__(self, filepath: str = None):
        self.filepath    = filepath
        self.cells       = []
        self.interpreter = None
        self._next_id    = 1
        self._init_interpreter()

        if filepath and os.path.exists(filepath):
            self._load_from_file(filepath)
        else:
            # Start with 3 empty cells
            self.add_cell("# Welcome to NEKOVA Notebook!\n"
                         "show \"Hello from NEKOVA Notebook!\"")
            self.add_cell("use math\nshow sqrt(144)\nshow round(pi)")
            self.add_cell("# Write your NEKOVA code here")

    def _init_interpreter(self):
        """Initialize a fresh interpreter."""
        from interpreter.interpreter import Interpreter
        self.interpreter = Interpreter()

    def add_cell(self, code: str = "",
                 cell_type: str = "code") -> Cell:
        """Add a new cell to the notebook."""
        cell = Cell(self._next_id, code, cell_type)
        self._next_id += 1
        self.cells.append(cell)
        return cell

    def execute_cell(self, cell_id: int) -> dict:
        """Execute a single cell and return results."""
        cell = self._get_cell(cell_id)
        if not cell:
            return {"error": f"Cell {cell_id} not found"}

        captured   = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        error      = None

        try:
            from lexer import Lexer
            from parser.parser import Parser

            tokens  = Lexer(cell.code).tokenize()
            program = Parser(tokens).parse()

            for stmt in program.statements:
                self.interpreter._execute_node(stmt)

        except Exception as e:
            error = str(e).strip()
            if "\n" in error:
                error = error.split("\n")[-1].strip()

        finally:
            sys.stdout = old_stdout

        cell.output   = captured.getvalue()
        cell.error    = error
        cell.executed = True

        return cell.to_dict()

    def execute_all(self) -> list:
        """Execute all cells in order."""
        self._init_interpreter()
        results = []
        for cell in self.cells:
            result = self.execute_cell(cell.id)
            results.append(result)
        return results

    def update_cell(self, cell_id: int,
                    code: str) -> dict:
        """Update a cell's code."""
        cell = self._get_cell(cell_id)
        if cell:
            cell.code     = code
            cell.executed = False
            cell.output   = ""
            cell.error    = None
        return cell.to_dict() if cell else {}

    def delete_cell(self, cell_id: int) -> bool:
        """Delete a cell."""
        self.cells = [c for c in self.cells
                      if c.id != cell_id]
        return True

    def move_cell(self, cell_id: int,
                  direction: str) -> bool:
        """Move a cell up or down."""
        idx = next((i for i, c in enumerate(self.cells)
                    if c.id == cell_id), None)
        if idx is None:
            return False

        if direction == "up" and idx > 0:
            self.cells[idx], self.cells[idx-1] = \
                self.cells[idx-1], self.cells[idx]
        elif (direction == "down" and
              idx < len(self.cells) - 1):
            self.cells[idx], self.cells[idx+1] = \
                self.cells[idx+1], self.cells[idx]

        return True

    def reset(self):
        """Reset interpreter state."""
        self._init_interpreter()
        for cell in self.cells:
            cell.executed = False
            cell.output   = ""
            cell.error    = None

    def save(self, filepath: str = None):
        """Save notebook to JSON file."""
        path = filepath or self.filepath or "notebook.aionb"
        data = {
            "version": NEKOVA_VERSION,
            "cells":   [c.to_dict() for c in self.cells]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    def _get_cell(self, cell_id: int):
        """Get a cell by ID."""
        return next((c for c in self.cells
                     if c.id == cell_id), None)

    def _load_from_file(self, filepath: str):
        """Load cells from an .aion file."""
        with open(filepath, "r",
                  encoding="utf-8") as f:
            source = f.read()

        # Split by blank lines into cells
        blocks = []
        current = []

        for line in source.splitlines():
            if not line.strip() and current:
                if any(l.strip() for l in current):
                    blocks.append("\n".join(current))
                current = []
            else:
                current.append(line)

        if current and any(l.strip() for l in current):
            blocks.append("\n".join(current))

        for block in blocks:
            self.add_cell(block)


# ── Flask server ──────────────────────────────────────────────

def create_notebook_app(notebook: Notebook) -> Flask:
    """Create Flask app for the notebook."""

    app = Flask(__name__)

    @app.route("/")
    def index():
        return NOTEBOOK_HTML

    @app.route("/api/cells", methods=["GET"])
    def get_cells():
        return jsonify({
            "cells":   [c.to_dict() for c in notebook.cells],
            "version": NEKOVA_VERSION,
        })

    @app.route("/api/cells", methods=["POST"])
    def add_cell():
        data = request.get_json()
        code = data.get("code", "")
        cell = notebook.add_cell(code)
        return jsonify(cell.to_dict())

    @app.route("/api/cells/<int:cell_id>",
               methods=["PUT"])
    def update_cell(cell_id):
        data = request.get_json()
        code = data.get("code", "")
        result = notebook.update_cell(cell_id, code)
        return jsonify(result)

    @app.route("/api/cells/<int:cell_id>/execute",
               methods=["POST"])
    def execute_cell(cell_id):
        result = notebook.execute_cell(cell_id)
        return jsonify(result)

    @app.route("/api/execute-all", methods=["POST"])
    def execute_all():
        results = notebook.execute_all()
        return jsonify({"results": results})

    @app.route("/api/cells/<int:cell_id>",
               methods=["DELETE"])
    def delete_cell(cell_id):
        notebook.delete_cell(cell_id)
        return jsonify({"success": True})

    @app.route("/api/reset", methods=["POST"])
    def reset():
        notebook.reset()
        return jsonify({"success": True})

    @app.route("/api/save", methods=["POST"])
    def save():
        path = notebook.save()
        return jsonify({"path": path})

    return app


def start_notebook(filepath: str = None,
                   port: int = 4000):
    """Start the NEKOVA Notebook server."""
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    notebook = Notebook(filepath)

    print()
    print(f"{Color.CYAN}{Color.BOLD}"
          f"  NEKOVA Notebook{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print(f"  {Color.GREEN}✓ Notebook running at "
          f"http://localhost:{port}{Color.RESET}")
    print(f"  {Color.DIM}Press Ctrl+C to stop"
          f"{Color.RESET}")
    if filepath:
        print(f"  {Color.DIM}File: {filepath}"
              f"{Color.RESET}")
    print()

    app = create_notebook_app(notebook)
    app.run(host="0.0.0.0",
            port=int(port),
            debug=False,
            use_reloader=False)


# ── HTML Interface ────────────────────────────────────────────

NOTEBOOK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEKOVA Notebook</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0d0d1a;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: #1a1a2e;
            border-bottom: 1px solid #2a2a4a;
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .logo {
            font-size: 1rem;
            font-weight: 800;
            color: #00d4ff;
            letter-spacing: 2px;
        }
        .toolbar {
            display: flex;
            gap: 8px;
        }
        .btn {
            padding: 6px 14px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
            transition: all 0.15s;
        }
        .btn-run-all {
            background: linear-gradient(135deg, #00d4ff, #0088cc);
            color: #000;
        }
        .btn-add { background: #2a2a4a; color: #e0e0e0; }
        .btn-reset { background: #2a2a4a; color: #e0e0e0; }
        .btn:hover { opacity: 0.85; }
        .notebook {
            max-width: 900px;
            margin: 32px auto;
            padding: 0 24px;
        }
        .cell {
            margin-bottom: 16px;
            border: 1px solid #2a2a4a;
            border-radius: 8px;
            overflow: hidden;
            transition: border-color 0.2s;
        }
        .cell:hover { border-color: #00d4ff40; }
        .cell.active { border-color: #00d4ff; }
        .cell-header {
            background: #141424;
            padding: 6px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #2a2a4a;
        }
        .cell-label {
            font-size: 0.7rem;
            color: #444;
            font-family: monospace;
        }
        .cell-actions {
            display: flex;
            gap: 6px;
        }
        .cell-btn {
            padding: 3px 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .btn-execute {
            background: #00d4ff;
            color: #000;
        }
        .btn-delete {
            background: #2a2a4a;
            color: #888;
        }
        .cell-editor {
            width: 100%;
            min-height: 80px;
            background: #0d0d1a;
            color: #e0e0e0;
            border: none;
            outline: none;
            padding: 16px;
            font-family: 'Cascadia Code', 'Fira Code', monospace;
            font-size: 13px;
            line-height: 1.7;
            resize: vertical;
            tab-size: 4;
        }
        .cell-output {
            padding: 12px 16px;
            font-family: monospace;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            border-top: 1px solid #2a2a4a;
            background: #0a0a15;
            color: #00ff88;
            display: none;
        }
        .cell-output.has-content { display: block; }
        .cell-output.error { color: #ff6b6b; }
        .cell-number {
            font-size: 0.7rem;
            color: #444;
            font-family: monospace;
            min-width: 30px;
        }
        .add-cell-btn {
            width: 100%;
            padding: 10px;
            background: transparent;
            border: 1px dashed #2a2a4a;
            border-radius: 8px;
            color: #444;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s;
            margin-bottom: 32px;
        }
        .add-cell-btn:hover {
            border-color: #00d4ff;
            color: #00d4ff;
        }
        .spinner {
            display: inline-block;
            width: 10px; height: 10px;
            border: 2px solid #00000040;
            border-top-color: #000;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0d0d1a; }
        ::-webkit-scrollbar-thumb { background: #2a2a4a; border-radius: 3px; }
    </style>
</head>
<body>
<div class="header">
    <div class="logo">⚡ NEKOVA Notebook</div>
    <div class="toolbar">
        <button class="btn btn-run-all" onclick="runAll()">▶▶ Run All</button>
        <button class="btn btn-add" onclick="addCell()">+ Add Cell</button>
        <button class="btn btn-reset" onclick="resetKernel()">↺ Reset</button>
    </div>
</div>

<div class="notebook" id="notebook"></div>

<script>
let cellCounter = 0;

async function loadCells() {
    const res   = await fetch('/api/cells');
    const data  = await res.json();
    const nb    = document.getElementById('notebook');
    nb.innerHTML = '';
    data.cells.forEach(cell => renderCell(cell));
    renderAddButton();
}

function renderCell(cell) {
    const nb  = document.getElementById('notebook');
    const div = document.createElement('div');
    div.className = 'cell';
    div.id = `cell-${cell.id}`;

    const hasOutput = cell.output || cell.error;
    const outputClass = cell.error
        ? 'cell-output error has-content'
        : hasOutput ? 'cell-output has-content' : 'cell-output';
    const outputText = cell.error
        ? `✗ ${cell.error}` : cell.output;

    div.innerHTML = `
        <div class="cell-header">
            <span class="cell-label">
                In [${cell.executed ? cell.id : ' '}]
            </span>
            <div class="cell-actions">
                <button class="cell-btn btn-execute"
                    onclick="runCell(${cell.id})">
                    ▶ Run
                </button>
                <button class="cell-btn btn-delete"
                    onclick="deleteCell(${cell.id})">
                    ✕
                </button>
            </div>
        </div>
        <textarea class="cell-editor"
            id="editor-${cell.id}"
            onkeydown="handleKey(event, ${cell.id})"
            onchange="updateCell(${cell.id})"
            >${cell.code}</textarea>
        <div class="${outputClass}" id="output-${cell.id}">${outputText}</div>
    `;

    // Insert before add button or append
    const addBtn = document.getElementById('add-btn');
    if (addBtn) nb.insertBefore(div, addBtn);
    else nb.appendChild(div);
}

function renderAddButton() {
    const nb  = document.getElementById('notebook');
    const old = document.getElementById('add-btn');
    if (old) old.remove();

    const btn = document.createElement('button');
    btn.id        = 'add-btn';
    btn.className = 'add-cell-btn';
    btn.textContent = '+ Add Cell';
    btn.onclick   = addCell;
    nb.appendChild(btn);
}

async function runCell(cellId) {
    const editor = document.getElementById(`editor-${cellId}`);
    const code   = editor.value;

    // Update code first
    await fetch(`/api/cells/${cellId}`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ code })
    });

    // Show loading
    const btn = document.querySelector(`#cell-${cellId} .btn-execute`);
    btn.innerHTML = '<span class="spinner"></span>';
    btn.disabled  = true;

    const res    = await fetch(`/api/cells/${cellId}/execute`, { method: 'POST' });
    const result = await res.json();

    // Update output
    const output = document.getElementById(`output-${cellId}`);
    if (result.error) {
        output.className = 'cell-output error has-content';
        output.textContent = `✗ ${result.error}`;
    } else if (result.output) {
        output.className = 'cell-output has-content';
        output.textContent = result.output;
    } else {
        output.className = 'cell-output has-content';
        output.textContent = '✓ (no output)';
    }

    // Update header
    const label = document.querySelector(`#cell-${cellId} .cell-label`);
    label.textContent = `In [${cellId}]`;

    btn.innerHTML = '▶ Run';
    btn.disabled  = false;
}

async function runAll() {
    const res     = await fetch('/api/execute-all', { method: 'POST' });
    const data    = await res.json();
    await loadCells();
}

async function addCell() {
    const res  = await fetch('/api/cells', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ code: '' })
    });
    const cell = await res.json();
    renderCell(cell);
    renderAddButton();
    document.getElementById(`editor-${cell.id}`).focus();
}

async function deleteCell(cellId) {
    await fetch(`/api/cells/${cellId}`, { method: 'DELETE' });
    document.getElementById(`cell-${cellId}`).remove();
}

async function updateCell(cellId) {
    const code = document.getElementById(`editor-${cellId}`).value;
    await fetch(`/api/cells/${cellId}`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ code })
    });
}

async function resetKernel() {
    await fetch('/api/reset', { method: 'POST' });
    await loadCells();
    alert('Kernel reset! All variables cleared.');
}

function handleKey(event, cellId) {
    // Tab → insert 4 spaces
    if (event.key === 'Tab') {
        event.preventDefault();
        const ta    = event.target;
        const start = ta.selectionStart;
        ta.value    = ta.value.substring(0, start) +
                      '    ' + ta.value.substring(start);
        ta.selectionStart = ta.selectionEnd = start + 4;
    }
    // Ctrl+Enter → run cell
    if (event.ctrlKey && event.key === 'Enter') {
        event.preventDefault();
        runCell(cellId);
    }
}

loadCells();
</script>
</body>
</html>"""