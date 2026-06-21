# =============================================================
# NEKOVA Phase 9 Tests — AI-Native Core
# remember / recall / forget  +  think as json/list/bool/schema
# =============================================================
import sys
import os
import re
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(code: str) -> list:
    """Run NEKOVA source, return list of non-empty output lines."""
    # Reset memory store between tests
    from nekova.ai import memory_store
    memory_store.forget_all()
    memory_store.clear_conversation()

    tokens = Lexer(code).tokenize()
    ast    = Parser(tokens).parse()
    interp = Interpreter()
    buf    = StringIO()
    sys.stdout = buf
    try:
        interp.execute(ast)
    finally:
        sys.stdout = sys.__stdout__
    text = re.sub(r'\x1b\[[0-9;]*m', '', buf.getvalue())
    return [l for l in text.splitlines() if l.strip()]


def run1(code: str) -> str:
    lines = run(code)
    return lines[-1] if lines else ""


# ==============================================================
# SECTION 1 — remember
# ==============================================================

class TestRemember:

    def test_remember_string(self):
        out = run1('remember "name" = "Emmanuel"\nshow recall "name"')
        assert out == "Emmanuel"

    def test_remember_number(self):
        out = run1('remember "score" = 100\nshow recall "score"')
        assert out == "100"

    def test_remember_float(self):
        out = run1('remember "pi" = 3.14\nshow recall "pi"')
        assert out == "3.14"

    def test_remember_boolean_true(self):
        out = run1('remember "active" = true\nshow recall "active"')
        assert out == "true"

    def test_remember_boolean_false(self):
        out = run1('remember "active" = false\nshow recall "active"')
        assert out == "false"

    def test_remember_dict(self):
        code = 'remember "cfg" = {"port": 8080}\nlet c = recall "cfg"\nshow c["port"]'
        out = run1(code)
        assert out == "8080"

    def test_remember_list(self):
        code = 'remember "langs" = ["nekova", "python"]\nlet l = recall "langs"\nshow l[0]'
        out = run1(code)
        assert out == "nekova"

    def test_remember_fstring_value(self):
        code = 'let user = "Emmanuel"\nremember "greeting" = f"Hello {user}"\nshow recall "greeting"'
        out = run1(code)
        assert out == "Hello Emmanuel"

    def test_remember_from_variable(self):
        code = 'let x = 42\nremember "answer" = x\nshow recall "answer"'
        out = run1(code)
        assert out == "42"

    def test_remember_overwrites(self):
        code = 'remember "x" = "first"\nremember "x" = "second"\nshow recall "x"'
        out = run1(code)
        assert out == "second"

    def test_remember_multiple_keys(self):
        code = (
            'remember "a" = "alpha"\n'
            'remember "b" = "beta"\n'
            'remember "c" = "gamma"\n'
            'show recall "a"\n'
            'show recall "b"\n'
            'show recall "c"'
        )
        lines = run(code)
        assert lines[-3:] == ["alpha", "beta", "gamma"]

    def test_remember_expression_value(self):
        code = 'let x = 10\nremember "double" = x + x\nshow recall "double"'
        out = run1(code)
        assert out == "20"


# ==============================================================
# SECTION 2 — recall
# ==============================================================

class TestRecall:

    def test_recall_existing(self):
        out = run1('remember "city" = "Abuja"\nshow recall "city"')
        assert out == "Abuja"

    def test_recall_missing_returns_none(self):
        # recall of missing key with no default → None displayed as 'null' or ''
        out = run1('let v = recall "no_such_key"\nshow v')
        assert out in ("null", "None", "")

    def test_recall_with_default(self):
        out = run1('show recall "missing_key" or "default_val"')
        assert out == "default_val"

    def test_recall_with_default_number(self):
        out = run1('show recall "missing" or 99')
        assert out == "99"

    def test_recall_existing_ignores_default(self):
        code = 'remember "lang" = "NEKOVA"\nshow recall "lang" or "unknown"'
        out = run1(code)
        assert out == "NEKOVA"

    def test_recall_in_assignment(self):
        code = 'remember "n" = "Emmanuel"\nlet name = recall "n"\nshow name'
        out = run1(code)
        assert out == "Emmanuel"

    def test_recall_in_fstring(self):
        code = 'remember "lang" = "NEKOVA"\nlet lang = recall "lang"\nshow f"Language: {lang}"'
        out = run1(code)
        assert out == "Language: NEKOVA"

    def test_recall_in_task(self):
        code = (
            'task greet():\n'
            '    let name = recall "user" or "stranger"\n'
            '    return f"Hello, {name}!"\n'
            'remember "user" = "Emmanuel"\n'
            'show greet()'
        )
        out = run1(code)
        assert out == "Hello, Emmanuel!"

    def test_recall_default_in_task(self):
        code = (
            'task greet():\n'
            '    let name = recall "nobody" or "stranger"\n'
            '    return f"Hello, {name}!"\n'
            'show greet()'
        )
        out = run1(code)
        assert out == "Hello, stranger!"

    def test_recall_in_if(self):
        code = (
            'remember "mode" = "dark"\n'
            'let m = recall "mode"\n'
            'if m == "dark":\n'
            '    show "dark mode"\n'
            'else:\n'
            '    show "light mode"'
        )
        out = run1(code)
        assert out == "dark mode"

    def test_recall_in_match(self):
        code = (
            'remember "status" = "active"\n'
            'let s = recall "status"\n'
            'match s:\n'
            '    when "active": show "running"\n'
            '    when "idle": show "stopped"\n'
            '    else: show "unknown"'
        )
        out = run1(code)
        assert out == "running"

    def test_recall_dict_value(self):
        code = (
            'remember "cfg" = {"host": "localhost", "port": 3000}\n'
            'let cfg = recall "cfg"\n'
            'show cfg["host"]'
        )
        out = run1(code)
        assert out == "localhost"


# ==============================================================
# SECTION 3 — forget
# ==============================================================

class TestForget:

    def test_forget_removes_key(self):
        code = 'remember "x" = 1\nforget "x"\nshow recall "x" or "gone"'
        out = run1(code)
        assert out == "gone"

    def test_forget_nonexistent_ok(self):
        # Forgetting a key that doesn't exist should not error
        out = run1('forget "never_existed"\nshow "ok"')
        assert out == "ok"

    def test_forget_all_clears_everything(self):
        code = (
            'remember "a" = 1\n'
            'remember "b" = 2\n'
            'remember "c" = 3\n'
            'forget all\n'
            'show recall "a" or "gone"\n'
            'show recall "b" or "gone"\n'
            'show recall "c" or "gone"'
        )
        lines = run(code)
        assert lines[-3:] == ["gone", "gone", "gone"]

    def test_forget_specific_key_only(self):
        code = (
            'remember "keep" = "yes"\n'
            'remember "remove" = "bye"\n'
            'forget "remove"\n'
            'show recall "keep"\n'
            'show recall "remove" or "gone"'
        )
        lines = run(code)
        assert lines[-2] == "yes"
        assert lines[-1] == "gone"

    def test_forget_then_re_remember(self):
        code = (
            'remember "x" = "first"\n'
            'forget "x"\n'
            'remember "x" = "second"\n'
            'show recall "x"'
        )
        out = run1(code)
        assert out == "second"

    def test_forget_all_then_remember(self):
        code = (
            'remember "a" = 1\n'
            'forget all\n'
            'remember "b" = 2\n'
            'show recall "a" or "gone"\n'
            'show recall "b"'
        )
        lines = run(code)
        assert lines[-2] == "gone"
        assert lines[-1] == "2"


# ==============================================================
# SECTION 4 — think as (structured AI output)
# Uses MockProvider which returns structured responses automatically
# ==============================================================

class TestThinkAsJSON:

    def test_think_as_json_is_dict(self):
        code = 'let d = think "get data" as json\nshow d["status"]'
        out = run1(code)
        assert out == "ok"

    def test_think_as_json_field_count(self):
        code = 'let d = think "get data" as json\nshow d["result"]'
        out = run1(code)
        assert out == "mock_value"

    def test_think_as_json_in_task(self):
        code = (
            'task get_data(q):\n'
            '    let d = think q as json\n'
            '    return d["result"]\n'
            'show get_data("query")'
        )
        out = run1(code)
        assert out == "mock_value"

    def test_think_as_json_multiple_calls(self):
        code = (
            'let a = think "first query" as json\n'
            'let b = think "second query" as json\n'
            'show a["status"]\n'
            'show b["status"]'
        )
        lines = run(code)
        assert lines[-2] == "ok"
        assert lines[-1] == "ok"

    def test_think_as_json_with_fstring_prompt(self):
        code = (
            'let topic = "NEKOVA"\n'
            'let d = think f"Get info about {topic}" as json\n'
            'show d["status"]'
        )
        out = run1(code)
        assert out == "ok"


class TestThinkAsList:

    def test_think_as_list_is_list(self):
        code = 'let items = think "list fruits" as list\nshow items[0]'
        out = run1(code)
        assert out == "item one"

    def test_think_as_list_indexable(self):
        code = 'let items = think "list items" as list\nshow items[1]'
        out = run1(code)
        assert out == "item two"

    def test_think_as_list_in_for_loop(self):
        code = (
            'let items = think "list fruits" as list\n'
            'for item in items:\n'
            '    show item'
        )
        lines = run(code)
        assert "item one" in lines
        assert "item two" in lines
        assert "item three" in lines

    def test_think_as_list_length(self):
        code = (
            'use collections\n'
            'let items = think "list three things" as list\n'
            'show list_length(items)'
        )
        out = run1(code)
        assert out == "3"

    def test_think_as_list_in_task(self):
        code = (
            'task get_items(prompt):\n'
            '    return think prompt as list\n'
            'let results = get_items("list things")\n'
            'show results[0]'
        )
        out = run1(code)
        assert out == "item one"


class TestThinkAsBool:

    def test_think_as_bool_true(self):
        code = 'let ok = think "Is the sky blue?" as bool\nshow ok'
        out = run1(code)
        assert out == "true"

    def test_think_as_bool_in_if(self):
        code = (
            'let ok = think "Is NEKOVA awesome?" as bool\n'
            'if ok:\n'
            '    show "yes"\n'
            'else:\n'
            '    show "no"'
        )
        out = run1(code)
        assert out == "yes"

    def test_think_as_bool_in_match(self):
        code = (
            'let result = think "Is 2+2=4?" as bool\n'
            'match result:\n'
            '    when true: show "correct"\n'
            '    when false: show "wrong"'
        )
        out = run1(code)
        assert out == "correct"

    def test_think_as_bool_in_task(self):
        code = (
            'task validate(q):\n'
            '    return think q as bool\n'
            'show validate("Is Python good?")'
        )
        out = run1(code)
        assert out in ("true", "false")


class TestThinkAsSchema:

    def test_think_as_schema_returns_dict(self):
        code = (
            'let u = think "get user" as schema {"name": "text", "age": "number"}\n'
            'show u["name"]'
        )
        out = run1(code)
        assert out == "mock_name"

    def test_think_as_schema_number_field(self):
        code = (
            'let u = think "get user" as schema {"name": "text", "age": "number"}\n'
            'show u["age"]'
        )
        out = run1(code)
        # 42.0 or 42
        assert out in ("42", "42.0")

    def test_think_as_schema_multiple_fields(self):
        code = (
            'let p = think "get product" as schema {"title": "text", "price": "number", "in_stock": "boolean"}\n'
            'show p["title"]'
        )
        out = run1(code)
        assert out == "mock_title"

    def test_think_as_schema_in_task(self):
        code = (
            'task get_profile(prompt):\n'
            '    return think prompt as schema {"name": "text", "role": "text"}\n'
            'let profile = get_profile("get profile")\n'
            'show profile["role"]'
        )
        out = run1(code)
        assert out == "mock_role"


class TestThinkAsText:

    def test_think_as_text_returns_string(self):
        code = 'let reply = think "say hello" as text\nshow reply'
        out = run1(code)
        assert isinstance(out, str)
        assert len(out) > 0

    def test_think_as_text_in_fstring(self):
        code = (
            'let reply = think "say hello" as text\n'
            'show f"AI said: {reply}"'
        )
        out = run1(code)
        assert out.startswith("AI said:")


# ==============================================================
# SECTION 5 — Integration: memory + think + match + db
# ==============================================================

class TestPhase9Integration:

    def test_remember_then_think(self):
        code = (
            'remember "user" = "Emmanuel"\n'
            'let name = recall "user"\n'
            'let greeting = think f"Say hello to {name}" as text\n'
            'show "done"'
        )
        out = run1(code)
        assert out == "done"

    def test_think_result_remembered(self):
        code = (
            'let d = think "get config" as json\n'
            'remember "last_result" = d["status"]\n'
            'show recall "last_result"'
        )
        out = run1(code)
        assert out == "ok"

    def test_memory_persists_across_tasks(self):
        code = (
            'task save_name(n):\n'
            '    remember "username" = n\n'
            'task get_name():\n'
            '    return recall "username" or "unknown"\n'
            'save_name("Emmanuel")\n'
            'show get_name()'
        )
        out = run1(code)
        assert out == "Emmanuel"

    def test_think_as_list_with_db(self):
        code = (
            'let db = connect(":memory:")\n'
            'db.create("items", {"name": "text"})\n'
            'let suggestions = think "list three ideas" as list\n'
            'for s in suggestions:\n'
            '    db.insert("items", {"name": s})\n'
            'show db.count("items")'
        )
        out = run1(code)
        assert out == "3"

    def test_memory_with_match(self):
        code = (
            'remember "theme" = "dark"\n'
            'let t = recall "theme"\n'
            'match t:\n'
            '    when "dark": show "dark mode on"\n'
            '    when "light": show "light mode on"\n'
            '    else: show "default mode"'
        )
        out = run1(code)
        assert out == "dark mode on"

    def test_think_as_bool_with_memory(self):
        code = (
            'remember "mode" = "production"\n'
            'let m = recall "mode"\n'
            'let is_prod = think f"Is {m} a production environment?" as bool\n'
            'show is_prod'
        )
        out = run1(code)
        assert out in ("true", "false")

    def test_forget_and_recall_in_loop(self):
        code = (
            'remember "count" = 0\n'
            'let i = 0\n'
            'repeat 3:\n'
            '    let c = recall "count" or 0\n'
            '    remember "count" = c + 1\n'
            'show recall "count"'
        )
        out = run1(code)
        assert out == "3"

    def test_think_schema_stored_in_memory(self):
        code = (
            'let profile = think "get profile" as schema {"name": "text", "age": "number"}\n'
            'remember "profile_name" = profile["name"]\n'
            'show recall "profile_name"'
        )
        out = run1(code)
        assert out == "mock_name"

    def test_all_phase9_features_together(self):
        code = (
            'remember "lang" = "NEKOVA"\n'
            'remember "version" = 2\n'
            'let lang = recall "lang"\n'
            'let ver = recall "version"\n'
            'let info = think f"Describe {lang} v{ver}" as json\n'
            'remember "last_info" = info["status"]\n'
            'let status = recall "last_info"\n'
            'match status:\n'
            '    when "ok": show "system ok"\n'
            '    else: show "system error"\n'
            'forget "last_info"\n'
            'show recall "lang"'
        )
        lines = run(code)
        assert "system ok" in lines
        assert "NEKOVA" in lines