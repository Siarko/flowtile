from __future__ import annotations

from . import tokenizer, parser
from .nodes import InstructionNode, IterationNode

MAX_NESTING_DEPTH = 10

RawInstruction = str
RawIteration = tuple[str, "RawInstructionBlock"]
RawInstructionBlock = list[RawInstruction | RawIteration]

def build_ast(instruction_lines: RawInstructionBlock, depth: int = 0) -> list[InstructionNode | IterationNode]:
    if depth >= MAX_NESTING_DEPTH:
        raise ValueError(f"Loop nesting depth exceeded: {depth} of max {MAX_NESTING_DEPTH}")

    result = []
    line = 1
    try:
        last_condition_node = None
        for instruction_data in instruction_lines:
            if isinstance(instruction_data, tuple):
                header_definition, body_definition = instruction_data
                iteration_header = tokenizer.tokenize(header_definition)
                iteration_body = build_ast(body_definition, depth + 1)
                result.append(parser.Parser(iteration_header).parse_loop_header(iteration_body))
            else:
                tokens = tokenizer.tokenize(instruction_data)
                instruction = parser.Parser(tokens).parse_instruction(last_condition_node)
                if instruction.condition is not None:
                    last_condition_node = instruction.condition
                result.append(instruction)
            line += 1
    except (parser.ParseError, tokenizer.TokenizeError) as e:
        e.line = line
        raise e

    return result