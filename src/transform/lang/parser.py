from .tokenizer import Token, TokenType
from .nodes import InstructionNode, IterationNode, ExpressionNode, OutputTargetNode, VariableNode, FunctionNode, LiteralNode

_COMPARISON_TOKEN_TYPES = {
    TokenType.OPERATOR_EQUAL,
    TokenType.OPERATOR_NOT_EQUAL,
    TokenType.OPERATOR_GREATER_THAN,
    TokenType.OPERATOR_GREATER_EQUAL_THAN,
    TokenType.OPERATOR_LESS_THAN,
    TokenType.OPERATOR_LESS_EQUAL_THAN,
}

_METHOD_AND = "and"
_METHOD_OR = "or"
_METHOD_ADD = "add"
_METHOD_SUB = "sub"
_METHOD_MUL = "mul"
_METHOD_DIV = "div"
_METHOD_MOD = "mod"
_METHOD_POW = "pow"
_METHOD_NEG = "neg" # Make it negative (*-1)
_METHOD_NOT = "not" # Invert logically
_METHOD_CON = "con" # concatenate

_COMPARISON_FUNCTION_NAMES = {
    TokenType.OPERATOR_EQUAL: "eq",
    TokenType.OPERATOR_NOT_EQUAL: "neq",
    TokenType.OPERATOR_GREATER_THAN: "gt",
    TokenType.OPERATOR_GREATER_EQUAL_THAN: "gteq",
    TokenType.OPERATOR_LESS_THAN: "lt",
    TokenType.OPERATOR_LESS_EQUAL_THAN: "lteq",
}

_TERM_FUNCTION_NAMES = {
    TokenType.OPERATOR_MULTIPLY: _METHOD_MUL,
    TokenType.OPERATOR_DIVIDE: _METHOD_DIV,
    TokenType.OPERATOR_MODULO: _METHOD_MOD,
}

class ParseError(Exception):
    def __init__(self, message: str, position: tuple[int, int]):
        super().__init__(message)
        self.message = message
        self.position = position
        self.line: int | None = None

class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._cursor = 0

    def _peek(self) -> Token:
        return self._tokens[self._cursor]

    def _advance(self) -> Token:
        token = self._tokens[self._cursor]
        self._cursor += 1
        return token

    def _check(self, type_: TokenType) -> bool:
        return self._peek().type == type_

    def _expect(self, type_: TokenType) -> Token:
        if not self._check(type_):
            raise ParseError(
                f"Expected {type_.name}, got {self._peek().type.name}",
                self._peek().declaration_position,
            )
        return self._advance()


    def parse_instruction(self, last_condition_node: ExpressionNode | None = None) -> InstructionNode:
        start_pos = self._peek().declaration_position[0]
        condition = self._parse_optional_condition(last_condition_node)
        suppress_gt = self._count_top_level_gt() <= 1
        expression = self._parse_expr(suppress_gt)
        if self._check(TokenType.END):
            outputs = []
        else:
            self._expect(TokenType.OPERATOR_GREATER_THAN)
            outputs = self._parse_output_list()
        end_pos = self._peek().declaration_position[1]
        self._expect(TokenType.END)
        return InstructionNode(condition, expression, outputs, definition_position=(start_pos, end_pos))

    def parse_loop_header(self, body: list[InstructionNode | IterationNode]) -> IterationNode:
        start_pos = self._peek().declaration_position[0]
        condition = self._parse_optional_condition()
        suppress_gt = self._count_top_level_gt() <= 1
        list_expression = self._parse_expr(suppress_gt)
        self._expect(TokenType.OPERATOR_GREATER_THAN)
        item_name, index_name = self._parse_loop_outputs()
        end_pos = self._peek().declaration_position[1]
        self._expect(TokenType.END)
        return IterationNode(condition, list_expression, item_name, index_name, body, definition_position=(start_pos, end_pos))

    def _count_top_level_gt(self) -> int:
        depth = 0
        count = 0
        for token in self._tokens[self._cursor:]:
            if token.type == TokenType.END:
                break
            if token.type in (TokenType.LEFT_PAREN, TokenType.LEFT_BRACKET):
                depth += 1
            elif token.type in (TokenType.RIGHT_PAREN, TokenType.RIGHT_BRACKET):
                depth -= 1
            elif token.type == TokenType.OPERATOR_GREATER_THAN and depth == 0:
                count += 1
        return count

    def _is_continuous_condition(self) -> bool:
        if not self._check(TokenType.OPERATOR_LAST_CONDITION):
            return False
        return True

    def _parse_optional_condition(self, last_condition_node: ExpressionNode | None = None) -> ExpressionNode | None:
        if self._is_continuous_condition():
            if last_condition_node is None:
                raise ParseError(
                    "Continuous condition statement found but last condition is missing!",
                    self._peek().declaration_position
                )
            self._advance()
            return last_condition_node
        if not self._check(TokenType.KEYWORD_IF):
            return None
        self._advance()
        self._expect(TokenType.LEFT_PAREN)
        condition = self._parse_expr()
        self._expect(TokenType.RIGHT_PAREN)
        return condition

    def _parse_output_list(self) -> list[OutputTargetNode]:
        outputs = [self._parse_output_item()]
        while self._check(TokenType.COMMA):
            self._advance()
            outputs.append(self._parse_output_item())
        return outputs

    def _parse_output_item(self) -> OutputTargetNode:
        name_token = self._expect(TokenType.IDENTIFIER)
        append_list = False
        if self._check(TokenType.LEFT_BRACKET):
            self._advance()
            self._expect(TokenType.RIGHT_BRACKET)
            append_list = True
        return OutputTargetNode(name_token.value, append_list, definition_position=name_token.declaration_position)

    def _parse_loop_outputs(self) -> tuple[str, str | None]:
        item_token = self._expect(TokenType.IDENTIFIER)
        if not self._check(TokenType.COMMA):
            return item_token.value, None
        self._advance()
        index_token = self._expect(TokenType.IDENTIFIER)
        if self._check(TokenType.COMMA):
            raise ParseError(
                "Loop output accepts at most 2 variables (item, index)",
                self._peek().declaration_position,
            )
        return item_token.value, index_token.value

    def _parse_expr(self, suppress_gt: bool = False) -> ExpressionNode:
        return self._parse_concat(suppress_gt)

    def _parse_concat(self, suppress_gt: bool = False) -> ExpressionNode:
        left = self._parse_logic_or(suppress_gt)
        while self._check(TokenType.OPERATOR_CONCAT):
            op_token = self._advance()
            right = self._parse_logic_or(suppress_gt)
            left = FunctionNode(_METHOD_CON, [left, right], definition_position=op_token.declaration_position)
        return left

    def _parse_logic_or(self, suppress_gt: bool = False) -> ExpressionNode:
        left = self._parse_logic_and(suppress_gt)
        while self._check(TokenType.OPERATOR_LOGIC_OR):
            op_token = self._advance()
            right = self._parse_logic_and(suppress_gt)
            left = FunctionNode(_METHOD_OR, [left, right], definition_position=op_token.declaration_position)
        return left

    def _parse_logic_and(self, suppress_gt: bool = False) -> ExpressionNode:
        left = self._parse_comparison(suppress_gt)
        while self._check(TokenType.OPERATOR_LOGIC_AND):
            op_token = self._advance()
            right = self._parse_comparison(suppress_gt)
            left = FunctionNode(_METHOD_AND, [left, right], definition_position=op_token.declaration_position)
        return left

    def _parse_comparison(self, suppress_gt: bool = False) -> ExpressionNode:
        left = self._parse_arithmetic()
        peek_type = self._peek().type
        if peek_type in _COMPARISON_TOKEN_TYPES and not (suppress_gt and peek_type == TokenType.OPERATOR_GREATER_THAN):
            op_token = self._advance()
            right = self._parse_arithmetic()
            func_name = _COMPARISON_FUNCTION_NAMES[op_token.type]
            return FunctionNode(func_name, [left, right], definition_position=op_token.declaration_position)
        return left

    def _parse_arithmetic(self) -> ExpressionNode:
        left = self._parse_term()
        while self._peek().type in (TokenType.OPERATOR_ADD, TokenType.OPERATOR_SUBTRACT):
            op_token = self._advance()
            right = self._parse_term()
            name = _METHOD_ADD if op_token.type == TokenType.OPERATOR_ADD else _METHOD_SUB
            left = FunctionNode(name, [left, right], definition_position=op_token.declaration_position)
        return left

    def _parse_term(self) -> ExpressionNode:
        left = self._parse_power()
        while self._peek().type in _TERM_FUNCTION_NAMES:
            op_token = self._advance()
            right = self._parse_power()
            left = FunctionNode(_TERM_FUNCTION_NAMES[op_token.type], [left, right], definition_position=op_token.declaration_position)
        return left

    def _parse_power(self) -> ExpressionNode:
        left = self._parse_unary()
        if self._check(TokenType.OPERATOR_POWER):
            op_token = self._advance()
            right = self._parse_power()
            return FunctionNode(_METHOD_POW, [left, right], definition_position=op_token.declaration_position)
        return left

    def _parse_unary(self) -> ExpressionNode:
        if self._check(TokenType.OPERATOR_NEGATIVE):
            op_token = self._advance()
            return FunctionNode(_METHOD_NEG, [self._parse_unary()], definition_position=op_token.declaration_position)
        if self._check(TokenType.OPERATOR_NOT):
            op_token = self._advance()
            return FunctionNode(_METHOD_NOT, [self._parse_unary()], definition_position=op_token.declaration_position)
        return self._parse_primary()

    def _parse_primary(self) -> ExpressionNode:
        token = self._peek()

        if token.type in (TokenType.NUMBER_INT, TokenType.NUMBER_FLOAT, TokenType.STRING, TokenType.BOOL):
            self._advance()
            return LiteralNode(token.value, definition_position=token.declaration_position)

        if token.type == TokenType.LEFT_PAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RIGHT_PAREN)
            return expr

        if token.type == TokenType.IDENTIFIER:
            self._advance()
            if self._check(TokenType.LEFT_PAREN):
                return self._parse_function_call(token)
            return self._parse_variable(token)

        raise ParseError(f"Unexpected token {token.type.name}", token.declaration_position)

    def _parse_function_call(self, name_token: Token) -> FunctionNode:
        self._expect(TokenType.LEFT_PAREN)
        args = []
        if not self._check(TokenType.RIGHT_PAREN):
            args.append(self._parse_expr())
            while self._check(TokenType.COMMA):
                self._advance()
                args.append(self._parse_expr())
        self._expect(TokenType.RIGHT_PAREN)
        return FunctionNode(name_token.value, args, definition_position=name_token.declaration_position)

    def _parse_variable(self, name_token: Token) -> VariableNode:
        indices = []
        while self._check(TokenType.LEFT_BRACKET):
            self._advance()
            indices.append(self._parse_expr())
            self._expect(TokenType.RIGHT_BRACKET)
        return VariableNode(name_token.value, indices, definition_position=name_token.declaration_position)