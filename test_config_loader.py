import os
import json
import pprint

from src.config_loader import Loader
import src.screens_schema as screens_schema

dir_path = os.path.dirname(os.path.realpath(__file__))

loader = Loader([dir_path+"/../config/config.yaml"])
loader.set_reference_types(screens_schema.TYPES)
loader.set_tag_parsers(screens_schema.TAGS)
config = loader.load_config(schema=screens_schema.SCHEMA)
print("=== CONFIG LOADED ===")
pprint.pprint(config, indent=2)