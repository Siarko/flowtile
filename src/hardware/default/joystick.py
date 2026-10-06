from src.hardware.device_provider import register_joystick_provider
from src.joystick import Joystick

JOYSTICK_HARDWARE_PINS = {
    4: Joystick.Button.CENTER,
    17: Joystick.Button.LEFT,
    22: Joystick.Button.RIGHT,
    23: Joystick.Button.DOWN,
    27: Joystick.Button.UP,
}

@register_joystick_provider("default")
def initialize():
    return Joystick(JOYSTICK_HARDWARE_PINS)