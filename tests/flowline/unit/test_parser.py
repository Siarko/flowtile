import pytest

from transform.lang.tokenizer import tokenize, TokenType
from transform.lang.parser import Parser, ParseError
from transform.lang.nodes import (
    FunctionNode, VariableNode, LiteralNode,
    OutputTargetNode, InstructionNode, ExpressionNode,
)


# ---------- Helpers ----------

def strip_positions(node):
    """Rekurencyjnie zeruje definition_position, żeby porównywać tylko strukturę/wartości."""
    if isinstance(node, FunctionNode):
        return FunctionNode(node.name, [strip_positions(a) for a in node.arguments])
    if isinstance(node, VariableNode):
        return VariableNode(node.name, [strip_positions(i) for i in node.indices])
    if isinstance(node, LiteralNode):
        return LiteralNode(node.value)
    if isinstance(node, OutputTargetNode):
        return OutputTargetNode(node.name, node.append_list)
    if isinstance(node, InstructionNode):
        return InstructionNode(
            strip_positions(node.condition) if node.condition is not None else None,
            strip_positions(node.expression),
            [strip_positions(o) for o in node.outputs],
        )
    if node is None:
        return None
    raise TypeError(f"Unknown node type: {type(node)}")


def assert_nodes_equal(actual, expected):
    assert strip_positions(actual) == strip_positions(expected)


def parse_expr_from_text(text: str) -> ExpressionNode:
    tokens = tokenize(text)
    parser = Parser(tokens)
    expr = parser._parse_expr()
    parser._expect(TokenType.END)
    return expr


def parse_instruction_from_text(text: str) -> InstructionNode:
    tokens = tokenize(text)
    parser = Parser(tokens)
    return parser.parse_instruction()


def var(name, indices=None):
    return VariableNode(name, indices or [])


def lit(value):
    return LiteralNode(value)


def func(name, *args):
    return FunctionNode(name, list(args))


# ---------- Literały i zmienne (primary) ----------

class TestPrimaryLiterals:
    def test_int_literal(self):
        assert_nodes_equal(parse_expr_from_text("5"), lit(5))

    def test_float_literal(self):
        assert_nodes_equal(parse_expr_from_text("1.5"), lit(1.5))

    def test_string_literal(self):
        assert_nodes_equal(parse_expr_from_text('"hello"'), lit("hello"))

    def test_bool_true(self):
        assert_nodes_equal(parse_expr_from_text("true"), lit(True))

    def test_bool_false(self):
        assert_nodes_equal(parse_expr_from_text("false"), lit(False))

    def test_simple_variable(self):
        assert_nodes_equal(parse_expr_from_text("x"), var("x"))


class TestPrimaryVariableIndexing:
    def test_single_index(self):
        assert_nodes_equal(parse_expr_from_text("lista[0]"), var("lista", [lit(0)]))

    def test_multi_level_index(self):
        assert_nodes_equal(
            parse_expr_from_text("lista[0][1]"),
            var("lista", [lit(0), lit(1)]),
        )

    def test_index_with_variable(self):
        assert_nodes_equal(parse_expr_from_text("lista[i]"), var("lista", [var("i")]))

    def test_index_with_expression(self):
        assert_nodes_equal(
            parse_expr_from_text("lista[i + 1]"),
            var("lista", [func("add", var("i"), lit(1))]),
        )


class TestPrimaryFunctionCalls:
    def test_no_args(self):
        assert_nodes_equal(parse_expr_from_text("foo()"), func("foo"))

    def test_single_arg(self):
        assert_nodes_equal(parse_expr_from_text("trim(x)"), func("trim", var("x")))

    def test_multiple_args(self):
        assert_nodes_equal(
            parse_expr_from_text("add(a, b)"),
            func("add", var("a"), var("b")),
        )

    def test_nested_function_calls(self):
        assert_nodes_equal(
            parse_expr_from_text("format_str(trim(x), y)"),
            func("format_str", func("trim", var("x")), var("y")),
        )

    def test_function_call_with_literal_args(self):
        assert_nodes_equal(
            parse_expr_from_text('slider_linear(x, 0, 200, step)'),
            func("slider_linear", var("x"), lit(0), lit(200), var("step")),
        )


class TestParenthesizedExpressions:
    def test_simple_parens(self):
        assert_nodes_equal(parse_expr_from_text("(a)"), var("a"))

    def test_parens_override_precedence(self):
        assert_nodes_equal(
            parse_expr_from_text("(a + b) * c"),
            func("mul", func("add", var("a"), var("b")), var("c")),
        )

    def test_nested_parens(self):
        assert_nodes_equal(parse_expr_from_text("((a))"), var("a"))


# ---------- Unary: negacja i not ----------

class TestUnaryOperators:
    def test_unary_negative_on_literal(self):
        assert_nodes_equal(parse_expr_from_text("-5"), func("neg", lit(5)))

    def test_unary_negative_on_variable(self):
        assert_nodes_equal(parse_expr_from_text("-x"), func("neg", var("x")))

    def test_double_negative(self):
        assert_nodes_equal(parse_expr_from_text("--x"), func("neg", func("neg", var("x"))))

    def test_logical_not(self):
        assert_nodes_equal(parse_expr_from_text("~a"), func("not", var("a")))

    def test_not_of_negative(self):
        assert_nodes_equal(parse_expr_from_text("~-2"), func("not", func("neg", lit(2))))

    def test_negative_after_binary_minus_is_binary_then_unary(self):
        # a - -b  ->  sub(a, neg(b))
        assert_nodes_equal(
            parse_expr_from_text("a - -b"),
            func("sub", var("a"), func("neg", var("b"))),
        )


# ---------- Priorytety arytmetyczne ----------

class TestArithmeticPrecedence:
    def test_multiplication_binds_tighter_than_addition(self):
        # a + b * c -> add(a, mul(b,c))
        assert_nodes_equal(
            parse_expr_from_text("a + b * c"),
            func("add", var("a"), func("mul", var("b"), var("c"))),
        )

    def test_left_associativity_of_subtraction(self):
        # a - b - c -> sub(sub(a,b), c)
        assert_nodes_equal(
            parse_expr_from_text("a - b - c"),
            func("sub", func("sub", var("a"), var("b")), var("c")),
        )

    def test_left_associativity_of_division(self):
        assert_nodes_equal(
            parse_expr_from_text("a / b / c"),
            func("div", func("div", var("a"), var("b")), var("c")),
        )

    def test_power_binds_tighter_than_multiplication(self):
        # a * b ^ c -> mul(a, pow(b,c))
        assert_nodes_equal(
            parse_expr_from_text("a * b ^ c"),
            func("mul", var("a"), func("pow", var("b"), var("c"))),
        )

    def test_power_right_associativity(self):
        # a ^ b ^ c -> pow(a, pow(b,c))
        assert_nodes_equal(
            parse_expr_from_text("a ^ b ^ c"),
            func("pow", var("a"), func("pow", var("b"), var("c"))),
        )

    def test_full_expression_from_spec_example(self):
        # a + b - v * 2
        assert_nodes_equal(
            parse_expr_from_text("a + b - v * 2"),
            func("sub", func("add", var("a"), var("b")), func("mul", var("v"), lit(2))),
        )

    def test_unary_binds_tighter_than_power(self):
        # -a ^ b -> pow(neg(a), b)   (unary jest wewnątrz power w gramatyce)
        assert_nodes_equal(
            parse_expr_from_text("-a ^ b"),
            func("pow", func("neg", var("a")), var("b")),
        )


# ---------- Porównania ----------

class TestComparisons:
    def test_equals(self):
        assert_nodes_equal(parse_expr_from_text("a == b"), func("eq", var("a"), var("b")))

    def test_not_equal(self):
        assert_nodes_equal(parse_expr_from_text("a ~= b"), func("neq", var("a"), var("b")))

    def test_greater(self):
        assert_nodes_equal(parse_expr_from_text("a > b"), func("gt", var("a"), var("b")))

    def test_less_than(self):
        assert_nodes_equal(parse_expr_from_text("a < b"), func("lt", var("a"), var("b")))

    def test_greater_or_equal(self):
        assert_nodes_equal(parse_expr_from_text("a >= b"), func("gteq", var("a"), var("b")))

    def test_less_or_equal(self):
        assert_nodes_equal(parse_expr_from_text("a <= b"), func("lteq", var("a"), var("b")))

    def test_comparison_of_arithmetic_expressions(self):
        # a + 1 > b * 2  ->  greater(add(a,1), mul(b,2))
        assert_nodes_equal(
            parse_expr_from_text("a + 1 > b * 2"),
            func("gt", func("add", var("a"), lit(1)), func("mul", var("b"), lit(2))),
        )


# ---------- Operatory logiczne i priorytety ----------

class TestLogicalOperators:
    def test_and(self):
        assert_nodes_equal(parse_expr_from_text("a && b"), func("and", var("a"), var("b")))

    def test_or(self):
        assert_nodes_equal(parse_expr_from_text("a || b"), func("or", var("a"), var("b")))

    def test_and_binds_tighter_than_or(self):
        # a || b && c -> or(a, and(b,c))
        assert_nodes_equal(
            parse_expr_from_text("a || b && c"),
            func("or", var("a"), func("and", var("b"), var("c"))),
        )

    def test_explicit_parens_override_logical_precedence(self):
        # (a || b) && c -> and(or(a,b), c)
        assert_nodes_equal(
            parse_expr_from_text("(a || b) && c"),
            func("and", func("or", var("a"), var("b")), var("c")),
        )

    def test_comparison_binds_tighter_than_and(self):
        # a > b && c > d -> and(greater(a,b), greater(c,d))
        assert_nodes_equal(
            parse_expr_from_text("a > b && c > d"),
            func("and", func("gt", var("a"), var("b")), func("gt", var("c"), var("d"))),
        )

    def test_left_associativity_of_and(self):
        # a && b && c -> and(and(a,b), c)
        assert_nodes_equal(
            parse_expr_from_text("a && b && c"),
            func("and", func("and", var("a"), var("b")), var("c")),
        )

    def test_left_associativity_of_or(self):
        assert_nodes_equal(
            parse_expr_from_text("a || b || c"),
            func("or", func("or", var("a"), var("b")), var("c")),
        )

    def test_mixed_full_precedence_chain(self):
        # a + 1 > b && c || d  ->  or(and(greater(add(a,1),b), c), d)
        assert_nodes_equal(
            parse_expr_from_text("a + 1 > b && c || d"),
            func("or",
                 func("and", func("gt", func("add", var("a"), lit(1)), var("b")), var("c")),
                 var("d")),
        )


# ---------- Pełne instrukcje (warstwa A) ----------

class TestFullInstructions:
    def test_simple_instruction_no_condition(self):
        node = parse_instruction_from_text("add(a, b) > c")
        assert node.condition is None
        assert_nodes_equal(node.expression, func("add", var("a"), var("b")))
        assert [o.name for o in node.outputs] == ["c"]
        assert [o.append_list for o in node.outputs] == [False]

    def test_instruction_with_condition(self):
        node = parse_instruction_from_text("if(a) x > y")
        assert_nodes_equal(node.condition, var("a"))
        assert_nodes_equal(node.expression, var("x"))
        assert [o.name for o in node.outputs] == ["y"]

    def test_instruction_with_complex_condition(self):
        node = parse_instruction_from_text("if(a > b && c) x > y")
        assert_nodes_equal(
            node.condition,
            func("and", func("gt", var("a"), var("b")), var("c")),
        )

    def test_multiple_outputs(self):
        node = parse_instruction_from_text("slider_linear(x, 0, 200, step) > x, step")
        assert [o.name for o in node.outputs] == ["x", "step"]
        assert [o.append_list for o in node.outputs] == [False, False]

    def test_list_append_output(self):
        node = parse_instruction_from_text("trim(item) > items[]")
        assert node.outputs[0].name == "items"
        assert node.outputs[0].append_list is True

    def test_mixed_scalar_and_list_outputs(self):
        node = parse_instruction_from_text("foo(x) > a, items[], b")
        assert [(o.name, o.append_list) for o in node.outputs] == [
            ("a", False), ("items", True), ("b", False),
        ]

    def test_assign_sep_not_consumed_by_comparison(self):
        # regression test: brak łańcuchów porównań oznacza brak kolizji z ASSIGN_SEP
        node = parse_instruction_from_text("a > b > c")
        assert_nodes_equal(node.expression, func("gt", var("a"), var("b")))
        assert [o.name for o in node.outputs] == ["c"]

    def test_arithmetic_expression_from_spec_example(self):
        node = parse_instruction_from_text("a + b - v * 2 > a")
        assert_nodes_equal(
            node.expression,
            func("sub", func("add", var("a"), var("b")), func("mul", var("v"), lit(2))),
        )
        assert [o.name for o in node.outputs] == ["a"]

    def test_instruction_without_output_is_valid(self):
        node = parse_instruction_from_text("add(a, b)")
        assert_nodes_equal(node.expression, func("add", var("a"), var("b")))
        assert node.outputs == []

    def test_instruction_without_output_with_condition(self):
        node = parse_instruction_from_text("if(flag) compute(x)")
        assert_nodes_equal(node.condition, var("flag"))
        assert_nodes_equal(node.expression, func("compute", var("x")))
        assert node.outputs == []

    def test_condition_with_string_equality(self):
        node = parse_instruction_from_text('if(color == "red") true > matched')
        assert_nodes_equal(node.condition, func("eq", var("color"), lit("red")))
        assert_nodes_equal(node.expression, lit(True))

    def test_condition_with_multiple_greater_than_comparisons(self):
        # dwa '>' w warunku (w nawiasach) i jeden '>' w expression (ASSIGN_SEP)
        node = parse_instruction_from_text("if(a > b && c > d) x > y")
        assert_nodes_equal(
            node.condition,
            func("and", func("gt", var("a"), var("b")), func("gt", var("c"), var("d"))),
        )
        assert_nodes_equal(node.expression, var("x"))
        assert [o.name for o in node.outputs] == ["y"]

    def test_condition_and_expression_both_with_greater_than(self):
        # '>' w warunku ORAZ dwa '>' w expression (porównanie + ASSIGN_SEP)
        node = parse_instruction_from_text("if(a > b) e > f > g")
        assert_nodes_equal(node.condition, func("gt", var("a"), var("b")))
        assert_nodes_equal(node.expression, func("gt", var("e"), var("f")))
        assert [o.name for o in node.outputs] == ["g"]

    def test_comparison_inside_function_call_before_assign_sep(self):
        # '>' zagnieżdżone w wywołaniu funkcji (głębokość > 0) nie liczy się
        # jako kandydat na ASSIGN_SEP - to jedyne top-level '>' nim jest
        node = parse_instruction_from_text("foo(a > b) > c")
        assert_nodes_equal(node.expression, func("foo", func("gt", var("a"), var("b"))))
        assert [o.name for o in node.outputs] == ["c"]

    def test_comparison_inside_call_and_chained_top_level_comparison(self):
        # '>' zagnieżdżone (głębokość > 0) + dwa top-level '>' w expression
        node = parse_instruction_from_text("foo(a > b) > c > d")
        assert_nodes_equal(
            node.expression,
            func("gt", func("foo", func("gt", var("a"), var("b"))), var("c")),
        )
        assert [o.name for o in node.outputs] == ["d"]


# ---------- Nagłówki pętli ----------

class TestLoopHeaders:
    def test_loop_header_single_output(self):
        tokens = tokenize("split(input, \"\\n\") > line")
        parser = Parser(tokens)
        node = parser.parse_loop_header([])
        assert node.condition is None
        assert node.output_item == "line"
        assert node.output_index is None
        assert_nodes_equal(node.list_expression, func("split", var("input"), lit("\n")))

    def test_loop_header_item_and_index(self):
        tokens = tokenize("lista > item, index")
        parser = Parser(tokens)
        node = parser.parse_loop_header([])
        assert node.output_item == "item"
        assert node.output_index == "index"

    def test_loop_header_with_condition(self):
        tokens = tokenize("if(a) lista > item, index")
        parser = Parser(tokens)
        node = parser.parse_loop_header([])
        assert_nodes_equal(node.condition, var("a"))

    def test_loop_header_with_comparison_condition(self):
        # '>' w warunku (w nawiasach) i jeden '>' w nagłówku pętli (separator)
        tokens = tokenize("if(a > b) lista > item, index")
        parser = Parser(tokens)
        node = parser.parse_loop_header([])
        assert_nodes_equal(node.condition, func("gt", var("a"), var("b")))
        assert_nodes_equal(node.list_expression, var("lista"))
        assert node.output_item == "item"
        assert node.output_index == "index"

    def test_loop_header_list_expression_with_comparison(self):
        # dwa top-level '>' w nagłówku: pierwszy to porównanie, drugi to separator
        tokens = tokenize("a > b > item, index")
        parser = Parser(tokens)
        node = parser.parse_loop_header([])
        assert node.condition is None
        assert_nodes_equal(node.list_expression, func("gt", var("a"), var("b")))
        assert node.output_item == "item"
        assert node.output_index == "index"

    def test_loop_header_stores_body(self):
        body = [parse_instruction_from_text("trim(x) > y")]
        tokens = tokenize("lista > item")
        parser = Parser(tokens)
        node = parser.parse_loop_header(body)
        assert node.body == body

    def test_loop_header_rejects_third_output(self):
        tokens = tokenize("lista > item, index, extra")
        parser = Parser(tokens)
        with pytest.raises(ParseError):
            parser.parse_loop_header([])


# ---------- Konkatenacja ----------

class TestConcatenation:
    def test_simple_concat(self):
        assert_nodes_equal(
            parse_expr_from_text("a .. b"),
            func("con", var("a"), var("b")),
        )

    def test_concat_string_literals(self):
        assert_nodes_equal(
            parse_expr_from_text('"hello" .. " world"'),
            func("con", lit("hello"), lit(" world")),
        )

    def test_concat_left_associativity(self):
        # a .. b .. c -> con(con(a, b), c)
        assert_nodes_equal(
            parse_expr_from_text("a .. b .. c"),
            func("con", func("con", var("a"), var("b")), var("c")),
        )

    def test_concat_binds_looser_than_arithmetic(self):
        # a + 1 .. b * 2 -> con(add(a, 1), mul(b, 2))
        assert_nodes_equal(
            parse_expr_from_text("a + 1 .. b * 2"),
            func("con", func("add", var("a"), lit(1)), func("mul", var("b"), lit(2))),
        )

    def test_concat_binds_looser_than_comparison(self):
        # a == b .. c ~= d -> con(eq(a, b), neq(c, d))
        assert_nodes_equal(
            parse_expr_from_text("a == b .. c ~= d"),
            func("con", func("eq", var("a"), var("b")), func("neq", var("c"), var("d"))),
        )

    def test_concat_binds_looser_than_logical(self):
        # a && b .. c || d -> con(and(a, b), or(c, d))
        assert_nodes_equal(
            parse_expr_from_text("a && b .. c || d"),
            func("con", func("and", var("a"), var("b")), func("or", var("c"), var("d"))),
        )

    def test_parens_override_concat_precedence(self):
        # (a .. b) + c -> add(con(a, b), c)
        assert_nodes_equal(
            parse_expr_from_text("(a .. b) + c"),
            func("add", func("con", var("a"), var("b")), var("c")),
        )

    def test_concat_numbers_with_no_surrounding_spaces(self):
        # regression: "1..2" must not be swallowed by the number tokenizer as a
        # (invalid) float - it's int(1), CONCAT, int(2)
        assert_nodes_equal(
            parse_expr_from_text("1..2"),
            func("con", lit(1), lit(2)),
        )

    def test_concat_with_function_calls(self):
        assert_nodes_equal(
            parse_expr_from_text("trim(a) .. trim(b)"),
            func("con", func("trim", var("a")), func("trim", var("b"))),
        )

    def test_concat_in_full_instruction(self):
        node = parse_instruction_from_text('"prefix: " .. x > result')
        assert_nodes_equal(node.expression, func("con", lit("prefix: "), var("x")))
        assert [o.name for o in node.outputs] == ["result"]

    def test_concat_full_chain_with_three_levels(self):
        # a + 1 .. b && c .. d * 2 -> con(con(add(a,1), and(b,c)), mul(d,2))
        assert_nodes_equal(
            parse_expr_from_text("a + 1 .. b && c .. d * 2"),
            func("con",
                 func("con", func("add", var("a"), lit(1)), func("and", var("b"), var("c"))),
                 func("mul", var("d"), lit(2))),
        )


# ---------- Błędy składniowe ----------

class TestParseErrors:
    def test_missing_closing_paren_raises(self):
        with pytest.raises(ParseError):
            parse_expr_from_text("(a + b")

    def test_missing_closing_bracket_raises(self):
        with pytest.raises(ParseError):
            parse_expr_from_text("lista[0")

    def test_condition_without_parens_raises(self):
        with pytest.raises(ParseError):
            parse_instruction_from_text("if a > b) x > y")

    def test_two_values_with_no_operator_raises(self):
        # "123 abc" tokenizuje się poprawnie na dwa tokeny, ale to błąd składniowy
        with pytest.raises(ParseError):
            parse_expr_from_text("123 abc")

    def test_trailing_tokens_after_expression_raise(self):
        # parse_expr_from_text sam wymusza END po wyrażeniu
        with pytest.raises(ParseError):
            parse_expr_from_text("a b")

    def test_empty_function_arg_list_with_trailing_comma_raises(self):
        with pytest.raises(ParseError):
            parse_expr_from_text("foo(a,)")

    def test_output_list_requires_at_least_one_identifier(self):
        with pytest.raises(ParseError):
            parse_instruction_from_text("a > ")

    def test_missing_condition_body_raises(self):
        with pytest.raises(ParseError):
            parse_instruction_from_text("if() x > y")