# General configuration

```yaml
general:
  screen_fps: 10        # int, render loop target FPS (min 1)
  sleep_after: -1       # int, seconds of inactivity before the screen sleeps; -1 = never
  animation:
    fps: 30             # int, FPS during a screen transition (min 1)
    delta_x: 30         # int, horizontal slide speed in pixels per frame
    delta_y: 10         # int, vertical slide speed in pixels per frame
  hardware:
    screen_initializer: !cwd hardware/screen.py     # optional
    joystick_initializer: !cwd hardware/joystick.py # optional
  transform:
    functions:
      - transform/format_bytes   # ".py" appended automatically
      - transform/slider_linear
```

## `screen_fps`

Target frames per second for the render loop. The display redraws at this rate regardless of whether data changed. Minimum 1.

## `sleep_after`

Seconds of joystick inactivity before the screen turns off. `-1` disables sleep entirely. Sleep can also be triggered or cancelled from a script via control sequences — see [data.md](data.md#script-control-sequences).

## `animation`

Controls the slide transition that plays when switching screens.

| key | default | meaning |
|---|---|---|
| `fps` | `30` | frame rate during the transition; higher = smoother, minimum 1 |
| `delta_x` | `30` | horizontal slide speed in pixels per frame; used when navigating left/right |
| `delta_y` | `10` | vertical slide speed in pixels per frame; used when navigating up/down |

The transition slides the old screen out and the new one in simultaneously. The direction of the slide matches the navigation direction. The transition ends as soon as both screens reach their final positions, so the actual duration depends on the screen dimensions divided by `delta_x`/`delta_y`.

## `hardware`

Optional paths to Python files that register custom hardware initializers. If omitted, the built-in SSD1322 screen and GPIO joystick defaults are used (`src/hardware/default/`).

A path can be absolute or relative. Relative paths are resolved against the **config directory** (where `config.yaml` lives). Using `!cwd` is the recommended way to write paths relative to the file that contains the key:

```yaml
hardware:
  screen_initializer: !cwd hardware/screen.py
```

### Supported displays

The app renders through `luma.core`'s canvas API, so any display supported by `luma.oled` (already a dependency) works with a custom initializer — just change the device class in your `screen.py`. The full device list is in the [luma.oled docs](https://luma-oled.readthedocs.io).

The interface (SPI or I2C) is also set in the initializer. SPI is used by the default; to use I2C replace `spi` with `i2c` from `luma.core.interface.serial`.

### Writing a custom initializer

Create a Python file and decorate an initializer function with `@register_screen_provider` or `@register_joystick_provider`. The decorator argument is an arbitrary name shown in startup logs.

```python
# config/hardware/screen.py — example: SSD1306 over I2C
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from src.hardware.device_provider import register_screen_provider

@register_screen_provider("ssd1306-i2c")
def init():
    serial = i2c(port=1, address=0x3C)
    return ssd1306(serial)
```

```python
# config/hardware/joystick.py
from src.hardware.device_provider import register_joystick_provider

@register_joystick_provider("my-joystick")
def init():
    # set up and return the Joystick object
    ...
    return joystick
```

The last registered provider wins — a user file always overrides the built-in default, because it is loaded after the defaults.

## `transform.functions`

List of Python files that register custom functions for the flowline pipeline. Each path has `.py` appended automatically and is resolved against the config directory. Every file is executed once at startup as a plain module; a single file can register more than one function.

See [flowline.md](flowline.md#custom-functions) for how to write a custom function.
