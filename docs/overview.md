# FlowTile

Config-driven status display for small monochrome screens. Draws tiles of data from shell commands on an SSD1322 OLED over SPI, navigated with a 5-button GPIO joystick.

Everything you see on screen is defined in YAML config: what shell commands to run, what their output means, and how to lay it out on screen.

**How does it work?**

Everything is organized into logical units:
- screen
- component
- navigation axis

There is one main navigation axis (root) with one default screen on it. There can be many screens on
each axis and axes can cross with each other - to create a grid-like navigation. 
Finally, each screen has a tree of components, each component can be rendered in a different way, using renderers. 
## Architecture

- **Config-driven.** No screen layout is hardcoded. `screens.yaml` / `components.yaml` / `navigation.yaml` / `sources.yaml` (or however you split it) describe data sources and layout; the app just interprets them.
- **Shell scripts are the data sources.** Whatever a script prints to stdout becomes display content, after formatting/transforming.
- **A small expression language ("flowline") transforms raw script output** into whatever variables a component needs before display. See [flowline.md](flowline.md).
- **Everything renders through PIL / luma.core** onto a `canvas`, either the real SSD1322 device or nothing - there's no software framebuffer preview, you need the actual hardware to see output.

## Data flow

```
shell script (stdout)
  -> CommandRunner            threaded, EOF-buffered, control-sequence aware
  -> DataSource                one per command, holds latest output batch
  -> Component.process_data    source_format -> transform (flowline) -> output_format
  -> content renderer          text / image / progressbar / chart
  -> canvas                    drawn every frame, at general.screen_fps
```

Screen switches, sleep/wake, and modal popups can also be triggered by a script, via a small escape-sequence protocol on stdout - see [data.md](data.md#script-control-sequences).

## Project layout

This repo (`flowtile/`) is the application only - fonts and built-in icons are included, but no deployment config. A real install places its own `config/` and `commands/` alongside the repo, outside it, so `git pull` never touches user files.

```
flowtile/                    ← this repo
  main.py                  entry point: loads config, wires everything, runs the render loop
  src/
    screens_schema.py       config schema (Key constants, TYPES, SCHEMA) + custom YAML tags
    config_loader.py        generic recursive schema-driven YAML loader
    component.py             Component: data pipeline + drawing
    component_registry.py    loads/flattens/inherits components from config
    component_property.py    Property: static value or !var reference
    screens.py                Screen / ScreenManager
    screen_navigation.py       axis-based screen navigation
    axis.py                     Axis / AxisElement model used by navigation
    screen_sleep.py              screen sleep/wake timer
    screen_animation.py           slide transition between screens
    modal_renderer.py              modal popup queue + rendering
    joystick.py                     GPIO joystick, edge-based button events
    hardware/
      device_provider.py           hardware initializer registry + dynamic loader
      gpio_gpiod.py                gpiod wrapper used by both display and joystick
      default/screen.py            built-in SSD1322 screen initializer
      default/joystick.py          built-in GPIO joystick initializer
    command_runner.py                 subprocess manager: threading, EOF buffering, control sequences
    data_source.py, data_source_collection.py, data_source_type.py
    variable_store.py                 per-component variable snapshot, backs !var
    game_loop.py                      fixed-fps loop timer
    render/                            content renderers: text, image, progressbar, chart
    transform/                         flowline language + function registry
      lang/                            tokenizer, parser, evaluator, environment, functions
    config/                            config_loader helpers (path matching, field binding)
  font/                     Tiny5, SpaceMono TTFs
  images/modal/             info/warn/error icons for the modal renderer
  tests/flowline/           pytest suite for the flowline language
  docs/                     this documentation

config/                     deployment config - outside the repo, write your own
  config.yaml               main config file (can include others)
  hardware/screen.py        optional custom hardware initializer
  transform/                optional custom flowline functions
commands/                   shell scripts used as data sources - also outside the repo
```

## Docs

- [examples.md](examples.md) - five annotated example configs covering most features
- [config.md](config.md) - main config file, `include`, `sources`
- [general.md](general.md) - `general` section: FPS, sleep, hardware initializers, transform functions
- [components.md](components.md) - component schema: layout, styling, inheritance, content renderers
- [data.md](data.md) - data pipeline: `source`, `source_format`, `output_format`, `static`, `persist`, script control sequences
- [flowline.md](flowline.md) - the `transform` expression language
- [navigation.md](navigation.md) - screens, navigation axes, joystick, modal, sleep
- [development.md](development.md) - running, testing, dev environment

## Tech stack

- Python 3.14, managed with `uv` (`pyproject.toml` / `uv.lock`)
- `gpiod` - GPIO for display and joystick
- `luma.oled` / `luma.core` - SSD1322 driver and canvas rendering
- `Pillow` - fonts, drawing, image loading
- `psutil` - killing subprocess trees cleanly
- `parse` - format-string based text extraction (`source_format`, chart's `format` option)
- `PyYAML` - config parsing
- `pytest` - test suite (flowline language)
