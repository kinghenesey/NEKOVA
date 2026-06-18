# =============================================================
# NEKOVA — Class Parser Mixin  (Phase 6)
# =============================================================
# Parses:
#
#   object Person:
#       name: text
#       age: number
#
#       init(name: text, age: number):
#           self.name = name
#           self.age = age
#
#       func greet():
#           return f"Hi, I'm {self.name}"
#
#   let p = new Person("Emmanuel", 25)
#
# Also handles inheritance:
#   object Employee extends Person:
#       ...

from nekova.lexer.token_types import TokenType
from nekova.parser.nodes import (
    ClassDefinition, MethodDefinition,
    NewInstance, SelfAccess, SelfAssign,
)


class ClassParserMixin:
    """Mixed into Parser to add object/class parsing."""

    def parse_class_definition(self):
        """
        object ClassName [extends ParentName]:
            field: type
            ...
            init(params):
                body
            func method(params):
                body
        """
        self._consume(TokenType.OBJECT)
        name = self._consume(TokenType.IDENTIFIER).value

        # Optional inheritance
        parent = None
        if (self._current().type == TokenType.IDENTIFIER
                and self._current().value == "extends"):
            self._advance()
            parent = self._consume(TokenType.IDENTIFIER).value

        self._consume(TokenType.COLON)

        fields      = []
        init_params = []
        init_body   = []
        methods     = []

        # Consume all the class body, which may have multiple
        # INDENT/DEDENT pairs (the lexer reindents on blank lines)
        self._skip_newlines()

        # Keep parsing until we run out of indented class content
        while self._current().type == TokenType.INDENT:
            self._consume(TokenType.INDENT)

            while self._current().type not in (TokenType.DEDENT, TokenType.EOF):
                self._skip_newlines()
                if self._current().type in (TokenType.DEDENT, TokenType.EOF):
                    break

                tok = self._current()

                # ── Field: name: type ─────────────────────
                if (tok.type == TokenType.IDENTIFIER
                        and self._peek_is(TokenType.COLON)):
                    field_name = self._consume(TokenType.IDENTIFIER).value
                    self._consume(TokenType.COLON)
                    if self._current().type == TokenType.IDENTIFIER:
                        type_hint = self._consume(TokenType.IDENTIFIER).value
                    else:
                        type_hint = "any"
                    self._skip_newlines()
                    fields.append((field_name, type_hint))

                # ── init(params): body ────────────────────
                elif tok.type == TokenType.INIT:
                    self._consume(TokenType.INIT)
                    self._consume(TokenType.LPAREN)
                    init_params = self._parse_param_list()
                    self._consume(TokenType.RPAREN)
                    self._consume(TokenType.COLON)
                    init_body = self.parse_block()
                    self._skip_newlines()

                # ── func method(): body ───────────────────
                elif tok.type == TokenType.FUNC:
                    self._consume(TokenType.FUNC)
                    method_name = self._consume(TokenType.IDENTIFIER).value
                    self._consume(TokenType.LPAREN)
                    params = self._parse_param_list()
                    self._consume(TokenType.RPAREN)
                    self._consume(TokenType.COLON)
                    body = self.parse_block()
                    self._skip_newlines()
                    methods.append(MethodDefinition(method_name, params, body))

                # ── async func method(): body ─────────────
                elif tok.type == TokenType.ASYNC:
                    self._consume(TokenType.ASYNC)
                    self._consume(TokenType.FUNC)
                    method_name = self._consume(TokenType.IDENTIFIER).value
                    self._consume(TokenType.LPAREN)
                    params = self._parse_param_list()
                    self._consume(TokenType.RPAREN)
                    self._consume(TokenType.COLON)
                    body = self.parse_block()
                    self._skip_newlines()
                    methods.append(MethodDefinition(method_name, params, body,
                                                    is_async=True))
                else:
                    self._advance()

            # Consume the DEDENT that closed this block
            if self._current().type == TokenType.DEDENT:
                self._consume(TokenType.DEDENT)
            self._skip_newlines()

        return ClassDefinition(name, fields, init_params,
                               init_body, methods, parent)

    def parse_new_instance(self):
        """new ClassName(arg1, arg2)"""
        self._consume(TokenType.NEW)
        class_name = self._consume(TokenType.IDENTIFIER).value
        self._consume(TokenType.LPAREN)
        args = []
        while self._current().type != TokenType.RPAREN:
            args.append(self._parse_expression())
            if self._current().type == TokenType.COMMA:
                self._advance()
        self._consume(TokenType.RPAREN)
        return NewInstance(class_name, args)

    def parse_self_expr(self):
        """
        self.attribute            → SelfAccess
        self.attribute = value    → SelfAssign
        self.method(args)         → MethodCall on SelfAccess
        """
        from nekova.parser.nodes import MethodCall
        self._consume(TokenType.SELF)
        self._consume(TokenType.DOT)
        attr = self._consume(TokenType.IDENTIFIER).value

        # self.method(args)
        if self._current().type == TokenType.LPAREN:
            self._consume(TokenType.LPAREN)
            args = []
            while self._current().type != TokenType.RPAREN:
                args.append(self._parse_expression())
                if self._current().type == TokenType.COMMA:
                    self._advance()
            self._consume(TokenType.RPAREN)
            return MethodCall(SelfAccess("__self__"), attr, args)

        # self.attr = value  (assignment)
        if self._current().type == TokenType.ASSIGN:
            self._consume(TokenType.ASSIGN)
            value = self._parse_expression()
            self._expect_newline_or_eof()
            return SelfAssign(attr, value)

        # self.attr  (read access)
        return SelfAccess(attr)

    def _parse_param_list(self) -> list:
        """Parse (name: type, name: type, ...) — returns [(name, hint)]."""
        params = []
        while self._current().type not in (TokenType.RPAREN, TokenType.EOF):
            if self._current().type == TokenType.IDENTIFIER:
                pname = self._consume(TokenType.IDENTIFIER).value
                phint = "any"
                if self._current().type == TokenType.COLON:
                    self._consume(TokenType.COLON)
                    if self._current().type == TokenType.IDENTIFIER:
                        phint = self._consume(TokenType.IDENTIFIER).value
                params.append((pname, phint))
                if self._current().type == TokenType.COMMA:
                    self._advance()
            else:
                break
        return params

    def _peek_is(self, token_type) -> bool:
        """Check if the next token (pos+1) is of the given type."""
        if self._current().type == TokenType.IDENTIFIER:
            pos = getattr(self, 'pos', 0)
            tokens = getattr(self, 'tokens', [])
            if pos + 1 < len(tokens):
                return tokens[pos + 1].type == token_type
        return False