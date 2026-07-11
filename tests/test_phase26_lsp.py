"""
Phase 26 — Developer Experience (LSP foundation)

Covers the first slice of Phase 26: multi-error parser recovery, a
parser correctness fix discovered while building it, the diagnostics
module, and the LSP server's JSON-RPC transport + document sync.
Hover and completion are separate, later pieces of this phase and are
not covered here yet.
"""
import unittest
import io
import json

from nekova.lexer.lexer import Lexer
from nekova.parser.parser import Parser, ParseError
from nekova.lsp.diagnostics import compute_diagnostics
from nekova.lsp import server as lsp_server


# ── Multi-error parser recovery ──────────────────────────────

class TestMultiErrorParserRecovery(unittest.TestCase):

    def test_single_error_still_raises_as_before(self):
        """Every existing caller that does Parser(tokens).parse() and
        expects a plain ParseError on invalid input must keep working
        exactly as before."""
        tokens = Lexer("let x = )\n").tokenize()
        with self.assertRaises(ParseError):
            Parser(tokens).parse()

    def test_valid_source_parses_with_no_errors(self):
        tokens = Lexer("let x = 5\nshow x\n").tokenize()
        program = Parser(tokens).parse()  # must not raise
        self.assertEqual(len(program.statements), 2)

    def test_two_independent_errors_both_collected(self):
        src = (
            "let x = )\n"
            "show 1\n"
            "let y = (\n"
            "show 2\n"
        )
        tokens = Lexer(src).tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParseError) as ctx:
            parser.parse()
        all_errors = ctx.exception.all_errors
        self.assertEqual(len(all_errors), 2)
        self.assertEqual(all_errors[0].line, 1)
        self.assertEqual(all_errors[1].line, 4)

    def test_first_error_raised_matches_first_collected(self):
        src = "let x = )\nshow (\n"
        tokens = Lexer(src).tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParseError) as ctx:
            parser.parse()
        self.assertEqual(ctx.exception, ctx.exception.all_errors[0])

    def test_parser_errors_attribute_populated(self):
        src = "let x = )\nshow 1\n"
        tokens = Lexer(src).tokenize()
        parser = Parser(tokens)
        with self.assertRaises(ParseError):
            parser.parse()
        self.assertEqual(len(parser.errors), 1)


# ── Keyword-as-identifier fallback fix ───────────────────────

class TestKeywordFallbackAllowlist(unittest.TestCase):

    def test_bare_rparen_raises_proper_error_not_swallowed(self):
        """Previously a stray ')' (or any non-keyword punctuation)
        was silently accepted as Identifier(token.value) by an
        over-broad denylist-based fallback meant only for keywords.
        It must now raise a real 'Unexpected token' error."""
        tokens = Lexer("let x = )\n").tokenize()
        with self.assertRaises(ParseError) as ctx:
            Parser(tokens).parse()
        self.assertIn("Unexpected", str(ctx.exception))

    def test_task_named_after_keyword_still_works(self):
        """The actual intended use case for the fallback -- calling a
        task whose name happens to be a keyword -- must still work."""
        from nekova.interpreter.interpreter import Interpreter
        import sys
        src = (
            'task repeat(text, n):\n'
            '    show text\n'
            'repeat("ha", 3)\n'
        )
        tokens = Lexer(src).tokenize()
        program = Parser(tokens).parse()
        interp = Interpreter()
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            interp.run(program)
        finally:
            sys.stdout = old
        self.assertIn("ha", buf.getvalue())


# ── Diagnostics module ────────────────────────────────────────

class TestDiagnostics(unittest.TestCase):

    def test_clean_source_has_no_diagnostics(self):
        self.assertEqual(compute_diagnostics("let x = 5\nshow x\n"), [])

    def test_syntax_error_produces_one_diagnostic(self):
        diags = compute_diagnostics("let x = )\n")
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0]["severity"], 1)
        self.assertEqual(diags[0]["source"], "nekova")

    def test_line_numbers_are_zero_indexed_for_lsp(self):
        """NEKOVA's own errors are 1-indexed; LSP positions must be
        0-indexed -- a syntax error on source line 1 should be
        diagnostic line 0."""
        diags = compute_diagnostics("let x = )\n")
        self.assertEqual(diags[0]["range"]["start"]["line"], 0)

    def test_multiple_errors_produce_multiple_diagnostics(self):
        src = (
            "let x = )\n"
            "show 1\n"
            "let y = (\n"
            "show 2\n"
        )
        diags = compute_diagnostics(src)
        self.assertEqual(len(diags), 2)
        lines = sorted(d["range"]["start"]["line"] for d in diags)
        self.assertEqual(lines, [0, 3])

    def test_lexer_error_produces_diagnostic_with_column(self):
        diags = compute_diagnostics('let x = "unterminated')
        self.assertEqual(len(diags), 1)
        self.assertGreaterEqual(diags[0]["range"]["start"]["character"], 0)

    def test_diagnostic_shape_is_json_serializable(self):
        diags = compute_diagnostics("let x = )\n")
        json.dumps(diags)  # must not raise


# ── LSP server transport ─────────────────────────────────────

class TestLspTransport(unittest.TestCase):

    def test_write_then_read_message_roundtrip(self):
        buf = io.BytesIO()
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        lsp_server.write_message(buf, msg)
        buf.seek(0)
        result = lsp_server.read_message(buf)
        self.assertEqual(result, msg)

    def test_read_message_returns_none_at_eof(self):
        buf = io.BytesIO(b"")
        self.assertIsNone(lsp_server.read_message(buf))

    def test_multiple_messages_in_sequence(self):
        buf = io.BytesIO()
        msg1 = {"jsonrpc": "2.0", "id": 1, "method": "a"}
        msg2 = {"jsonrpc": "2.0", "id": 2, "method": "b"}
        lsp_server.write_message(buf, msg1)
        lsp_server.write_message(buf, msg2)
        buf.seek(0)
        self.assertEqual(lsp_server.read_message(buf), msg1)
        self.assertEqual(lsp_server.read_message(buf), msg2)


class TestLspDispatch(unittest.TestCase):

    def setUp(self):
        lsp_server._open_documents.clear()

    def _dispatch_and_capture(self, message):
        out = io.BytesIO()
        result = lsp_server.dispatch(out, message)
        out.seek(0)
        responses = []
        while True:
            m = lsp_server.read_message(out)
            if m is None:
                break
            responses.append(m)
        return result, responses

    def test_initialize_responds_with_capabilities(self):
        keep_running, responses = self._dispatch_and_capture({
            "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {},
        })
        self.assertTrue(keep_running)
        self.assertEqual(len(responses), 1)
        self.assertIn("capabilities", responses[0]["result"])

    def test_did_open_publishes_diagnostics(self):
        keep_running, responses = self._dispatch_and_capture({
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {
                "uri": "file:///t.nk", "text": "let x = )\n",
            }},
        })
        self.assertEqual(len(responses), 1)
        self.assertEqual(
            responses[0]["method"], "textDocument/publishDiagnostics")
        self.assertEqual(len(responses[0]["params"]["diagnostics"]), 1)

    def test_did_open_clean_source_publishes_empty_diagnostics(self):
        _, responses = self._dispatch_and_capture({
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {
                "uri": "file:///t.nk", "text": "show 1\n",
            }},
        })
        self.assertEqual(responses[0]["params"]["diagnostics"], [])

    def test_did_change_updates_diagnostics(self):
        self._dispatch_and_capture({
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {
                "uri": "file:///t.nk", "text": "let x = )\n",
            }},
        })
        _, responses = self._dispatch_and_capture({
            "jsonrpc": "2.0", "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": "file:///t.nk"},
                "contentChanges": [{"text": "show 1\n"}],
            },
        })
        self.assertEqual(responses[0]["params"]["diagnostics"], [])

    def test_did_close_clears_diagnostics_and_document(self):
        self._dispatch_and_capture({
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {
                "uri": "file:///t.nk", "text": "let x = )\n",
            }},
        })
        self.assertIn("file:///t.nk", lsp_server._open_documents)
        _, responses = self._dispatch_and_capture({
            "jsonrpc": "2.0", "method": "textDocument/didClose",
            "params": {"textDocument": {"uri": "file:///t.nk"}},
        })
        self.assertEqual(responses[0]["params"]["diagnostics"], [])
        self.assertNotIn("file:///t.nk", lsp_server._open_documents)

    def test_exit_stops_the_server_loop(self):
        keep_running, _ = self._dispatch_and_capture({
            "jsonrpc": "2.0", "method": "exit", "params": {},
        })
        self.assertFalse(keep_running)

    def test_shutdown_responds_and_keeps_running(self):
        keep_running, responses = self._dispatch_and_capture({
            "jsonrpc": "2.0", "id": 5, "method": "shutdown", "params": {},
        })
        self.assertTrue(keep_running)
        self.assertEqual(responses[0]["id"], 5)

    def test_unknown_request_gets_method_not_found_error(self):
        # textDocument/completion isn't wired up yet (a later Phase
        # 26 piece) -- hover now is, so this had to move to a method
        # that's still genuinely unimplemented.
        _, responses = self._dispatch_and_capture({
            "jsonrpc": "2.0", "id": 9, "method": "textDocument/completion",
            "params": {},
        })
        self.assertIn("error", responses[0])
        self.assertEqual(responses[0]["error"]["code"], -32601)

    def test_unknown_notification_silently_ignored(self):
        keep_running, responses = self._dispatch_and_capture({
            "jsonrpc": "2.0", "method": "$/someNotification", "params": {},
        })
        self.assertTrue(keep_running)
        self.assertEqual(responses, [])


# ── Hover ─────────────────────────────────────────────────────

class TestHoverModule(unittest.TestCase):

    def test_keyword_hover(self):
        from nekova.lsp.hover import compute_hover
        r = compute_hover("let x = 5\n", 0, 0)
        self.assertIsNotNone(r)
        self.assertIn("variable", r["contents"]["value"])
        self.assertEqual(r["range"]["start"], {"line": 0, "character": 0})
        self.assertEqual(r["range"]["end"], {"line": 0, "character": 3})

    def test_builtin_hover(self):
        from nekova.lsp.hover import compute_hover
        src = "let data = [3, 1, 2]\nlet r = data |> sort()\n"
        # find the character position of "sort" on line 1
        col = src.split("\n")[1].index("sort")
        r = compute_hover(src, 1, col)
        self.assertIsNotNone(r)
        self.assertIn("sort(", r["contents"]["value"])

    def test_user_defined_task_hover_shows_real_signature_and_docstring(self):
        from nekova.lsp.hover import compute_hover
        src = (
            'task add(a, b):\n'
            '    """Adds two numbers."""\n'
            '    return a + b\n'
            'show add(1, 2)\n'
        )
        col = src.split("\n")[0].index("add")
        r = compute_hover(src, 0, col)
        self.assertIsNotNone(r)
        self.assertIn("add(a, b)", r["contents"]["value"])
        self.assertIn("Adds two numbers.", r["contents"]["value"])

    def test_hover_on_call_site_finds_definition(self):
        from nekova.lsp.hover import compute_hover
        src = (
            'task add(a, b):\n'
            '    return a + b\n'
            'show add(1, 2)\n'
        )
        col = src.split("\n")[2].index("add")
        r = compute_hover(src, 2, col)
        self.assertIsNotNone(r)
        self.assertIn("add(a, b)", r["contents"]["value"])

    def test_nested_task_closure_hover_finds_definition(self):
        """Hover should find task definitions nested inside another
        task's body too (e.g. the counter-factory closure pattern),
        not just top-level ones."""
        from nekova.lsp.hover import compute_hover
        src = (
            'task make_counter():\n'
            '    let count = 0\n'
            '    task increment():\n'
            '        count = count + 1\n'
            '        return count\n'
            '    return increment\n'
        )
        line3 = src.split("\n")[2]
        col = line3.index("increment")
        r = compute_hover(src, 2, col)
        self.assertIsNotNone(r)
        self.assertIn("increment()", r["contents"]["value"])

    def test_no_hover_on_whitespace(self):
        from nekova.lsp.hover import compute_hover
        r = compute_hover("let x = 5\n", 0, 3)  # the space
        self.assertIsNone(r)

    def test_string_literal_does_not_false_positive_as_keyword(self):
        from nekova.lsp.hover import compute_hover
        src = 'show "let me explain"\n'
        col = src.index("let")
        r = compute_hover(src, 0, col)
        self.assertIsNone(r)

    def test_hover_tolerates_syntax_errors_elsewhere_in_document(self):
        """A hover request over a keyword shouldn't fail just because
        some other part of the same document has a syntax error --
        keyword/builtin lookup only needs the token stream."""
        from nekova.lsp.hover import compute_hover
        src = "let x = )\nshow x\n"
        r = compute_hover(src, 0, 0)  # hover over 'let'
        self.assertIsNotNone(r)


class TestHoverServerIntegration(unittest.TestCase):

    def setUp(self):
        lsp_server._open_documents.clear()

    def test_hover_request_through_dispatch(self):
        out = io.BytesIO()
        lsp_server.dispatch(out, {
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": {
                "uri": "file:///t.nk", "text": "let x = 5\n",
            }},
        })
        out = io.BytesIO()
        lsp_server.dispatch(out, {
            "jsonrpc": "2.0", "id": 1, "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": "file:///t.nk"},
                "position": {"line": 0, "character": 0},
            },
        })
        out.seek(0)
        response = lsp_server.read_message(out)
        self.assertIsNotNone(response["result"])

    def test_hover_on_unopened_document_returns_none_not_crash(self):
        out = io.BytesIO()
        lsp_server.dispatch(out, {
            "jsonrpc": "2.0", "id": 1, "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": "file:///never-opened.nk"},
                "position": {"line": 0, "character": 0},
            },
        })
        out.seek(0)
        response = lsp_server.read_message(out)
        self.assertIsNone(response["result"])

    def test_malformed_hover_request_does_not_crash_server(self):
        out = io.BytesIO()
        lsp_server.dispatch(out, {
            "jsonrpc": "2.0", "id": 1, "method": "textDocument/hover",
            "params": {},
        })
        out.seek(0)
        response = lsp_server.read_message(out)
        self.assertIsNone(response["result"])

    def test_initialize_advertises_hover_provider(self):
        out = io.BytesIO()
        lsp_server.dispatch(out, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {},
        })
        out.seek(0)
        response = lsp_server.read_message(out)
        self.assertTrue(response["result"]["capabilities"]["hoverProvider"])


if __name__ == "__main__":
    unittest.main()