from __future__ import annotations

from typing import Any

from .nodes import (
    ExpressionNode, FunctionNode, VariableNode, LiteralNode,
    InstructionNode, IterationNode, OutputTargetNode,
)
from .environment import Environment
from .functions import FunctionRegistry, FunctionCallError, ValueType


class EvaluationError(Exception):
    def __init__(self, message: str, position: tuple[int, int] | None):
        super().__init__(message)
        self.message = message
        self.position = position

class IndexTypeError(EvaluationError):
    pass

class IndexOutOfRangeError(EvaluationError):
    pass

def evaluate_expression(node: ExpressionNode, env: Environment, registry: FunctionRegistry) -> Any:
    if isinstance(node, LiteralNode):
        return node.value

    if isinstance(node, VariableNode):
        value = env.get(node.name)
        for index_node in node.indices:
            index_value = evaluate_expression(index_node, env, registry)
            if not isinstance(index_value, int) or isinstance(index_value, bool):
                raise IndexTypeError(
                    f"List index must be an int, got {type(index_value).__name__}",
                    index_node.definition_position,
                )
            if not isinstance(value, list):
                raise IndexTypeError(
                    f"Cannot index into non-list value '{node.name}'",
                    node.definition_position,
                )
            if index_value < 0 or index_value >= len(value):
                raise IndexOutOfRangeError(
                    f"Index {index_value} out of range for '{node.name}' (length {len(value)})",
                    index_node.definition_position,
                )
            value = value[index_value]
        return value

    if isinstance(node, FunctionNode):
        try:
            function_spec = registry.get(node.name)
            arg_spec = zip(function_spec.param_types, node.arguments)
            arg_values = []
            for req_type, arg in arg_spec:
                if req_type is ValueType.NODE:
                    arg_values.append(arg)
                else:
                    arg_values.append(evaluate_expression(arg, env, registry))
            return registry.call(node.name, arg_values, env)
        except FunctionCallError as e:
            raise EvaluationError(str(e), node.definition_position) from e

    raise AssertionError(f"Unhandled expression node type: {type(node)}")


def _is_truthy(value: Any) -> bool:
    if not isinstance(value, bool):
        raise EvaluationError(
            f"Condition must evaluate to bool, got {type(value).__name__}", None
        )
    return value

def _hoist_outputs(outputs: list[OutputTargetNode], env: Environment) -> None:
    for output in outputs:
        default = [] if output.append_list else None
        env.declare(output.name, default)


def _assign_single(output: OutputTargetNode, value: Any, env: Environment) -> None:
    if output.append_list:
        env.append_to_list(output.name, value)
    else:
        env.set(output.name, value)


def _assign_outputs(
    outputs: list[OutputTargetNode],
    result: Any,
    env: Environment,
    position: tuple[int, int] | None,
) -> None:
    if isinstance(result, tuple):
        if len(outputs) > len(result):
            raise EvaluationError(
                f"Expression returns {len(result)} value(s), "
                f"but {len(outputs)} output variable(s) given",
                position,
            )
        for output, value in zip(outputs, result):
            _assign_single(output, value, env)
        return

    if len(outputs) != 1:
        raise EvaluationError(
            f"Expression returns a single value, but {len(outputs)} output variables given",
            position,
        )
    _assign_single(outputs[0], result, env)


def execute_instruction(node: InstructionNode, env: Environment, registry: FunctionRegistry) -> None:
    _hoist_outputs(node.outputs, env)

    if node.condition is not None:
        condition_value = evaluate_expression(node.condition, env, registry)
        if not _is_truthy(condition_value):
            return

    result = evaluate_expression(node.expression, env, registry)
    if len(node.outputs) > 0:
        _assign_outputs(node.outputs, result, env, node.expression.definition_position)


def execute_loop(node: IterationNode, env: Environment, registry: FunctionRegistry) -> None:
    if node.condition is not None:
        condition_value = evaluate_expression(node.condition, env, registry)
        if not _is_truthy(condition_value):
            return

    list_value = evaluate_expression(node.list_expression, env, registry)
    if not isinstance(list_value, list):
        raise EvaluationError(
            f"Loop expression must evaluate to a list, got {type(list_value).__name__}",
            node.list_expression.definition_position,
        )

    append_target_names = _list_append_targets(node.body)
    collected: dict[str, list[Any]] = {name: [] for name in append_target_names}

    for index, item in enumerate(list_value):
        iteration_env = env.child_scope()
        iteration_env.set(node.output_item, item)
        if node.output_index is not None:
            iteration_env.set(node.output_index, index)

        execute_block(node.body, iteration_env, registry)

        for name in append_target_names:
            if iteration_env.exists(name):
                collected[name].extend(iteration_env.get(name))

    for name, values in collected.items():
        env.set(name, values)


def _list_append_targets(body: list[InstructionNode | IterationNode]) -> set[str]:
    names = set()
    for stmt in body:
        if isinstance(stmt, InstructionNode):
            for output in stmt.outputs:
                if output.append_list:
                    names.add(output.name)
    return names

def execute_block(nodes: list[InstructionNode | IterationNode], env: Environment, registry: FunctionRegistry) -> None:
    for node in nodes:
        if isinstance(node, InstructionNode):
            execute_instruction(node, env, registry)
        elif isinstance(node, IterationNode):
            execute_loop(node, env, registry)
        else:
            raise AssertionError(f"Unhandled statement node type: {type(node)}")