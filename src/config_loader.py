import typing

import yaml
import os
import enum
from copy import deepcopy

from .config import path_matching
from .config.config_field import ConfigField
from .config_loader_schema import Keys as SchemaKeys, AutoDefault

_path_divider = "/"
_path_current = '.'
_path_parent = '..'


class Traveler:
    _ROOT_PATH = ['']
    _path = ['']
    _data = {}

    def __init__(self, data):
        self._data = data
        self.system_path = ''

    def get_value(self, path=None, default=None):
        path = self.get_path(path).lstrip(_path_divider).split(_path_divider)
        element = self._data
        for p in path:
            if len(p) == 0:
                continue
            if type(element) is list:
                try:
                    p = int(p)
                    if p < 0 or p >= len(element):
                        return default
                    element = element[p]
                    continue
                except ValueError:
                    return default
            if p not in element:
                return default
            element = element[p]
        return element

    def set_value(self, value):
        path = [p for p in self.get_path().lstrip(_path_divider).split(_path_divider) if p]
        if not path:
            return
        element = self._data
        for p in path[:-1]:
            if type(element) is list:
                element = element[int(p)]
            else:
                element = element[p]
        last = path[-1]
        if type(element) is list:
            element[int(last)] = value
        else:
            element[last] = value

    def get_path(self, modifier=None):
        if modifier is None:
            result = self._path
        else:
            modifier_stack = modifier.split(_path_divider)
            path_copy = self._path.copy()
            for element in modifier_stack:
                if element == _path_current:
                    continue
                if element == _path_parent:
                    path_copy.pop()
                    continue
                path_copy.append(element)
            result = path_copy
        return _path_divider.join(result)

    def step_into(self, element_key):
        self._path.append(element_key)

    def step_out(self):
        self._path.pop()


class Loader:
    def __init__(self, file_names=("config.yaml", "config.yml"), file_directory: None | str | list[str] = None):
        self._file_names = file_names
        if file_directory is None:
            self._file_directory = [os.getcwd()]
            print(f"Config directory not set, using CWD: {self._file_directory}")
        else:
            self._file_directory = file_directory if type(file_directory) is list else [file_directory]
            print(f"Config directory set to: {self._file_directory}")
        self._reference_types = {}
        self._tag_parsers = {}
        self._full_config_path = None
        self._defines_paths: list[str] = []

    def set_defines_paths(self, paths: list[str]):
        self._defines_paths = paths

    def set_tag_parsers(self, parsers: dict):
        self._tag_parsers = parsers

    def set_reference_types(self, types: dict):
        self._reference_types = types

    def get_config_file_path(self):
        if self._full_config_path is None:
            for filename in self._file_names:
                full_path = os.path.join(*self._file_directory, filename)
                if os.path.exists(full_path):
                    self._full_config_path = full_path
                    print(f"Using main config file: {full_path}")
                    return full_path
            raise FileNotFoundError("No configuration file found", self._file_names, "in directory",
                                    self._file_directory)
        return self._full_config_path

    def load_config(self, schema=None):
        if schema is None:
            schema = {}
        config_path = self.get_config_file_path()
        loader = yaml.SafeLoader
        self._register_tag_parsers(loader)
        full_config = self._single_config_file_load(loader, config_path)
        if schema is not None:
            self.check_config(full_config, schema)
            return self.prepare_config(full_config, schema, config_path)
        return full_config

    def _single_config_file_load(self, loader, path: str):
        result = {}
        print(f"Loading config from file: {path}")
        file_dir = os.path.dirname(os.path.abspath(path))

        class _FileLoader(loader):
            pass
        _FileLoader.add_constructor(
            '!cwd',
            lambda l, node: os.path.join(file_dir, l.construct_scalar(node))
        )

        with open(path, "r", encoding="utf-8") as f:
            try:
                config = yaml.load(f, Loader=_FileLoader)
                result.update(config)
                if SchemaKeys.Include in config and config[SchemaKeys.Include] is not None:
                    for include_path in config[SchemaKeys.Include]:
                        include_path = os.path.join(os.path.dirname(path), include_path)
                        include_config = self._single_config_file_load(loader, include_path)
                        result.update(include_config)
                    del result[SchemaKeys.Include]
                return result
            except yaml.YAMLError as e:
                raise RuntimeError(f"Error parsing {path}: {e}")

    def check_config(self, config_data, schema):
        config_traveler = Traveler(config_data)
        self._recurrent_config_check(config_traveler, schema)
        print("== Configuration Verified ==")

    def _recurrent_config_check(self, config, schema):
        print(f"Checking {config.get_path()}")
        schema = self.get_reference_type(schema)

        self._check_field_type(config, schema)
        self._check_field_value(config, schema)
        self._load_dynamic_subschema(config, schema)
        if type(config.get_value()) is list and SchemaKeys.Schema in schema:
            if SchemaKeys.MaxElements in schema and len(config.get_value()) > schema[SchemaKeys.MaxElements]:
                max_elems = schema[SchemaKeys.MaxElements]
                raise RuntimeError(
                    f"Config schema mismatch; Max element count ({max_elems}) exceeded for path: {config.get_path()}")
            index = 0
            for subdata in config.get_value():
                config.step_into(str(index))
                self._recurrent_config_check(config, schema[SchemaKeys.Schema])
                config.step_out()
                index += 1
        if type(config.get_value()) is dict and SchemaKeys.Schema in schema:  # Check dictionary children
            if SchemaKeys.MaxElements in schema and len(config.get_value()) > schema[SchemaKeys.MaxElements]:
                max_elems = schema[SchemaKeys.MaxElements]
                raise RuntimeError(
                    f"Config schema mismatch; Max element count ({max_elems}) exceeded for path: {config.get_path()}")
            wildcard_present = False
            wildcard_omit = []
            for key, sub_schema in schema[SchemaKeys.Schema].items():  # For text keys
                if key == SchemaKeys.Wildcard:
                    wildcard_present = True
                    continue
                sub_schema = self.get_reference_type(sub_schema)
                if key not in config.get_value():
                    if Loader._is_key_required(config, sub_schema):
                        raise RuntimeError(
                            f"Config schema mismatch; Missing key \"{key}\" for path: {config.get_path()}")
                    continue
                wildcard_omit.append(key)  # Let's skip explicitly defined keys in wildcard checks
                config.step_into(key)
                self._recurrent_config_check(config, sub_schema)
                config.step_out()
            if wildcard_present:
                sub_schema = schema[SchemaKeys.Schema][SchemaKeys.Wildcard]
                for key, subdata in config.get_value().items():  # For wildcard - all keys
                    if key in wildcard_omit: continue  # Skip explicitly defined keys
                    config.step_into(key)
                    self._recurrent_config_check(config, sub_schema)
                    config.step_out()
            else:
                extra_keys = list(set(config.get_value().keys()) ^ set(wildcard_omit))
                if len(extra_keys) > 0:
                    raise RuntimeError(
                        f"Config schema mismatch, found unexpected keys {extra_keys} in {config.get_path()}")

    def _check_field_value(self, config, schema: dict):
        if SchemaKeys.ValueValidator in schema:  # Check with custom validator
            (valid, message) = schema[SchemaKeys.ValueValidator](config)
            if not valid:
                raise RuntimeError(f"Config schema mismatch for path: {config.get_path()}. Message: {message}")

    def _parse_field_value(self, config, schema: dict):
        if SchemaKeys.ValueParser in schema:  # Parse with custom function
            return True, schema[SchemaKeys.ValueParser](config)
        return False, None

    def _load_dynamic_subschema(self, config, schema):
        if SchemaKeys.SchemaCallback in schema:
            value_type = type(config.get_value())
            schema_schema = schema[SchemaKeys.Schema] or {}
            dynamic_schema = schema[SchemaKeys.SchemaCallback](value_type, config)
            if type(dynamic_schema) is dict:
                schema_schema.update(dynamic_schema)
                schema[SchemaKeys.Schema] = schema_schema

    def get_reference_type(self, schema: dict):
        result = deepcopy(schema)
        if SchemaKeys.ReferenceType in result:
            referenced_type_name = result[SchemaKeys.ReferenceType]
            if referenced_type_name not in self._reference_types:
                raise RuntimeError(f"Unknown reference type: {referenced_type_name}")
            referenced_type = deepcopy(self._reference_types[referenced_type_name])
            for key, value in result.items():
                if key is not SchemaKeys.ReferenceType:
                    referenced_type[key] = value
            return referenced_type

        return result

    def prepare_config(self, config, schema, system_path):
        print(f"== Preparing config ==")
        print(f" - Adding lists of defined properties")
        self._add_field_index(config, self._defines_paths)
        traveler = Traveler(config)
        traveler.system_path = system_path
        self._recursive_prepare_config(traveler, schema)
        return config

    def _recursive_prepare_config(self, traveler, original_schema):
        print(f"Preparing {traveler.get_path()}")
        schema = self.get_reference_type(original_schema)
        update_value, new_value = self._parse_field_value(traveler, schema)
        if update_value:
            traveler.set_value(new_value)
        if type(traveler.get_value()) is list and SchemaKeys.Schema in schema:
            index = 0
            for subdata in traveler.get_value():
                traveler.step_into(str(index))
                self._recursive_prepare_config(traveler, schema[SchemaKeys.Schema])
                traveler.step_out()
                index += 1
        if type(traveler.get_value()) is dict and SchemaKeys.Schema in schema:
            wildcard_present = False
            wildcard_omit = []
            for key, sub_schema in schema[SchemaKeys.Schema].items():  # For text keys
                construct_auto_default = False
                if key == SchemaKeys.Wildcard:
                    wildcard_present = True
                    continue
                sub_schema = self.get_reference_type(sub_schema)
                if key not in traveler.get_value():
                    if SchemaKeys.Default in sub_schema:
                        if sub_schema[SchemaKeys.Default] is AutoDefault:
                            print(f"Constructing auto default value for {traveler.get_path(key)}")
                            construct_auto_default = True
                        else:
                            print(f"Set default value for {traveler.get_path(key)} -> \"{sub_schema[SchemaKeys.Default]}\"")
                            traveler.get_value()[key] = deepcopy(sub_schema[SchemaKeys.Default])  # set default value
                else:
                    print(f"Value present for {traveler.get_path(key)} -> \"{traveler.get_value()[key]}\"")
                required_type = sub_schema[SchemaKeys.Type]
                if isinstance(required_type, type) and issubclass(required_type, enum.Enum):
                    print(f"Convert value for enum for {traveler.get_path(key)}")
                    traveler.get_value()[key] = sub_schema[SchemaKeys.Type](traveler.get_value()[key])
                wildcard_omit.append(key)  # Let's skip explicitly defined keys in wildcartyped checks
                traveler.step_into(key)
                self._recursive_prepare_config(traveler, sub_schema)
                if construct_auto_default:
                    pass #TODO implement auto construction of default value, based on schema
                traveler.step_out()

            if wildcard_present:
                sub_schema = schema[SchemaKeys.Schema][SchemaKeys.Wildcard]
                for key, subdata in traveler.get_value().items():  # For wildcard - all keys
                    if key in wildcard_omit: continue  # Skip explicitly defined keys
                    traveler.step_into(key)
                    self._recursive_prepare_config(traveler, sub_schema)
                    traveler.step_out()

    def _check_field_matches(self, data, expected) -> bool:
        if isinstance(expected, (list, tuple)):
            return any(self._check_field_matches(data, e) for e in expected)

        if isinstance(expected, type) and issubclass(expected, enum.Enum):
            return isinstance(data, expected) or data in [e.value for e in expected]

        return isinstance(data, expected)

    def _check_field_describe(self, expected) -> str:
        if isinstance(expected, (list, tuple)):
            return " | ".join(self._check_field_describe(e) for e in expected)

        if isinstance(expected, type) and issubclass(expected, enum.Enum):
            values = ", ".join(repr(e.value) for e in expected)
            return f"{expected.__name__} ({values})"

        return getattr(expected, "__name__", repr(expected))

    def _check_field_type(self, traveler, schema):
        required_types = schema[SchemaKeys.Type]
        if type(required_types) is not list:
            required_types = [required_types]
        data = traveler.get_value()
        path = traveler.get_path()
        if not any(self._check_field_matches(data, t) for t in required_types):
            raise RuntimeError(
                f"Config schema mismatch for path: {path}. "
                f"Expected: {self._check_field_describe(required_types)}; "
                f"got: {type(data).__name__} ({data!r})"
            )

    @staticmethod
    def _is_key_required(traveler, schema):
        if SchemaKeys.Default in schema:
            return False
        else:
            if SchemaKeys.RequiredValidator in schema:
                return schema[SchemaKeys.RequiredValidator](traveler)
            if SchemaKeys.Required in schema:
                return schema[SchemaKeys.Required]
            return True

    def _register_tag_parsers(self, yaml_loader):
        for tag_name, parser in self._tag_parsers.items():
            yaml_loader.add_constructor(tag_name, parser)

    def _is_path_in_list(self, path: str, define_paths: list[str]) -> bool:
        if path == '':
            path = "/"
        for pattern in define_paths:
            if len(path_matching.find_matching_paths([path], pattern)) > 0:
                return True
        return False

    def _add_field_index(self, config: dict, define_paths, path = ''):
        if self._is_path_in_list(path, define_paths):
            config['__defined'] = list(config.keys())
        for key, value in config.items():
            if type(value) is dict:
                self._add_field_index(value, define_paths, path + "/" + key)

    @staticmethod
    def load_fields(obj, data: dict):
        hints = typing.get_type_hints(type(obj), include_extras=True)
        for attr_name, annotation in hints.items():
            if typing.get_origin(annotation) is not typing.Annotated:
                continue
            _, *extras = typing.get_args(annotation)
            meta = next((e for e in extras if isinstance(e, ConfigField)), None)
            if meta is None:
                continue
            if isinstance(meta.key, str):
                value = data.get(meta.key, meta.default)
            else:
                current = data
                for k in meta.key:
                    if not isinstance(current, dict) or k not in current:
                        current = meta.default
                        break
                    current = current[k]
                value = current
            setattr(obj, attr_name, value)