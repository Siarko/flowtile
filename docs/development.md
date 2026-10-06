# Development

## Environment

Dependencies are managed with `uv` (`pyproject.toml` / `uv.lock`), Python 3.14. A `.devcontainer/` is provided for VS Code / any devcontainer-compatible editor.

```bash
uv sync
```

## Running

```bash
cd flowtile
uv run python main.py
```

Needs an actual SSD1322 over SPI and `/dev/gpiochip0` — display and GPIO code (`device_provider.py`, `gpio_gpiod.py`, `joystick.py`) only works on the target hardware (Raspberry Pi 5 / OpenWrt). There's no software framebuffer fallback for local development.

`main.py` looks for config in `../config/` relative to itself (a sibling directory of the repo), and runs source scripts with that config directory as their working directory.

## Config validation without hardware

```bash
uv run python test_config_loader.py
```

A small standalone script that loads and validates config the same way `main.py` does, without touching any hardware — useful for checking a config change is well-formed.

## Tests

The flowline language (tokenizer, parser, evaluator, environment, functions) has a pytest suite under `..`:

```bash
uv run pytest
```

`pyproject.toml` points `pythonpath` at `src` and `testpaths` at `tests`, so plain `pytest` from the repo root works too once dependencies are installed.

Nothing else in the app currently has test coverage - display/GPIO code isn't testable without hardware, and the config/component/screen layer doesn't have tests yet.

## Manual joystick check

```bash
uv run python src/joystick_test.py
```

Not a pytest test - a standalone script that prints button events as you press them. Useful for confirming GPIO wiring before trusting the real app.
