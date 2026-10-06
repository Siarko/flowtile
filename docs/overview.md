# FlowTile

Config-driven status display for small screens. Draws tiles of data from shell commands on a luma-supported OLED, navigated with a 5-button GPIO joystick.

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
- **Everything renders through PIL / luma.core** onto a `canvas`, either the real device or nothing - there's no software framebuffer preview, you need the actual hardware to see output.

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
flowtile/                   ← this repo, no need to touch anything here
  font/                     built-in fonts (Tiny5, SpaceMono)
  images/                   built-in icons
  docs/                     documentation
  src/                      application source

config/                     your deployment config - create this yourself, outside the repo
  config.yaml               main config (can include the files below). This one is read first
  some-file.yaml            you can create any yaml file. to use it, include it in `include` section in main config file
  hardware/                 optional: custom screen / joystick initializers
    screen.py               look at default ones to figure out what they do
    joystick.py
  transform/                optional: custom flowline functions
    functions.py

commands/                   your shell scripts — also outside the repo
  uptime.sh
  ...
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
- `luma.oled` / `luma.core` - OLED drivers and canvas rendering
- `Pillow` - fonts, drawing, image loading
- `psutil` - killing subprocess trees cleanly
- `parse` - format-string based text extraction (`source_format`, chart's `format` option)
- `PyYAML` - config parsing
- `pytest` - test suite (flowline language)
