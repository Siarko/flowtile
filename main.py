import copy
import os
import sys
import time

from functools import partial
from queue import Empty

from luma.core.render import canvas

import src.ExecMode as ExecMode
import src.command_runner as command_runner
from src import screen_navigation
from src.controll_sequence_manager import ControlSequenceManager
from src.game_loop import GameLoop
from src.data_source import DataSource
from src.hardware import device_provider
from src.screen_animation import ScreenAnimation
from src.screen_navigation import NavigationDirection, ScreenNavigation
from src.screen_sleep import ScreenSleep
from src.command_runner import ControlCommand
from src.modal_renderer import ModalRenderer, ModalType
import src.config_loader as ConfigLoader
from src.joystick import Joystick
import src.screens as screens
import src.hardware.device_provider

import src.data_source_collection as DataSourceCollection

import src.component_registry as component_registry
from src.screens import Component

from src.screens_schema import Key as SchemaKeys, Key, SourceType
from src.screens_schema import SCHEMA as CONFIG_SCHEMA
from src.screens_schema import TYPES as REFERENCE_TYPES
from src.screens_schema import TAGS as CONFIG_TAG_PARSERS

import src.transform.registry as function_registry

# Initializer imports - import files just to initialize them
# Do not remove

import src.hardware.default.screen  # Default screen provider
import src.hardware.default.joystick  # Default joystick provider

import src.render.text
import src.render.image
import src.render.progressbar
import src.render.chart

config_dir = [os.path.dirname(__file__), '..', 'config']
command_dir = os.path.join(*config_dir)

game_loop = GameLoop()


def on_process_stop(runner: command_runner.CommandRunner, event_type: command_runner.ProcessEvent, command_id: str):
    last_error_code = runner.get_exit_code(command_id)
    if last_error_code != 0:
        print(f"Process {command_id} errored with code {last_error_code}")
        error_queue = runner.get_error_output(command_id)
        try:
            while True:
                line: bytes = error_queue.get_nowait()
                print(f"  [{command_id}] {line.decode('utf-8', errors='replace')}")
        except Empty:
            pass


def load_commands(commands_data: dict, runner: command_runner.CommandRunner):
    for command_id, command_data in commands_data.items():
        interval = None
        eof_string = command_data[SchemaKeys.SOURCES_EOF_STRING]
        if command_data[SchemaKeys.SOURCES_EXEC_MODE] == ExecMode.ExecMode.REPEAT:
            interval = command_data[SchemaKeys.SOURCES_REFRESH]
        runner.add_command(
            command_id=command_id,
            command=command_data[SchemaKeys.SOURCES_SCRIPT],
            interval=interval,
            eof_string=eof_string
        )
        print(f"Added command {command_id}")
        print(f"\tCommand ID: {command_id}")
        print(f"\tCommand: {command_data[SchemaKeys.SOURCES_SCRIPT]}")
        print(f"\tExec Mode: {command_data[SchemaKeys.SOURCES_EXEC_MODE]}")
        print(f"\tInterval: {interval}")
        print(f"\tEOF: {eof_string}")
    runner.add_process_event_handler(
        command_runner.ProcessEvent.STOP,
        partial(on_process_stop, runner)
    )


def start_commands(commands_data: dict, runner: command_runner.CommandRunner):
    for command_id, command_data in commands_data.items():
        if not command_data[SchemaKeys.SOURCES_AUTOSTART]:
            continue
        runner.process_start(command_id)
        print(f"Started boot command {command_id}")


should_run = True


def construct_screen_manage_handler(runner: command_runner.CommandRunner):
    def manage_screen_commands(old_screen: screens.Screen | None, new_screen: screens.Screen):
        if old_screen is not None:
            print(f"Unloading processes for screen {old_screen.screen_id}")
            for command in old_screen.get_all_commands():
                if not command["persistent"]:
                    runner.process_stop(command["name"])
        print(f"Loading processes for screen {new_screen.screen_id}")
        for command in new_screen.get_all_commands():
            runner.process_start(command["name"])

    return manage_screen_commands


def load_screens(config: dict):
    manager = screens.ScreenManager()
    for screen_id, screen_data in config.items():
        print(f"\tLoading screen {screen_id}")
        screen = screens.Screen(screen_id)
        screen.label = screen_data[SchemaKeys.COMPONENT_LABEL]
        screen_component = screen_data[SchemaKeys.SCREENS_COMPONENT]
        if len(screen_component) == 1 or type(screen_component) is str:
            if type(screen_component) is str:
                component_id = screen_component
            else:
                component_id = next(iter(screen_data[SchemaKeys.SCREENS_COMPONENT]))
            screen.set_component(component_id)
            print(f"\t\tAdded component {component_id}")
        manager.add_screen(screen)
    return manager


def main():
    runner = command_runner.CommandRunner()
    runner.set_cwd(command_dir)
    print("=== PREPARING CONFIG ===")
    config_loader = ConfigLoader.Loader(file_directory=config_dir)
    config_loader.set_reference_types(REFERENCE_TYPES)
    config_loader.set_tag_parsers(CONFIG_TAG_PARSERS)
    config = config_loader.load_config(schema=CONFIG_SCHEMA)
    print("=== CONFIG LOADED ===")
    print(config)
    game_loop.set_target_fps(config[SchemaKeys.GENERAL][SchemaKeys.GENERAL_SCREEN_FPS])
    game_loop.set_animation_fps(
        config[SchemaKeys.GENERAL][SchemaKeys.GENERAL_ANIMATION][SchemaKeys.GENERAL_ANIMATION_FPS])
    print("=== LOADING COMMANDS ===")
    load_commands(config[SchemaKeys.SOURCES], runner)
    start_commands(config[SchemaKeys.SOURCES], runner)
    print("=== LOADING SCREENS ===")
    function_registry.load_user_functions(
        config[SchemaKeys.GENERAL][SchemaKeys.GENERAL_TRANSFORM][SchemaKeys.GENERAL_FUNCTIONS])

    def prepare_static_component_source(name, data):
        data_section = data[Key.COMPONENT_DATA]
        source_section = data_section[Key.COMPONENT_SOURCE]
        if type(source_section) is dict:
            if source_section[Key.COMPONENT_SOURCE_TYPE] == SourceType.TEXT:
                source_name = "text.component." + name
                static_data_source = DataSource(source_name)
                static_data_source.set_content(source_section[Key.COMPONENT_SOURCE_NAME])
                DataSourceCollection.register(static_data_source)
                source_section[Key.COMPONENT_SOURCE_NAME] = source_name

    def allocate_component(name, data):
        c = Component(name)
        prepare_static_component_source(name, data)
        config_loader.load_fields(c, data)
        c.fields_loaded()

        return c

    component_registry.load_components(config, allocate_component)

    screen_manager = load_screens(config[SchemaKeys.SCREENS])
    screen_navigator = screen_navigation.load_from_config(config[SchemaKeys.NAV])
    screen_manager.set_home_screen(screen_navigator.get_home_screen())

    def screen_switch_handler(screen, direction: NavigationDirection):
        game_loop.set_animation_mode(True)
        screen_manager.set_current_screen(screen)
        if screen_manager.previous_screen != screen_manager.current_screen:
            animation_config = config[SchemaKeys.GENERAL][SchemaKeys.GENERAL_ANIMATION]
            x = 0
            y = 0
            match direction:
                case NavigationDirection.LEFT:
                    x = animation_config[SchemaKeys.GENERAL_ANIMATION_DELTA_X]
                case NavigationDirection.RIGHT:
                    x = -animation_config[SchemaKeys.GENERAL_ANIMATION_DELTA_X]
                case NavigationDirection.UP:
                    y = -animation_config[SchemaKeys.GENERAL_ANIMATION_DELTA_Y]
                case _:
                    y = animation_config[SchemaKeys.GENERAL_ANIMATION_DELTA_Y]

            screen_manager.set_screen_animation(ScreenAnimation(x, y))

    screen_navigator.set_screen_handler(screen_switch_handler)

    print("=== PREPARING DEVICES ===")
    user_screen_initializer = config.get(Key.GENERAL, {}).get(Key.GENERAL_HARDWARE, {}).get(Key.GENERAL_HARDWARE_SCREEN,
                                                                                            None)
    user_joystick_initializer = config.get(Key.GENERAL, {}).get(Key.GENERAL_HARDWARE, {}).get(
        Key.GENERAL_HARDWARE_JOYSTICK, None)
    device_provider_dir_cwd = os.path.join(*config_dir)
    device_provider.load_user_initializer_path(user_screen_initializer, device_provider_dir_cwd)
    device_provider.load_user_initializer_path(user_joystick_initializer, device_provider_dir_cwd)

    screen_initializer = device_provider.get_device_initializer(device_provider.DeviceType.SCREEN)
    print(f"Initializing screen with \"{screen_initializer.get_name()}\" initializer")
    device = screen_initializer.initialize()

    joystick_initializer = device_provider.get_device_initializer(device_provider.DeviceType.JOYSTICK)
    print(f"Initializing joystick with \"{joystick_initializer.get_name()}\" initializer")
    joystick = joystick_initializer.initialize()
    print("=== APP STARTED ===")
    screen_sleep_controller = ScreenSleep()

    joystick.on_button_change(
        lambda button, button_state, event: screen_navigator.navigate(NavigationDirection.UP),
        Joystick.Button.UP,
        Joystick.ButtonState.DOWN
    )
    joystick.on_button_change(
        lambda button, button_state, event: screen_navigator.navigate(NavigationDirection.DOWN),
        Joystick.Button.DOWN,
        Joystick.ButtonState.DOWN
    )
    joystick.on_button_change(
        lambda button, button_state, event: screen_navigator.navigate(NavigationDirection.LEFT),
        Joystick.Button.LEFT,
        Joystick.ButtonState.DOWN
    )
    joystick.on_button_change(
        lambda button, button_state, event: screen_navigator.navigate(NavigationDirection.RIGHT),
        Joystick.Button.RIGHT,
        Joystick.ButtonState.DOWN
    )
    joystick.on_button_change(
        lambda button, state, event: screen_sleep_controller.start(),
        Joystick.Button.ANY,
        Joystick.ButtonState.ANY
    )
    joystick.watch_events()

    screen_manager.set_on_change(construct_screen_manage_handler(runner))
    screen_manager.set_on_change_complete(lambda s1, s2: game_loop.set_animation_mode(False))

    for command_id in runner.get_all_commands():
        source = DataSource(command_id)
        source.set_callback(runner.create_source_callback(command_id))
        DataSourceCollection.register(source)

    screen_sleep_controller.set_sleep_time(config[SchemaKeys.GENERAL][SchemaKeys.GENERAL_SLEEP_AFTER])
    screen_sleep_controller.set_on_change(lambda active: device.show() if active else device.hide())
    screen_sleep_controller.start()

    modal_renderer = ModalRenderer(screen_manager.screens['modal'])

    control_manager = ControlSequenceManager()
    control_manager.register_handler("WAKEUP", lambda _: screen_sleep_controller.start())
    control_manager.register_handler("SLEEP", lambda _: screen_sleep_controller.stop())
    control_manager.register_handler("SCREEN", lambda c: screen_manager.set_current_screen(c.params['path']))
    control_manager.register_handler("MODAL", lambda c: modal_renderer.queue(
        ModalType(c.params['type']),
        c.params['title'],
        c.params['message']
    ))

    while game_loop.is_running():
        # Process control commands from all sources
        for ctrl_queue in runner.get_all_ctrl_outputs():
            control_manager.consume(ctrl_queue)

        # Always run prepare for persistent components
        prepared = []
        for component in component_registry.get_persistent_components():
            component.prepare([])
            prepared.append(component.name)

        # Then run prepare for current screen components
        current_screen = screen_manager.get_current_screen()
        current_screen.prepare(prepared)

        # Draw screen / modal
        if screen_sleep_controller.update():
            with canvas(device) as draw:
                screen_manager.draw(draw, device)
                if modal_renderer.is_active():
                    modal_renderer.render(draw, device)

        game_loop.update()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        game_loop.stop()
