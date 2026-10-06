from luma.core.interface.serial import spi
from luma.oled.device import ssd1322

from src.hardware.device_provider import register_screen_provider
from src.hardware.gpio_gpiod import GPIODWrapper

DC_PIN = 24    # Data/Command pin
RST_PIN = 25   # Reset pin

@register_screen_provider("default")
def init_device():
    print("  [device] creating GPIO wrapper")
    gpioWrapper = GPIODWrapper(chip_name='/dev/gpiochip0')
    print("  [device] initializing SPI")
    serial = spi(gpio=gpioWrapper, gpio_DC=DC_PIN, gpio_RST=RST_PIN)
    print("  [device] creating ssd1322 device")
    device = ssd1322(serial)
    print("  [device] done")
    return device
