import pytest

from transform.lang.tokenizer import tokenize
from transform.lang.parser import Parser
from transform.lang.nodes import (
    InstructionNode, IterationNode,
    FunctionNode, VariableNode, LiteralNode,
)
from transform.lang.environment import Environment, VariableTypeConflictError, UndefinedVariableError
from transform.lang.functions import FunctionRegistry, FunctionSpec, ValueType, build_core_registry
from transform.lang.evaluator import (
    evaluate_expression, execute_instruction, execute_loop, execute_block,
    EvaluationError, IndexTypeError, IndexOutOfRangeError,
)


# ---------- Helpers ----------

def parse_instruction(text: str) -> InstructionNode:
    return Parser(tokenize(text)).parse_instruction()


def parse_loop(text: str, body: list) -> IterationNode:
    return Parser(tokenize(text)).parse_loop_header(body)


def make_env(static: dict | None = None) -> Environment:
    return Environment(static_store=static if static is not None else {})


@pytest.fixture
def registry() -> FunctionRegistry:
    r = build_core_registry()
    r.register(FunctionSpec("trim", [ValueType.STRING], lambda s: s.strip()))
    r.register(FunctionSpec("split", [ValueType.STRING, ValueType.STRING], lambda s, sep: s.split(sep)))
    r.register(FunctionSpec("merge", [ValueType.LIST], lambda items: "".join(str(i) for i in items)))
    r.register(FunctionSpec(
        "slider_linear", [ValueType.NUMERIC] * 4,
        lambda x, lo, hi, step: (
            (hi, -step) if x + step > hi else
            (lo, -step) if x + step < lo else
            (x + step, step)
        ),
    ))
    return r


# ---------- evaluate_expression: literały, zmienne, indeksowanie ----------

class TestEvaluateLiterals:
    def test_int_literal(self, registry):
        env = make_env()
        assert evaluate_expression(LiteralNode(5), env, registry) == 5

    def test_string_literal(self, registry):
        env = make_env()
        assert evaluate_expression(LiteralNode("hi"), env, registry) == "hi"

    def test_bool_literal(self, registry):
        env = make_env()
        assert evaluate_expression(LiteralNode(True), env, registry) is True

    def test_list_literal(self, registry):
        env = make_env()
        assert evaluate_expression(LiteralNode([1, 2, 3]), env, registry) == [1, 2, 3]


class TestEvaluateVariables:
    def test_read_static_variable(self, registry):
        env = make_env(static={"x": 42})
        node = VariableNode("x", [])
        assert evaluate_expression(node, env, registry) == 42

    def test_read_dynamic_variable(self, registry):
        env = make_env()
        env.set("y", "hello")
        node = VariableNode("y", [])
        assert evaluate_expression(node, env, registry) == "hello"

    def test_dynamic_shadows_static(self, registry):
        env = make_env(static={"x": 1})
        env.set("x", 99)
        node = VariableNode("x", [])
        assert evaluate_expression(node, env, registry) == 99

    def test_read_undefined_variable_raises(self, registry):
        env = make_env()
        node = VariableNode("missing", [])
        with pytest.raises(Exception):
            evaluate_expression(node, env, registry)


class TestEvaluateIndexing:
    def test_single_index(self, registry):
        env = make_env()
        env.set("items", ["a", "b", "c"])
        node = VariableNode("items", [LiteralNode(1)])
        assert evaluate_expression(node, env, registry) == "b"

    def test_multi_level_index(self, registry):
        env = make_env()
        env.set("matrix", [[1, 2], [3, 4]])
        node = VariableNode("matrix", [LiteralNode(1), LiteralNode(0)])
        assert evaluate_expression(node, env, registry) == 3

    def test_index_with_expression(self, registry):
        env = make_env()
        env.set("items", ["a", "b", "c"])
        env.set("i", 0)
        index_expr = FunctionNode("add", [VariableNode("i", []), LiteralNode(1)])
        node = VariableNode("items", [index_expr])
        assert evaluate_expression(node, env, registry) == "b"

    def test_index_out_of_range_raises(self, registry):
        env = make_env()
        env.set("items", ["a"])
        node = VariableNode("items", [LiteralNode(5)])
        with pytest.raises(IndexOutOfRangeError):
            evaluate_expression(node, env, registry)

    def test_negative_index_raises(self, registry):
        env = make_env()
        env.set("items", ["a", "b"])
        node = VariableNode("items", [LiteralNode(-1)])
        with pytest.raises(IndexOutOfRangeError):
            evaluate_expression(node, env, registry)

    def test_index_into_non_list_raises(self, registry):
        env = make_env()
        env.set("x", 5)
        node = VariableNode("x", [LiteralNode(0)])
        with pytest.raises(IndexTypeError):
            evaluate_expression(node, env, registry)

    def test_non_int_index_raises(self, registry):
        env = make_env()
        env.set("items", ["a", "b"])
        node = VariableNode("items", [LiteralNode("0")])
        with pytest.raises(IndexTypeError):
            evaluate_expression(node, env, registry)

    def test_bool_index_raises(self, registry):
        env = make_env()
        env.set("items", ["a", "b"])
        node = VariableNode("items", [LiteralNode(True)])
        with pytest.raises(IndexTypeError):
            evaluate_expression(node, env, registry)

    def test_index_out_of_range_reports_correct_length(self, registry):
        env = make_env()
        env.set("items", ["a", "b"])
        node = VariableNode("items", [LiteralNode(2)])
        with pytest.raises(IndexOutOfRangeError, match="length 2"):
            evaluate_expression(node, env, registry)


class TestEvaluateFunctionCalls:
    def test_simple_call(self, registry):
        env = make_env()
        node = FunctionNode("add", [LiteralNode(2), LiteralNode(3)])
        assert evaluate_expression(node, env, registry) == 5

    def test_nested_call(self, registry):
        env = make_env()
        inner = FunctionNode("add", [LiteralNode(1), LiteralNode(2)])
        outer = FunctionNode("mul", [inner, LiteralNode(10)])
        assert evaluate_expression(outer, env, registry) == 30

    def test_function_returning_list_used_as_value(self, registry):
        env = make_env()
        env.set("text", "a,b,c")
        node = FunctionNode("split", [VariableNode("text", []), LiteralNode(",")])
        assert evaluate_expression(node, env, registry) == ["a", "b", "c"]

    def test_tuple_returning_function_as_nested_argument_raises_type_error(self, registry):
        env = make_env()
        env.set("x", 0.0)
        env.set("step", 1.0)
        slider = FunctionNode("slider_linear", [
            VariableNode("x", []), LiteralNode(0), LiteralNode(10),
            VariableNode("step", []),
        ])
        node = FunctionNode("mul", [slider, LiteralNode(2)])
        with pytest.raises(EvaluationError):
            evaluate_expression(node, env, registry)

    def test_unknown_function_wrapped_as_evaluation_error(self, registry):
        env = make_env()
        node = FunctionNode("nonexistent", [LiteralNode(1)])
        with pytest.raises(EvaluationError):
            evaluate_expression(node, env, registry)

    def test_type_error_wrapped_as_evaluation_error(self, registry):
        env = make_env()
        node = FunctionNode("add", [LiteralNode(1), LiteralNode("x")])
        with pytest.raises(EvaluationError):
            evaluate_expression(node, env, registry)

    def test_arguments_evaluated_left_to_right_exactly_once(self, registry):
        calls = []

        def counting_fn(x):
            calls.append(x)
            return x

        registry.register(FunctionSpec("count", [ValueType.NUMERIC], counting_fn))
        env = make_env()
        node = FunctionNode("add", [
            FunctionNode("count", [LiteralNode(1)]),
            FunctionNode("count", [LiteralNode(2)]),
        ])
        evaluate_expression(node, env, registry)
        assert calls == [1, 2]


# ---------- execute_instruction ----------

class TestExecuteInstructionBasic:
    def test_simple_assignment(self, registry):
        env = make_env()
        node = parse_instruction("add(2, 3) > result")
        execute_instruction(node, env, registry)
        assert env.get("result") == 5

    def test_condition_true_executes(self, registry):
        env = make_env()
        env.set("flag", True)
        node = parse_instruction("if(flag) add(1, 1) > result")
        execute_instruction(node, env, registry)
        assert env.get("result") == 2

    def test_condition_false_skips_and_keeps_prior_value(self, registry):
        static = {"result": 99}
        env = make_env(static)
        env.set("flag", False)
        node = parse_instruction("if(flag) add(1, 1) > result")
        execute_instruction(node, env, registry)
        assert env.get("result") == 99

    def test_hoisting_creates_output_even_if_condition_false(self, registry):
        env = make_env()
        env.set("flag", False)
        node = parse_instruction("if(flag) add(1, 1) > result")
        execute_instruction(node, env, registry)
        assert env.exists("result")
        assert env.get("result") is None

    def test_non_bool_condition_raises(self, registry):
        env = make_env()
        env.set("flag", 1)
        node = parse_instruction("if(flag) add(1, 1) > result")
        with pytest.raises(EvaluationError):
            execute_instruction(node, env, registry)

    def test_plain_variable_assignment_no_function_call(self, registry):
        env = make_env()
        env.set("a", 7)
        node = parse_instruction("a > b")
        execute_instruction(node, env, registry)
        assert env.get("b") == 7


class TestExecuteInstructionMultipleOutputs:
    def test_multiple_outputs_from_tuple_returning_function(self, registry):
        env = make_env()
        env.set("x", 8.0)
        env.set("step", 5.0)
        node = parse_instruction("slider_linear(x, 0, 10, step) > x, step")
        execute_instruction(node, env, registry)
        assert env.get("x") == 10.0
        assert env.get("step") == -5.0

    def test_single_output_takes_first_value_and_discards_rest(self, registry):
        env = make_env()
        env.set("x", 8.0)
        env.set("step", 5.0)
        node = parse_instruction("slider_linear(x, 0, 10, step) > only_one")
        execute_instruction(node, env, registry)
        assert env.get("only_one") == 10.0

    def test_more_outputs_than_returned_values_raises(self, registry):
        env = make_env()
        node = parse_instruction("add(1, 2) > a, b")
        with pytest.raises(EvaluationError):
            execute_instruction(node, env, registry)

    def test_split_returns_single_list_value_not_unpacked(self, registry):
        env = make_env()
        env.set("input", "a b c")
        node = parse_instruction('split(input, " ") > words')
        execute_instruction(node, env, registry)
        assert env.get("words") == ["a", "b", "c"]

    def test_scalar_result_with_multiple_outputs_raises(self, registry):
        # add() zwraca zwykły int (nie tuple) - 2 outputy to błąd, nie ciche rozpakowanie znaków/cyfr
        env = make_env()
        node = parse_instruction("add(1, 2) > a, b, c")
        with pytest.raises(EvaluationError):
            execute_instruction(node, env, registry)


class TestExecuteInstructionListAppend:
    def test_append_to_new_list(self, registry):
        env = make_env()
        env.set("item", "  hello  ")
        node = parse_instruction("trim(item) > items[]")
        execute_instruction(node, env, registry)
        assert env.get("items") == ["hello"]

    def test_append_multiple_times(self, registry):
        env = make_env()
        node1 = parse_instruction('"a" > items[]')
        node2 = parse_instruction('"b" > items[]')
        execute_instruction(node1, env, registry)
        execute_instruction(node2, env, registry)
        assert env.get("items") == ["a", "b"]

    def test_append_to_existing_non_list_raises(self, registry):
        env = make_env()
        env.set("x", 5)
        node = parse_instruction('"a" > x[]')
        with pytest.raises(VariableTypeConflictError):
            execute_instruction(node, env, registry)

    def test_append_persists_in_static_across_sessions(self, registry):
        static = {"items": []}
        env1 = make_env(static)
        execute_instruction(parse_instruction('"a" > items[]'), env1, registry)
        env2 = make_env(static)
        execute_instruction(parse_instruction('"b" > items[]'), env2, registry)
        assert static["items"] == ["a", "b"]


class TestExecuteInstructionStaticPersistence:
    def test_static_variable_persists_across_sessions(self, registry):
        static = {"counter": 0}
        env1 = make_env(static)
        execute_instruction(parse_instruction("add(counter, 1) > counter"), env1, registry)
        assert static["counter"] == 1

        env2 = make_env(static)
        execute_instruction(parse_instruction("add(counter, 1) > counter"), env2, registry)
        assert static["counter"] == 2

    def test_dynamic_variable_does_not_persist(self, registry):
        static = {}
        env1 = make_env(static)
        execute_instruction(parse_instruction('"temp" > x'), env1, registry)
        assert "x" not in static

        env2 = make_env(static)
        assert not env2.exists("x")


# ---------- execute_loop ----------

class TestExecuteLoopBasic:
    def test_simple_map_over_list(self, registry):
        env = make_env()
        env.set("raw", ["  a ", " b  ", "c "])
        body = [parse_instruction("trim(item) > items[]")]
        node = parse_loop("raw > item", body)
        execute_loop(node, env, registry)
        assert env.get("items") == ["a", "b", "c"]

    def test_loop_with_index(self, registry):
        env = make_env()
        env.set("raw", ["a", "b", "c"])
        body = [parse_instruction("index > indices[]")]
        node = parse_loop("raw > item, index", body)
        execute_loop(node, env, registry)
        assert env.get("indices") == [0, 1, 2]

    def test_loop_over_empty_list(self, registry):
        env = make_env()
        env.set("raw", [])
        body = [parse_instruction("trim(item) > items[]")]
        node = parse_loop("raw > item", body)
        execute_loop(node, env, registry)
        assert env.get("items") == []

    def test_item_not_leaked_outside_loop(self, registry):
        env = make_env()
        env.set("raw", ["a"])
        body = [parse_instruction("trim(item) > items[]")]
        node = parse_loop("raw > item", body)
        execute_loop(node, env, registry)
        assert not env.exists("item")

    def test_index_not_leaked_outside_loop(self, registry):
        env = make_env()
        env.set("raw", ["a"])
        body = [parse_instruction("index > indices[]")]
        node = parse_loop("raw > item, index", body)
        execute_loop(node, env, registry)
        assert not env.exists("index")


class TestExecuteLoopConditionalSkipping:
    def test_conditional_append_skips_element_when_condition_false(self, registry):
        env = make_env()
        env.set("raw", ["a", "b", "c"])
        body = [
            parse_instruction('neq(item, "b") > keep'),
            parse_instruction("if(keep) item > items[]"),
        ]
        node = parse_loop("raw > item", body)
        execute_loop(node, env, registry)
        assert env.get("items") == ["a", "c"]

    def test_loop_condition_false_skips_entire_loop(self, registry):
        static = {"items": ["preexisting"]}
        env = make_env(static)
        env.set("raw", ["a", "b"])
        env.set("enabled", False)
        body = [parse_instruction("item > items[]")]
        node = parse_loop("if(enabled) raw > item", body)
        execute_loop(node, env, registry)
        assert env.get("items") == ["preexisting"]

    def test_loop_expression_not_list_raises(self, registry):
        env = make_env()
        env.set("raw", "not a list")
        body = [parse_instruction("item > items[]")]
        node = parse_loop("raw > item", body)
        with pytest.raises(EvaluationError):
            execute_loop(node, env, registry)

    def test_loop_expression_non_bool_condition_raises(self, registry):
        env = make_env()
        env.set("raw", [1, 2])
        env.set("flag", 1)  # nie bool
        body = [parse_instruction("item > items[]")]
        node = parse_loop("if(flag) raw > item", body)
        with pytest.raises(EvaluationError):
            execute_loop(node, env, registry)


class TestExecuteLoopIsolation:
    def test_iterations_do_not_see_each_others_temp_vars(self, registry):
        env = make_env()
        env.set("raw", [1, 2, 3])
        body = [
            parse_instruction("item > seen"),
            parse_instruction("seen > results[]"),
        ]
        node = parse_loop("raw > item", body)
        execute_loop(node, env, registry)
        assert env.get("results") == [1, 2, 3]

    def test_static_mutation_inside_loop_persists(self, registry):
        static = {"total": 0}
        env = make_env(static)
        env.set("raw", [1, 2, 3])
        body = [parse_instruction("add(total, item) > total")]
        node = parse_loop("raw > item", body)
        execute_loop(node, env, registry)
        assert static["total"] == 6

    def test_parent_dynamic_not_mutated_by_loop_body(self, registry):
        env = make_env()
        env.set("raw", [1, 2])
        env.set("marker", "untouched")
        body = [parse_instruction('"changed" > marker')]
        node = parse_loop("raw > item", body)
        execute_loop(node, env, registry)
        assert env.get("marker") == "untouched"


class TestNestedLoops:
    def test_nested_loop_full_pipeline(self, registry):
        env = make_env()
        env.set("input", "hello\n world \n!")
        split_instr = parse_instruction('split(input, "\\n") > lines')
        inner_body = [parse_instruction("trim(line) > trimmed[]")]
        loop = parse_loop("lines > line", inner_body)
        merge_instr = parse_instruction("merge(trimmed) > output")

        execute_block([split_instr, loop, merge_instr], env, registry)
        assert env.get("output") == "helloworld!"

    def test_deeply_nested_loop_collects_independently_per_level(self, registry):
        env = make_env()
        env.set("groups", [["a", "b"], ["c", "d"]])
        inner_body = [parse_instruction("item > flat_inner[]")]
        outer_body = [
            parse_loop("group > item", inner_body),
            parse_instruction("flat_inner > all_groups[]"),
        ]
        outer = parse_loop("groups > group", outer_body)
        execute_block([outer], env, registry)
        assert env.get("all_groups") == [["a", "b"], ["c", "d"]]


# ---------- execute_block: integracja pełnych skryptów ----------

class TestFullScripts:
    def test_slider_bounce_over_multiple_frames(self, registry):
        static = {"x": 0.0, "step": 1.0}
        script = [parse_instruction("slider_linear(x, 0, 3, step) > x, step")]

        for _ in range(3):
            env = make_env(static)
            execute_block(script, env, registry)

        assert static["x"] == 3.0
        assert static["step"] == 1.0

        env = make_env(static)
        execute_block(script, env, registry)
        assert static["x"] == 3.0
        assert static["step"] == -1.0

    def test_script_with_condition_and_loop_and_merge(self, registry):
        static = {"a": True}
        env = make_env(static)
        env.set("input", "  hello world  ")

        instructions = [parse_instruction('split(input, " ") > raw_words')]
        body = [parse_instruction("trim(word) > words[]")]
        instructions.append(parse_loop("if(a) raw_words > word, index", body))
        instructions.append(parse_instruction("merge(words) > output"))

        execute_block(instructions, env, registry)
        result = env.get("output")
        assert "hello" in result and "world" in result


# ---------- Błędy propagujące się z evaluate_expression w kontekście instrukcji ----------

class TestErrorPropagation:
    def test_undefined_variable_in_expression_propagates(self, registry):
        env = make_env()
        node = parse_instruction("add(missing, 1) > result")
        with pytest.raises(Exception):
            execute_instruction(node, env, registry)

    def test_undefined_variable_in_condition_propagates(self, registry):
        env = make_env()
        node = parse_instruction("if(missing_flag) 1 > result")
        with pytest.raises(Exception):
            execute_instruction(node, env, registry)

    def test_error_position_is_preserved(self, registry):
        env = make_env()
        node = parse_instruction("add(1, true) > result")
        with pytest.raises(EvaluationError) as exc_info:
            execute_instruction(node, env, registry)
        assert exc_info.value.position is not None

    def test_division_by_zero_propagates(self, registry):
        env = make_env()
        node = parse_instruction("div(1, 0) > result")
        with pytest.raises(EvaluationError):
            execute_instruction(node, env, registry)


class TestConcatOperatorTokenizesAndRunsWithoutSpaces:
    def test_two_int_literals_glued_together(self, registry):
        env = make_env()
        node = parse_instruction("1..2 > result")
        execute_instruction(node, env, registry)
        assert env.get("result") == "12"

    def test_two_float_literals_glued_together(self, registry):
        env = make_env()
        node = parse_instruction("1.5..2.5 > result")
        execute_instruction(node, env, registry)
        assert env.get("result") == "1.52.5"


# ---------- flush() between lines - mirrors Component.process_data's per-line reset ----------

class TestFlushBetweenLines:
    """Component.process_data runs one flowline pass per input line, on the same
    Environment, calling env.flush() after each one. Dynamic output variables from
    one line must not leak into the next; static (data.static) variables must."""

    def test_dynamic_output_does_not_leak_to_next_line(self, registry):
        env = make_env()
        script = [parse_instruction("trim(input) > seen")]

        env.set("input", " first ")
        execute_block(script, env, registry)
        assert env.get("seen") == "first"
        env.flush()

        assert not env.exists("seen")
        env.set("input", " second ")
        execute_block(script, env, registry)
        assert env.get("seen") == "second"

    def test_static_accumulator_survives_flush_across_lines(self, registry):
        static = {"total": 0}
        env = make_env(static)
        script = [parse_instruction("add(total, item) > total")]

        for item in (1, 2, 3):
            env.set("item", item)
            execute_block(script, env, registry)
            env.flush()

        assert static["total"] == 6

    def test_is_defined_guard_is_the_safe_way_to_check_this_lines_value(self, registry):
        # source_format only produces "number" on some lines (e.g. a numbered rule
        # that only matches line 1). is_none(number) would crash on a line where
        # "number" was never set - is_defined(number) is the correct guard, since
        # it checks the raw variable node instead of evaluating it.
        static = {"last_seen": -1}
        env = make_env(static)
        script = [parse_instruction("if(is_defined(number)) number > last_seen")]

        env.set_multiple({"input": "irrelevant"})  # no "number" this line
        execute_block(script, env, registry)
        env.flush()
        assert static["last_seen"] == -1  # untouched, no crash

        env.set_multiple({"input": "irrelevant", "number": 42})
        execute_block(script, env, registry)
        env.flush()
        assert static["last_seen"] == 42

    def test_referencing_a_flushed_dynamic_variable_raises(self, registry):
        # matches the existing, established behavior for any undefined variable
        # (see TestEvaluateVariables.test_read_undefined_variable_raises) - it's
        # raised straight from Environment.get(), not wrapped as an EvaluationError.
        env = make_env()
        execute_block([parse_instruction('"x" > seen')], env, registry)
        env.flush()
        with pytest.raises(UndefinedVariableError):
            execute_instruction(parse_instruction("seen > copy"), env, registry)