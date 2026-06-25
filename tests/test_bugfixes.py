# =============================================================
# NEKOVA — Bug Fix Tests (Senior Engineer Review Response)
# =============================================================

import sys, os, io, re, pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def run(source):
    from nekova.lexer.lexer import Lexer
    from nekova.parser.parser import Parser
    from nekova.interpreter.interpreter import Interpreter
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        tokens  = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        interp  = Interpreter()
        for stmt in program.statements:
            interp._execute_node(stmt)
    finally:
        sys.stdout = old
    return re.sub(r'\033\[[^m]*m', '', buf.getvalue()).strip()


# === Bug 2.1 — Transpiler bare imports ===

class TestTranspilerImports:
    def test_no_bare_from_lexer_import(self):
        import inspect
        from nekova.compiler.transpiler import NEKOVATranspiler
        src = inspect.getsource(NEKOVATranspiler)
        assert "from lexer import" not in src

    def test_no_bare_from_parser_import(self):
        import inspect
        from nekova.compiler.transpiler import NEKOVATranspiler
        src = inspect.getsource(NEKOVATranspiler)
        assert "from parser import" not in src
        assert "from parser.nodes import" not in src

    def test_transpiler_instantiates(self):
        from nekova.compiler.transpiler import NEKOVATranspiler
        assert NEKOVATranspiler() is not None


# === Bug 2.2 — Tab indentation ===

class TestTabIndentation:
    def test_tab_indent_if_block(self):
        src = "if true:\n\tshow \"indented\""
        assert run(src) == "indented"

    def test_tab_indent_task(self):
        src = "task greet():\n\tshow \"hello\"\ngreet()"
        assert run(src) == "hello"

    def test_tab_indent_for_loop(self):
        src = "for i in [1, 2]:\n\tshow i"
        out = run(src)
        assert "1" in out and "2" in out

    def test_tab_produces_indent_token(self):
        from nekova.lexer.lexer import Lexer
        from nekova.lexer.token_types import TokenType
        tokens = Lexer("if true:\n\tshow 1").tokenize()
        assert TokenType.INDENT in [t.type for t in tokens]

    def test_spaces_still_work(self):
        assert run("if true:\n    show \"spaces\"") == "spaces"


# === Bug 2.3 — f-string uses LexerError ===

class TestFstringError:
    def test_unterminated_fstring_raises_lexer_error(self):
        from nekova.lexer.lexer import Lexer, LexerError
        with pytest.raises(LexerError):
            Lexer('f"unterminated').tokenize()

    def test_not_bare_syntax_error(self):
        from nekova.lexer.lexer import Lexer
        with pytest.raises(Exception) as exc_info:
            Lexer('f"unterminated').tokenize()
        assert type(exc_info.value).__name__ != "SyntaxError"

    def test_valid_fstring_unaffected(self):
        assert run("x = \"World\"\nshow f\"Hello {x}!\"") == "Hello World!"


# === Bug 2.6 — Augmented assignment tokens ===

class TestAugmentedAssignmentLexer:
    def test_plus_equal_token(self):
        from nekova.lexer.lexer import Lexer
        from nekova.lexer.token_types import TokenType
        tokens = Lexer("x += 1").tokenize()
        assert TokenType.PLUS_EQUAL in [t.type for t in tokens]

    def test_minus_equal_token(self):
        from nekova.lexer.lexer import Lexer
        from nekova.lexer.token_types import TokenType
        tokens = Lexer("x -= 1").tokenize()
        assert TokenType.MINUS_EQUAL in [t.type for t in tokens]

    def test_star_equal_token(self):
        from nekova.lexer.lexer import Lexer
        from nekova.lexer.token_types import TokenType
        tokens = Lexer("x *= 2").tokenize()
        assert TokenType.STAR_EQUAL in [t.type for t in tokens]

    def test_slash_equal_token(self):
        from nekova.lexer.lexer import Lexer
        from nekova.lexer.token_types import TokenType
        tokens = Lexer("x /= 2").tokenize()
        assert TokenType.SLASH_EQUAL in [t.type for t in tokens]


# === Bug 2.6 — Augmented assignment execution ===

class TestAugmentedAssignmentExecution:
    def test_plus_equal(self):
        assert run("x = 5\nx += 3\nshow x") == "8"

    def test_minus_equal(self):
        assert run("x = 10\nx -= 4\nshow x") == "6"

    def test_star_equal(self):
        assert run("x = 3\nx *= 4\nshow x") == "12"

    def test_slash_equal(self):
        result = run("x = 20\nx /= 4\nshow x")
        assert result in ("5", "5.0")

    def test_plus_equal_string_concat(self):
        assert run("s = \"hello\"\ns += \" world\"\nshow s") == "hello world"

    def test_augmented_in_loop(self):
        assert run("total = 0\nfor i in [1, 2, 3]:\n    total += i\nshow total") == "6"

    def test_chained_plus_equal(self):
        assert run("x = 0\nx += 1\nx += 1\nx += 1\nshow x") == "3"

    def test_minus_equal_to_zero(self):
        assert run("x = 5\nx -= 5\nshow x") == "0"

    def test_star_equal_repeated(self):
        assert run("x = 2\nx *= 2\nx *= 2\nshow x") == "8"


# === Bug 2.7 — import stdout ===

class TestImportStdout:
    def test_use_no_stdout_pollution(self):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            from nekova.lexer.lexer import Lexer
            from nekova.parser.parser import Parser
            from nekova.interpreter.interpreter import Interpreter
            tokens  = Lexer("use math\nshow sqrt(9)").tokenize()
            program = Parser(tokens).parse()
            interp  = Interpreter()
            interp.debug = False
            for stmt in program.statements:
                interp._execute_node(stmt)
        finally:
            sys.stdout = old
        out = buf.getvalue()
        assert "imported" not in out

    def test_only_program_output_in_stdout(self):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            from nekova.lexer.lexer import Lexer
            from nekova.parser.parser import Parser
            from nekova.interpreter.interpreter import Interpreter
            tokens  = Lexer("use math\nshow sqrt(9)").tokenize()
            program = Parser(tokens).parse()
            interp  = Interpreter()
            interp.debug = False
            for stmt in program.statements:
                interp._execute_node(stmt)
        finally:
            sys.stdout = old
        out = re.sub(r'\033\[[^m]*m', '', buf.getvalue()).strip()
        assert out in ("3.0", "3")


# === Feature: elif ===

class TestElifLexer:
    def test_elif_token(self):
        from nekova.lexer.lexer import Lexer
        from nekova.lexer.token_types import TokenType
        tokens = Lexer("elif x > 0:").tokenize()
        assert TokenType.ELIF in [t.type for t in tokens]

    def test_elif_in_keywords(self):
        from nekova.lexer.token_types import KEYWORDS
        assert "elif" in KEYWORDS


class TestElifExecution:
    def test_elif_middle_branch(self):
        src = "x = 5\nif x > 10:\n    show \"big\"\nelif x > 3:\n    show \"medium\"\nelse:\n    show \"small\""
        assert run(src) == "medium"

    def test_elif_first_branch_wins(self):
        src = "x = 15\nif x > 10:\n    show \"big\"\nelif x > 3:\n    show \"medium\"\nelse:\n    show \"small\""
        assert run(src) == "big"

    def test_elif_falls_to_else(self):
        src = "x = 1\nif x > 10:\n    show \"big\"\nelif x > 3:\n    show \"medium\"\nelse:\n    show \"small\""
        assert run(src) == "small"

    def test_elif_without_else(self):
        src = "x = 5\nif x > 10:\n    show \"big\"\nelif x > 3:\n    show \"medium\""
        assert run(src) == "medium"

    def test_elif_no_match_no_else(self):
        src = "x = 1\nif x > 10:\n    show \"big\"\nelif x > 3:\n    show \"medium\""
        assert run(src) == ""

    def test_multiple_elif_chains(self):
        src = (
            "score = 75\n"
            "if score >= 90:\n"
            "    show \"A\"\n"
            "elif score >= 80:\n"
            "    show \"B\"\n"
            "elif score >= 70:\n"
            "    show \"C\"\n"
            "else:\n"
            "    show \"F\""
        )
        assert run(src) == "C"

    def test_elif_complex_condition(self):
        src = "x = 5\ny = 3\nif x > 10:\n    show \"a\"\nelif x > 4 and y < 5:\n    show \"b\"\nelse:\n    show \"c\""
        assert run(src) == "b"