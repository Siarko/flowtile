import src.component_registry as component_registry
import src.data_source_collection as DataSourceCollection
import src.screens as screens
from src.data_source import DataSource
from src.screens import Component
from src.screens_schema import Key, SourceType


def _prepare_static_component_source(name: str, data: dict):
    data_section = data[Key.COMPONENT_DATA]
    source_section = data_section[Key.COMPONENT_SOURCE]
    if type(source_section) is dict:
        if source_section[Key.COMPONENT_SOURCE_TYPE] == SourceType.TEXT:
            source_name = "text.component." + name
            static_data_source = DataSource(source_name)
            static_data_source.set_content(source_section[Key.COMPONENT_SOURCE_NAME])
            DataSourceCollection.register(static_data_source)
            source_section[Key.COMPONENT_SOURCE_NAME] = source_name


def _load_screens(screens_config: dict) -> screens.ScreenManager:
    manager = screens.ScreenManager()
    for screen_id, screen_data in screens_config.items():
        print(f"\tLoading screen {screen_id}")
        screen = screens.Screen(screen_id)
        screen.label = screen_data[Key.COMPONENT_LABEL]
        screen_component = screen_data[Key.SCREENS_COMPONENT]
        if len(screen_component) == 1 or type(screen_component) is str:
            if type(screen_component) is str:
                component_id = screen_component
            else:
                component_id = next(iter(screen_data[Key.SCREENS_COMPONENT]))
            screen.set_component(component_id)
            print(f"\t\tAdded component {component_id}")
        manager.add_screen(screen)
    return manager


def setup(config: dict, config_loader) -> screens.ScreenManager:
    print("=== LOADING SCREENS ===")

    def allocate_component(name: str, data: dict) -> Component:
        c = Component(name)
        _prepare_static_component_source(name, data)
        config_loader.load_fields(c, data)
        c.fields_loaded()
        return c

    component_registry.load_components(config, allocate_component)
    return _load_screens(config[Key.SCREENS])
