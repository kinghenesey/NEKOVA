from nekova.lexer.token_types import TokenType
from nekova.lexer.token import Token
from nekova.parser.nodes import (
    Program, IntegerLiteral, FloatLiteral, StringLiteral, FStringLiteral,
    BooleanLiteral, NullLiteral, ListLiteral, DictLiteral,
    Identifier, BinaryOp, UnaryOp, AssignStatement,
    ShowStatement, ThinkStatement, PipelineStatement, ModelStatement, ParallelStatement, MemoryStatement,
    SandboxStatement, PipelineDefStatement, RunPipelineStatement, IfStatement, RepeatStatement,
    WhileStatement, TryStatement, ForStatement,
    TaskStatement, ReturnStatement, UseStatement,
    ImportStatement, CallExpression, IndexExpression,
    MethodCall
)


class ParseError(Exception):
    """Raised when the parser encounters invalid syntax."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n  Line {line}: {message}")


class Parser:
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

        if token.type == TokenType.USE:
            return self._parse_use()

        if token.type == TokenType.IMPORT:
            return self._parse_import()

        if token.type == TokenType.IDENTIFIER:
            return self._parse_identifier_statement()

        if token.type in (TokenType.NEWLINE, TokenType.EOF):
            return None

        raise ParseError(
            f"Unexpected token '{token.value}' — "
            f"NEKOVA doesn't know what to do with this here.",
            token.line
        )

    def _parse_show(self):
        """Parse:  show <expression>"""
        line = self._current().line
        self._consume(TokenType.SHOW)
        expr = self._parse_expression()
        self._expect_newline_or_eof()
        return ShowStatement(expr)

    def _parse_think(self):
        """Parse:  think <prompt>"""
        line = self._current().line
        self._consume(TokenType.THINK)
        prompt = self._parse_expression()
        self._expect_newline_or_eof()
        return ThinkStatement(prompt, line=line)

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

        if (not self._at_end() and
                self._current().type == TokenType.ELSE):
            self._consume(TokenType.ELSE)
            self._consume(TokenType.COLON)
            self._expect_newline_or_eof()
            self._skip_newlines()
            else_body = self._parse_block()

        return IfStatement(condition, then_body, else_body)

    def _parse_repeat(self):
        """
        Parse:
            repeat <count>:
                <body>
        """
        self._consume(TokenType.REPEAT)
        count = self._parse_expression()
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return RepeatStatement(count, body)
    
    def _parse_while(self):
        """
        Parse:
            while <condition>:
                <body>
        """
        self._consume(TokenType.WHILE)
        condition = self._parse_expression()
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return WhileStatement(condition, body)
    
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
        self._consume(TokenType.TRY)
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        try_body = self._parse_block()

        self._skip_newlines()
        self._consume(TokenType.CATCH)

        # Optional error variable: catch error:
        error_var = None
        if self._current().type == TokenType.IDENTIFIER:
            error_var = self._advance().value

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        catch_body = self._parse_block()

        return TryStatement(try_body, catch_body,
                            error_var)
    
    def _parse_for(self):
        """
        Parse:
            for <variable> in <iterable>:
                <body>
        """
        self._consume(TokenType.FOR)

        # Variable name
        variable = self._consume(
            TokenType.IDENTIFIER).value

        self._consume(TokenType.IN)

        # Iterable expression
        iterable = self._parse_expression()

        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()

        body = self._parse_block()

        return ForStatement(variable, iterable, body)

    def _parse_task(self):
        """
        Parse:
            task <name>(<params>):
                <body>
        """
        self._consume(TokenType.TASK)
        name = self._consume(TokenType.IDENTIFIER).value

        self._consume(TokenType.LPAREN)
        params = []
        while self._current().type != TokenType.RPAREN:
            params.append(self._consume(TokenType.IDENTIFIER).value)
            if self._current().type == TokenType.COMMA:
                self._advance()
        self._consume(TokenType.RPAREN)
        self._consume(TokenType.COLON)
        self._expect_newline_or_eof()
        self._skip_newlines()
        body = self._parse_block()
        return TaskStatement(name, params, body)

    def _parse_return(self):
        """Parse:  return <expression>"""
        self._consume(TokenType.RETURN)
        if self._current().type in (TokenType.NEWLINE, TokenType.EOF):
            return ReturnStatement(None)
        value = self._parse_expression()
        self._expect_newline_or_eof()
        return ReturnStatement(value)

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

    def _parse_identifier_statement(self):
        """
        An identifier can start two things:
            name = "value"     → assignment
            greet("Emmanuel")  → function call
        """
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

        # Assignment
        if token.type == TokenType.ASSIGN:
            self._consume(TokenType.ASSIGN)

            # Captured think: thought = think "prompt"
            if self._current().type == TokenType.THINK:
                node = self._parse_think()
                node.variable = name
                return node
            
            # Captured parallel: results = autonomous parallel:
            if self._current().type == TokenType.AUTONOMOUS:
                node = self._parse_autonomous()
                node.variable = name
                return node
            
            # Captured pipeline run: result = run pipeline name
            if self._current().type == TokenType.RUN:
                node = self._parse_run_pipeline()
                node.variable = name
                return node

            value = self._parse_expression()

            # Captured pipeline: report = "prompt" -> agent1 -> agent2
            if self._current().type == TokenType.ARROW:
                node = self._parse_pipeline(value)
                node.variable = name
                return node

            self._expect_newline_or_eof()
            return AssignStatement(name, value, type_hint=type_hint)

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
        """Parse an expression (handles comparisons)."""
        return self._parse_comparison()

    def _parse_comparison(self):
        """Parse comparison operators: == != < <= > >="""
        left = self._parse_addition()

        comparison_ops = {
            TokenType.EQUALS:     "==",
            TokenType.NOT_EQUALS: "!=",
            TokenType.LESS:       "<",
            TokenType.LESS_EQ:    "<=",
            TokenType.GREATER:    ">",
            TokenType.GREATER_EQ: ">=",
        }

        while self._current().type in comparison_ops:
            op  = comparison_ops[self._current().type]
            self._advance()
            right = self._parse_addition()
            left  = BinaryOp(left, op, right)

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
            TokenType.MODULO,   TokenType.POWER
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
                # Index access: items[0]
                if self._current().type == TokenType.LBRACKET:
                    self._advance()
                    index = self._parse_expression()
                    self._consume(TokenType.RBRACKET)
                    expr = IndexExpression(expr, index)

                # Method call: name.upper()
                elif (self._current().type == TokenType.DOT):
                    self._advance()  # consume dot
                    method = self._consume(
                        TokenType.IDENTIFIER).value
                    self._consume(TokenType.LPAREN)
                    args = []
                    while self._current().type != TokenType.RPAREN:
                        args.append(self._parse_expression())
                        if self._current().type == TokenType.COMMA:
                            self._advance()
                    self._consume(TokenType.RPAREN)
                    expr = MethodCall(expr, method, args)

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

        raise ParseError(
            f"Unexpected '{token.value}' — "
            f"expected a value, variable, or expression.",
            token.line
        )
    
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
