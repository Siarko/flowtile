from __future__ import annotations

from dataclasses import dataclass, field

LiteralTypes = int | float | bool | str | list

@dataclass(frozen=True)
class Node:
    definition_position: tuple[int, int] | None = field(default=None, kw_only=True)

@dataclass(frozen=True)
class FunctionNode(Node):
    name: str
    arguments: list[ExpressionNode]

@dataclass(frozen=True)
class VariableNode(Node):
    name: str
    indices: list[ExpressionNode]

@dataclass(frozen=True)
class LiteralNode(Node):
    value: LiteralTypes

ExpressionNode = FunctionNode | VariableNode | LiteralNode

@dataclass(frozen=True)
class OutputTargetNode(Node):
    name: str
    append_list: bool = False

@dataclass(frozen=True)
class InstructionNode(Node):
    condition: ExpressionNode | None
    expression: ExpressionNode
    outputs: list[OutputTargetNode]

@dataclass(frozen=True)
class IterationNode(Node):
    condition: ExpressionNode | None
    list_expression: ExpressionNode
    output_item: str
    output_index: str | None
    body: list[InstructionNode | IterationNode]