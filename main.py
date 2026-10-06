import os

from src import screen_navigation
from src.controll_sequence_manager import ControlSequenceManager
from src.game_loop import GameLoop
from src.screen_animation import ScreenAnimation
from src.screen_navigation import NavigationDirection
from src.screen_sleep import ScreenSleep
from src.modal_renderer import ModalRenderer, ModalType
import src.config_loader as ConfigLoader
import src.command_runner as command_runner

from src.screens_schema import Key
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

import src.sources_loader as sources_loader
import src.component_loader as component_loader
import src.input_setup as input_setup
import src.render_loop as render_loop
from src.hardware.setup import setup as setup_devices

config_dir = [os.path.dirname(__file__), '..', 'config']
command_dir = os.path.join(*config_dir)


def main():
    game_loop = GameLoop()
    try:
        print("=== PREPARING CONFIG ===")
        config_loader = ConfigLoader.Loader(file_directory=config_dir)
        config_loader.set_reference_types(REFERENCE_TYPES)
        config_loader.set_tag_parsers(CONFIG_TAG_PARSERS)
        config = config_loader.load_config(schema=CONFIG_SCHEMA)
        print("=== CONFIG LOADED ===")
        print(config)
        game_loop.set_target_fps(config[Key.GENERAL][Key.GENERAL_SCREEN_FPS])
        game_loop.set_animation_fps(config[Key.GENERAL][Key.GENERAL_ANIMATION][Key.GENERAL_ANIMATION_FPS])

        runner = command_runner.CommandRunner()
        sources_loader.setup(config, runner, command_dir)

        function_registry.load_user_functions(
            config[Key.GENERAL][Key.GENERAL_TRANSFORM][Key.GENERAL_FUNCTIONS])

        screen_manager = component_loader.setup(config, config_loader)

        screen_navigator = screen_navigation.load_from_config(config[Key.NAV])
        screen_manager.set_home_screen(screen_navigator.get_home_screen())

        def screen_switch_handler(screen, direction: NavigationDirection):
            game_loop.set_animation_mode(True)
            screen_manager.set_current_screen(screen)
            if screen_manager.previous_screen != screen_manager.current_screen:
                animation_config = config[Key.GENERAL][Key.GENERAL_ANIMATION]
                x = 0
                y = 0
                match direction:
                    case NavigationDirection.LEFT:
                        x = animation_config[Key.GENERAL_ANIMATION_DELTA_X]
                    case NavigationDirection.RIGHT:
                        x = -animation_config[Key.GENERAL_ANIMATION_DELTA_X]
                    case NavigationDirection.UP:
                        y = -animation_config[Key.GENERAL_ANIMATION_DELTA_Y]
                    case _:
                        y = animation_config[Key.GENERAL_ANIMATION_DELTA_Y]
                screen_manager.set_screen_animation(ScreenAnimation(x, y))

        screen_navigator.set_screen_handler(screen_switch_handler)

        device, joystick = setup_devices(config, command_dir)
        print("=== APP STARTED ===")

        screen_sleep_controller = ScreenSleep()
        screen_sleep_controller.set_sleep_time(config[Key.GENERAL][Key.GENERAL_SLEEP_AFTER])
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

        screen_manager.set_on_change(sources_loader.make_screen_change_handler(runner))
        screen_manager.set_on_change_complete(lambda s1, s2: game_loop.set_animation_mode(False))

        input_setup.wire(joystick, screen_navigator, screen_sleep_controller)

        render_loop.run(game_loop, runner, screen_manager, screen_sleep_controller, modal_renderer, control_manager,
                        device)
    except KeyboardInterrupt:
        game_loop.stop()


if __name__ == "__main__":
    main()
