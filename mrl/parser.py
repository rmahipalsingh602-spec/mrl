from __future__ import annotations

from ast_nodes import (
    AICommandNode,
    BinaryOpNode,
    CountedLoopNode,
    FunctionCallNode,
    FunctionDefNode,
    IdentifierNode,
    IfNode,
    ImportNode,
    InstallNode,
    LiteralNode,
    LoopNode,
    PrintNode,
    ProgramNode,
    SourceLocation,
    UIButtonNode,
    UITextNode,
    UIWindowNode,
    UnaryOpNode,
    VariableAssignNode,
)
from errors import ParserError
from lexer import Token, TokenType


class Parser:
    def __init__(
        self,
        tokens: list[Token],
        *,
        source_lines: list[str] | None = None,
        file_path: str | None = None,
    ) -> None:
        self.tokens = tokens
        self.source_lines = source_lines
        self.file_path = file_path
        self.current = 0

    def parse(self) -> ProgramNode:
        statements = []
        self.skip_newlines()

        while not self.check(TokenType.EOF):
            if self.check(TokenType.KHATAM):
                raise self.error("Unexpected 'khatam' without an open block.", self.peek())
            if self.check(TokenType.WARNA):
                raise self.error("Unexpected 'warna' without an open if block.", self.peek())
            statements.append(self.parse_statement())
            self.skip_newlines()

        return ProgramNode(location=SourceLocation(1, 1), statements=statements)

    def parse_statement(self):
        mrl_token = self.consume(TokenType.MRL, "Each statement must begin with 'mrl'.")

        if self.match(TokenType.BOLO):
            node = self.parse_print_node(self.previous())
            self.consume_statement_end("Expected end of line after print statement.")
            return node

        if self.match(TokenType.RAKHO):
            node = self.parse_assignment_node(mrl_token)
            self.consume_statement_end("Expected end of line after assignment.")
            return node

        if self.match(TokenType.AGAR):
            return self.parse_if_node(mrl_token)

        if self.match(TokenType.JAB):
            return self.parse_loop_node(mrl_token)

        if self.match(TokenType.GINO):
            return self.parse_counted_loop_node(mrl_token)

        if self.match(TokenType.FUNCTION):
            return self.parse_function_definition(mrl_token)

        if self.match(TokenType.CALL):
            node = self.parse_call_node(mrl_token)
            self.consume_statement_end("Expected end of line after function call.")
            return node

        if self.match(TokenType.IMPORT):
            node = self.parse_import_node(mrl_token)
            self.consume_statement_end("Expected end of line after import statement.")
            return node

        if self.match(TokenType.INSTALL):
            node = self.parse_install_node(mrl_token)
            self.consume_statement_end("Expected end of line after install statement.")
            return node

        if self.match(TokenType.AI):
            node = self.parse_ai_node(mrl_token)
            self.consume_statement_end("Expected end of line after ai statement.")
            return node

        if self.match(TokenType.UI):
            return self.parse_ui_window(mrl_token)

        raise self.error("Unknown statement after 'mrl'.", self.peek())

    def parse_print_node(self, token: Token) -> PrintNode:
        expression = self.parse_expression()
        return PrintNode(location=self.location_from_token(token), expression=expression)

    def parse_assignment_node(self, token: Token) -> VariableAssignNode:
        name_token = self.consume(TokenType.IDENTIFIER, "Expected a variable name after 'rakho'.")
        self.consume(TokenType.EQUAL, "Expected '=' after variable name.")
        expression = self.parse_expression()
        return VariableAssignNode(
            location=self.location_from_token(token),
            name=name_token.lexeme,
            expression=expression,
        )

    def parse_if_node(self, token: Token) -> IfNode:
        condition = self.parse_expression()

        if self.match(TokenType.BOLO):
            inline_print = self.parse_print_node(self.previous())
            self.consume_statement_end("Expected end of line after inline if statement.")
            return IfNode(
                location=self.location_from_token(token),
                condition=condition,
                body=[inline_print],
                else_body=None,
            )

        self.consume(TokenType.NEWLINE, "Expected 'bolo' or a new line after if condition.")
        body = self.parse_block_until("if", {TokenType.WARNA, TokenType.KHATAM})

        else_body = None
        if self.match(TokenType.WARNA):
            self.consume(TokenType.NEWLINE, "Expected a new line after 'warna'.")
            else_body = self.parse_block_until("else", {TokenType.KHATAM})

        self.consume(TokenType.KHATAM, "Expected 'khatam' to close the if block.")
        if self.check(TokenType.NEWLINE):
            self.advance()

        return IfNode(
            location=self.location_from_token(token),
            condition=condition,
            body=body,
            else_body=else_body,
        )

    def parse_loop_node(self, token: Token) -> LoopNode:
        self.consume(TokenType.TAK, "Expected 'tak' after 'jab'.")
        condition = self.parse_expression()
        self.consume(TokenType.NEWLINE, "Expected a new line after loop condition.")
        body = self.parse_block("loop")
        return LoopNode(location=self.location_from_token(token), condition=condition, body=body)

    def parse_counted_loop_node(self, token: Token) -> CountedLoopNode:
        variable = self.consume(TokenType.IDENTIFIER, "Expected a loop variable after 'gino'.")
        self.consume(TokenType.EQUAL, "Expected '=' after the loop variable.")
        start_expression = self.parse_expression()
        self.consume(TokenType.SE, "Expected 'se' after the loop start value.")
        end_expression = self.parse_expression()

        if self.match(TokenType.KADAM):
            step_expression = self.parse_expression()
        else:
            step_expression = LiteralNode(
                location=self.location_from_token(variable),
                value=1,
            )

        self.consume(TokenType.NEWLINE, "Expected a new line after counted loop header.")
        body = self.parse_block("counted loop")
        return CountedLoopNode(
            location=self.location_from_token(token),
            variable_name=variable.lexeme,
            start_expression=start_expression,
            end_expression=end_expression,
            step_expression=step_expression,
            body=body,
        )

    def parse_function_definition(self, token: Token) -> FunctionDefNode:
        name_token = self.consume(TokenType.IDENTIFIER, "Expected a function name after 'function'.")
        self.consume(TokenType.LPAREN, "Expected '(' after function name.")

        parameters: list[str] = []
        if not self.check(TokenType.RPAREN):
            while True:
                parameter = self.consume(TokenType.IDENTIFIER, "Expected a parameter name.")
                parameters.append(parameter.lexeme)
                if not self.match(TokenType.COMMA):
                    break

        self.consume(TokenType.RPAREN, "Expected ')' after function parameters.")
        self.consume(TokenType.NEWLINE, "Expected a new line after function declaration.")
        body = self.parse_block("function")

        return FunctionDefNode(
            location=self.location_from_token(token),
            name=name_token.lexeme,
            parameters=parameters,
            body=body,
        )

    def parse_call_node(self, token: Token) -> FunctionCallNode:
        name_token = self.consume(TokenType.IDENTIFIER, "Expected a function name after 'call'.")
        self.consume(TokenType.LPAREN, "Expected '(' after function name.")

        arguments = []
        if not self.check(TokenType.RPAREN):
            while True:
                arguments.append(self.parse_expression())
                if not self.match(TokenType.COMMA):
                    break

        self.consume(TokenType.RPAREN, "Expected ')' after function arguments.")
        return FunctionCallNode(
            location=self.location_from_token(token),
            name=name_token.lexeme,
            arguments=arguments,
        )

    def parse_import_node(self, token: Token) -> ImportNode:
        if self.match(TokenType.IDENTIFIER):
            module_name = self.previous().lexeme
        elif self.match(TokenType.STRING):
            module_name = str(self.previous().literal)
        else:
            raise self.error("Expected a module name after 'import'.", self.peek())

        return ImportNode(location=self.location_from_token(token), module_name=module_name)

    def parse_install_node(self, token: Token) -> InstallNode:
        if self.match(TokenType.IDENTIFIER):
            package_name = self.previous().lexeme
        elif self.match(TokenType.STRING):
            package_name = str(self.previous().literal)
        else:
            raise self.error("Expected a package name after 'install'.", self.peek())

        return InstallNode(location=self.location_from_token(token), package_name=package_name)

    def parse_ai_node(self, token: Token) -> AICommandNode:
        prompt = self.consume(TokenType.STRING, "Expected a quoted AI prompt after 'ai'.")
        return AICommandNode(location=self.location_from_token(token), prompt=str(prompt.literal))

    def parse_ui_window(self, token: Token) -> UIWindowNode:
        self.consume_identifier_value("window", "Expected 'window' after 'ui'.")
        title_token = self.consume(TokenType.STRING, "Expected a quoted window title after 'ui window'.")
        self.consume(TokenType.NEWLINE, "Expected a new line after the window title.")

        elements = []
        self.skip_newlines()
        while not self.is_ui_end():
            if self.check(TokenType.EOF):
                raise self.error("Missing 'end' to close the ui window block.", self.peek())
            elements.append(self.parse_ui_element())
            self.consume_statement_end("Expected end of line after ui element.")
            self.skip_newlines()

        self.consume_identifier_value("end", "Expected 'end' to close the ui window block.")
        if self.check(TokenType.NEWLINE):
            self.advance()

        return UIWindowNode(
            location=self.location_from_token(token),
            title=str(title_token.literal),
            elements=elements,
        )

    def parse_ui_element(self):
        token = self.consume(TokenType.IDENTIFIER, "Expected a ui element such as 'button' or 'text'.")
        if token.lexeme == "button":
            label = self.consume(TokenType.STRING, "Expected a quoted button label.")
            return UIButtonNode(location=self.location_from_token(token), label=str(label.literal))
        if token.lexeme == "text":
            value = self.consume(TokenType.STRING, "Expected quoted text content.")
            return UITextNode(location=self.location_from_token(token), value=str(value.literal))
        raise self.error("Unsupported ui element. Use 'button' or 'text'.", token)

    def parse_block(self, block_name: str):
        return self.parse_block_until(block_name, {TokenType.KHATAM}, consume_end=True)

    def parse_block_until(
        self,
        block_name: str,
        terminators: set[TokenType],
        *,
        consume_end: bool = False,
    ):
        statements = []
        self.skip_newlines()

        while not self.check(*terminators):
            if self.check(TokenType.EOF):
                raise self.error(f"Missing block terminator to close the {block_name} block.", self.peek())
            statements.append(self.parse_statement())
            self.skip_newlines()

        if consume_end:
            self.consume(TokenType.KHATAM, f"Expected 'khatam' to close the {block_name} block.")
            if self.check(TokenType.NEWLINE):
                self.advance()
        return statements

    def parse_expression(self):
        return self.parse_or()

    def parse_or(self):
        expression = self.parse_and()

        while self.match(TokenType.YA):
            operator = self.previous()
            right = self.parse_and()
            expression = BinaryOpNode(
                location=self.location_from_token(operator),
                left=expression,
                operator=operator.lexeme,
                right=right,
            )

        return expression

    def parse_and(self):
        expression = self.parse_equality()

        while self.match(TokenType.AUR):
            operator = self.previous()
            right = self.parse_equality()
            expression = BinaryOpNode(
                location=self.location_from_token(operator),
                left=expression,
                operator=operator.lexeme,
                right=right,
            )

        return expression

    def parse_equality(self):
        expression = self.parse_comparison()

        while self.match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            operator = self.previous()
            right = self.parse_comparison()
            expression = BinaryOpNode(
                location=self.location_from_token(operator),
                left=expression,
                operator=operator.lexeme,
                right=right,
            )

        return expression

    def parse_comparison(self):
        expression = self.parse_term()

        while self.match(
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
            TokenType.LESS,
            TokenType.LESS_EQUAL,
        ):
            operator = self.previous()
            right = self.parse_term()
            expression = BinaryOpNode(
                location=self.location_from_token(operator),
                left=expression,
                operator=operator.lexeme,
                right=right,
            )

        return expression

    def parse_term(self):
        expression = self.parse_factor()

        while self.match(TokenType.PLUS, TokenType.MINUS):
            operator = self.previous()
            right = self.parse_factor()
            expression = BinaryOpNode(
                location=self.location_from_token(operator),
                left=expression,
                operator=operator.lexeme,
                right=right,
            )

        return expression

    def parse_factor(self):
        expression = self.parse_unary()

        while self.match(TokenType.STAR, TokenType.SLASH):
            operator = self.previous()
            right = self.parse_unary()
            expression = BinaryOpNode(
                location=self.location_from_token(operator),
                left=expression,
                operator=operator.lexeme,
                right=right,
            )

        return expression

    def parse_unary(self):
        if self.match(TokenType.MINUS, TokenType.NAHI):
            operator = self.previous()
            operand = self.parse_unary()
            return UnaryOpNode(
                location=self.location_from_token(operator),
                operator=operator.lexeme,
                operand=operand,
            )
        return self.parse_primary()

    def parse_primary(self):
        if self.match(TokenType.SACH):
            token = self.previous()
            return LiteralNode(location=self.location_from_token(token), value=True)

        if self.match(TokenType.JHOOTH):
            token = self.previous()
            return LiteralNode(location=self.location_from_token(token), value=False)

        if self.match(TokenType.NUMBER):
            token = self.previous()
            return LiteralNode(location=self.location_from_token(token), value=token.literal)

        if self.match(TokenType.STRING):
            token = self.previous()
            return LiteralNode(location=self.location_from_token(token), value=token.literal)

        if self.match(TokenType.IDENTIFIER):
            token = self.previous()
            return IdentifierNode(location=self.location_from_token(token), name=token.lexeme)

        if self.match(TokenType.LPAREN):
            expression = self.parse_expression()
            self.consume(TokenType.RPAREN, "Expected ')' after expression.")
            return expression

        raise self.error("Expected an expression.", self.peek())

    def consume_statement_end(self, message: str) -> None:
        if self.match(TokenType.NEWLINE):
            return
        if self.check(TokenType.EOF):
            return
        raise self.error(message, self.peek())

    def skip_newlines(self) -> None:
        while self.match(TokenType.NEWLINE):
            pass

    def match(self, *token_types: TokenType) -> bool:
        if self.check(*token_types):
            self.advance()
            return True
        return False

    def consume(self, token_type: TokenType, message: str) -> Token:
        if self.check(token_type):
            return self.advance()
        raise self.error(message, self.peek())

    def consume_identifier_value(self, expected: str, message: str) -> Token:
        token = self.consume(TokenType.IDENTIFIER, message)
        if token.lexeme != expected:
            raise self.error(message, token)
        return token

    def is_ui_end(self) -> bool:
        return self.check(TokenType.IDENTIFIER) and self.peek().lexeme == "end"

    def check(self, *token_types: TokenType) -> bool:
        return self.peek().type in token_types

    def advance(self) -> Token:
        if not self.check(TokenType.EOF):
            self.current += 1
        return self.previous()

    def peek(self) -> Token:
        return self.tokens[self.current]

    def previous(self) -> Token:
        return self.tokens[self.current - 1]

    def location_from_token(self, token: Token) -> SourceLocation:
        return SourceLocation(token.line, token.column)

    def error(self, message: str, token: Token) -> ParserError:
        return ParserError(
            message,
            line=token.line,
            column=token.column,
            source_lines=self.source_lines,
            file_path=self.file_path,
        )
