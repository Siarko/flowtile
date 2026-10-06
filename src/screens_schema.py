import os
from enum import Enum
from typing import TypeVar, Any
from yaml import ScalarNode, SequenceNode

from .axis import AxisElementType
from .config_loader import Traveler
from .config_loader_schema import Keys as Schema, AutoDefault
from . import ExecMode
from .direction import Direction

from .component_property import PropertyType, Property
import src.transform.lang.flowline as flowline
import re


class Align(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class AlignV(Enum):
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


class SourceType(Enum):
    TEXT = "text"
    COMMAND = "command"


class SourceFormatType(Enum):
    WILDCARD = "widlcard"
    REGEX = "regex"
    NUMBERED = "number"


class Key:
    TAG_VARIABLE = "!var"
    TAG_PROPERTY_TYPE = "type"
    TAG_PROPERTY_VALUE = "value"

    SOURCES = "sources"
    SOURCES_SCRIPT = "script"
    SOURCES_EXEC_MODE = "exec_mode"
    SOURCES_REFRESH = "refresh"
    SOURCES_EOF_STRING = "eof_string"
    SOURCES_AUTOSTART = "autostart"

    SCREENS = "screens"
    SCREENS_COMPONENT = "component"

    DIRECTION = "direction"

    COMPONENTS = "components"
    COMPONENT_EXPLICIT_PROPERTIES = "__EXPLICIT_PROPERTIES"
    COMPONENT_CHILDREN = "children"
    COMPONENT_SOURCE = "source"
    COMPONENT_SOURCE_TYPE = "type"
    COMPONENT_SOURCE_NAME = "name"

    COMPONENT_DATA = "data"
    COMPONENT_STATIC = "static"
    COMPONENT_SOURCE_MULTILINE = "source_multiline"
    COMPONENT_SOURCE_FORMAT = "source_format"
    COMPONENT_OUTPUT_FORMAT = "output_format"
    COMPONENT_TRANSFORM = "transform"
    COMPONENT_TRANSFORM_FUNCTION = "function"
    COMPONENT_TRANSFORM_IN = "in"
    COMPONENT_TRANSFORM_OUT = "out"

    TAG_SOURCE_TYPE_TEXT = "!type:text"
    TAG_SOURCE_TYPE_COMMAND = "!type:command"

    COMPONENT_PERSIST = "persist"
    COMPONENT_SIZE = "size"
    COMPONENT_PADDING = "padding"

    COMPONENT_ALIGN = "align"
    COMPONENT_ALIGN_V = "align_v"
    COMPONENT_BORDER = "border"

    COMPONENT_BORDER_COLOR = "border_color"

    COMPONENT_VISIBLE = "visible"
    COMPONENT_COLOR = "color"
    COMPONENT_BG_COLOR = "color_bg"
    COMPONENT_LABEL = "label"
    COMPONENT_PARENT = "parent"
    COMPONENT_CONTENT_RENDER = "content_render"

    COMPONENT_CONTENT_RENDER_TYPE = "type"

    COMPONENT_STYLING_FONTSIZE = "font_size"
    COMPONENT_STYLING_FONT = "font"

    COMPONENT_EDGE_TOP = "top"
    COMPONENT_EDGE_BOTTOM = "bottom"
    COMPONENT_EDGE_LEFT = "left"
    COMPONENT_EDGE_RIGHT = "right"

    NAV = "navigation"
    NAV_ROOT = "root"
    NAV_DEFAULT = "default"
    NAV_DIRECTION = "direction"
    NAV_WRAP = "wrap"
    NAV_ELEMENTS = "elements"
    NAV_ELEMENTS_TYPE = "type"
    NAV_ELEMENTS_TYPE_AXIS = "type"
    NAV_ELEMENTS_TYPE_SCREEN = "type"
    NAV_ELEMENTS_NAME = "name"
    NAV_TAG_AXIS = "!axis"

    GENERAL = "general"
    GENERAL_SLEEP_AFTER = "sleep_after"
    GENERAL_SCREEN_FPS = "screen_fps"
    GENERAL_ANIMATION = "animation"
    GENERAL_ANIMATION_FPS = "fps"
    GENERAL_ANIMATION_DELTA_X = "delta_x"
    GENERAL_ANIMATION_DELTA_Y = "delta_y"

    GENERAL_TRANSFORM = "transform"
    GENERAL_FUNCTIONS = "functions"

    GENERAL_HARDWARE = "hardware"
    GENERAL_HARDWARE_SCREEN = "screen_initializer"
    GENERAL_HARDWARE_JOYSTICK = "joystick_initializer"


def construct_text_source(loader, node):
    value = None
    if isinstance(node, ScalarNode):
        value = [loader.construct_scalar(node)]
    if isinstance(node, SequenceNode):
        value = loader.construct_sequence(node)

    return {
        Key.COMPONENT_SOURCE_TYPE: SourceType.TEXT,
        Key.COMPONENT_SOURCE_NAME: value
    }


TAGS = {
    Key.TAG_VARIABLE: lambda loader, node: Property(
        PropertyType.VARIABLE,
        loader.construct_scalar(node)
    ),
    Key.NAV_TAG_AXIS: lambda loader, node: {
        Key.NAV_ELEMENTS_TYPE: AxisElementType.AXIS,
        Key.NAV_ELEMENTS_NAME: loader.construct_scalar(node)
    },
    Key.TAG_SOURCE_TYPE_TEXT: construct_text_source,
    Key.TAG_SOURCE_TYPE_COMMAND: lambda loader, node: {
        Key.COMPONENT_SOURCE_TYPE: SourceType.COMMAND,
        Key.COMPONENT_SOURCE_NAME: loader.construct_scalar(node)
    }
}

RENDERER_TEXT = "text"
RENDERER_TEXT_LINE_SPACE = "line_space"

RENDERER_IMAGE = "image"
RENDERER_PROGRESSBAR = "progressbar"
RENDERER_PROGRESSBAR_MIN = "min"
RENDERER_PROGRESSBAR_MAX = "max"
RENDERER_PROGRESSBAR_FORMAT = "format"

RENDERER_CHART = "chart"
RENDERER_CHART_MIN = "min"
RENDERER_CHART_MAX = "max"
RENDERER_CHART_AUTOSCALE = "autoscale"
RENDERER_CHART_BACKGROUND = "background"
RENDERER_CHART_LINE_SIZE = "line_size"
RENDERER_CHART_GRID_VALUES = "grid_values"
RENDERER_CHART_GRID_TIME = "grid_time"
RENDERER_CHART_SAMPLE_COUNT = "sample_count"
RENDERER_CHART_FORMAT = "format"
RENDERER_CHART_SHOW_MAX_VAL = "show_max_value"
RENDERER_SCHEMAS = {
    RENDERER_TEXT: {
        RENDERER_TEXT_LINE_SPACE: {
            Schema.Type: int,
            Schema.Default: 0
        }
    },
    RENDERER_IMAGE: {},
    RENDERER_PROGRESSBAR: {
        RENDERER_PROGRESSBAR_MIN: {
            Schema.Type: int,
            Schema.Default: 0
        },
        RENDERER_PROGRESSBAR_MAX: {
            Schema.Type: int,
            Schema.Default: 100
        },
        RENDERER_PROGRESSBAR_FORMAT: {
            Schema.Type: str,
            Schema.Default: "{value:d}"
        }
    },
    RENDERER_CHART: {
        RENDERER_CHART_MIN: {
            Schema.Type: int,
            Schema.Default: 0
        },
        RENDERER_CHART_MAX: {
            Schema.Type: int,
            Schema.Default: 100
        },
        RENDERER_CHART_AUTOSCALE: {
            Schema.Type: bool,
            Schema.Default: False
        },
        RENDERER_CHART_BACKGROUND: {
            Schema.Type: int,
            Schema.Default: 100
        },
        RENDERER_CHART_LINE_SIZE: {
            Schema.Type: int,
            Schema.Default: 1
        },
        RENDERER_CHART_GRID_TIME: {
            Schema.Type: int,
            Schema.Default: 7
        },
        RENDERER_CHART_GRID_VALUES: {
            Schema.Type: int,
            Schema.Default: 5
        },
        RENDERER_CHART_SAMPLE_COUNT: {
            Schema.Type: int,
            Schema.Default: 20
        },
        RENDERER_CHART_FORMAT: {
            Schema.Type: str,
            Schema.Default: "{value:d}"
        },
        RENDERER_CHART_SHOW_MAX_VAL: {
            Schema.Type: bool,
            Schema.Default: False
        }
    }
}


def get_content_renderer_schema(value_type: type, traveler) -> dict:
    renderer_type = traveler.get_value("./type")
    if renderer_type is None:
        raise Exception(f"Renderer type must be set for path {traveler.get_path()}")
    if renderer_type not in RENDERER_SCHEMAS:
        raise Exception(f"Renderer type \"{renderer_type}\" cannot be validated - schema not defined")
    return RENDERER_SCHEMAS[renderer_type]


def transform_parser(config):
    value = config.get_value()
    result = []
    if type(value) is list:
        instruction_lines = []
        for line in value:
            if type(line) is dict:
                instruction_lines.append(line.popitem())
            elif type(line) is str:
                instruction_lines.append(line)
            else:
                raise Exception(f"Flowline parsing: Line \"{line}\" cannot be validated")
        print("Compiling Flowline script...")
        ast = flowline.build_ast(instruction_lines)
        print("Compilation complete")
        return ast
    return result


def component_source_parser(config) -> dict | None:
    val = config.get_value()
    if val is None:
        return {
            Key.COMPONENT_SOURCE_TYPE: None,
            Key.COMPONENT_SOURCE_NAME: None
        }
    if type(val) is str:
        return {
            Key.COMPONENT_SOURCE_TYPE: SourceType.COMMAND,
            Key.COMPONENT_SOURCE_NAME: val
        }
    return val


def component_postprocessor(config) -> dict:
    value = config.get_value()
    defined_properties = list(value.keys())
    value[Key.COMPONENT_EXPLICIT_PROPERTIES] = defined_properties
    return value


def rgb(color: int) -> str:
    return "rgb({},{},{})".format(color, color, color)


def rgba(color: int, alpha: int) -> str:
    return "rgba({},{},{},{})".format(color, color, color, alpha)


def color_parser(config) -> Property[str]:
    val = config.get_value()
    if type(val) is Property:
        return val
    color_string = "rgba(0,0,0,0)"
    if type(val) is int and val > -1:
        color_string = rgb(val)
    if isinstance(val, str):
        color_string = val
    return Property(PropertyType.VALUE, color_string)


def border_color_parser(config) -> dict:
    val = config.get_value()
    if type(val) is dict:
        return val

    color = color_parser(config)
    return {
        Key.COMPONENT_EDGE_TOP: color,
        Key.COMPONENT_EDGE_BOTTOM: color,
        Key.COMPONENT_EDGE_LEFT: color,
        Key.COMPONENT_EDGE_RIGHT: color
    }


def property_parser(config):
    value = config.get_value()
    if type(value) is Property:
        return value

    return Property(PropertyType.VALUE, value)


def border_parser(c):
    if type(c.get_value()) == int:
        return {
            Key.COMPONENT_EDGE_TOP: Property(PropertyType.VALUE, c.get_value()),
            Key.COMPONENT_EDGE_BOTTOM: Property(PropertyType.VALUE, c.get_value()),
            Key.COMPONENT_EDGE_LEFT: Property(PropertyType.VALUE, c.get_value()),
            Key.COMPONENT_EDGE_RIGHT: Property(PropertyType.VALUE, c.get_value())
        }
    elif type(c.get_value()) == Property:
        return {
            Key.COMPONENT_EDGE_TOP: c.get_value(),
            Key.COMPONENT_EDGE_BOTTOM: c.get_value(),
            Key.COMPONENT_EDGE_LEFT: c.get_value(),
            Key.COMPONENT_EDGE_RIGHT: c.get_value()
        }
    else:
        return c.get_value()


def source_format_parser(c):
    value = c.get_value()
    wildcard = None
    numbered = {}
    regex = {}
    if isinstance(value, list):
        numbered = dict(value)
    if isinstance(value, str):
        wildcard = value
    if isinstance(value, dict):
        for key, value in value.items():
            if key == "*":
                wildcard = value
                continue
            if isinstance(key, str):
                try:
                    re.compile(key)
                    regex[key] = value
                except re.error:
                    raise RuntimeError(f"Source format regex is invalid ({key})")
                continue
            if type(key) == int:
                numbered[key] = value
                continue
            raise RuntimeError(f"Source format definition is incorrect (key type = {type(key)})")
    type(value)
    return {
        SourceFormatType.NUMBERED: numbered,
        SourceFormatType.REGEX: regex,
        SourceFormatType.WILDCARD: wildcard
    }


def target_format_parser(c):
    value = c.get_value()
    if isinstance(value, str):
        return [value]
    return value


def transform_functions_parser(c: Traveler):
    file_path = c.system_path
    config_dir = os.path.dirname(file_path)
    value = c.get_value()
    return [os.path.join(config_dir, v) for v in value]


TYPES = {
    Key.COMPONENT_CHILDREN: {
        Schema.Type: dict,
        Schema.Required: False,
        Schema.Schema: {
            Schema.Wildcard: {
                Schema.Type: dict,
                Schema.ValueParser: component_postprocessor,
                Schema.Schema: {
                    Key.COMPONENT_PARENT: {
                        Schema.Type: str,
                        Schema.Default: None
                    },
                    Key.COMPONENT_CONTENT_RENDER: {
                        Schema.Type: [str, dict],
                        Schema.Default: None,
                        Schema.ValueParser: lambda c: {
                            Key.COMPONENT_CONTENT_RENDER_TYPE: c.get_value()
                        } if type(c.get_value()) == str else c.get_value(),
                        Schema.Schema: {
                            Key.COMPONENT_CONTENT_RENDER_TYPE: {
                                Schema.Type: str
                            }
                        },
                        Schema.SchemaCallback: get_content_renderer_schema
                    },
                    Key.COMPONENT_DATA: {
                        Schema.Type: dict,
                        Schema.Default: {Key.COMPONENT_SOURCE: None},
                        Schema.Schema: {
                            Key.COMPONENT_SOURCE: {
                                Schema.Type: [str, dict],
                                Schema.Default: None,
                                Schema.ValueParser: component_source_parser,
                            },
                            Key.COMPONENT_STATIC: {
                                Schema.Type: dict,
                                Schema.Default: {}
                            },
                            Key.COMPONENT_SOURCE_MULTILINE: {
                                Schema.Type: bool,
                                Schema.Default: False
                            },
                            Key.COMPONENT_SOURCE_FORMAT: {
                                Schema.Type: [str, dict],
                                Schema.ValueParser: source_format_parser,
                                Schema.Default: []
                            },
                            Key.COMPONENT_OUTPUT_FORMAT: {
                                Schema.Type: [str, list],
                                Schema.ValueParser: target_format_parser,
                                Schema.Default: None
                            },
                            Key.COMPONENT_TRANSFORM: {
                                Schema.Type: list,
                                Schema.Default: [],
                                Schema.ValueParser: transform_parser
                            }
                        }
                    },

                    Key.COMPONENT_PERSIST: {
                        Schema.Type: bool,
                        Schema.Default: False
                    },
                    Key.DIRECTION: {
                        Schema.Type: Direction,
                        Schema.Default: Direction.ROW
                    },
                    Key.COMPONENT_SIZE: {
                        Schema.Type: [int, str],
                        Schema.Default: None
                    },
                    Key.COMPONENT_PADDING: {
                        Schema.Type: [int, dict],
                        Schema.Default: 0,
                        Schema.ValueParser: lambda c: {
                            Key.COMPONENT_EDGE_TOP: c.get_value(),
                            Key.COMPONENT_EDGE_BOTTOM: c.get_value(),
                            Key.COMPONENT_EDGE_LEFT: c.get_value(),
                            Key.COMPONENT_EDGE_RIGHT: c.get_value()
                        } if type(c.get_value()) == int else c.get_value(),
                        Schema.Schema: {
                            Key.COMPONENT_EDGE_TOP: {
                                Schema.Type: int,
                                Schema.Default: 0
                            },
                            Key.COMPONENT_EDGE_BOTTOM: {
                                Schema.Type: int,
                                Schema.Default: 0
                            },
                            Key.COMPONENT_EDGE_LEFT: {
                                Schema.Type: int,
                                Schema.Default: 0
                            },
                            Key.COMPONENT_EDGE_RIGHT: {
                                Schema.Type: int,
                                Schema.Default: 0
                            }
                        }
                    },
                    Key.COMPONENT_ALIGN: {
                        Schema.Type: [Align, Property],
                        Schema.Default: Align.LEFT,
                        Schema.ValueParser: property_parser
                    },
                    Key.COMPONENT_ALIGN_V: {
                        Schema.Type: [AlignV, Property],
                        Schema.Default: AlignV.TOP,
                        Schema.ValueParser: property_parser
                    },
                    Key.COMPONENT_BORDER: {
                        Schema.Type: [int, dict, Property],
                        Schema.Default: 0,
                        Schema.ValueParser: border_parser,
                        Schema.Schema: {
                            Key.COMPONENT_EDGE_TOP: {
                                Schema.Type: [int, Property],
                                Schema.Default: Property(PropertyType.VALUE, 0),
                                Schema.ValueParser: property_parser
                            },
                            Key.COMPONENT_EDGE_BOTTOM: {
                                Schema.Type: [int, Property],
                                Schema.Default: Property(PropertyType.VALUE, 0),
                                Schema.ValueParser: property_parser
                            },
                            Key.COMPONENT_EDGE_LEFT: {
                                Schema.Type: [int, Property],
                                Schema.Default: Property(PropertyType.VALUE, 0),
                                Schema.ValueParser: property_parser
                            },
                            Key.COMPONENT_EDGE_RIGHT: {
                                Schema.Type: [int, Property],
                                Schema.Default: Property(PropertyType.VALUE, 0),
                                Schema.ValueParser: property_parser
                            }
                        }
                    },
                    Key.COMPONENT_BORDER_COLOR: {
                        Schema.Type: [int, str, dict, Property],
                        Schema.Default: Property(PropertyType.VALUE, rgb(255)),
                        Schema.ValueParser: border_color_parser,
                        Schema.Schema: {
                            Key.COMPONENT_EDGE_TOP: {
                                Schema.Type: [int, str, Property],
                                Schema.Default: Property(PropertyType.VALUE, 0),
                                Schema.ValueParser: color_parser,
                            },
                            Key.COMPONENT_EDGE_BOTTOM: {
                                Schema.Type: [int, str, Property],
                                Schema.Default: Property(PropertyType.VALUE, 0),
                                Schema.ValueParser: color_parser,
                            },
                            Key.COMPONENT_EDGE_LEFT: {
                                Schema.Type: [int, str, Property],
                                Schema.Default: Property(PropertyType.VALUE, 0),
                                Schema.ValueParser: color_parser,
                            },
                            Key.COMPONENT_EDGE_RIGHT: {
                                Schema.Type: [int, str, Property],
                                Schema.Default: Property(PropertyType.VALUE, 0),
                                Schema.ValueParser: color_parser,
                            }
                        }
                    },
                    Key.COMPONENT_VISIBLE: {
                        Schema.Type: [bool, Property],
                        Schema.Default: Property(PropertyType.VALUE, True)
                    },
                    Key.COMPONENT_COLOR: {
                        Schema.Type: [int, str, Property],
                        Schema.Default: Property(PropertyType.VALUE, rgb(150)),
                        Schema.ValueParser: color_parser
                    },
                    Key.COMPONENT_BG_COLOR: {
                        Schema.Type: [int, str, Property],
                        Schema.Default: Property(PropertyType.VALUE, rgba(0, 0)),
                        Schema.ValueParser: color_parser
                    },
                    Key.COMPONENT_STYLING_FONTSIZE: {
                        Schema.Type: [int, Property],
                        Schema.Default: Property(PropertyType.VALUE, 8),
                        Schema.ValueParser: property_parser
                    },
                    Key.COMPONENT_STYLING_FONT: {
                        Schema.Type: str,
                        Schema.Default: None
                    },
                    Key.COMPONENT_CHILDREN: {
                        Schema.ReferenceType: Key.COMPONENT_CHILDREN
                    }
                }
            }
        }
    }
}

SCHEMA = {
    Schema.Type: dict,
    Schema.Schema: {
        Key.SOURCES: {
            Schema.Type: dict,
            Schema.Schema: {
                Schema.Wildcard: {
                    Schema.Type: dict,
                    Schema.Schema: {
                        Key.SOURCES_SCRIPT: {
                            Schema.Type: list
                        },
                        Key.SOURCES_EXEC_MODE: {
                            Schema.Type: ExecMode.ExecMode,
                        },
                        Key.SOURCES_REFRESH: {
                            Schema.Type: [float, int],
                            Schema.RequiredValidator: lambda v:
                            v.get_value("./" + Key.SOURCES_EXEC_MODE) == ExecMode.ExecMode.REPEAT,
                            Schema.Default: 1
                        },
                        Key.SOURCES_EOF_STRING: {
                            Schema.Type: str,
                            Schema.Default: None
                        },
                        Key.SOURCES_AUTOSTART: {
                            Schema.Type: bool,
                            Schema.Default: False
                        }
                    }
                }
            }
        },
        Key.SCREENS: {
            Schema.Type: dict,
            Schema.Schema: {
                Schema.Wildcard: {
                    Schema.Type: dict,
                    Schema.Schema: {
                        Key.COMPONENT_LABEL: {
                            Schema.Type: str,
                            Schema.Default: None
                        },
                        Key.SCREENS_COMPONENT: {
                            Schema.Type: [dict, str],
                            Schema.Required: True,
                            Schema.MaxElements: 1,
                            Schema.ReferenceType: Key.COMPONENT_CHILDREN
                        }
                    }
                }
            }
        },
        Key.NAV: {
            Schema.Type: dict,
            Schema.Schema: {
                Schema.Wildcard: {
                    Schema.Type: dict,
                    Schema.Schema: {
                        Key.NAV_ROOT: {
                            Schema.Type: bool,
                            Schema.Default: False
                        },
                        Key.NAV_DEFAULT: {
                            Schema.Type: str,
                            Schema.Default: None
                        },
                        Key.NAV_WRAP: {
                            Schema.Type: bool,
                            Schema.Default: True
                        },
                        Key.NAV_DIRECTION: {
                            Schema.Type: Direction,
                            Schema.Default: Direction.ROW
                        },
                        Key.NAV_ELEMENTS: {
                            Schema.Type: list,
                            Schema.Default: [],
                            Schema.Schema: {
                                Schema.Type: [dict, str],
                                Schema.ValueParser: lambda v: {
                                    Key.NAV_ELEMENTS_TYPE: AxisElementType.SCREEN,
                                    Key.NAV_ELEMENTS_NAME: v.get_value()
                                } if type(v.get_value()) is str else v.get_value(),
                            }
                        }
                    }
                }
            }
        },
        Key.COMPONENTS: {
            Schema.Type: dict,
            Schema.ReferenceType: Key.COMPONENT_CHILDREN
        },
        Key.GENERAL: {
            Schema.Type: dict,
            Schema.Schema: {
                Key.GENERAL_SLEEP_AFTER: {
                    Schema.Type: int,
                    Schema.Default: 0
                },
                Key.GENERAL_SCREEN_FPS: {
                    Schema.Type: int,
                    Schema.Default: 10,
                    Schema.ValueValidator: lambda v: (False, "Fps can't be less than 1") if v.get_value() < 1 else (
                        True, None)
                },
                Key.GENERAL_ANIMATION: {
                    Schema.Type: dict,
                    Schema.Default: {
                        Key.GENERAL_ANIMATION_FPS: 30,
                        Key.GENERAL_ANIMATION_DELTA_X: 30,
                        Key.GENERAL_ANIMATION_DELTA_Y: 10,
                    },
                    Schema.Schema: {
                        Key.GENERAL_ANIMATION_FPS: {
                            Schema.Type: int,
                            Schema.Default: 30,
                            Schema.ValueValidator: lambda v: (False,
                                                              "Fps can't be less than 1") if v.get_value() < 1 else (
                                True, None)
                        },
                        Key.GENERAL_ANIMATION_DELTA_X: {
                            Schema.Type: int,
                            Schema.Default: 30,
                        },
                        Key.GENERAL_ANIMATION_DELTA_Y: {
                            Schema.Type: int,
                            Schema.Default: 10,
                        }
                    }
                },
                Key.GENERAL_HARDWARE: {
                    Schema.Type: dict,
                    Schema.Default: {
                        Key.GENERAL_HARDWARE_SCREEN: None,
                        Key.GENERAL_HARDWARE_JOYSTICK: None
                    },
                    Schema.Schema: {
                        Key.GENERAL_HARDWARE_SCREEN: {
                            Schema.Type: str,
                            Schema.Default: None
                        },
                        Key.GENERAL_HARDWARE_JOYSTICK: {
                            Schema.Type: str,
                            Schema.Default: None
                        },
                    }
                },
                Key.GENERAL_TRANSFORM: {
                    Schema.Type: dict,
                    Schema.Schema: {
                        Key.GENERAL_FUNCTIONS: {
                            Schema.Type: list,
                            Schema.Default: [],
                            Schema.ValueParser: transform_functions_parser
                        }
                    }
                }
            }
        }
    }
}
