# =============================================================
# NEKOVA Phase 7 Tests — Pattern Matching + Web + Database
# =============================================================
import pytest
import sys
import os
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser
from nekova.interpreter.interpreter import Interpreter


def run(code: str) -> list:
    """Run NEKOVA source and return list of output lines."""
    tokens = Lexer(code).tokenize()
    ast    = Parser(tokens).parse()
    interp = Interpreter()

    captured   = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        interp.execute(ast)
    finally:
        sys.stdout = old_stdout

    text = captured.getvalue()
    # Strip ANSI codes so tests stay colour-agnostic
    import re
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    return [l for l in text.splitlines() if l.strip()]


# ==============================================================
# SECTION 1 — Pattern Matching (match/when)
# ==============================================================

class TestPatternMatchingValues:

    def test_match_first_arm(self):
        out = run("match 200:\n    when 200: show \"OK\"\n    when 404: show \"Not found\"")
        assert out == ["OK"]

    def test_match_second_arm(self):
        out = run("match 404:\n    when 200: show \"OK\"\n    when 404: show \"Not found\"")
        assert out == ["Not found"]

    def test_match_else(self):
        out = run("match 999:\n    when 200: show \"OK\"\n    when 404: show \"Not found\"\n    else: show \"Unknown\"")
        assert out == ["Unknown"]

    def test_match_no_arm_no_else(self):
        out = run("match 999:\n    when 1: show \"one\"\n    when 2: show \"two\"")
        assert out == []

    def test_match_string_value(self):
        out = run('match "hello":\n    when "hello": show "hi"\n    when "bye": show "goodbye"')
        assert out == ["hi"]

    def test_match_boolean_true(self):
        out = run("match true:\n    when true: show \"yes\"\n    when false: show \"no\"")
        assert out == ["yes"]

    def test_match_boolean_false(self):
        out = run("match false:\n    when true: show \"yes\"\n    when false: show \"no\"")
        assert out == ["no"]

    def test_match_variable_subject(self):
        out = run("let s = 200\nmatch s:\n    when 200: show \"good\"\n    else: show \"bad\"")
        assert out == ["good"]

    def test_match_expression_subject(self):
        out = run("let x = 100\nmatch x + 100:\n    when 200: show \"two hundred\"\n    else: show \"other\"")
        assert out == ["two hundred"]

    def test_match_multiple_arms_order(self):
        out = run("match 1:\n    when 1: show \"first\"\n    when 1: show \"second\"")
        assert out == ["first"]

    def test_match_else_only(self):
        out = run("match 42:\n    else: show \"catch all\"")
        assert out == ["catch all"]

    def test_match_integer_literals(self):
        for status, expected in [(200, "ok"), (201, "created"), (400, "bad"), (500, "error")]:
            out = run(
                f"match {status}:\n"
                "    when 200: show \"ok\"\n"
                "    when 201: show \"created\"\n"
                "    when 400: show \"bad\"\n"
                "    when 500: show \"error\"\n"
                "    else: show \"unknown\""
            )
            assert out == [expected], f"status={status}"


class TestPatternMatchingTypes:

    def test_match_type_text(self):
        out = run('let v = "hello"\nmatch v:\n    when text: show "is text"\n    when number: show "is number"')
        assert out == ["is text"]

    def test_match_type_number_int(self):
        out = run("let v = 42\nmatch v:\n    when text: show \"is text\"\n    when number: show \"is number\"")
        assert out == ["is number"]

    def test_match_type_number_float(self):
        out = run("let v = 3.14\nmatch v:\n    when text: show \"is text\"\n    when number: show \"is number\"")
        assert out == ["is number"]

    def test_match_type_boolean(self):
        out = run("let v = true\nmatch v:\n    when boolean: show \"is bool\"\n    when number: show \"is number\"")
        assert out == ["is bool"]

    def test_match_type_list(self):
        out = run("let v = [1, 2, 3]\nmatch v:\n    when list: show \"is list\"\n    else: show \"other\"")
        assert out == ["is list"]

    def test_match_type_dict(self):
        out = run('let v = {"a": 1}\nmatch v:\n    when dict: show "is dict"\n    else: show "other"')
        assert out == ["is dict"]

    def test_match_type_null(self):
        out = run("let v = null\nmatch v:\n    when null: show \"is null\"\n    else: show \"other\"")
        assert out == ["is null"]

    def test_match_type_any(self):
        out = run("let v = 42\nmatch v:\n    when any: show \"matches anything\"")
        assert out == ["matches anything"]

    def test_match_type_else_fallback(self):
        out = run("let v = 3.14\nmatch v:\n    when text: show \"text\"\n    else: show \"not text\"")
        assert out == ["not text"]

    def test_match_boolean_not_number(self):
        # bool is NOT matched by `when number` — it has its own type
        out = run("let v = true\nmatch v:\n    when number: show \"number\"\n    when boolean: show \"boolean\"")
        assert out == ["boolean"]


class TestPatternMatchingBodies:

    def test_match_body_multiline(self):
        code = (
            'let x = 1\n'
            'match x:\n'
            '    when 1:\n'
            '        show "line one"\n'
            '        show "line two"\n'
            '    else: show "other"'
        )
        out = run(code)
        assert out == ["line one", "line two"]

    def test_match_body_uses_fstring(self):
        out = run('let s = 404\nmatch s:\n    when 404: show f"Error {s}"\n    else: show "ok"')
        assert out == ["Error 404"]

    def test_match_in_task(self):
        code = (
            'task check(code):\n'
            '    match code:\n'
            '        when 200: return "OK"\n'
            '        when 404: return "Not found"\n'
            '        else: return "Unknown"\n'
            'show check(200)\n'
            'show check(404)\n'
            'show check(500)'
        )
        out = run(code)
        assert out == ["OK", "Not found", "Unknown"]

    def test_match_nested(self):
        code = (
            'let a = 1\n'
            'let b = 2\n'
            'match a:\n'
            '    when 1:\n'
            '        match b:\n'
            '            when 2: show "1 and 2"\n'
            '            else: show "1 only"\n'
            '    else: show "not 1"'
        )
        out = run(code)
        assert out == ["1 and 2"]

    def test_match_result_used_in_assignment(self):
        code = (
            'task label(n):\n'
            '    match n:\n'
            '        when 0: return "zero"\n'
            '        when 1: return "one"\n'
            '        else: return "many"\n'
            'let result = label(1)\n'
            'show result'
        )
        out = run(code)
        assert out == ["one"]


# ==============================================================
# SECTION 2 — Database Module (use database + connect())
# ==============================================================

class TestDatabaseConnect:

    def test_connect_returns_dbobject(self):
        from nekova.interpreter.interpreter import _DBObject
        tokens = Lexer('let db = connect(":memory:")').tokenize()
        ast    = Parser(tokens).parse()
        interp = Interpreter()
        captured = StringIO()
        sys.stdout = captured
        try:
            interp.execute(ast)
        finally:
            sys.stdout = sys.__stdout__
        db = interp.env.get("db")
        assert isinstance(db, _DBObject)

    def test_connect_in_memory(self):
        out = run('let db = connect(":memory:")\nshow "connected"')
        assert "connected" in out


class TestDatabaseCRUD:

    def _fresh_db(self):
        code = (
            'let db = connect(":memory:")\n'
            'db.create("users", {"name": "text", "email": "text", "age": "number"})\n'
        )
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        interp = Interpreter()
        captured = StringIO()
        sys.stdout = captured
        try:
            interp.execute(ast)
        finally:
            sys.stdout = sys.__stdout__
        return interp

    def test_create_table(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        assert db.exists("users")

    def test_insert_and_count(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Emmanuel", "email": "e@x.com", "age": 25})
        db.insert("users", {"name": "Alice",    "email": "a@x.com", "age": 30})
        assert db.count("users") == 2

    def test_query_all(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Emmanuel", "email": "e@x.com", "age": 25})
        rows = db.query("users").all()
        assert len(rows) == 1
        assert rows[0].name == "Emmanuel"

    def test_query_where(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Emmanuel", "email": "e@x.com", "age": 25})
        db.insert("users", {"name": "Alice",    "email": "a@x.com", "age": 30})
        rows = db.query("users").where("name", "Alice").all()
        assert len(rows) == 1
        assert rows[0].name == "Alice"

    def test_query_first(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Emmanuel", "email": "e@x.com", "age": 25})
        row = db.query("users").first()
        assert row is not None
        assert row.name == "Emmanuel"

    def test_query_first_none(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        row = db.query("users").first()
        assert row is None

    def test_row_attribute_access(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Emmanuel", "email": "e@x.com", "age": 25})
        row = db.query("users").first()
        assert row.name  == "Emmanuel"
        assert row.email == "e@x.com"
        assert row.id    == 1

    def test_row_subscript_access(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Alice", "email": "a@x.com", "age": 30})
        row = db.query("users").first()
        assert row["name"] == "Alice"

    def test_count_with_where(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Emmanuel", "email": "e@x.com", "age": 25})
        db.insert("users", {"name": "Alice",    "email": "a@x.com", "age": 30})
        assert db.query("users").where("name", "Alice").count() == 1

    def test_tables_list(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        assert "users" in db.tables()

    def test_exists_true(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        assert db.exists("users") is True

    def test_exists_false(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        assert db.exists("posts") is False

    def test_raw_sql(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Emmanuel", "email": "e@x.com", "age": 25})
        rows = db.sql("SELECT * FROM users")
        assert len(rows) == 1
        assert rows[0]["name"] == "Emmanuel"

    def test_find_helper(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Emmanuel", "email": "e@x.com", "age": 25})
        rows = db.find("users")
        assert len(rows) == 1
        assert rows[0]["name"] == "Emmanuel"

    def test_drop_table(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        assert db.exists("users")
        db.drop("users")
        assert db.exists("users") is False

    def test_close_reconnect(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.close()   # should not raise

    def test_query_order(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        db.insert("users", {"name": "Charlie", "email": "c@x.com", "age": 22})
        db.insert("users", {"name": "Alice",   "email": "a@x.com", "age": 30})
        db.insert("users", {"name": "Bob",     "email": "b@x.com", "age": 25})
        rows = db.query("users").order("name").all()
        names = [r.name for r in rows]
        assert names == ["Alice", "Bob", "Charlie"]

    def test_query_limit(self):
        interp = self._fresh_db()
        db = interp.env.get("db")
        for i in range(5):
            db.insert("users", {"name": f"User{i}", "email": f"u{i}@x.com", "age": 20+i})
        rows = db.query("users").limit(3).all()
        assert len(rows) == 3


class TestDatabaseInNEKOVACode:

    def test_db_for_loop(self):
        code = (
            'let db = connect(":memory:")\n'
            'db.create("items", {"name": "text"})\n'
            'db.insert("items", {"name": "apple"})\n'
            'db.insert("items", {"name": "banana"})\n'
            'let rows = db.query("items").all()\n'
            'for row in rows:\n'
            '    show row.name'
        )
        out = run(code)
        assert "apple" in out
        assert "banana" in out

    def test_db_fstring_output(self):
        code = (
            'let db = connect(":memory:")\n'
            'db.create("users", {"name": "text", "age": "number"})\n'
            'db.insert("users", {"name": "Emmanuel", "age": 25})\n'
            'let u = db.query("users").first()\n'
            'show f"{u.name} is {u.age}"'
        )
        out = run(code)
        assert out[-1] == "Emmanuel is 25"

    def test_db_count_output(self):
        code = (
            'let db = connect(":memory:")\n'
            'db.create("t", {"x": "text"})\n'
            'db.insert("t", {"x": "a"})\n'
            'db.insert("t", {"x": "b"})\n'
            'db.insert("t", {"x": "c"})\n'
            'show db.count("t")'
        )
        out = run(code)
        assert out[-1] == "3"

    def test_db_with_match(self):
        code = (
            'let db = connect(":memory:")\n'
            'db.create("orders", {"status": "text"})\n'
            'db.insert("orders", {"status": "paid"})\n'
            'let o = db.query("orders").first()\n'
            'match o.status:\n'
            '    when "paid": show "Payment received"\n'
            '    when "pending": show "Awaiting payment"\n'
            '    else: show "Unknown status"'
        )
        out = run(code)
        assert out[-1] == "Payment received"

    def test_use_database_module(self):
        code = (
            'use database\n'
            'db_connect(":memory:")\n'
            'db_create("items", "name text")\n'
            'show "db ready"'
        )
        out = run(code)
        assert "db ready" in out


# ==============================================================
# SECTION 3 — Web Module (parse & structure tests — no blocking)
# ==============================================================

class TestWebModuleParsing:

    def test_route_parses(self):
        from nekova.parser.nodes import RouteStatement
        code = 'use web\nroute GET "/":\n    return "hello"'
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        routes = [n for n in ast.statements if isinstance(n, RouteStatement)]
        assert len(routes) == 1
        assert routes[0].method == "GET"
        assert routes[0].path   == "/"

    def test_route_post_parses(self):
        from nekova.parser.nodes import RouteStatement
        code = 'use web\nroute POST "/api/chat":\n    return "reply"'
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        routes = [n for n in ast.statements if isinstance(n, RouteStatement)]
        assert routes[0].method == "POST"
        assert routes[0].path   == "/api/chat"

    def test_route_put_parses(self):
        from nekova.parser.nodes import RouteStatement
        code = 'use web\nroute PUT "/users":\n    return "updated"'
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        routes = [n for n in ast.statements if isinstance(n, RouteStatement)]
        assert routes[0].method == "PUT"

    def test_route_delete_parses(self):
        from nekova.parser.nodes import RouteStatement
        code = 'use web\nroute DELETE "/users":\n    return "deleted"'
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        routes = [n for n in ast.statements if isinstance(n, RouteStatement)]
        assert routes[0].method == "DELETE"

    def test_serve_with_port_parses(self):
        from nekova.parser.nodes import ServeStatement
        code = "use web\nserve port: 8080"
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        serves = [n for n in ast.statements if isinstance(n, ServeStatement)]
        assert len(serves) == 1
        assert serves[0].port_expr is not None

    def test_serve_no_port_parses(self):
        from nekova.parser.nodes import ServeStatement
        code = "use web\nserve"
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        serves = [n for n in ast.statements if isinstance(n, ServeStatement)]
        assert len(serves) == 1
        assert serves[0].port_expr is None

    def test_multiple_routes_parse(self):
        from nekova.parser.nodes import RouteStatement
        code = (
            'use web\n'
            'route GET "/":\n'
            '    return "home"\n'
            'route GET "/about":\n'
            '    return "about"\n'
            'route POST "/api/data":\n'
            '    return "data"'
        )
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        routes = [n for n in ast.statements if isinstance(n, RouteStatement)]
        assert len(routes) == 3
        paths = [r.path for r in routes]
        assert "/" in paths
        assert "/about" in paths
        assert "/api/data" in paths

    def test_route_body_has_statements(self):
        from nekova.parser.nodes import RouteStatement
        code = 'route GET "/":\n    show "hello"\n    return "done"'
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        routes = [n for n in ast.statements if isinstance(n, RouteStatement)]
        assert len(routes[0].body) >= 1


class TestWebModuleRegistry:

    def _silence(self, code):
        tokens = Lexer(code).tokenize()
        ast    = Parser(tokens).parse()
        interp = Interpreter()
        captured = StringIO()
        sys.stdout = captured
        try:
            interp.execute(ast)
        finally:
            sys.stdout = sys.__stdout__
        return interp

    def test_use_web_loads_web_app(self):
        interp = self._silence('use web')
        assert interp.env.get("web_app") is not None

    def test_use_web_loads_web_start(self):
        interp = self._silence('use web')
        assert interp.env.get("web_start") is not None

    def test_use_web_loads_response_helpers(self):
        interp = self._silence('use web')
        assert interp.env.get("web_html") is not None
        assert interp.env.get("web_json") is not None
        assert interp.env.get("web_text") is not None

    def test_web_response_helpers_callable(self):
        interp = self._silence('use web')
        web_html = interp.env.get("web_html")
        result   = web_html("<h1>Hello</h1>")
        assert "<h1>Hello</h1>" in result

    def test_route_registers_with_server(self):
        from nekova.web import web_module as wm
        wm._server = None
        code = 'route GET "/test":\n    return "ok"'
        self._silence(code)
        assert wm._server is not None
        routes = wm._server.router.get_routes()
        paths  = [r.path for r in routes]
        assert "/test" in paths

    def test_route_handler_returns_response(self):
        from nekova.web import web_module as wm
        from nekova.web.request import NEKOVARequest
        from nekova.web.response import NEKOVAResponse
        from nekova.runtime import ReturnSignal
        wm._server = None

        code = 'route GET "/ping":\n    return html("<h1>pong</h1>")'
        self._silence(code)

        route    = wm._server.router.get_routes()[0]
        request  = NEKOVARequest(method="GET", path="/ping")
        response = route.handler(request)

        assert isinstance(response, NEKOVAResponse)
        assert "pong" in response.body


# ==============================================================
# SECTION 4 — Integration: Match + DB + Web together
# ==============================================================

class TestIntegration:

    def test_match_db_results(self):
        code = (
            'let db = connect(":memory:")\n'
            'db.create("products", {"name": "text", "stock": "number"})\n'
            'db.insert("products", {"name": "Widget", "stock": 0})\n'
            'let p = db.query("products").first()\n'
            'match p.stock:\n'
            '    when 0: show "Out of stock"\n'
            '    else: show "In stock"'
        )
        out = run(code)
        assert out[-1] == "Out of stock"

    def test_type_match_on_db_row_field(self):
        code = (
            'let db = connect(":memory:")\n'
            'db.create("notes", {"content": "text"})\n'
            'db.insert("notes", {"content": "hello"})\n'
            'let n = db.query("notes").first()\n'
            'match n.content:\n'
            '    when text: show "text field"\n'
            '    else: show "other"'
        )
        out = run(code)
        assert out[-1] == "text field"

    def test_match_inside_for_loop_over_db(self):
        code = (
            'let db = connect(":memory:")\n'
            'db.create("t", {"val": "number"})\n'
            'db.insert("t", {"val": 1})\n'
            'db.insert("t", {"val": 2})\n'
            'db.insert("t", {"val": 3})\n'
            'let rows = db.query("t").all()\n'
            'for row in rows:\n'
            '    match row.val:\n'
            '        when 1: show "one"\n'
            '        when 2: show "two"\n'
            '        else: show "many"'
        )
        out = run(code)
        assert out[-3:] == ["one", "two", "many"]