from nekova.lexer.token_types import TokenType
from nekova.lexer.token import Token
from nekova.parser.nodes import (
    Program, IntegerLiteral, FloatLiteral, StringLiteral, FStringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral, DictLiteral,
    Identifier, BinaryOp, UnaryOp, AssignStatement,
    ShowStatement, ThinkStatement, PipelineStatement, ModelStatement, ParallelStatement, MemoryStatement,
    SandboxStatement, PipelineDefStatement, RunPipelineStatement, IfStatement, RepeatStatement,
    WhileStatement, TryStatement, ForStatement,
    TaskStatement, ReturnStatement, BreakStatement, ContinueStatement, GlobalStatement, UnpackStatement, UseStatement,
    ImportStatement, CallExpression, IndexExpression,
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

    def _stamp(self, node, line: int):
        """Stamp a source line number onto any AST node and return it."""
        node.line = line
        return node

    # ----------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------

    def parse(self) -> Program:
        """Parse all tokens and return the root Program node."""
        statements = []

        self._skip_newlines()

        while not self._at_end():
            stmt = self._parse_statement()
            if stmt is not None:
                statements.append(stmt)
            self._skip_newlines()

        return Program(statements)

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
                f"Unexpected string — did you mean to use 'show' or '->'?",
                token.line
            )

        if token.type == TokenType.ARROW:
            return self._parse_pipeline(self._parse_primary())

        if token.type == TokenType.IF:
            return self._parse_if()

        if token.type == TokenType.REPEAT:
            return self._parse_repeat()

        if token.type == TokenType.WHILE:
            return self._parse_while()
        
        if token.type == TokenType.TRY:
            return self._parse_try()
        
        if token.type == TokenType.FOR:
            return self._parse_for()

        if token.type == TokenType.TASK:
            return self._parse_task()

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

    def _parse_think(self):
        """
        Parse:
            think <prompt>
            think <prompt> as json
            think <prompt> as list
            think <prompt> as bool
            think <prompt> as text
            think <prompt> as schema {"key": "type", ...}
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
                    self._expect_newline_or_eof()
                    return ThinkAsStatement(prompt, fmt, line=line)

                # as schema {...}
                if fmt == "schema":
                    schema = self._parse_expression()
                    self._expect_newline_or_eof()
                    return ThinkAsStatement(prompt, "schema",
                                           schema=schema, line=line)

                # Unknown format — fall back
                self._expect_newline_or_eof()
                return ThinkAsStatement(prompt, fmt, line=line)

            # as {...}  — treat as inline schema shorthand
            elif fmt_tok.type == TokenType.LBRACE:
                schema = self._parse_expression()
                self._expect_newline_or_eof()
                return ThinkAsStatement(prompt, "schema",
                                        schema=schema, line=line)

        self._expect_newline_or_eof()
        return ThinkStatement(prompt, line=line)

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
                    return ThinkAsStatement(prompt, "schema",
                                            schema=schema, line=line)
                return ThinkAsStatement(prompt, fmt, line=line)

            elif fmt_tok.type == TokenType.LBRACE:
                schema = self._parse_expression()
                return ThinkAsStatement(prompt, "schema",
                                        schema=schema, line=line)

        return ThinkStatement(prompt, line=line)

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

        # Optional return type hint:  -> type
        return_type = None
        if self._current().type == TokenType.ARROW:
            self._advance()
            return_type = self._consume(TokenType.IDENTIFIER).value

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()

        if return_type or any(p[1] for p in params):
            return self._stamp(TypedTaskStatement(name, params, body, return_type, line=line), line)
        # Back-compat: strip type hints to old (name, default, is_vararg) tuple
        simple = [(p[0], p[2], p[3]) for p in params]
        return self._stamp(TaskStatement(name, simple, body), line)

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

    def _parse_let(self):
        """
        Parse:  let name: type = value
                let name = value

        The 'let' keyword makes declarations unambiguous — the name
        always follows immediately, then an optional ': type', then '= value'.
        """
        line  = self._current().line
        self._consume(TokenType.LET)
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
            return self._stamp(AssignStatement(name, value, type_hint=type_hint), line)

        # Fetch expression: let res = fetch "url" method "GET"
        if self._current().type == TokenType.FETCH:
            value = self.parse_fetch_expr()
            self._expect_newline_or_eof()
            return self._stamp(AssignStatement(name, value, type_hint=type_hint), line)

        value = self._parse_expression()

        # Captured pipeline: let report = "prompt" -> agent1 -> agent2
        if self._current().type == TokenType.ARROW:
            node = self._parse_pipeline(value)
            node.variable = name
            return self._stamp(node, line)

        self._expect_newline_or_eof()
        return self._stamp(AssignStatement(name, value, type_hint=type_hint), line)

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

    def _parse_block(self) -> list:
        """
        Parse an indented block of statements.
        Blocks start with INDENT and end with DEDENT.
        """
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
        """Parse an expression — handles ternary (val if cond else other)."""
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
        """Parse unary operators: - not"""
        if self._current().type == TokenType.MINUS:
            self._advance()
            return UnaryOp("-", self._parse_primary())

        if self._current().type == TokenType.NOT:
            self._advance()
            return UnaryOp("not", self._parse_primary())

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
            return StringLiteral(token.value)

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

                else:
                    break

            return expr
        
        if token.type == TokenType.LBRACE:
            return self._parse_dict()
        
        if token.type == TokenType.LBRACKET:
            return self._parse_list()

        if token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN)
            return expr

        # recall used as expression: let x = recall "key"
        if token.type == TokenType.RECALL:
            return self._parse_recall_expr()

        # think as expression: let x = think "prompt" as json
        if token.type == TokenType.THINK:
            return self._parse_think_expr()

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

        raise ParseError(
            f"Unexpected '{token.value}' — "
            f"expected a value, variable, or expression.",
            token.line
        )
    
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
        """Parse: [1, 2, 3]"""
        self._consume(TokenType.LBRACKET)
        elements = []

        while self._current().type != TokenType.RBRACKET:
            if self._at_end():
                raise ParseError(
                    "List was never closed — "
                    "did you forget a ']'?",
                    self._current().line
                )
            elements.append(self._parse_expression())
            if self._current().type == TokenType.COMMA:
                self._advance()

        self._consume(TokenType.RBRACKET)
        return ListLiteral(elements)
    
    def _parse_dict(self):
        """Parse: {name: "Emmanuel", age: 20}"""
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
        """Parse the argument list of a function call."""
        self._consume(TokenType.LPAREN)
        args = []
        while self._current().type != TokenType.RPAREN:
            args.append(self._parse_expression())
            if self._current().type == TokenType.COMMA:
                self._advance()
        self._consume(TokenType.RPAREN)
        return CallExpression(name, args)

    # ----------------------------------------------------------
    # Utility methods
    # ----------------------------------------------------------

    def _current(self) -> Token:
        """Return the token at the current position."""
        return self.tokens[self.pos]

    def _parse_fstring(self, raw: str) -> FStringLiteral:
        """
        Parse an f-string into a FStringLiteral node.

        Splits the raw string on {expr} placeholders and
        produces a list of ('str', text) and ('expr', AST node) parts.

        Examples:
            f"Hello {name}!"
            f"Result: {a + b}"
            f"{greeting}, {first} {last}!"
        """
        import re
        parts = []

        # Split on {expr} — keep the delimiters
        segments = re.split(r'(\{[^}]*\})', raw)

        for segment in segments:
            if not segment:
                continue

            if segment.startswith('{') and segment.endswith('}'):
                # Expression inside braces
                expr_src = segment[1:-1].strip()
                if not expr_src:
                    # Empty braces {} — treat as empty string
                    parts.append(('str', ''))
                    continue
                try:
                    # Parse the inner expression using a fresh parser
                    from nekova.lexer.lexer import Lexer
                    from nekova.lexer.token_types import TokenType as TT
                    inner_tokens = Lexer(expr_src).tokenize()
                    inner_parser = Parser(inner_tokens)
                    expr_node = inner_parser._parse_expression()
                    parts.append(('expr', expr_node))
                except Exception:
                    # If parsing fails, treat as a plain string
                    parts.append(('str', segment))
            else:
                parts.append(('str', segment))

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