from nekova.lexer.token_types import TokenType, KEYWORDS
from nekova.lexer.token import Token
from nekova.parser.nodes import (
    Program, IntegerLiteral, FloatLiteral, StringLiteral, FStringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral, TupleLiteral, DictLiteral,
    Identifier, BinaryOp, UnaryOp, AssignStatement,
    ShowStatement, ThinkStatement, PipelineStatement, ModelStatement, ParallelStatement, MemoryStatement,
    SandboxStatement, PipelineDefStatement, RunPipelineStatement, IfStatement, RepeatStatement,
    WhileStatement, TryStatement, ForStatement,
    TaskStatement, ReturnStatement, BreakStatement, ContinueStatement, GlobalStatement, UnpackStatement, UseStatement,
    ListDestructureStatement, DictDestructureStatement, SpreadElement,
    EnumDefinition, SetLiteral, ConverseStatement,
    ImportStatement, CallExpression, IndexExpression, IndexAssignStatement,
    MethodCall,
    PropertyAccess,
    ClassDefinition, MethodDefinition,
    NewInstance, SelfAccess, SelfAssign,
    # Phase 7
    MatchStatement, MatchArm, RouteStatement, ServeStatement,
    # Phase 9
    ThinkAsStatement, RememberStatement, RecallStatement, ForgetStatement,
    # Phase 15
    SliceExpression, RaiseStatement, PassStatement, AssertStatement, TernaryExpression,
    # Phase 16
    SpeakStatement, ListenExpression, EveryStatement,
    TestBlock, ExpectStatement, ImagineStatement,
    ShapeDefinition, WatchStatement,
    # Phase 17
    YieldStatement, DecoratorStatement, ErrorDefinition, TypedTaskStatement,
    # Phase 21
    PromptStatement, RetryStatement,
    # Phase 22
    ObserveStatement, MockStatement,
)
from nekova.parser.async_nodes import (
    AsyncFunctionNode, AwaitNode, StreamThinkNode, FetchNode
)
from nekova.parser.async_parser import AsyncParserMixin
from nekova.parser.class_parser import ClassParserMixin
from nekova.parser.match_parser import MatchParserMixin
from nekova.parser.web_parser import WebParserMixin



class ParseError(Exception):
    """Raised when the parser encounters invalid syntax."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  Line {line}: {message}")


# Token types for actual language keywords (if, show, task, model, ...).
# Used by _parse_primary's last-resort "keyword as identifier" fallback
# so it only ever fires for real keywords being reused as a name (e.g.
# a task called `repeat`), not for punctuation/operators like a stray
# ')' or ','. See that fallback for why this matters.
_KEYWORD_TOKEN_TYPES = set(KEYWORDS.values())


class Parser(AsyncParserMixin, ClassParserMixin, MatchParserMixin, WebParserMixin):
    """
    Converts a list of Tokens into an AST.

    Usage:
        parser  = Parser(tokens)
        program = parser.parse()
    """

    def __init__(self, tokens: list):
        # Filter out blank newlines at the start
        self.tokens  = tokens
        self.pos     = 0
        # Phase 26: multi-error parser recovery. Collected here as
        # parse() catches and resynchronizes past each ParseError
        # instead of stopping at the first one. Most callers still
        # get the exact same single-exception behavior as before (see
        # parse() below) — this list exists for callers that want
        # every error in one pass, like the LSP's diagnostics.
        self.errors  = []

    def _stamp(self, node, line: int):
        """Stamp a source line number onto any AST node and return it."""
        node.line = line
        return node

    # ----------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------

    def parse(self) -> Program:
        """
        Parse all tokens and return the root Program node.

        On a syntax error, previously this let the ParseError
        propagate straight out of the while loop, so a file with
        several unrelated mistakes only ever reported the first one 
        — fix it, re-run, hit the next one, repeat. Now each error is
        caught, resynchronized past (skip to the next likely
        statement boundary), and parsing continues, so all of them
        can be collected in self.errors in a single pass.

        Every existing caller that does `Parser(tokens).parse()` and
        expects a single ParseError exception on invalid input keeps
        working exactly as before — if there were any errors, the
        first one is still raised at the end, with the same message
        and line it always had. It just now also carries
        `.all_errors` (the full list) for callers that want more than
        one, like the LSP's diagnostics.
        """
        statements = self._parse_all_statements()

        if self.errors:
            first = self.errors[0]
            first.all_errors = list(self.errors)
            raise first

        return Program(statements)

    def parse_best_effort(self) -> Program:
        """
        Like parse(), but always returns a Program — every statement
        successfully parsed before, between, and after any errors —
        instead of raising. self.errors still gets populated exactly
        the same way, for callers that want to know what went wrong.

        For LSP features that need *something* to work with even on
        a document that's currently invalid, which is the normal
        state of a file while someone is actively typing: e.g.
        autocomplete needs to see a task defined earlier in the file
        even if the line the cursor is currently on doesn't parse
        yet. parse() intentionally keeps its strict contract (raise
        on any error) for every other caller — this is a separate,
        explicit opt-in rather than a behavior change to the
        existing method.
        """
        return Program(self._parse_all_statements())

    def _parse_all_statements(self) -> list:
        """Shared core loop for parse() and parse_best_effort()."""
        statements = []

        self._skip_newlines()

        while not self._at_end():
            try:
                stmt = self._parse_statement()
                if stmt is not None:
                    statements.append(stmt)
                self._skip_newlines()
            except ParseError as e:
                self.errors.append(e)
                self._synchronize()

        return statements

    def _synchronize(self):
        """
        After a parse error, skip tokens up to the next likely
        statement boundary (a NEWLINE, since top-level statements are
        newline-terminated) so parse() can attempt the next statement
        instead of stopping. A simple, standard recovery heuristic —
        it won't always land in a perfectly sensible spot for badly
        malformed input, but it's what lets a single pass surface
        several independent errors instead of just the first.
        """
        while not self._at_end() and self._current().type != TokenType.NEWLINE:
            self._advance()
        self._skip_newlines()

    # ----------------------------------------------------------
    # Statement parsers
    # ----------------------------------------------------------

    def _parse_statement(self):
        """Decide which kind of statement to parse next."""
        token = self._current()

        if token.type == TokenType.SHOW:
            return self._parse_show()
        
        if token.type == TokenType.THINK:
            return self._parse_think()
        
        if token.type == TokenType.MODEL:
            return self._parse_model()
        
        if token.type == TokenType.PIPELINE_DEF:
            return self._parse_pipeline_def()
        
        if token.type == TokenType.RUN:
            return self._parse_run_pipeline()
        
        if token.type == TokenType.AUTONOMOUS:
            return self._parse_autonomous()
        
        if token.type == TokenType.MEMORY:
            return self._parse_memory()
        
        if token.type == TokenType.SANDBOX:
            return self._parse_sandbox()
        
        if token.type == TokenType.STRING:
            # Could be a pipeline: "prompt" -> agent1 -> agent2
            first = self._parse_primary()
            if self._current().type == TokenType.ARROW:
                return self._parse_pipeline(first)
            raise ParseError(
                "Unexpected string — did you mean to use 'show' or '->'?",
                token.line
            )

        if token.type == TokenType.ARROW:
            return self._parse_pipeline(self._parse_primary())

        if token.type == TokenType.IF:
            return self._parse_if()

        if token.type == TokenType.REPEAT:
            # If followed by '(' it's a function call, not a loop
            if self._peek_type() == TokenType.LPAREN:
                self._advance()  # consume REPEAT token
                expr = Identifier('repeat')
                self._consume(TokenType.LPAREN)
                args = []
                while self._current().type != TokenType.RPAREN:
                    args.append(self._parse_expression())
                    if self._current().type == TokenType.COMMA:
                        self._advance()
                self._consume(TokenType.RPAREN)
                call = CallExpression(expr, args)
                self._expect_newline_or_eof()
                return call
            return self._parse_repeat()

        if token.type == TokenType.WHILE:
            return self._parse_while()
        
        if token.type == TokenType.TRY:
            return self._parse_try()
        
        if token.type == TokenType.FOR:
            return self._parse_for()

        if token.type == TokenType.TASK:
            return self._parse_task()

        if token.type == TokenType.RETRY:
            return self._parse_retry()

        if token.type == TokenType.OBSERVE:
            return self._parse_observe()

        if token.type == TokenType.MOCK:
            return self._parse_mock()

        if token.type == TokenType.RETURN:
            return self._parse_return()

        if token.type == TokenType.BREAK:
            self._advance()
            self._expect_newline_or_eof()
            return BreakStatement()

        if token.type == TokenType.CONTINUE:
            self._advance()
            self._expect_newline_or_eof()
            return ContinueStatement()

        if token.type == TokenType.GLOBAL:
            return self._parse_global()

        if token.type == TokenType.USE:
            return self._parse_use()

        if token.type == TokenType.IMPORT:
            return self._parse_import()
        
        if token.type == TokenType.ASYNC:
            return self.parse_async_function()

        if token.type == TokenType.AWAIT:
            return self.parse_await_expr()

        if token.type == TokenType.STREAM:
            return self.parse_stream_think()

        if token.type == TokenType.FETCH:
            return self.parse_fetch_expr()

        if token.type == TokenType.OBJECT:
            return self.parse_class_definition()

        if token.type == TokenType.NEW:
            node = self.parse_new_instance()
            self._expect_newline_or_eof()
            return node

        if token.type == TokenType.SELF:
            return self.parse_self_expr()

        if token.type == TokenType.LET:
            return self._parse_let()

        if token.type == TokenType.CONST:
            return self._parse_const()

        if token.type == TokenType.ENUM:
            return self._parse_enum()

        if token.type == TokenType.CONVERSE:
            return self._parse_converse()

        if token.type == TokenType.YIELD:
            return self._parse_yield()

        if token.type == TokenType.AT:
            return self._parse_decorator()

        if token.type == TokenType.ERROR_TYPE:
            return self._parse_error_def()

        if token.type == TokenType.CLASS:
            return self.parse_class_definition()

        if token.type == TokenType.SPEAK:
            return self._parse_speak()

        if token.type == TokenType.LISTEN:
            return self._parse_listen_stmt()

        if token.type == TokenType.EVERY:
            return self._parse_every()

        if token.type == TokenType.TEST:
            return self._parse_test()

        if token.type == TokenType.EXPECT:
            return self._parse_expect()

        if token.type == TokenType.IMAGINE:
            return self._parse_imagine()

        if token.type == TokenType.SHAPE:
            return self._parse_shape()

        if token.type == TokenType.WATCH:
            return self._parse_watch()

        if token.type == TokenType.IDENTIFIER:
            if token.value == "pass":
                self._advance()
                self._expect_newline_or_eof()
                return self._stamp(PassStatement(line=token.line), token.line)
            if token.value == "assert":
                return self._parse_assert()
            if token.value == "raise":
                return self._parse_raise()
            if token.value == "prompt" and self._looks_like_prompt_def():
                return self._parse_prompt()

            # Tuple unpacking: a, b, c = expr
            # Peek ahead — if after the first IDENTIFIER there's a COMMA,
            # this is a multi-variable unpack assignment.
            if (self.pos + 1 < len(self.tokens)
                    and self.tokens[self.pos + 1].type == TokenType.COMMA):
                return self._parse_unpack()

            return self._parse_identifier_statement()

        if token.type == TokenType.REMEMBER:
            return self._parse_remember()

        if token.type == TokenType.RECALL:
            return self._parse_recall()

        if token.type == TokenType.FORGET:
            return self._parse_forget()

        if token.type == TokenType.MATCH:
            return self._parse_match()

        if token.type == TokenType.ROUTE:
            return self._parse_route()

        if token.type == TokenType.SERVE:
            return self._parse_serve()

        if token.type in (TokenType.NEWLINE, TokenType.EOF):
            return None

        raise ParseError(
            f"Unexpected token '{token.value}' — "
            f"NEKOVA doesn't know what to do with this here.",
            token.line
        )


    # ── Phase 16: Standout Feature Parsers ───────────────────

    def _parse_speak(self):
        """Parse:  speak <expression>"""
        line = self._current().line
        self._consume(TokenType.SPEAK)
        expr = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(SpeakStatement(expr, line=line), line)

    def _parse_listen_stmt(self):
        """Parse:  listen  or  listen "prompt"  as a statement."""
        line = self._current().line
        self._consume(TokenType.LISTEN)
        prompt = None
        if self._current().type == TokenType.STRING:
            prompt = StringLiteral(self._advance().value)
        self._expect_newline_or_eof()
        return self._stamp(ListenExpression(prompt, line=line), line)

    def _parse_every(self):
        """
        Parse:
            every 5s:
                <body>
            every 1m:
                <body>
            every 10s 3 times:
                <body>
        """
        line = self._current().line
        self._consume(TokenType.EVERY)

        # interval value
        interval_val = self._parse_expression()

        # interval unit — must be an identifier ending in s/m/h
        # e.g. "5s" is tokenised as INTEGER(5) IDENTIFIER(s)
        # OR the user writes "every 5 s:" with a space
        unit = "s"
        cur = self._current()
        if cur.type == TokenType.IDENTIFIER and cur.value in ("s", "m", "h", "ms"):
            unit = cur.value
            self._advance()

        # optional "X times" or "forever"
        max_runs = None
        if (self._current().type == TokenType.INTEGER or
                (self._current().type == TokenType.IDENTIFIER
                 and self._current().value == "times")):
            if self._current().type == TokenType.INTEGER:
                max_runs = self._advance().value
                # consume optional "times"
                if (self._current().type == TokenType.IDENTIFIER
                        and self._current().value == "times"):
                    self._advance()

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return self._stamp(
            EveryStatement(interval_val, unit, body, max_runs, line=line), line
        )

    def _parse_test(self):
        """
        Parse:
            test "label":
                expect expr == val
                expect other == val
        """
        line = self._current().line
        self._consume(TokenType.TEST)
        # label — must be a string literal
        label_tok = self._consume(TokenType.STRING)
        label = label_tok.value
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return self._stamp(TestBlock(label, body, line=line), line)

    def _parse_expect(self):
        """Parse:  expect <expression>"""
        line = self._current().line
        self._consume(TokenType.EXPECT)
        expr = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(ExpectStatement(expr, line=line), line)

    def _parse_imagine(self):
        """
        Parse (as statement):
            imagine "prompt"
            let img = imagine "prompt" as url
            imagine "prompt" as path
        """
        line = self._current().line
        self._consume(TokenType.IMAGINE)
        prompt = self._parse_expression()
        fmt = "url"
        if self._current().type == TokenType.AS:
            self._advance()
            fmt = self._consume(TokenType.IDENTIFIER).value
        self._expect_newline_or_eof()
        return self._stamp(ImagineStatement(prompt, result_format=fmt, line=line), line)

    def _parse_imagine_expr(self):
        """Parse imagine as an expression (right-hand side of let)."""
        line = self._current().line
        self._consume(TokenType.IMAGINE)
        prompt = self._parse_expression()
        fmt = "url"
        if self._current().type == TokenType.AS:
            self._advance()
            fmt = self._consume(TokenType.IDENTIFIER).value
        return self._stamp(ImagineStatement(prompt, result_format=fmt, line=line), line)

    def _parse_shape(self):
        """
        Parse:
            shape User:
                name str
                age  int
                email str = "unknown"
        """
        line = self._current().line
        self._consume(TokenType.SHAPE)
        name = self._consume(TokenType.IDENTIFIER).value
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()

        # Parse field definitions inside an INDENT block
        fields = []
        self._consume(TokenType.INDENT)
        while self._current().type not in (TokenType.DEDENT, TokenType.EOF):
            if self._current().type == TokenType.NEWLINE:
                self._advance()
                continue
            fname = self._consume(TokenType.IDENTIFIER).value
            ftype = self._consume(TokenType.IDENTIFIER).value
            default = None
            if self._current().type == TokenType.ASSIGN:
                self._advance()
                default = self._parse_expression()
            fields.append((fname, ftype, default))
            if self._current().type == TokenType.NEWLINE:
                self._advance()
        if self._current().type == TokenType.DEDENT:
            self._advance()

        return self._stamp(ShapeDefinition(name, fields, line=line), line)

    def _parse_watch(self):
        """
        Parse:
            watch "filename.txt":
                <body>
            watch my_var:
                <body>
        """
        line = self._current().line
        self._consume(TokenType.WATCH)
        target = self._parse_expression()
        is_file = isinstance(target, StringLiteral)
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return self._stamp(WatchStatement(target, body, is_file, line=line), line)


    # ── Phase 17 Parsers ─────────────────────────────────────

    def _parse_yield(self):
        """yield [expression]"""
        line = self._current().line
        self._consume(TokenType.YIELD)
        expr = None
        if self._current().type not in (TokenType.NEWLINE, TokenType.EOF,
                                         TokenType.DEDENT):
            expr = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(YieldStatement(expr, line=line), line)

    def _parse_decorator(self):
        """
        @decorator_name
        @decorator_name(args)
        task name(...):
            body
        """
        line = self._current().line
        self._consume(TokenType.AT)
        # Parse decorator expression (name or call) — accept any token as name
        dec_name = self._advance().value
        dec_expr_node = Identifier(dec_name)
        if self._current().type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            args = []
            while self._current().type != TokenType.RPAREN:
                args.append(self._parse_expression())
                if self._current().type == TokenType.COMMA:
                    self._advance()
            self._consume(TokenType.RPAREN)
            dec_expr_node = CallExpression(dec_expr_node, args)
        self._expect_newline_or_eof()
        self._skip_newlines()

        # Collect stacked decorators
        decorators = [dec_expr_node]
        while self._current().type == TokenType.AT:
            self._consume(TokenType.AT)
            dname = self._advance().value  # allow keyword names
            dnode = Identifier(dname)
            if self._current().type == TokenType.LPAREN:
                self._consume(TokenType.LPAREN)
                dargs = []
                while self._current().type != TokenType.RPAREN:
                    dargs.append(self._parse_expression())
                    if self._current().type == TokenType.COMMA:
                        self._advance()
                self._consume(TokenType.RPAREN)
                dnode = CallExpression(dnode, dargs)
            decorators.append(dnode)
            self._expect_newline_or_eof()
            self._skip_newlines()

        # Must be followed by task
        if self._current().type != TokenType.TASK:
            raise ParseError(
                f"Expected 'task' after decorator, "
                f"got '{self._current().value}'.",
                self._current().line
            )
        target = self._parse_task()

        # Apply decorators right-to-left
        node = target
        for dec in reversed(decorators):
            node = DecoratorStatement(dec, node, line=line)
        return node

    def _parse_error_def(self):
        """
        error NetworkError:
            message str
            code    int = 0
        """
        line = self._current().line
        self._consume(TokenType.ERROR_TYPE)
        name = self._consume(TokenType.IDENTIFIER).value
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()

        fields = []
        self._consume(TokenType.INDENT)
        while self._current().type not in (TokenType.DEDENT, TokenType.EOF):
            if self._current().type == TokenType.NEWLINE:
                self._advance(); continue
            fname = self._consume(TokenType.IDENTIFIER).value
            ftype = self._consume(TokenType.IDENTIFIER).value
            default = None
            if self._current().type == TokenType.ASSIGN:
                self._advance()
                default = self._parse_expression()
            fields.append((fname, ftype, default))
            if self._current().type == TokenType.NEWLINE:
                self._advance()
        if self._current().type == TokenType.DEDENT:
            self._advance()
        return self._stamp(ErrorDefinition(name, fields, line=line), line)

    def _parse_assert(self):
        """Parse:  assert <condition> [, "message"]"""
        line = self._current().line
        self._advance()  # consume "assert"
        condition = self._parse_expression()
        message = None
        if self._current().type == TokenType.COMMA:
            self._advance()
            message = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(AssertStatement(condition, message, line=line), line)

    def _parse_raise(self):
        """Parse:  raise <expression>"""
        line = self._current().line
        self._advance()  # consume "raise"
        expr = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(RaiseStatement(expr, line=line), line)

    def _parse_show(self):
        """Parse:  show <expr> [<expr2> ...]  (space-separated)"""
        line = self._current().line
        self._consume(TokenType.SHOW)
        expr = self._parse_expression()
        extras = []
        # Keep consuming comma-separated OR consecutive expressions
        while self._current().type == TokenType.COMMA:
            self._advance()
            extras.append(self._parse_expression())
        self._expect_newline_or_eof()
        return self._stamp(ShowStatement(expr, extras), line)

    def _parse_think_using_model(self):
        """
        Parse an optional explicit model-selection clause:
            think "..." using "claude-sonnet"
            think "..." as json using "claude-sonnet"

        'using' is a soft keyword (matched by value, like 'budget'
        and 'error' elsewhere in a think clause) so it stays a plain
        identifier everywhere else in the language. Returns the
        model expression Node, or None if not present.
        """
        if (self._current().type == TokenType.IDENTIFIER
                and self._current().value == "using"):
            self._advance()  # consume 'using'
            return self._parse_expression()
        return None

    def _parse_think_with_budget(self):
        """
        Parse an optional token-budget clause on a think statement:
            think "..." with budget: 500
            think "..." as json with budget: 500

        Returns the budget expression Node, or None if not present.
        Does not consume the trailing newline.
        """
        if self._current().type != TokenType.WITH:
            return None
        self._advance()  # consume 'with'
        budget_tok = self._current()
        if budget_tok.value != "budget":
            raise ParseError(
                f"Expected 'budget' after 'with' in a think clause, "
                f"got '{budget_tok.value}'.\n"
                f"  Example:  think \"...\" with budget: 500"
            )
        self._advance()  # consume 'budget'
        self._consume(TokenType.COLON)
        return self._parse_expression()

    def _parse_think_on_error(self):
        """
        Parse an optional inline error-handling clause on a think
        statement:
            think "..." when error: <fallback-expr>
            think "..." as json when error: <fallback-expr>

        'error' is a soft keyword here (just an identifier) so it
        doesn't need to be reserved. Returns the fallback expression
        Node, or None if the clause isn't present. Does not consume
        the trailing newline — callers handle that themselves.
        """
        if self._current().type != TokenType.WHEN:
            return None
        self._advance()  # consume 'when'
        err_tok = self._current()
        if err_tok.value != "error":
            raise ParseError(
                f"Expected 'error' after 'when' in a think clause, "
                f"got '{err_tok.value}'.\n"
                f"  Example:  think \"...\" when error: \"fallback\""
            )
        self._advance()  # consume 'error' (lexes as ERROR_TYPE keyword)
        self._consume(TokenType.COLON)
        return self._parse_expression()

    def _parse_think(self):
        """
        Parse:
            think <prompt>
            think <prompt> as json
            think <prompt> as list
            think <prompt> as bool
            think <prompt> as text
            think <prompt> as schema {"key": "type", ...}
            think <prompt> [as <format>] using "<model>"
            think <prompt> [as <format>] with budget: <n>
            think <prompt> [as <format>] when error: <fallback>
        """
        line = self._current().line
        self._consume(TokenType.THINK)
        prompt = self._parse_expression()

        # Check for optional  as <format>
        if self._current().type == TokenType.AS:
            self._advance()   # consume 'as'
            fmt_tok = self._current()

            # as json / as list / as bool / as text
            if fmt_tok.type == TokenType.IDENTIFIER:
                fmt = fmt_tok.value.lower()
                self._advance()

                if fmt in ("json", "list", "bool", "text", "number"):
                    model = self._parse_think_using_model()
                    budget = self._parse_think_with_budget()
                    on_error = self._parse_think_on_error()
                    self._expect_newline_or_eof()
                    return ThinkAsStatement(prompt, fmt, line=line, model=model,
                                            budget=budget, on_error=on_error)

                # as schema {...}
                if fmt == "schema":
                    schema = self._parse_expression()
                    model = self._parse_think_using_model()
                    budget = self._parse_think_with_budget()
                    on_error = self._parse_think_on_error()
                    self._expect_newline_or_eof()
                    return ThinkAsStatement(prompt, "schema",
                                           schema=schema, line=line, model=model,
                                           budget=budget, on_error=on_error)

                # Unknown format — fall back
                model = self._parse_think_using_model()
                budget = self._parse_think_with_budget()
                on_error = self._parse_think_on_error()
                self._expect_newline_or_eof()
                return ThinkAsStatement(prompt, fmt, line=line, model=model,
                                        budget=budget, on_error=on_error)

            # as {...}  — treat as inline schema shorthand
            elif fmt_tok.type == TokenType.LBRACE:
                schema = self._parse_expression()
                model = self._parse_think_using_model()
                budget = self._parse_think_with_budget()
                on_error = self._parse_think_on_error()
                self._expect_newline_or_eof()
                return ThinkAsStatement(prompt, "schema",
                                        schema=schema, line=line, model=model,
                                        budget=budget, on_error=on_error)

        model = self._parse_think_using_model()
        budget = self._parse_think_with_budget()
        on_error = self._parse_think_on_error()
        self._expect_newline_or_eof()
        return ThinkStatement(prompt, line=line, model=model,
                              budget=budget, on_error=on_error)

    def _parse_remember(self):
        """
        Parse:
            remember "key" = <value>
        """
        line = self._current().line
        self._advance()   # consume 'remember'

        key_expr = self._parse_expression()

        # Expect '='
        self._consume(TokenType.ASSIGN)

        value_expr = self._parse_expression()
        self._expect_newline_or_eof()
        return RememberStatement(key_expr, value_expr, line=line)

    def _parse_recall(self):
        """
        Parse:
            recall "key"
            recall "key" or <default>
        """
        line = self._current().line
        self._advance()   # consume 'recall'

        key_expr = self._parse_expression()

        # Optional:  or <default>
        default = None
        if (self._current().type == TokenType.IDENTIFIER and
                self._current().value == "or"):
            self._advance()
            default = self._parse_expression()

        self._expect_newline_or_eof()
        return RecallStatement(key_expr, default=default, line=line)

    def _parse_think_expr(self):
        """
        Parse think used as an expression (inside return, let, show, etc.)
            return think "prompt" as json
            let x = think f"..." as list
            let x = think "..." using "claude-sonnet"
            let x = think "..." with budget: 500
            let x = think "..." when error: "fallback"
        Delegates to _parse_think() which handles plain and 'as' variants.
        Does NOT call _expect_newline_or_eof — the caller handles line endings.
        """
        line = self._current().line
        self._advance()   # consume 'think'
        prompt = self._parse_expression()

        if self._current().type == TokenType.AS:
            self._advance()   # consume 'as'
            fmt_tok = self._current()

            if fmt_tok.type == TokenType.IDENTIFIER:
                fmt = fmt_tok.value.lower()
                self._advance()

                if fmt == "schema":
                    schema = self._parse_expression()
                    model = self._parse_think_using_model()
                    budget = self._parse_think_with_budget()
                    on_error = self._parse_think_on_error()
                    return ThinkAsStatement(prompt, "schema",
                                            schema=schema, line=line, model=model,
                                            budget=budget, on_error=on_error)
                model = self._parse_think_using_model()
                budget = self._parse_think_with_budget()
                on_error = self._parse_think_on_error()
                return ThinkAsStatement(prompt, fmt, line=line, model=model,
                                        budget=budget, on_error=on_error)

            elif fmt_tok.type == TokenType.LBRACE:
                schema = self._parse_expression()
                model = self._parse_think_using_model()
                budget = self._parse_think_with_budget()
                on_error = self._parse_think_on_error()
                return ThinkAsStatement(prompt, "schema",
                                        schema=schema, line=line, model=model,
                                        budget=budget, on_error=on_error)

        model = self._parse_think_using_model()
        budget = self._parse_think_with_budget()
        on_error = self._parse_think_on_error()
        return ThinkStatement(prompt, line=line, model=model,
                              budget=budget, on_error=on_error)

    def _parse_recall_expr(self):
        """
        Parse recall used as an expression (RHS of assignment, in show, etc.)
            let x = recall "key"
            show recall "name" or "default"

        Uses _parse_addition (not _parse_expression) for key so that the OR
        token is NOT consumed by the expression parser — allowing us to handle
        the optional  or <default>  clause ourselves.
        """
        line = self._current().line
        self._advance()   # consume 'recall'
        # Use addition-level (not full expression) so OR stays unconsumed
        key_expr = self._parse_addition()
        default = None
        if self._current().type == TokenType.OR:
            self._advance()   # consume 'or'
            default = self._parse_addition()
        return RecallStatement(key_expr, default=default, line=line)

    def _parse_forget(self):
        """
        Parse:
            forget "key"
            forget all
        """
        line = self._current().line
        self._advance()   # consume 'forget'

        cur = self._current()
        if cur.type == TokenType.IDENTIFIER and cur.value == "all":
            self._advance()
            self._expect_newline_or_eof()
            return ForgetStatement(forget_all=True, line=line)

        key_expr = self._parse_expression()
        self._expect_newline_or_eof()
        return ForgetStatement(key_expr=key_expr, line=line)

    def _parse_model(self):
        """Parse:  model "provider-name" """
        line = self._current().line
        self._consume(TokenType.MODEL)
        provider = self._parse_expression()
        self._expect_newline_or_eof()
        return ModelStatement(provider=provider, line=line)

    def _parse_pipeline(self, first_step):
        """
        Parse: step -> step -> step
        'first_step' is already parsed — we continue from ->
        """
        line = self._current().line
        steps = [first_step]

        while self._current().type == TokenType.ARROW:
            self._consume(TokenType.ARROW)
            # Each step is an identifier or expression
            step = self._parse_primary()
            steps.append(step)

        self._expect_newline_or_eof()
        return PipelineStatement(steps=steps, line=line)
    
    def _parse_autonomous(self):
        """
        Parse:
            autonomous parallel:
                <body>
        """
        line = self._current().line
        self._consume(TokenType.AUTONOMOUS)
        self._consume(TokenType.PARALLEL)
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return ParallelStatement(body=body, line=line)
    
    def _parse_memory(self):
        """
        Parse:
            memory <name>:
                <key> = <value>
                <key> = <value>
        """
        line = self._current().line
        self._consume(TokenType.MEMORY)
        name = self._consume(TokenType.IDENTIFIER).value
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return MemoryStatement(name=name, body=body, line=line)
    
    def _parse_sandbox(self):
        """
        Parse:
            sandbox strict:
                <body>
            sandbox relaxed:
                <body>
        """
        line = self._current().line
        self._consume(TokenType.SANDBOX)

        # Parse the mode — strict or relaxed
        mode_token = self._current()
        if mode_token.type == TokenType.STRICT:
            mode = "strict"
            self._consume(TokenType.STRICT)
        elif mode_token.type == TokenType.RELAXED:
            mode = "relaxed"
            self._consume(TokenType.RELAXED)
        else:
            raise ParseError(
                f"Expected 'strict' or 'relaxed' after 'sandbox', "
                f"got '{mode_token.value}'.",
                mode_token.line
            )

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return SandboxStatement(mode=mode, body=body, line=line)
    
    def _parse_pipeline_def(self):
        """
        Parse:
            pipeline <name>:
                collect <expression>
                process with ai
                generate report
                save to database
        """
        line = self._current().line
        self._consume(TokenType.PIPELINE_DEF)
        name = self._consume(TokenType.IDENTIFIER).value
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()

        steps = []
        self._consume(TokenType.INDENT)
        self._skip_newlines()

        while (not self._at_end() and
            self._current().type != TokenType.DEDENT):

            token = self._current()

            # collect "prompt" or collect variable
            if token.type == TokenType.COLLECT:
                self._consume(TokenType.COLLECT)
                expr = self._parse_expression()
                steps.append({"type": "collect", "expr": expr})

            # process with ai
            elif (token.type == TokenType.IDENTIFIER and
                token.value == "process"):
                self._advance()  # consume 'process'
                if self._current().type == TokenType.WITH:
                    self._consume(TokenType.WITH)
                if self._current().type == TokenType.IDENTIFIER:
                    provider = self._advance().value
                else:
                    provider = "ai"
                steps.append({"type": "process",
                            "provider": provider})

            # generate report
            elif token.type == TokenType.GENERATE:
                self._consume(TokenType.GENERATE)
                if self._current().type == TokenType.IDENTIFIER:
                    format_name = self._advance().value
                else:
                    format_name = "report"
                steps.append({"type": "generate",
                            "format": format_name})

            # save to database
            elif token.type == TokenType.SAVE:
                self._consume(TokenType.SAVE)
                if self._current().type == TokenType.IDENTIFIER:
                    self._advance()  # consume 'to'
                if self._current().type == TokenType.IDENTIFIER:
                    target = self._advance().value
                else:
                    target = "database"
                steps.append({"type": "save",
                            "target": target})

            else:
                self._advance()  # skip unknown tokens

            self._skip_newlines()

        if self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)

        return PipelineDefStatement(
            name=name, steps=steps, line=line)
    
    def _parse_run_pipeline(self):
        """
        Parse:
            run pipeline <name>
            result = run pipeline <name>
        """
        line = self._current().line
        self._consume(TokenType.RUN)
        self._consume(TokenType.PIPELINE_DEF)
        name = self._consume(TokenType.IDENTIFIER).value
        self._expect_newline_or_eof()
        return RunPipelineStatement(name=name, line=line)

    def _parse_if(self):
        """
        Parse:
            if <condition>:
                <body>
            else:
                <body>
        """
        line = self._current().line
        self._consume(TokenType.IF)
        condition = self._parse_expression()
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()

        then_body = self._parse_block()
        else_body = []

        self._skip_newlines()

        # Parse any number of elif branches.
        # We track _tail — the last elif node — so each new elif
        # is attached directly to the previous one's else_body.
        # This avoids the broken pattern of assigning _tail but
        # never using it for subsequent attachments.
        _tail = None  # points to the last IfStatement node in the chain

        while (not self._at_end() and
               self._current().type == TokenType.ELIF):
            self._consume(TokenType.ELIF)
            elif_condition = self._parse_expression()
            self._consume(TokenType.COLON)
            self._expect_newline_or_eof()
            self._skip_newlines()
            elif_body = self._parse_block()
            self._skip_newlines()

            elif_node = IfStatement(elif_condition, elif_body, [])

            if _tail is None:
                # First elif — attach to the top-level else_body
                else_body = [elif_node]
            else:
                # Subsequent elif — attach to the previous elif's else_body
                _tail.else_body = [elif_node]

            _tail = elif_node  # advance tail to the new node

        if (not self._at_end() and
                self._current().type == TokenType.ELSE):
            self._consume(TokenType.ELSE)
            self._consume(TokenType.COLON)
            self._expect_newline_or_eof()
            self._skip_newlines()
            final_else = self._parse_block()

            if _tail is None:
                # No elif at all — else attaches directly to the if
                else_body = final_else
            else:
                # Attach final else to the last elif node
                _tail.else_body = final_else

        return self._stamp(IfStatement(condition, then_body, else_body), line)

    def _parse_repeat(self):
        """
        Parse:
            repeat <count>:
                <body>
        """
        line = self._current().line
        self._consume(TokenType.REPEAT)
        count = self._parse_expression()
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return self._stamp(RepeatStatement(count, body), line)

    def _parse_while(self):
        """
        Parse:
            while <condition>:
                <body>
        """
        line = self._current().line
        self._consume(TokenType.WHILE)
        condition = self._parse_expression()
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return self._stamp(WhileStatement(condition, body), line)

    def _parse_try(self):
        """
        Parse:
            try:
                <body>
            catch:
                <handler>

            try:
                <body>
            catch error:
                <handler>
        """
        line = self._current().line
        self._consume(TokenType.TRY)
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        try_body = self._parse_block()

        self._skip_newlines()

        # Optional catch block
        catch_body = []
        error_var = None
        if self._current().type == TokenType.CATCH:
            self._consume(TokenType.CATCH)
            if self._current().type == TokenType.IDENTIFIER:
                error_var = self._advance().value
            self._consume(TokenType.COLON)
            self._expect_newline_or_eof()
            self._skip_newlines()
            catch_body = self._parse_block()
            self._skip_newlines()

        # Optional finally block
        finally_body = []
        if (self._current().type == TokenType.IDENTIFIER
                and self._current().value == "finally"):
            self._advance()  # consume "finally"
            self._consume(TokenType.COLON)
            self._expect_newline_or_eof()
            self._skip_newlines()
            finally_body = self._parse_block()

        return self._stamp(TryStatement(try_body, catch_body, error_var, finally_body), line)

    def _parse_for(self):
        """
        Parse:
            for <variable> in <iterable>:
                <body>

            for <a>, <b> in <iterable>:   ← multi-variable (enumerate/zip)
                <body>
        """
        line = self._current().line
        self._consume(TokenType.FOR)

        # Collect one or more loop variables (comma-separated)
        variables = [self._consume(TokenType.IDENTIFIER).value]
        while self._current().type == TokenType.COMMA:
            self._advance()  # consume comma
            variables.append(self._consume(TokenType.IDENTIFIER).value)

        # Single variable — store as string (backwards compatible)
        variable = variables[0] if len(variables) == 1 else variables

        self._consume(TokenType.IN)

        # Iterable expression
        iterable = self._parse_expression()

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()

        body = self._parse_block()

        return self._stamp(ForStatement(variable, iterable, body), line)

    def _parse_task_param_list(self):
        """
        Parse a parenthesized parameter list shared by task/prompt:
            (a, b=1, c: int, d: int = 2, *args)
        Returns list of (name, type_hint_or_None, default_or_None, is_vararg).
        Assumes the opening '(' has NOT yet been consumed.
        NOTE: named _parse_task_param_list (not _parse_param_list) to
        avoid colliding with ClassParserMixin._parse_param_list, which
        has a different contract (LPAREN already consumed, returns
        (name, hint) pairs only) and is used by object/init/async
        parsing.
        """
        self._consume(TokenType.LPAREN)
        params = []
        while self._current().type != TokenType.RPAREN:
            is_vararg = False
            if self._current().type == TokenType.MULTIPLY:
                self._advance()
                is_vararg = True
            pname = self._consume(TokenType.IDENTIFIER).value
            # Optional type hint:  name: type
            type_hint = None
            if self._current().type == TokenType.COLON:
                self._advance()
                type_hint = self._consume(TokenType.IDENTIFIER).value
            # Optional default:  name = expr  or  name: type = expr
            default = None
            if self._current().type == TokenType.ASSIGN:
                self._advance()
                default = self._parse_expression()
            params.append((pname, type_hint, default, is_vararg))
            if self._current().type == TokenType.COMMA:
                self._advance()
        self._consume(TokenType.RPAREN)
        return params

    def _parse_task(self):
        """
        Parse:
            task <name>(<params>):
            task <name>(a: int, b: int) -> int:
        params: (name, type_hint_or_None, default_or_None, is_vararg)
        """
        line = self._current().line
        self._consume(TokenType.TASK)
        name = self._advance().value  # allow keyword names

        params = self._parse_task_param_list()

        # Optional return type hint:  -> type
        return_type = None
        if self._current().type == TokenType.ARROW:
            self._advance()
            return_type = self._consume(TokenType.IDENTIFIER).value

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        docstring, body = self._parse_block_with_docstring()

        if return_type or any(p[1] for p in params):
            return self._stamp(TypedTaskStatement(name, params, body, return_type,
                                                   line=line, docstring=docstring), line)
        # Back-compat: strip type hints to old (name, default, is_vararg) tuple
        simple = [(p[0], p[2], p[3]) for p in params]
        return self._stamp(TaskStatement(name, simple, body, docstring=docstring), line)

    def _looks_like_prompt_def(self) -> bool:
        """
        Disambiguates `prompt name(...):` (a prompt block definition)
        from `prompt` used as an ordinary variable, e.g. `prompt = "x"`
        or `show prompt`. 'prompt' is a soft keyword — not reserved —
        specifically so existing code that uses it as a variable name
        keeps working. Only treat it as a definition when it's
        immediately followed by `IDENTIFIER (`.
        """
        nxt = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
        nxt2 = self.tokens[self.pos + 2] if self.pos + 2 < len(self.tokens) else None
        return (nxt is not None and nxt.type == TokenType.IDENTIFIER
                and nxt2 is not None and nxt2.type == TokenType.LPAREN)

    def _parse_prompt(self):
        """
        Parse:
            prompt summarize(text, style="professional"):
                \"\"\"Summarize the following in a {style} tone: {text}\"\"\"

        The body is parsed with a dedicated loop (not the shared
        _parse_block) because a bare string literal isn't normally
        allowed as a standalone statement anywhere else in NEKOVA —
        it's special-cased here so a prompt's docstring template
        doesn't need an `f` prefix to interpolate {var} placeholders.
        """
        line = self._current().line
        self._advance()  # consume the 'prompt' identifier token
        name = self._advance().value  # allow keyword names

        params = self._parse_task_param_list()

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        body = self._parse_prompt_body()

        return self._stamp(PromptStatement(name, params, body, line=line), line)

    def _parse_prompt_body(self) -> list:
        """
        Like _parse_block, but a bare STRING/F_STRING statement is
        allowed and is parsed as an interpolation template (reusing
        _parse_fstring so {var} placeholders resolve against the
        prompt's own parameters, even without an `f` prefix).

        Single-line body (fix, matching _parse_block): e.g.
        `prompt greet(name): "Hello, {name}!"`.
        """
        statements = []

        if self._current().type not in (TokenType.NEWLINE, TokenType.INDENT):
            if self._current().type == TokenType.STRING:
                tok = self._advance()
                return [self._parse_fstring(tok.value)]
            stmt = self._parse_statement()
            return [stmt] if stmt is not None else []

        self._skip_newlines()

        if self._current().type != TokenType.INDENT:
            raise ParseError(
                "Expected an indented block here. "
                "Did you forget to indent?",
                self._current().line
            )

        self._consume(TokenType.INDENT)
        self._skip_newlines()

        while (not self._at_end() and
               self._current().type != TokenType.DEDENT):
            if self._current().type == TokenType.STRING:
                tok = self._advance()
                self._expect_newline_or_eof()
                statements.append(self._parse_fstring(tok.value))
            else:
                stmt = self._parse_statement()
                if stmt is not None:
                    statements.append(stmt)
            self._skip_newlines()

        if self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)

        return statements

    def _parse_retry(self):
        """
        Parse:
            retry 3 times with exponential backoff:
                let result = think "analyse this" as json
            fallback:
                let result = {error: "unavailable"}

            retry 5 times:              # no backoff -> immediate retry
                connect_to_service()
        """
        line = self._current().line
        self._consume(TokenType.RETRY)

        times = self._parse_expression()

        # optional "times"
        if (self._current().type == TokenType.IDENTIFIER
                and self._current().value == "times"):
            self._advance()

        # optional "with <exponential|linear> backoff"
        backoff = None
        if self._current().type == TokenType.WITH:
            self._advance()
            if self._current().type == TokenType.IDENTIFIER:
                strategy = self._advance().value.lower()
                if (self._current().type == TokenType.IDENTIFIER
                        and self._current().value == "backoff"):
                    self._advance()
                backoff = strategy

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()

        self._skip_newlines()

        fallback_body = None
        if (not self._at_end()
                and self._current().type == TokenType.FALLBACK):
            self._consume(TokenType.FALLBACK)
            self._consume(TokenType.COLON)
            self._expect_newline_or_eof()
            self._skip_newlines()
            fallback_body = self._parse_block()

        return self._stamp(
            RetryStatement(times, backoff, body, fallback_body, line=line), line
        )

    def _parse_observe(self):
        """
        Parse:
            observe "pipeline run" with tags {user: user_id}:
                let summary = think summarize(document)

            observe "quick check":
                validate(input)
        """
        line = self._current().line
        self._consume(TokenType.OBSERVE)

        label = self._parse_expression()

        tags = None
        if self._current().type == TokenType.WITH:
            self._advance()
            if (self._current().type == TokenType.IDENTIFIER
                    and self._current().value == "tags"):
                self._advance()
            tags = self._parse_expression()

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()

        return self._stamp(ObserveStatement(label, tags, body, line=line), line)

    def _parse_mock(self):
        """
        Parse:  mock think as "sports"
        Only meaningful inside a `test` block — stubs `think` for
        the rest of that test so it doesn't make a real AI call.
        """
        line = self._current().line
        self._consume(TokenType.MOCK)
        target = self._advance().value  # e.g. "think" — allow keyword names
        self._consume(TokenType.AS)
        value = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(MockStatement(target, value, line=line), line)

    def _parse_return(self):
        """Parse:  return <expression>"""
        line = self._current().line
        self._consume(TokenType.RETURN)
        if self._current().type in (TokenType.NEWLINE, TokenType.EOF):
            return self._stamp(ReturnStatement(None), line)
        value = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(ReturnStatement(value), line)

    def _parse_global(self):
        """
        Parse:  global name
                global name1, name2, name3

        Declares that one or more names refer to the global scope
        inside the current task body.
        """
        line = self._current().line
        self._consume(TokenType.GLOBAL)
        names = []
        names.append(self._consume(TokenType.IDENTIFIER).value)
        while self._current().type == TokenType.COMMA:
            self._advance()
            names.append(self._consume(TokenType.IDENTIFIER).value)
        self._expect_newline_or_eof()
        return self._stamp(GlobalStatement(names), line)

    def _parse_unpack(self):
        """
        Parse:  a, b, c = [1, 2, 3]
                x, y = get_coords()

        Collects all left-hand identifiers separated by commas,
        then parses the right-hand expression after '='.
        """
        line = self._current().line
        names = []
        names.append(self._consume(TokenType.IDENTIFIER).value)
        while self._current().type == TokenType.COMMA:
            self._advance()  # consume comma
            names.append(self._consume(TokenType.IDENTIFIER).value)
        self._consume(TokenType.ASSIGN)
        value = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(UnpackStatement(names, value), line)

    def _parse_use(self):
        """Parse:  use <module>"""
        self._consume(TokenType.USE)
        module = self._consume(TokenType.IDENTIFIER).value
        self._expect_newline_or_eof()
        return UseStatement(module)
    
    def _parse_import(self):
        """
        Parse import statements in three forms:

            import "utils.nk"
            import greet from "utils.nk"
            import greet, add, PI from "utils.nk"
        """
        self._consume(TokenType.IMPORT)

        # Check if next token is a string (old form) or identifier (named form)
        if self._current().type == TokenType.STRING:
            # import "utils.nk"
            filepath = self._consume(TokenType.STRING).value
            self._expect_newline_or_eof()
            return ImportStatement(filepath, names=None)

        # Named import: import name1, name2 from "file.nk"
        names = []
        names.append(self._consume(TokenType.IDENTIFIER).value)

        while (self._current().type == TokenType.COMMA or
               (self._current().type == TokenType.IDENTIFIER and
                self._current().value != "from")):
            if self._current().type == TokenType.COMMA:
                self._advance()  # skip comma
            if (self._current().type == TokenType.IDENTIFIER and
                    self._current().value != "from"):
                names.append(self._consume(TokenType.IDENTIFIER).value)

        # Expect 'from' keyword
        if (self._current().type == TokenType.IDENTIFIER and
                self._current().value == "from"):
            self._advance()  # consume 'from'
        else:
            raise SyntaxError(
                f"Expected 'from' after import names, "
                f"got '{self._current().value}'"
            )

        filepath = self._consume(TokenType.STRING).value
        self._expect_newline_or_eof()
        return ImportStatement(filepath, names=names)

    def _parse_converse(self):
        """
        Parse:
            converse:
                think "..."
                listen
                think "..."
        """
        line = self._current().line
        self._consume(TokenType.CONVERSE)
        self._consume(TokenType.COLON)
        body = self._parse_block()
        return self._stamp(ConverseStatement(body, line=line), line)

    def _parse_enum(self):
        """
        Parse:  enum Status: PENDING, ACTIVE, DONE

        Single-line member list, comma-separated. Each member becomes
        an attribute on the enum evaluating to its own name as a
        string (Status.ACTIVE == "ACTIVE").
        """
        line = self._current().line
        self._consume(TokenType.ENUM)
        name = self._consume(TokenType.IDENTIFIER).value
        self._consume(TokenType.COLON)

        members = [self._consume(TokenType.IDENTIFIER).value]
        while self._current().type == TokenType.COMMA:
            self._advance()
            members.append(self._consume(TokenType.IDENTIFIER).value)

        self._expect_newline_or_eof()
        return self._stamp(EnumDefinition(name, members, line=line), line)

    def _parse_const(self):
        """
        Parse:  const NAME = value
                const NAME: type = value

        Deliberately simpler than 'let' — no destructuring, no captured
        think/pipeline/autonomous forms. A const is meant to be a single
        immutable named value; reassigning it later is a runtime error
        (see Interpreter._exec_AssignStatement).
        """
        line = self._current().line
        self._consume(TokenType.CONST)
        name = self._consume(TokenType.IDENTIFIER).value

        type_hint = None
        if self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
            if self._current().type == TokenType.IDENTIFIER:
                type_hint = self._consume(TokenType.IDENTIFIER).value

        self._consume(TokenType.ASSIGN)
        value = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(
            AssignStatement(name, value, type_hint=type_hint, is_const=True),
            line
        )

    def _parse_let(self):
        """
        Parse:  let name: type = value
                let name = value

        The 'let' keyword makes declarations unambiguous — the name
        always follows immediately, then an optional ': type', then '= value'.
        """
        line  = self._current().line
        self._consume(TokenType.LET)

        # Destructuring:  let [first, ...rest] = my_list
        if self._current().type == TokenType.LBRACKET:
            return self._parse_list_destructure(line)

        # Destructuring (tuple-style):  let (first, second) = my_pair
        # Same semantics as bracket destructuring — 'let (' can only
        # mean this, since a plain declaration never starts with '('.
        if self._current().type == TokenType.LPAREN:
            return self._parse_list_destructure(
                line, open_tok=TokenType.LPAREN, close_tok=TokenType.RPAREN
            )

        # Destructuring:  let {name, age} = my_dict
        if self._current().type == TokenType.LBRACE:
            return self._parse_dict_destructure(line)

        name  = self._consume(TokenType.IDENTIFIER).value

        # Optional type hint:  name: type
        type_hint = None
        if self._current().type == TokenType.COLON:
            self._consume(TokenType.COLON)
            if self._current().type == TokenType.IDENTIFIER:
                type_hint = self._consume(TokenType.IDENTIFIER).value

        # Assignment
        self._consume(TokenType.ASSIGN)

        # Captured think: let thought = think "prompt"
        if self._current().type == TokenType.THINK:
            node = self._parse_think()
            node.variable = name
            return self._stamp(node, line)

        # Captured parallel: let results = autonomous parallel:
        if self._current().type == TokenType.AUTONOMOUS:
            node = self._parse_autonomous()
            node.variable = name
            return self._stamp(node, line)

        # Captured pipeline run: let result = run pipeline name
        if self._current().type == TokenType.RUN:
            node = self._parse_run_pipeline()
            node.variable = name
            return self._stamp(node, line)

        # Awaited expression: let result = await asyncFn()
        if self._current().type == TokenType.AWAIT:
            value = self.parse_await_expr()
            self._expect_newline_or_eof()
            return self._stamp(AssignStatement(name, value, type_hint=type_hint, is_declaration=True), line)

        # Fetch expression: let res = fetch "url" method "GET"
        if self._current().type == TokenType.FETCH:
            value = self.parse_fetch_expr()
            self._expect_newline_or_eof()
            return self._stamp(AssignStatement(name, value, type_hint=type_hint, is_declaration=True), line)

        value = self._parse_expression()

        # Captured pipeline: let report = "prompt" -> agent1 -> agent2
        if self._current().type == TokenType.ARROW:
            node = self._parse_pipeline(value)
            node.variable = name
            return self._stamp(node, line)

        self._expect_newline_or_eof()
        return self._stamp(AssignStatement(name, value, type_hint=type_hint, is_declaration=True), line)

    def _parse_list_destructure(self, line, open_tok=None, close_tok=None):
        """
        Parse:  let [first, second] = my_list
                let [first, ...rest] = my_list
                let (first, second) = my_pair       (tuple-style, same semantics)
                let (first, ...rest) = my_list

        '...rest' — if present — must be the last element and captures
        every remaining item as a list. Without it, the source list may
        have extra trailing items (they're simply ignored), but must
        have at least as many items as there are named targets.

        open_tok/close_tok let this same parser handle both the
        bracket form ([...]) and the parenthesized tuple form ((...)) —
        they're semantically identical, just different punctuation.
        """
        open_tok  = open_tok  or TokenType.LBRACKET
        close_tok = close_tok or TokenType.RBRACKET

        self._consume(open_tok)
        targets = []
        rest = None
        if self._current().type != close_tok:
            while True:
                if self._current().type == TokenType.ELLIPSIS:
                    self._consume(TokenType.ELLIPSIS)
                    rest = self._consume(TokenType.IDENTIFIER).value
                    break  # rest must be the last pattern element
                targets.append(self._consume(TokenType.IDENTIFIER).value)
                if self._current().type == TokenType.COMMA:
                    self._advance()
                    continue
                break
        self._consume(close_tok)
        self._consume(TokenType.ASSIGN)
        value = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(
            ListDestructureStatement(targets, rest, value), line
        )

    def _parse_dict_destructure(self, line):
        """
        Parse:  let {name, age} = my_dict

        Each name inside {} is both the dict key to read and the
        variable name it's bound to.
        """
        self._consume(TokenType.LBRACE)
        keys = []
        if self._current().type != TokenType.RBRACE:
            keys.append(self._consume(TokenType.IDENTIFIER).value)
            while self._current().type == TokenType.COMMA:
                self._advance()
                keys.append(self._consume(TokenType.IDENTIFIER).value)
        self._consume(TokenType.RBRACE)
        self._consume(TokenType.ASSIGN)
        value = self._parse_expression()
        self._expect_newline_or_eof()
        return self._stamp(DictDestructureStatement(keys, value), line)

    def _parse_identifier_statement(self):
        """
        An identifier can start two things:
            name = "value"     → assignment
            greet("Emmanuel")  → function call
        """
        line  = self._current().line
        name  = self._consume(TokenType.IDENTIFIER).value
        token = self._current()

       # Typed assignment: name: type = value
        type_hint = None
        if token.type == TokenType.COLON:
            self._consume(TokenType.COLON)
            # Read the type name (text, number, boolean, list, dict)
            if self._current().type == TokenType.IDENTIFIER:
                type_hint = self._consume(TokenType.IDENTIFIER).value
            token = self._current()

        # Augmented assignment: x += 1, x -= 1, x *= 2, x /= 2
        _AUG = {
            TokenType.PLUS_EQUAL:  "+",
            TokenType.MINUS_EQUAL: "-",
            TokenType.STAR_EQUAL:  "*",
            TokenType.SLASH_EQUAL: "/",
        }
        if token.type in _AUG:
            op = _AUG[token.type]
            self._advance()  # consume +=  -=  *=  /=
            rhs = self._parse_expression()
            self._expect_newline_or_eof()
            # Desugar: x += rhs  →  x = x + rhs
            expanded = BinaryOp(Identifier(name), op, rhs)
            return self._stamp(AssignStatement(name, expanded), line)

        # Assignment
        if token.type == TokenType.ASSIGN:
            self._consume(TokenType.ASSIGN)

            # Captured think: thought = think "prompt"
            if self._current().type == TokenType.THINK:
                node = self._parse_think()
                node.variable = name
                return self._stamp(node, line)

            # Captured parallel: results = autonomous parallel:
            if self._current().type == TokenType.AUTONOMOUS:
                node = self._parse_autonomous()
                node.variable = name
                return self._stamp(node, line)

            # Captured pipeline run: result = run pipeline name
            if self._current().type == TokenType.RUN:
                node = self._parse_run_pipeline()
                node.variable = name
                return self._stamp(node, line)

            value = self._parse_expression()

            # Captured pipeline: report = "prompt" -> agent1 -> agent2
            if self._current().type == TokenType.ARROW:
                node = self._parse_pipeline(value)
                node.variable = name
                return self._stamp(node, line)

            self._expect_newline_or_eof()
            return self._stamp(AssignStatement(name, value, type_hint=type_hint), line)

        # Index assignment: name["key"] = val  or  name[0] = val
        if token.type == TokenType.LBRACKET:
            self._advance()                          # consume '['
            index = self._parse_expression()
            self._consume(TokenType.RBRACKET)
            # Must be followed by '=' to be an assignment statement
            if self._current().type == TokenType.ASSIGN:
                self._advance()                      # consume '='
                value = self._parse_expression()
                self._expect_newline_or_eof()
                return self._stamp(
                    IndexAssignStatement(Identifier(name), index, value),
                    line)
            # Otherwise it's a read — rebuild as expression, supporting chains
            expr = IndexExpression(Identifier(name), index)
            # Handle further chaining: name[a][b] = val  or  name[a].method()
            while self._current().type in (
                    TokenType.DOT, TokenType.LBRACKET):
                if self._current().type == TokenType.DOT:
                    self._advance()
                    prop = self._advance().value
                    if self._current().type == TokenType.LPAREN:
                        self._consume(TokenType.LPAREN)
                        args = []
                        while self._current().type != TokenType.RPAREN:
                            args.append(self._parse_expression())
                            if self._current().type == TokenType.COMMA:
                                self._advance()
                        self._consume(TokenType.RPAREN)
                        expr = MethodCall(expr, prop, args)
                    else:
                        expr = PropertyAccess(expr, prop)
                else:
                    # Another index: name[a][b] — could be assignment LHS
                    self._advance()                  # consume '['
                    idx2 = self._parse_expression()
                    self._consume(TokenType.RBRACKET)
                    # Peek: if followed by '=' this is a chained assignment
                    if self._current().type == TokenType.ASSIGN:
                        self._advance()              # consume '='
                        value = self._parse_expression()
                        self._expect_newline_or_eof()
                        return self._stamp(
                            IndexAssignStatement(expr, idx2, value), line)
                    expr = IndexExpression(expr, idx2)
            self._expect_newline_or_eof()
            return expr

        # Function call
        if token.type == TokenType.LPAREN:
            call = self._finish_call(name)
            # Pipeline starting with a function call result
            if self._current().type == TokenType.ARROW:
                return self._parse_pipeline(call)
            self._expect_newline_or_eof()
            return call

        # Standalone pipeline: researcher -> marketer -> reporter
        if token.type == TokenType.ARROW:
            return self._parse_pipeline(Identifier(name))

        # Dot method call / property chain: obj.method() or obj.prop.method()
        if token.type == TokenType.DOT:
            expr = Identifier(name)
            while self._current().type == TokenType.DOT:
                self._advance()  # consume dot
                prop = self._advance().value  # allow keyword method names
                if self._current().type == TokenType.LPAREN:
                    self._consume(TokenType.LPAREN)
                    call_args = []
                    while self._current().type != TokenType.RPAREN:
                        call_args.append(self._parse_expression())
                        if self._current().type == TokenType.COMMA:
                            self._advance()
                    self._consume(TokenType.RPAREN)
                    expr = MethodCall(expr, prop, call_args)
                else:
                    expr = PropertyAccess(expr, prop)
            self._expect_newline_or_eof()
            return expr

        raise ParseError(
            f"Expected '=' or '(' after '{name}'.",
            token.line
        )

    # ----------------------------------------------------------
    # Block parser
    # ----------------------------------------------------------

    def _parse_block_with_docstring(self):
        """
        Like _parse_block, but if the block opens with a bare string
        literal (STRING or F_STRING) on its own line, that string is
        treated as a docstring rather than causing a parse error.

        Bare string statements aren't valid anywhere else in NEKOVA
        (you'd normally use 'show "..."'), so this is unambiguous —
        a leading bare string can only be documentation.

        Returns (docstring_text_or_None, body_statements).

        Single-line body (fix, matching _parse_block): if the body
        is written directly on the same line as the ':' — e.g.
        `task add(a, b): return a + b` — there's obviously no
        INDENT/DEDENT pair, and no possibility of a docstring either
        (a docstring only makes sense as its own line at the top of
        a real block), so it's just one inline statement.
        """
        docstring = None
        statements = []

        if self._current().type not in (TokenType.NEWLINE, TokenType.INDENT):
            stmt = self._parse_statement()
            return None, ([stmt] if stmt is not None else [])

        self._skip_newlines()          # consume NEWLINE after ':'

        if self._current().type != TokenType.INDENT:
            raise ParseError(
                "Expected an indented block here. "
                "Did you forget to indent?",
                self._current().line
            )

        self._consume(TokenType.INDENT)
        self._skip_newlines()

        if self._current().type in (TokenType.STRING, TokenType.F_STRING):
            docstring = self._current().value
            self._advance()
            self._expect_newline_or_eof()
            self._skip_newlines()

        while (not self._at_end() and
               self._current().type != TokenType.DEDENT):
            stmt = self._parse_statement()
            if stmt is not None:
                statements.append(stmt)
            self._skip_newlines()

        if self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)

        return docstring, statements

    def _parse_block(self) -> list:
        """
        Parse a block of statements following a ':' — either a
        normal indented multi-line block, or (fix) a single
        statement written directly on the same line as the ':',
        e.g. `if true: show "yes"` or `task add(a, b): return a + b`.
        This never actually worked (confirmed against the real
        1.10.0 release, not assumed to be a new regression) — there
        was no branch anywhere that recognized "content follows the
        ':' directly, no NEWLINE/INDENT involved at all" as anything
        other than a malformed block.

        Some callers consume the NEWLINE right after ':' themselves
        (via _expect_newline_or_eof) before calling this; others
        don't. Both are handled the same way here: if the current
        token is neither NEWLINE nor INDENT, there was never a
        newline at all — the whole body is inline — so parse exactly
        one statement instead of expecting an INDENT/DEDENT pair
        that will never come.
        """
        if self._current().type not in (TokenType.NEWLINE, TokenType.INDENT):
            stmt = self._parse_statement()
            return [stmt] if stmt is not None else []

        statements = []

        self._skip_newlines()          # consume NEWLINE after ':'

        if self._current().type != TokenType.INDENT:
            raise ParseError(
                "Expected an indented block here. "
                "Did you forget to indent?",
                self._current().line
            )

        self._consume(TokenType.INDENT)
        self._skip_newlines()

        while (not self._at_end() and
               self._current().type != TokenType.DEDENT):
            stmt = self._parse_statement()
            if stmt is not None:
                statements.append(stmt)
            self._skip_newlines()

        if self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)

        return statements

    # ----------------------------------------------------------
    # Expression parsers
    # ----------------------------------------------------------

    def _parse_expression(self):
        """
        Parse an expression — handles the pipe operator (loosest
        binding) wrapped around ternary (val if cond else other).
        """
        expr = self._parse_ternary()
        while self._current().type == TokenType.PIPE:
            line = self._current().line
            self._advance()  # consume '|>'
            rhs = self._parse_ternary()
            expr = self._build_pipe_call(expr, rhs, line)
        return expr

    def _build_pipe_call(self, piped_value, rhs, line):
        """
        `a |> f(x, y)`  ->  f(a, x, y)   (a becomes the first arg)
        `a |> f`        ->  f(a)         (bare name, no parens)
        Anything else on the right of `|>` is a parse error — pipe
        needs a task/function to call.
        """
        if isinstance(rhs, CallExpression):
            rhs.args.insert(0, piped_value)
            return rhs
        if isinstance(rhs, Identifier):
            return CallExpression(rhs.name, [piped_value])
        raise ParseError(
            "The right side of '|>' must be a task call or task name, "
            f"e.g. `data |> filter()` — got {type(rhs).__name__}.",
            line
        )

    def _parse_ternary(self):
        """Parse ternary (val if cond else other)."""
        expr = self._parse_logical_or()
        # Ternary: <true_val> if <condition> else <false_val>
        if self._current().type == TokenType.IF:
            line = self._current().line
            self._advance()  # consume "if"
            condition = self._parse_logical_or()
            if self._current().type == TokenType.ELSE:
                self._advance()  # consume "else"
                false_expr = self._parse_expression()
                return TernaryExpression(condition, expr, false_expr, line=line)
        return expr

    def _parse_logical_or(self):
        """Parse 'or' operator."""
        left = self._parse_logical_and()
        while self._current().type == TokenType.OR:
            self._advance()
            right = self._parse_logical_and()
            left  = BinaryOp(left, "or", right)
        return left

    def _parse_logical_and(self):
        """Parse 'and' operator."""
        left = self._parse_comparison()
        while self._current().type == TokenType.AND:
            self._advance()
            right = self._parse_comparison()
            left  = BinaryOp(left, "and", right)
        return left

    def _parse_comparison(self):
        """Parse comparison operators: == != < <= > >= in not in is is not"""
        left = self._parse_addition()

        comparison_ops = {
            TokenType.EQUALS:     "==",
            TokenType.NOT_EQUALS: "!=",
            TokenType.LESS:       "<",
            TokenType.LESS_EQ:    "<=",
            TokenType.GREATER:    ">",
            TokenType.GREATER_EQ: ">=",
        }

        while True:
            cur = self._current()
            if cur.type in comparison_ops:
                op = comparison_ops[cur.type]
                self._advance()
                right = self._parse_addition()
                left  = BinaryOp(left, op, right)
            elif cur.type == TokenType.IN:
                self._advance()
                right = self._parse_addition()
                left  = BinaryOp(left, "in", right)
            elif cur.type == TokenType.NOT:
                # not in
                saved = self.pos
                self._advance()
                if self._current().type == TokenType.IN:
                    self._advance()
                    right = self._parse_addition()
                    left  = BinaryOp(left, "not in", right)
                else:
                    self.pos = saved
                    break
            elif cur.type == TokenType.IDENTIFIER and cur.value == "is":
                self._advance()
                if self._current().type == TokenType.NOT:
                    self._advance()
                    right = self._parse_addition()
                    left  = BinaryOp(left, "is not", right)
                else:
                    right = self._parse_addition()
                    left  = BinaryOp(left, "is", right)
            else:
                break

        return left

    def _parse_addition(self):
        """Parse + and - operators."""
        left = self._parse_multiplication()

        while self._current().type in (TokenType.PLUS, TokenType.MINUS):
            op    = self._current().value
            self._advance()
            right = self._parse_multiplication()
            left  = BinaryOp(left, op, right)

        return left

    def _parse_multiplication(self):
        """Parse * / % ** operators."""
        left = self._parse_unary()

        while self._current().type in (
            TokenType.MULTIPLY, TokenType.DIVIDE,
            TokenType.MODULO,   TokenType.POWER,
            TokenType.FLOOR_DIVIDE
        ):
            op    = self._current().value
            self._advance()
            right = self._parse_unary()
            left  = BinaryOp(left, op, right)

        return left

    def _parse_unary(self):
        """Parse unary operators: - not (recursive for not not x, - -x)"""
        if self._current().type == TokenType.MINUS:
            self._advance()
            return UnaryOp("-", self._parse_unary())

        if self._current().type == TokenType.NOT:
            self._advance()
            return UnaryOp("not", self._parse_unary())

        return self._parse_primary()

    def _parse_primary(self):
        """Parse the most basic expressions — literals, identifiers, groups."""
        token = self._current()

        if token.type == TokenType.INTEGER:
            self._advance()
            return IntegerLiteral(token.value)

        if token.type == TokenType.FLOAT:
            self._advance()
            return FloatLiteral(token.value)

        if token.type == TokenType.STRING:
            self._advance()
            expr = StringLiteral(token.value)
            # Allow chained .method() or [index] on string literals
            expr = self._apply_postfix(expr)
            return expr

        if token.type == TokenType.F_STRING:
            self._advance()
            return self._parse_fstring(token.value)

        if token.type == TokenType.BOOLEAN:
            self._advance()
            return BooleanLiteral(token.value)

        if token.type == TokenType.NULL:
            self._advance()
            return NullLiteral()

        if token.type == TokenType.IDENTIFIER:
            self._advance()
            # Check if this is a function call
            if self._current().type == TokenType.LPAREN:
                expr = self._finish_call(token.value)
            else:
                expr = Identifier(token.value)

            # Check for chained operations
            while True:
                # Index access or slice: items[0], items[1:3], items[:2]
                if self._current().type == TokenType.LBRACKET:
                    self._advance()
                    expr = self._finish_index_or_slice(expr)

                # Method call or property access: name.upper() or args.name
                elif (self._current().type == TokenType.DOT):
                    self._advance()  # consume dot
                    prop = self._advance().value  # allow keyword method names
                    if self._current().type == TokenType.LPAREN:
                        # Method call: obj.method(args)
                        self._consume(TokenType.LPAREN)
                        call_args = []
                        while self._current().type != TokenType.RPAREN:
                            call_args.append(self._parse_expression())
                            if self._current().type == TokenType.COMMA:
                                self._advance()
                        self._consume(TokenType.RPAREN)
                        expr = MethodCall(expr, prop, call_args)
                    else:
                        # Property access: obj.prop (no parentheses)
                        expr = PropertyAccess(expr, prop)

                # Optional chaining: obj?.prop or obj?.method(args) —
                # short-circuits to null if obj is null, instead of
                # raising an error.
                elif (self._current().type == TokenType.QUESTION_DOT):
                    self._advance()  # consume ?.
                    prop = self._advance().value
                    if self._current().type == TokenType.LPAREN:
                        self._consume(TokenType.LPAREN)
                        call_args = []
                        while self._current().type != TokenType.RPAREN:
                            call_args.append(self._parse_expression())
                            if self._current().type == TokenType.COMMA:
                                self._advance()
                        self._consume(TokenType.RPAREN)
                        expr = MethodCall(expr, prop, call_args, optional=True)
                    else:
                        expr = PropertyAccess(expr, prop, optional=True)

                else:
                    break

            return expr
        
        if token.type == TokenType.LBRACE:
            # Disambiguate {} / {k: v} (dict) from {a, b, c} (set):
            # a dict entry is always 'identifier-or-string COLON'; a
            # set element never has that shape. Empty {} stays a dict,
            # matching the existing convention. Skips whitespace-only
            # tokens (NEWLINE/INDENT/DEDENT) so multi-line literals are
            # disambiguated correctly too.
            def _first_real_tokens(count):
                skip = (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT)
                found = []
                i = self.pos + 1
                while i < len(self.tokens) and len(found) < count:
                    if self.tokens[i].type not in skip:
                        found.append(self.tokens[i])
                    i += 1
                return found

            lookahead = _first_real_tokens(2)
            first  = lookahead[0] if len(lookahead) > 0 else None
            second = lookahead[1] if len(lookahead) > 1 else None

            # Composite literals — {} dict/set, [] list — previously
            # returned straight from _parse_primary with no postfix
            # handling, so `[3,1,2].sort()` or `{"a":1}.keys()` raised
            # "Unexpected token '.'": only identifiers got .method()
            # treatment, because `let x = [...]; x.sort()` routes
            # through a different call site that does apply postfix.
            # Wrapping every composite literal here generalizes it.
            if first is None or first.type in (TokenType.RBRACE, TokenType.ELLIPSIS):
                return self._apply_postfix(self._parse_dict())  # {} or {...spread} — dict
            if (first.type in (TokenType.IDENTIFIER, TokenType.STRING)
                    and second is not None and second.type == TokenType.COLON):
                return self._apply_postfix(self._parse_dict())  # {key: value, ...} — dict
            return self._apply_postfix(self._parse_set())       # {1, 2, 3} / {a, b} — set
        
        if token.type == TokenType.LBRACKET:
            return self._apply_postfix(self._parse_list())

        if token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            if self._current().type == TokenType.COMMA:
                # A comma inside the parens makes this a tuple literal
                # rather than a plain grouped expression.
                elements = [expr]
                while self._current().type == TokenType.COMMA:
                    self._advance()
                    if self._current().type == TokenType.RPAREN:
                        break  # trailing comma, e.g. (1, 2,)
                    elements.append(self._parse_expression())
                self._consume(TokenType.RPAREN)
                return self._apply_postfix(TupleLiteral(elements))
            self._consume(TokenType.RPAREN)
            return self._apply_postfix(expr)

        # recall used as expression: let x = recall "key"
        if token.type == TokenType.RECALL:
            return self._parse_recall_expr()

        # think as expression: let x = think "prompt" as json
        if token.type == TokenType.THINK:
            return self._parse_think_expr()

        # await as a general expression: show await greet(name),
        # return await greet(name), x + await greet(name), etc. —
        # not just the two narrow positions (standalone statement,
        # 'let x = await ...') it was previously restricted to.
        if token.type == TokenType.AWAIT:
            return self.parse_await_expr()

        if token.type == TokenType.NEW:
            return self.parse_new_instance()

        if token.type == TokenType.SELF:
            return self.parse_self_expr()

        if token.type == TokenType.LISTEN:
            self._advance()
            prompt = None
            if self._current().type == TokenType.STRING:
                prompt = StringLiteral(self._advance().value)
            return ListenExpression(prompt, line=token.line)

        if token.type == TokenType.IMAGINE:
            return self._parse_imagine_expr()

        # Last-resort: treat an actual keyword as an identifier when
        # used as an expression. This allows calling tasks whose
        # names happen to be keywords (e.g. repeat("ha", 3) when
        # repeat is a user-defined task).
        #
        # This used to check `token.type not in (NEWLINE, EOF,
        # DEDENT, INDENT)` — a denylist that let through far more
        # than keywords: any stray punctuation or operator token
        # (a bare ')', a misplaced ',', etc.) that reached this point
        # also matched, silently becoming Identifier(token.value)
        # instead of the "Unexpected token" ParseError it should
        # have raised. That meant some genuine syntax errors were
        # never actually detected at all, not just poorly recovered
        # from — a real problem for diagnostics that need to catch
        # every mistake, not just the ones that happen to crash later.
        # Now it's a proper allowlist of real keyword token types.
        if token.type in _KEYWORD_TOKEN_TYPES:
            self._advance()  # consume the keyword token
            name = token.value
            expr = Identifier(name)
            # Check for immediate call: repeat(...)
            while self._current().type == TokenType.LPAREN:
                self._consume(TokenType.LPAREN)
                args = []
                while self._current().type != TokenType.RPAREN:
                    args.append(self._parse_expression())
                    if self._current().type == TokenType.COMMA:
                        self._advance()
                self._consume(TokenType.RPAREN)
                expr = CallExpression(expr, args)
            # Check for dot access or index after
            while self._current().type in (TokenType.DOT, TokenType.LBRACKET):
                if self._current().type == TokenType.DOT:
                    self._advance()
                    prop = self._advance().value
                    if self._current().type == TokenType.LPAREN:
                        self._consume(TokenType.LPAREN)
                        margs = []
                        while self._current().type != TokenType.RPAREN:
                            margs.append(self._parse_expression())
                            if self._current().type == TokenType.COMMA:
                                self._advance()
                        self._consume(TokenType.RPAREN)
                        expr = MethodCall(expr, prop, margs)
                    else:
                        expr = PropertyAccess(expr, prop)
                else:
                    self._advance()
                    expr = self._finish_index_or_slice(expr)
            return expr

        raise ParseError(
            f"Unexpected '{token.value}' — "
            f"expected a value, variable, or expression.",
            token.line
        )
    
    def _apply_postfix(self, expr):
        """Apply any trailing .method(), [index], or [slice] to expr."""
        while self._current().type in (TokenType.DOT, TokenType.LBRACKET):
            if self._current().type == TokenType.DOT:
                self._advance()
                prop = self._advance().value
                if self._current().type == TokenType.LPAREN:
                    self._consume(TokenType.LPAREN)
                    args = []
                    while self._current().type != TokenType.RPAREN:
                        args.append(self._parse_expression())
                        if self._current().type == TokenType.COMMA:
                            self._advance()
                    self._consume(TokenType.RPAREN)
                    expr = MethodCall(expr, prop, args)
                else:
                    expr = PropertyAccess(expr, prop)
            else:
                self._advance()  # consume [
                expr = self._finish_index_or_slice(expr)
        return expr

    def _finish_index_or_slice(self, obj):
        """After consuming '[', parse index OR slice, then ']'."""
        line = self._current().line
        # Check for slice: if we see ':' right away or after optional start
        start = None
        if self._current().type != TokenType.COLON and self._current().type != TokenType.RBRACKET:
            start = self._parse_expression()

        if self._current().type == TokenType.COLON:
            # It's a slice
            self._advance()  # consume ':'
            stop = None
            if self._current().type not in (TokenType.RBRACKET, TokenType.COLON):
                stop = self._parse_expression()
            step = None
            if self._current().type == TokenType.COLON:
                self._advance()
                if self._current().type != TokenType.RBRACKET:
                    step = self._parse_expression()
            self._consume(TokenType.RBRACKET)
            return SliceExpression(obj, start, stop, step, line=line)
        else:
            # Regular index
            self._consume(TokenType.RBRACKET)
            return IndexExpression(obj, start)

    def _parse_list(self):
        """
        Parse: [1, 2, 3]
               [...list_a, ...list_b]        -- spread
               [...list_a, extra, ...list_b] -- mixed
        """
        self._consume(TokenType.LBRACKET)
        elements = []

        while self._current().type != TokenType.RBRACKET:
            if self._at_end():
                raise ParseError(
                    "List was never closed — "
                    "did you forget a ']'?",
                    self._current().line
                )
            if self._current().type == TokenType.ELLIPSIS:
                self._consume(TokenType.ELLIPSIS)
                elements.append(SpreadElement(self._parse_expression()))
            else:
                elements.append(self._parse_expression())
            if self._current().type == TokenType.COMMA:
                self._advance()

        self._consume(TokenType.RBRACKET)
        return ListLiteral(elements)
    
    def _parse_set(self):
        """
        Parse: {1, 2, 3}   -- a set literal
        Disambiguated from a dict at the LBRACE dispatch point in
        _parse_primary (a dict entry always has 'key: value' shape).
        """
        self._consume(TokenType.LBRACE)
        elements = []
        self._skip_newlines()

        while self._current().type != TokenType.RBRACE:
            if self._at_end():
                raise ParseError(
                    "Set was never closed — did you forget a '}'?",
                    self._current().line
                )
            elements.append(self._parse_expression())
            if self._current().type == TokenType.COMMA:
                self._advance()
            self._skip_newlines()

        self._consume(TokenType.RBRACE)
        return SetLiteral(elements)

    def _parse_dict(self):
        """Parse: {name: "Emmanuel", age: 20}
                  {...defaults, ...overrides}   -- spread
        """
        self._consume(TokenType.LBRACE)
        pairs = []

        # Skip any newlines after opening brace
        self._skip_newlines()

        while self._current().type != TokenType.RBRACE:
            if self._at_end():
                raise ParseError(
                    "Dictionary was never closed.",
                    self._current().line
                )

            # Spread:  ...other_dict
            if self._current().type == TokenType.ELLIPSIS:
                self._consume(TokenType.ELLIPSIS)
                pairs.append((SpreadElement(self._parse_expression()), None))
                if self._current().type == TokenType.COMMA:
                    self._advance()
                self._skip_newlines()
                continue

            # Parse key as string
            if self._current().type == TokenType.IDENTIFIER:
                key = StringLiteral(self._advance().value)
            elif self._current().type == TokenType.STRING:
                key = StringLiteral(self._advance().value)
            else:
                raise ParseError(
                    "Dictionary key must be a word.",
                    self._current().line
                )

            # Consume colon
            self._consume(TokenType.COLON)

            # Skip INDENT tokens that might appear
            # after colon due to indentation system
            while self._current().type in (
                TokenType.INDENT, TokenType.DEDENT,
                TokenType.NEWLINE
            ):
                self._advance()

            # Parse value
            value = self._parse_addition()
            pairs.append((key, value))

            # Skip comma and whitespace
            if self._current().type == TokenType.COMMA:
                self._advance()

            self._skip_newlines()

        self._consume(TokenType.RBRACE)
        return DictLiteral(pairs)

    def _finish_call(self, name: str) -> CallExpression:
        """
        Parse the argument list of a function call.
            greet("Sam")
            greet(name="Sam", greeting="Hi")     -- keyword arguments
            greet("Sam", greeting="Hi")          -- mixed (positional first)
        A bare 'identifier = expr' inside the parens is a keyword
        argument, not a positional one — this is unambiguous here since
        a positional argument is never itself an assignment expression.
        """
        self._consume(TokenType.LPAREN)
        args = []
        kwargs = {}
        while self._current().type != TokenType.RPAREN:
            if (self._current().type == TokenType.IDENTIFIER
                    and self._peek_is(TokenType.ASSIGN)):
                kw_name = self._consume(TokenType.IDENTIFIER).value
                self._consume(TokenType.ASSIGN)
                kwargs[kw_name] = self._parse_expression()
            else:
                args.append(self._parse_expression())
            if self._current().type == TokenType.COMMA:
                self._advance()
        self._consume(TokenType.RPAREN)
        return CallExpression(name, args, kwargs)

    # ----------------------------------------------------------
    # Utility methods
    # ----------------------------------------------------------

    def _current(self) -> Token:
        """Return the token at the current position."""
        return self.tokens[self.pos]

    def _peek_type(self, offset: int = 1):
        """Return the TokenType at pos+offset without consuming."""
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx].type
        return TokenType.EOF

    def _parse_fstring(self, raw: str) -> FStringLiteral:
        """
        Parse an f-string into a FStringLiteral node.

        Splits the raw string on {expr} placeholders and
        produces a list of ('str', text) and ('expr', AST node) parts.

        Supports nested f-strings: f"outer {f'inner {x}'}"
        Uses brace-depth counting so inner braces are handled correctly.

        Examples:
            f"Hello {name}!"
            f"Result: {a + b}"
            f"{greeting}, {first} {last}!"
            f"outer {f'inner {x}'}"
        """
        parts  = []
        i      = 0
        length = len(raw)
        buf    = []   # accumulates plain-text characters

        while i < length:
            ch = raw[i]

            if ch != '{':
                buf.append(ch)
                i += 1
                continue

            # Flush buffered plain text
            if buf:
                parts.append(('str', ''.join(buf)))
                buf = []

            # Scan forward to the matching closing brace,
            # counting depth so nested braces work correctly.
            depth = 1
            i    += 1   # skip opening {
            expr_chars = []

            while i < length and depth > 0:
                c = raw[i]
                if c == '{':
                    depth += 1
                    expr_chars.append(c)
                elif c == '}':
                    depth -= 1
                    if depth > 0:
                        expr_chars.append(c)
                else:
                    expr_chars.append(c)
                i += 1

            expr_src = ''.join(expr_chars).strip()

            if not expr_src:
                # Empty braces {} — treat as empty string
                parts.append(('str', ''))
                continue

            try:
                from nekova.lexer.lexer import Lexer
                inner_tokens = Lexer(expr_src).tokenize()
                inner_parser = Parser(inner_tokens)
                expr_node    = inner_parser._parse_expression()
                parts.append(('expr', expr_node))
            except Exception:
                # If parsing the inner expression fails, keep it as literal text
                parts.append(('str', '{' + expr_src + '}'))

        # Flush any remaining plain text
        if buf:
            parts.append(('str', ''.join(buf)))

        return FStringLiteral(parts)

    def _advance(self) -> Token:
        """Consume the current token and move forward."""
        token = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def _at_end(self) -> bool:
        """Returns True when we reach EOF."""
        return self._current().type == TokenType.EOF

    def _consume(self, expected: TokenType) -> Token:
        """
        Consume the current token if it matches the expected type.
        Raises ParseError if it doesn't match.
        """
        token = self._current()
        if token.type != expected:
            raise ParseError(
                f"Expected '{expected.name}' but got "
                f"'{token.type.name}' ('{token.value}').",
                token.line
            )
        return self._advance()

    def _skip_newlines(self):
        """Skip over any newline tokens."""
        while (not self._at_end() and
               self._current().type == TokenType.NEWLINE):
            self._advance()

    def _expect_newline_or_eof(self):
        """After a statement, expect a newline or end of file."""
        if self._current().type == TokenType.NEWLINE:
            self._advance()
        elif self._current().type == TokenType.EOF:
            pass
        # If neither, we just continue — the next parse will catch errors

    # ── Aliases for AsyncParserMixin ──────────────────────────────────────────
    # The async parser uses a consistent public API. These thin wrappers
    # delegate to the private underscore methods already on Parser.

    def expect(self, token_type_name: str) -> "Token":
        """Consume a token of the given type (by name string) or raise."""
        tt = TokenType[token_type_name]
        return self._consume(tt)

    def advance(self) -> "Token":
        """Consume and return the current token."""
        return self._advance()

    def current_token_is(self, token_type_name: str) -> bool:
        """Return True if the current token type matches the given name."""
        return self._current().type == TokenType[token_type_name]

    def parse_block(self) -> list:
        """Delegate to the existing block parser."""
        return self._parse_block()

    @property
    def current_token(self):
        """Direct token access used by AsyncParserMixin."""
        return self._current()

    def parse_expr(self):
        """Alias used by AsyncParserMixin."""
        return self._parse_expression()