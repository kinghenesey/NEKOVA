from nekova.lexer.token_types import TokenType
from nekova.parser.async_nodes import (
    AsyncFunctionNode,
    AwaitNode,
    StreamThinkNode,
    FetchNode,
)


class AsyncParserMixin:
    """
    Mixin for the main Parser class.
    Assumes self has:
      - self.current_token  : current Token object  (.type, .value)
      - self.advance()      : move to next token
      - self.expect(type)   : consume a token of the given type or raise
      - self.parse_expr()   : parse a single expression
      - self.parse_block()  : parse an indented block → list[Node]
      - self.current_token_is(type) : bool
    """

    # ── async func ───────────────────────────────────────────────────────────
    def parse_async_function(self):
        """
        async func <name>(<params>):   -- or --
        async task <name>(<params>):
            <body>
        """
        self.expect("ASYNC")
        # Bug 25 fix: accept both 'func' and 'task' after 'async'
        if self.current_token_is("FUNC"):
            self.expect("FUNC")
        elif self.current_token_is("TASK"):
            self.expect("TASK")
        else:
            self.expect("FUNC")  # trigger the normal error
        name = self.advance().value  # allow keyword names (uses mixin's advance)

        self.expect("LPAREN")
        params = self._parse_param_list()
        self.expect("RPAREN")

        return_type = None
        if self.current_token_is("ARROW"):          # -> text
            self.advance()
            return_type = self.expect("IDENTIFIER").value

        self.expect("COLON")
        body = self.parse_block()

        return AsyncFunctionNode(name, params, body, return_type)

    # ── await ─────────────────────────────────────────────────────────────────
    def parse_await_expr(self):
        """
        await <expr>
        Usually sits on the RHS of an assignment; we return AwaitNode so the
        interpreter can schedule it with asyncio.
        """
        self.expect("AWAIT")
        expr = self.parse_expr()
        return AwaitNode(expr)

    # ── stream think ──────────────────────────────────────────────────────────
    def parse_stream_think(self):
        """
        stream think <prompt_expr>:
            each <chunk_var>:
                <body>
        """
        self.expect("STREAM")
        self.expect("THINK")
        prompt = self.parse_expr()
        self.expect("COLON")
        self._skip_newlines()          # allow each on the next line

        # Mandatory `each <var>:` sub-clause (may be on next line inside block)
        # Consume the INDENT that wraps the each clause, if present
        if self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)

        self.expect("EACH")
        chunk_var = self.expect("IDENTIFIER").value
        self.expect("COLON")

        body = self.parse_block()

        # Consume matching DEDENT if we consumed an INDENT above
        if self._current().type == TokenType.DEDENT:
            self._consume(TokenType.DEDENT)
        return StreamThinkNode(prompt, chunk_var, body)

    # ── fetch ─────────────────────────────────────────────────────────────────
    def parse_fetch_expr(self):
        """
        fetch <url_expr>
        fetch <url_expr> method "POST" headers {...} body {...}
        """
        self.expect("FETCH")
        url = self.parse_expr()

        method = "GET"
        headers = {}
        body_expr = None

        # Optional keyword modifiers
        while self.current_token_is("IDENTIFIER"):
            kw = self.current_token.value.lower()
            if kw == "method":
                self.advance()
                method = self.expect("STRING").value.upper()
            elif kw == "headers":
                self.advance()
                headers = self.parse_expr()   # expects a dict literal / expr
            elif kw == "body":
                self.advance()
                body_expr = self.parse_expr()
            else:
                break

        return FetchNode(url, method, headers, body_expr)