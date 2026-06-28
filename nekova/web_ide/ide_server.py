# =============================================================
# NEKOVA Web IDE — Premium Server v2.0
# =============================================================
import os
import sys
import json
import traceback
from io import StringIO
from flask import Flask, request, jsonify, send_from_directory

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from nekova.config import NEKOVA_VERSION, NEKOVA_CODENAME


def create_ide_app() -> Flask:
    static_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "static")

    app = Flask(__name__,
                static_folder=static_dir,
                static_url_path="/static")

    @app.route("/")
    def index():
        return send_from_directory(static_dir, "index.html")

    @app.route("/api/run", methods=["POST"])
    def run_code():
        data = request.get_json()
        code = data.get("code", "")
        if not code.strip():
            return jsonify({"output": "", "error": None, "time": 0})
        output, error, elapsed = _execute_code(code)
        return jsonify({
            "output":  output,
            "error":   error,
            "time":    elapsed,
            "version": NEKOVA_VERSION,
        })

    @app.route("/api/examples", methods=["GET"])
    def get_examples():
        return jsonify({"examples": EXAMPLES})

    @app.route("/api/version", methods=["GET"])
    def get_version():
        return jsonify({
            "version":  NEKOVA_VERSION,
            "codename": NEKOVA_CODENAME,
        })

    @app.route("/api/complete", methods=["POST"])
    def autocomplete():
        data   = request.get_json()
        prefix = data.get("prefix", "")
        return jsonify({"suggestions": _get_completions(prefix)})

    @app.route("/api/format", methods=["POST"])
    def format_code():
        data = request.get_json()
        code = data.get("code", "")
        try:
            from formatter import NEKOVAFormatter
            formatter = NEKOVAFormatter()
            formatted = formatter.format(code)
            return jsonify({"formatted": formatted, "error": None})
        except Exception as e:
            return jsonify({"formatted": code, "error": str(e)})

    @app.route("/api/save", methods=["POST"])
    def save_file():
        data     = request.get_json()
        filename = data.get("filename", "untitled.nk")
        code     = data.get("code", "")
        safe     = os.path.basename(filename)
        if not safe.endswith(".nk"):
            safe += ".nk"
        path = os.path.join("examples", safe)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            return jsonify({"success": True, "path": path})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})

    @app.route("/api/files", methods=["GET"])
    def list_files():
        files = []
        for fname in os.listdir("examples"):
            if fname.endswith(".nk"):
                files.append(fname)
        return jsonify({"files": sorted(files)})

    @app.route("/api/load", methods=["POST"])
    def load_file():
        data     = request.get_json()
        filename = data.get("filename", "")
        safe     = os.path.basename(filename)
        path     = os.path.join("examples", safe)
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            return jsonify({"code": code, "error": None})
        except Exception as e:
            return jsonify({"code": "", "error": str(e)})

    return app


def _execute_code(source: str):
    import time
    captured   = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    start      = time.perf_counter()
    error      = None
    try:
        from lexer import Lexer
        from parser.parser import Parser
        from interpreter.interpreter import Interpreter
        tokens      = Lexer(source).tokenize()
        program     = Parser(tokens).parse()
        interpreter = Interpreter()
        interpreter.execute(program)
    except Exception as e:
        error = str(e).strip()
    finally:
        sys.stdout = old_stdout
    elapsed = (time.perf_counter() - start) * 1000
    output  = captured.getvalue()
    return output, error, round(elapsed, 2)


def _get_completions(prefix: str) -> list:
    all_keywords = [
        "show", "think", "if", "else", "repeat", "while",
        "for", "in", "task", "return", "use", "import",
        "and", "or", "not", "true", "false", "null",
        "model", "autonomous", "parallel", "memory",
        "sandbox", "strict", "relaxed", "pipeline",
        "collect", "generate", "save", "with", "run",
        "try", "catch",
    ]
    builtins = [
        "to_text", "to_number", "length", "ask", "clear",
        "sleep", "type_of", "random_num", "ai_ask",
        "ai_summarize", "ai_generate", "vision_scan",
        "voice_speak", "voice_listen",
    ]
    modules = [
        "math", "text", "files", "datetime", "collections",
        "ai", "agents", "ui", "web", "database",
        "vision", "voice",
    ]
    all_items = all_keywords + builtins + modules
    if not prefix:
        return all_keywords[:12]
    return [s for s in all_items
            if s.startswith(prefix.lower())][:10]


EXAMPLES = [
    {
        "name": "Hello World",
        "category": "basics",
        "code": 'name = "World"\nshow "Hello, {name}!"\nshow "Welcome to NEKOVA — the AI-native language."',
    },
    {
        "name": "Think (AI)",
        "category": "ai",
        "code": '# AI-native syntax — think calls the AI directly\nthink "What makes NEKOVA unique as a programming language?"\n\n# Capture the response\nidea = think "Give me one creative app idea in one sentence"\nshow "AI said: {idea}"',
    },
    {
        "name": "Agent Pipeline",
        "category": "ai",
        "code": '# Chain agents — output flows left to right\n"Analyze the future of AI in Africa" -> researcher -> writer',
    },
    {
        "name": "Neural Pipeline",
        "category": "ai",
        "code": 'pipeline market_research:\n    collect "Nigerian fintech startups 2025"\n    process with ai\n    generate report\n    save to database\n\nrun pipeline market_research',
    },
    {
        "name": "Parallel Execution",
        "category": "ai",
        "code": '# Run multiple AI tasks simultaneously\nautonomous parallel:\n    think "What is the capital of Nigeria?"\n    think "What is the capital of Ghana?"\n    think "What is the capital of Kenya?"',
    },
    {
        "name": "Memory Block",
        "category": "ai",
        "code": '# Data persists between program runs\nmemory user_profile:\n    name = "Emmanuel"\n    language = "NEKOVA"\n    version = "1.2.0"\n\nshow user_profile["name"]\nshow user_profile["language"]',
    },
    {
        "name": "Model Routing",
        "category": "ai",
        "code": '# Switch AI providers at runtime\nmodel "mock"\nthink "Testing with mock provider"\n\nmodel "gemini"\nthink "Now using Gemini"',
    },
    {
        "name": "Sandbox",
        "category": "ai",
        "code": '# Secure execution environment\nsandbox strict:\n    show "Running in strict mode"\n    think "What is 2 + 2?"\n    show "AI calls work inside sandbox!"',
    },
    {
        "name": "Variables & Types",
        "category": "basics",
        "code": 'name = "Emmanuel"\nage = 20\nheight = 1.85\nis_developer = true\n\nshow "Name: {name}"\nshow "Age: {age}"\nshow "Type: {type_of(name)}"',
    },
    {
        "name": "If / Else",
        "category": "basics",
        "code": 'score = 85\n\nif score >= 90:\n    show "Grade: A"\nelse:\n    if score >= 80:\n        show "Grade: B"\n    else:\n        show "Grade: C"',
    },
    {
        "name": "Loops",
        "category": "basics",
        "code": '# Repeat loop\nrepeat 3:\n    show "NEKOVA is powerful!"\n\n# For loop\nfruits = ["mango", "banana", "orange"]\nfor fruit in fruits:\n    show "Fruit: {fruit}"\n\n# While loop\ncount = 1\nwhile count <= 5:\n    show count\n    count = count + 1',
    },
    {
        "name": "Tasks (Functions)",
        "category": "basics",
        "code": 'task greet(name, lang):\n    show "Hello {name}!"\n    show "You are coding in {lang}"\n    return "Greeting sent!"\n\nresult = greet("Emmanuel", "NEKOVA")\nshow result',
    },
    {
        "name": "Math Module",
        "category": "stdlib",
        "code": 'use math\n\nshow sqrt(144)\nshow floor(3.9)\nshow ceil(3.1)\nshow abs(-42)\nshow round(pi)',
    },
    {
        "name": "Try / Catch",
        "category": "basics",
        "code": 'try:\n    x = 10 / 0\n    show "This won\'t print"\ncatch error:\n    show "Caught error: {error}"',
    },
    {
        "name": "FizzBuzz",
        "category": "basics",
        "code": 'count = 1\nwhile count <= 20:\n    if count % 15 == 0:\n        show "FizzBuzz"\n    else:\n        if count % 3 == 0:\n            show "Fizz"\n        else:\n            if count % 5 == 0:\n                show "Buzz"\n            else:\n                show count\n    count = count + 1',
    },
]


def start_ide(port: int = 3000):
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)

    from nekova.config import Color
    print()
    print(f"{Color.CYAN}{Color.BOLD}  NEKOVA Web IDE v2.0{Color.RESET}")
    print(f"  {Color.DIM}{'─' * 40}{Color.RESET}")
    print(f"  {Color.GREEN}✓ Running at http://localhost:{port}{Color.RESET}")
    print(f"  {Color.DIM}Press Ctrl+C to stop{Color.RESET}")
    print()

    app = create_ide_app()
    app.run(host="0.0.0.0", port=int(port),
            debug=False, use_reloader=False)