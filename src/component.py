import re

from typing import Any, Annotated
import parse

from PIL.ImageDraw import ImageDraw

from .config.config_field import ConfigField
from .render.component_renderer import ComponentContentRenderer
from .component_property import ComponentPropertyAccessor, Property

from .transform.lang.environment import Environment
from .transform.lang.evaluator import execute_block

ComponentData = dict[str, Any]
ComponentNameData = dict[str, ComponentData]
ComponentSource = list[list[ComponentNameData]]

from .render.bounding_box import BoundingBox
from .screens_schema import Key as SchemaKeys, Direction, Align, AlignV, Key, SourceFormatType

from .data_source_type import DataSourceType
import src.data_source_collection as DataSourceCollection
import src.render.registry as RenderRegistry
import src.component_registry as component_registry

import src.variable_store as variable_store
import src.transform.registry as flowline_functions


class Component:
    source: Annotated[dict, ConfigField([SchemaKeys.COMPONENT_DATA, SchemaKeys.COMPONENT_SOURCE])]
    static_definitions: Annotated[dict, ConfigField([SchemaKeys.COMPONENT_DATA, SchemaKeys.COMPONENT_STATIC])]
    persist: Annotated[bool, ConfigField(SchemaKeys.COMPONENT_PERSIST)]
    source_multiline: Annotated[bool, ConfigField([SchemaKeys.COMPONENT_DATA, SchemaKeys.COMPONENT_SOURCE_MULTILINE])]
    source_format: Annotated[dict, ConfigField([SchemaKeys.COMPONENT_DATA, SchemaKeys.COMPONENT_SOURCE_FORMAT])]
    output_format: Annotated[list[str] | None, ConfigField([SchemaKeys.COMPONENT_DATA, SchemaKeys.COMPONENT_OUTPUT_FORMAT])]
    transform_pipeline: Annotated[list, ConfigField([SchemaKeys.COMPONENT_DATA, SchemaKeys.COMPONENT_TRANSFORM])]
    children: Annotated[list[str], ConfigField(SchemaKeys.COMPONENT_CHILDREN, [])]

    direction: Annotated[Direction, ConfigField(SchemaKeys.DIRECTION)]
    size: Annotated[int | str | None, ConfigField(SchemaKeys.COMPONENT_SIZE)]
    padding: Annotated[dict, ConfigField(SchemaKeys.COMPONENT_PADDING)]
    align: Annotated[Property[Align], ConfigField(SchemaKeys.COMPONENT_ALIGN)]
    align_v: Annotated[Property[AlignV], ConfigField(SchemaKeys.COMPONENT_ALIGN_V)]
    border: Annotated[dict, ConfigField(SchemaKeys.COMPONENT_BORDER)]
    border_color: Annotated[dict[str, Property], ConfigField(SchemaKeys.COMPONENT_BORDER_COLOR)]
    color: Annotated[Property[str], ConfigField(SchemaKeys.COMPONENT_COLOR)]
    bg_color: Annotated[Property[str], ConfigField(SchemaKeys.COMPONENT_BG_COLOR)]
    content_render_config: Annotated[dict, ConfigField(SchemaKeys.COMPONENT_CONTENT_RENDER)]
    font_size: Annotated[Property[int], ConfigField(SchemaKeys.COMPONENT_STYLING_FONTSIZE)]
    font_name: Annotated[str | None, ConfigField(SchemaKeys.COMPONENT_STYLING_FONT)]
    visible: Annotated[Property[bool], ConfigField(SchemaKeys.COMPONENT_VISIBLE)]

    def __init__(self, name: str):
        self.name = name
        self.prop_access = ComponentPropertyAccessor(name)
        self.data_lines: list[str] = []
        self.data_variables: list[dict[str, Any]] = []

        self._renderer: ComponentContentRenderer
        self._defined_fields: list[str] = []

        self.runtime: Environment

    def fields_loaded(self):
        self.runtime = Environment(self.static_definitions)
        self.align.datatype = Align
        self.align_v.datatype = AlignV

        self.static_definitions["component_name"] = self.name
        self.static_definitions["log_prefix"] = self.name

    def _get_renderer(self, renderer_data, data_type) -> ComponentContentRenderer:
        if renderer_data is None:
            if data_type == DataSourceType.IMAGE:
                renderer_name = "image"
            else:
                renderer_name = "text"
        else:
            renderer_name = renderer_data[SchemaKeys.COMPONENT_CONTENT_RENDER_TYPE]
        return RenderRegistry.get(renderer_name, self.name)

    def prepare(self, skip: list[str]):
        if self.name not in skip:
            data_source = DataSourceCollection.get(self.source[Key.COMPONENT_SOURCE_NAME])
            renderer_data = self.content_render_config

            self.data_lines, self.data_variables = self.process_data(data_source.get_content(self))
            self._renderer = self._get_renderer(renderer_data, data_source.get_content_type())
            self._renderer.set_options(renderer_data or {})
            self._renderer.prepare(self)
        if self.children:
            self._prepare_children(self.children, skip)

    def _prepare_children(self, children: list[str], skip: list[str]):
        for child_name in children:
            child = component_registry.get_component(child_name)
            child.prepare(skip)

    def _draw_border(self, canvas: ImageDraw, bb: BoundingBox):
        top = self.prop_access.get(self.border[Key.COMPONENT_EDGE_TOP])
        bottom = self.prop_access.get(self.border[Key.COMPONENT_EDGE_BOTTOM])
        left = self.prop_access.get(self.border[Key.COMPONENT_EDGE_LEFT])
        right = self.prop_access.get(self.border[Key.COMPONENT_EDGE_RIGHT])

        outer_tl = (bb.x, bb.y)
        outer_tr = (bb.x2, bb.y)
        outer_br = (bb.x2, bb.y2)
        outer_bl = (bb.x, bb.y2)

        inner_tl = (bb.x + left - 1, bb.y + top - 1)
        inner_tr = (bb.x2 - right + 1, bb.y + top - 1)
        inner_br = (bb.x2 - right + 1, bb.y2 - bottom + 1)
        inner_bl = (bb.x + left - 1, bb.y2 - bottom + 1)
        if top > 0:
            canvas.polygon(
                [outer_tl, outer_tr, inner_tr, inner_tl],
                fill=self.prop_access.get(self.border_color[Key.COMPONENT_EDGE_TOP])
            )
        if right > 0:
            canvas.polygon(
                [outer_tr, outer_br, inner_br, inner_tr],
                fill=self.prop_access.get(self.border_color[Key.COMPONENT_EDGE_RIGHT])
            )
        if bottom > 0:
            canvas.polygon(
                [outer_br, outer_bl, inner_bl, inner_br],
                fill=self.prop_access.get(self.border_color[Key.COMPONENT_EDGE_BOTTOM])
            )
        if left > 0:
            canvas.polygon(
                [outer_bl, outer_tl, inner_tl, inner_bl],
                fill=self.prop_access.get(self.border_color[Key.COMPONENT_EDGE_LEFT])
            )

    def draw(self, canvas: ImageDraw, bb: BoundingBox):
        if not self.prop_access.get(self.visible):
            return
        bg_color = self.prop_access.get(self.bg_color)
        if bg_color != -1:
            canvas.rectangle(
                (bb.x, bb.y, bb.x2, bb.y2),
                fill=bg_color
            )
        if self.border:
            self._draw_border(canvas, bb)

        pad_top = self.padding[Key.COMPONENT_EDGE_TOP] + self.prop_access.get(self.border[Key.COMPONENT_EDGE_TOP])
        pad_right = self.padding[Key.COMPONENT_EDGE_RIGHT] + self.prop_access.get(self.border[Key.COMPONENT_EDGE_RIGHT])
        pad_bottom = self.padding[Key.COMPONENT_EDGE_BOTTOM] + self.prop_access.get(
            self.border[Key.COMPONENT_EDGE_BOTTOM])
        pad_left = self.padding[Key.COMPONENT_EDGE_LEFT] + self.prop_access.get(self.border[Key.COMPONENT_EDGE_LEFT])
        inner_x = bb.x + pad_left
        inner_y = bb.y + pad_top
        inner_w = bb.w - pad_left - pad_right
        inner_h = bb.h - pad_top - pad_bottom
        bb = BoundingBox(inner_x, inner_y, inner_w, inner_h)

        if self.children:
            _draw_children(self.children, self.direction, canvas, bb)
        else:
            self._draw_content(canvas, bb)

    def _draw_content(self, canvas: ImageDraw, bb: BoundingBox):
        if self._renderer:
            self._renderer.render(canvas, self, bb)

    def _format_input(self, input_lines: list) -> list[dict[str, Any]]:
        variables = []
        lines = input_lines

        def _match_line(l) -> str | None:
            if not isinstance(l, str):
                return None
            for expr, input_format in self.source_format[SourceFormatType.REGEX].items():
                if re.match(expr, l):
                    return input_format
            return None

        def _process_parsing(v_set, input_line_no, input_line):
            if self.source_format is not None:
                target_format = None
                if input_line_no in self.source_format[SourceFormatType.NUMBERED]:
                    target_format = self.source_format[SourceFormatType.NUMBERED][line_no]
                elif (candidate := _match_line(input_line)) is not None:
                    target_format = candidate
                elif isinstance(self.source_format[SourceFormatType.WILDCARD], str):
                    target_format = self.source_format[SourceFormatType.WILDCARD]
                if target_format:
                    parse_result = parse.parse(target_format, input_line)
                    if parse_result is not None:
                        v_set.update(parse_result.named)
            return v_set

        if self.source_multiline:
            var_set = {"input": "\n".join(lines)}
            for line_no, line in enumerate(lines, start=1):
                _process_parsing(var_set, line_no, line)
            variables.append(var_set)
        else:
            for line_no, line in enumerate(lines, start=1):
                var_set = {"input": line}
                _process_parsing(var_set, line_no, line)
                variables.append(var_set)
        return variables

    def process_data(self, input_lines: list[str]) -> tuple[list[str], list[dict]]:
        variables: list[dict[str, Any]] = self._format_input(input_lines)
        output_lines = []

        format_lines = ["{input}"] if self.output_format is None else self.output_format
        for var_set in variables:
            if len(self.transform_pipeline) > 0:
                self.runtime.set_multiple(var_set)
                execute_block(self.transform_pipeline, self.runtime, flowline_functions.get_function_registry())
                var_set.update(self.runtime.dump())

            variable_store.set_multiple(self.name, var_set)
            for format_line in format_lines:
                try:
                    output_lines.append(format_line.format(**var_set))
                except KeyError:
                    pass
            self.runtime.flush()

        return output_lines, variables


def _parse_size(size: None | int | str) -> tuple[str, float]:
    if size is None:
        return 'unsized', 0.0
    if isinstance(size, int):
        return 'pct', float(size)
    if isinstance(size, str) and size.endswith('px'):
        return 'fixed', float(size[:-2])
    raise ValueError(f"Invalid size value: {size!r}")


def _draw_children(elements: list[str], direction: Direction, canvas: ImageDraw, bb: BoundingBox):
    if len(elements) == 0:
        return

    cross_total = bb.h if direction == Direction.ROW else bb.w
    total = bb.w if direction == Direction.ROW else bb.h

    fixed_total = 0.0
    pct_total = 0.0
    unsized_count = 0

    for child_name in elements:
        child = component_registry.get_component(child_name)
        kind, val = _parse_size(child.size)
        if kind == 'fixed':
            fixed_total += val
        elif kind == 'pct':
            pct_total += val
        else:
            unsized_count += 1

    remaining = total - fixed_total
    pct_allocated = int((pct_total / 100.0) * remaining)
    remaining_for_unsized = remaining - pct_allocated
    unsized_size = remaining_for_unsized / unsized_count if unsized_count else 0.0

    cursor = 0.0
    for child_name in elements:
        child = component_registry.get_component(child_name)
        kind, val = _parse_size(child.size)
        if kind == 'fixed':
            child_main = val
        elif kind == 'pct':
            child_main = (val / 100.0) * remaining
        else:
            child_main = round(unsized_size)

        child_main = int(child_main)

        if direction == Direction.ROW:
            child.draw(canvas, BoundingBox(bb.x + int(cursor), bb.y, child_main, cross_total))
        else:
            child.draw(canvas, BoundingBox(bb.x, bb.y + int(cursor), cross_total, child_main))

        cursor += child_main
