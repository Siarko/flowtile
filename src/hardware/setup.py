from src.hardware import device_provider
from src.screens_schema import Key


def setup(config: dict, cwd: str):
    print("=== PREPARING DEVICES ===")
    hardware_config = config.get(Key.GENERAL, {}).get(Key.GENERAL_HARDWARE, {})
    user_screen_path = hardware_config.get(Key.GENERAL_HARDWARE_SCREEN, None)
    user_joystick_path = hardware_config.get(Key.GENERAL_HARDWARE_JOYSTICK, None)

    device_provider.load_user_initializer_path(user_screen_path, cwd)
    device_provider.load_user_initializer_path(user_joystick_path, cwd)

    screen_initializer = device_provider.get_device_initializer(device_provider.DeviceType.SCREEN)
    print(f"Initializing screen with \"{screen_initializer.get_name()}\" initializer")
    device = screen_initializer.initialize()

    joystick_initializer = device_provider.get_device_initializer(device_provider.DeviceType.JOYSTICK)
    print(f"Initializing joystick with \"{joystick_initializer.get_name()}\" initializer")
    joystick = joystick_initializer.initialize()

    return device, joystick
