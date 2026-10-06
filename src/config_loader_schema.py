from enum import Enum


class AutoDefault:
    pass

class Keys:
    Include = "include"
    Type = "type"
    ReferenceType = "referenceType"

    Schema = "schema"
    SchemaCallback = "schema_callback"
    Wildcard = "*"
    ValueValidator = "value_validator"
    ValueParser = "value_parser"
    RequiredValidator = "required_validator"
    Required = "required"
    MaxElements = "max_elements"
    Default = "default"
