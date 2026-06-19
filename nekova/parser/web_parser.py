# =============================================================
# NEKOVA Parser — Web DSL Mixin (Phase 7)
# =============================================================
from nekova.lexer.token_types import TokenType
from nekova.parser.nodes import RouteStatement, ServeStatement


class WebParserMixin:
    """
    Mixin that adds route/serve DSL parsing.

    Syntax:
        route GET "/path":
            <body>

        route POST "/api/users":
            <body>

        serve port: 8080
        serve
    """

    def _parse_route(self) -> RouteStatement:
        self._advance()   # consume 'route'

        # HTTP method — identifier like GET, POST, PUT, DELETE
        method_tok = self._current()
        if method_tok.type != TokenType.IDENTIFIER:
            from nekova.parser.parser import ParseError
            raise ParseError(
                "Expected HTTP method after 'route' (GET, POST, PUT, DELETE)",
                method_tok.line
            )
        method = method_tok.value.upper()
        self._advance()

        # Path — string literal
        path_tok = self._current()
        if path_tok.type not in (TokenType.STRING, TokenType.F_STRING):
            from nekova.parser.parser import ParseError
            raise ParseError(
                "Expected path string after HTTP method",
                path_tok.line
            )
        path = path_tok.value
        self._advance()

        self._consume(TokenType.COLON)
        self._skip_newlines()

        body = self._parse_block()

        return RouteStatement(method, path, body)

    def _parse_serve(self) -> ServeStatement:
        self._advance()   # consume 'serve'

        port_expr = None

        # Optional:  serve port: 8080
        if (self._current().type == TokenType.IDENTIFIER and
                self._current().value == "port"):
            self._advance()   # consume 'port'
            self._consume(TokenType.COLON)
            port_expr = self._parse_expression()

        self._expect_newline_or_eof()
        return ServeStatement(port_expr)