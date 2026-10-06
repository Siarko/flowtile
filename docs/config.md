# Config files

All config is YAML. One file is loaded directly (`config.yaml` or `config.yml`, first one found in the config directory), and it can pull in others with `include`.

```yaml
# paths are relative to the directory config.yaml lives in
include:
  - sources.yaml
  - components.yaml
  - screens.yaml
  - navigation.yaml
```

Included files are merged into the root config by top-level key (`sources`, `components`, `screens`, `navigation`, ...). Includes are read after the root file and override it on key collisions, so in practice keep each top-level key in exactly one file.

There's nothing special about the included file names - split things however makes sense. The example deployment in this repo uses one file per top-level section (`sources.yaml`, `components.yaml`, `screens.yaml`, `navigation.yaml`), but that's a convention, not a requirement.

## How loading works

1. `config.yaml` is read; includes are recursively read and merged in.
2. The whole thing is checked against a schema (`src/screens_schema.py`): required keys, types, allowed values. Unknown keys are rejected unless the schema declares a wildcard for that spot.
3. The config is walked again to fill in defaults, run value parsers (e.g. turning `border: 4` into a `{top, bottom, left, right}` dict, or compiling a `transform` list into a flowline AST), and convert plain strings into enums.

You don't need to know any of this to write config - it's here so schema errors make sense. If the app rejects your config, the error names the path (like `/sources/uptime/refresh`) and what was expected.

## Custom YAML tags

A few tags do useful things beyond plain YAML:

- `!var name` - use another value's runtime variable instead of a literal. See [components.md](components.md#property-values-and-var).
- `!type:text` - a component's data source is inline static text instead of a command. See [data.md](data.md#source).
- `!type:command name` - explicit form of a command-name source; equivalent to just writing the name as a plain string.
- `!axis name` - reference another navigation axis from inside an axis's `elements`. See [navigation.md](navigation.md).
- `!cwd path` - resolve `path` relative to the YAML file that contains the tag, returning an absolute path. Useful when config is split across files in different directories: each file can reference its own sibling scripts or resources without knowing where the root config lives.

## `general`

`screen_fps`, `sleep_after`, `hardware` (custom screen/joystick initializers) and `transform.functions` (custom flowline functions). See [general.md](general.md).

## `sources`

A source is a command to run. Its output becomes available to components via `data.source`.

```yaml
sources:
  <source_name>:
    script: [str, ...]           # command + arguments, e.g. ["/bin/ash", "../commands/uptime.sh"]
    exec_mode: single | repeat   # single: run once, keep last output. repeat: rerun on a timer
    refresh: int                 # seconds between runs, required if exec_mode is repeat
    eof_string: str              # optional, see below
    autostart: bool              # start this command when the app boots (default false)
```

- `script` is passed straight to `subprocess.Popen`, with cwd set to the **config directory** - so relative paths in `script` are relative to where your `config.yaml` lives. Use `!cwd` for paths that should be relative to a specific included file instead of the config root.
- Commands only actually run while a screen that references them is current, unless `autostart: true` (runs from boot regardless) or the owning component has `persist: true` (see [data.md](data.md#persist), also keeps it running regardless of screen). Switching away from a screen stops its other, non-persistent commands.
- `refresh` only matters for `repeat` mode; `single` runs the command once and keeps the last output forever (until the process is restarted by a screen switch that starts it again).
- `eof_string`: if a command prints multiple lines per "update" and you want them delivered as one atomic batch, have it print this exact string as its own line once it's done. Lines are buffered until the EOF string shows up, then flushed together. Without it, every line is delivered as its own single-line batch.
- A script can also send control commands (switch screen, sleep/wake, show a modal) instead of, or in addition to, data - see [data.md](data.md#script-control-sequences).
