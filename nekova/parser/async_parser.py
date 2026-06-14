from nekova.parser.async_nodes import (
    AsyncFunctionNode,
    AwaitNode,
    StreamThinkNode,
    FetchNode,
)


class AsyncParserMixin:
    """
    Mixin for the main Parser class.
    Expects self to have: current_token, advance(), expect(type),
    parse_expr(), parse_block(), current_token_is(type)
    """

    def parse_async_function(self):
        """Parse:  async task <name>(<params>): <body>"""
        self.expect("ASYNC")
        self.expect("TASK")
        name = self.expect("IDENTIFIER").value
        self.expect("LPAREN")
        params = self._parse_param_list()
        self.expect("RPAREN")
        return_type = None
        if self.current_token_is("ARROW"):
            self.advance()
            return_type = self.expect("IDENTIFIER").value
        self.expect("COLON")
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self.parse_block()
        return AsyncFunctionNode(name, params, body, return_type)

    def _parse_param_list(self):
        params = []
        while not self.current_token_is("RPAREN"):
            param_name = self.expect("IDENTIFIER").value
            type_hint = None
            if self.current_token_is("COLON"):
                self.advance()
                type_hint = self.expect("IDENTIFIER").value
            params.append((param_name, type_hint))
            if self.current_token_is("COMMA"):
                self.advance()
        return params

    def parse_await_expr(self):
        """Parse:  await <expr>"""
        self.expect("AWAIT")
        expr = self.parse_expr()
        return AwaitNode(expr)

    def parse_stream_think(self):
        """Parse:  stream think <prompt>: each <var>: <body>"""
        self.expect("STREAM")
        self.expect("THINK")
        prompt = self.parse_expr()
        self.expect("COLON")
        self._expect_newline_or_eof()
        self._skip_newlines()
        self.expect("EACH")
        chunk_var = self.expect("IDENTIFIER").value
        self.expect("COLON")
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self.parse_block()
        return StreamThinkNode(prompt, chunk_var, body)

    def parse_fetch_expr(self):
        """Parse:  fetch <url> [method "POST"] [headers {...}] [body {...}]"""
        self.expect("FETCH")
        url = self.parse_expr()
        method = "GET"
        headers = {}
        body_expr = None
        while self.current_token_is("IDENTIFIER"):
            kw = self.current_token.value.lower()
            if kw == "method":
                self.advance()
                method = self.expect("STRING").value.upper()
            elif kw == "headers":
                self.advance()
                headers = self.parse_expr()
            elif kw == "body":
                self.advance()
                body_expr = self.parse_expr()
            else:
                break
        return FetchNode(url, method, headers, body_expr)
