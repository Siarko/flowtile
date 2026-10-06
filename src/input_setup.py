from src.joystick import Joystick
from src.screen_navigation import NavigationDirection, ScreenNavigation
from src.screen_sleep import ScreenSleep


def wire(joystick: Joystick, navigator: ScreenNavigation, sleep_controller: ScreenSleep):
    joystick.on_button_change(
        lambda button, button_state, event: navigator.navigate(NavigationDirection.UP),
        Joystick.Button.UP,
        Joystick.ButtonState.DOWN
    )
    joystick.on_button_change(
        lambda button, button_state, event: navigator.navigate(NavigationDirection.DOWN),
        Joystick.Button.DOWN,
        Joystick.ButtonState.DOWN
    )
    joystick.on_button_change(
        lambda button, button_state, event: navigator.navigate(NavigationDirection.LEFT),
        Joystick.Button.LEFT,
        Joystick.ButtonState.DOWN
    )
    joystick.on_button_change(
        lambda button, button_state, event: navigator.navigate(NavigationDirection.RIGHT),
        Joystick.Button.RIGHT,
        Joystick.ButtonState.DOWN
    )
    joystick.on_button_change(
        lambda button, state, event: sleep_controller.start(),
        Joystick.Button.ANY,
        Joystick.ButtonState.ANY
    )
    joystick.watch_events()
