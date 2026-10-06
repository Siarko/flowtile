# Data pipeline

Every leaf component reads from a `data:` block. This is where raw script output turns into whatever the content renderer needs.

```yaml
<component_name>:
  data:
    source: str | !type:text [...]   # where the data comes from
    source_multiline: bool           # default false
    source_format: str | dict        # extract named variables from the raw text
    static: {name: value, ...}       # persistent variables, seeded before the pipeline runs
    transform: [instruction, ...]    # flowline pipeline, see flowline.md
    output_format: str | [str]       # final rendered line(s)
  persist: bool                      # keep the source command running even off-screen
```

## `source`

A source is either a command name (from `sources:`, see [config.md](config.md#sources)) or inline static text:

```yaml
data:
  source: uptime           # plain string = command name
```

```yaml
data:
  source: !type:text
    - Line 1
    - Line 2
```

`!type:text` (or a bare string after it) gives fixed content - useful for labels that never change. It's registered internally as a one-off data source named `text.component.<component_name>`.

## `source_format`

Runs `parse.parse(format, line)` ([pypi.org/project/parse](https://pypi.org/project/parse/) - like `str.format()` but for extraction) per input line, and merges any named fields into that line's variables. Every line's raw text is always available as `input`, even without `source_format`.

Four shapes:

```yaml
source_format: "{day}-{month}-{year}"      # one format, applied to every line
```

```yaml
source_format:                              # by line number (1-indexed)
  1: "Random number:{number:d}"
  2: "{line_two}"
  3: "{line_three}"
```

```yaml
source_format:                              # by regex match against the line
  "^ERROR": "ERROR: {message}"
  "*": "{message}"                           # "*" is the fallback/wildcard entry
```

Entry types are checked in this order:
1. Number lines
2. Regex
3. Wildcard (there's only one)

First match wins.

A line that matches nothing just keeps its `input` variable and whatever `static` seeded.

## `source_multiline`

- `false` (default): each output line is processed independently - one variable set, one pass through `transform` / `output_format` per line, `input` = that line.
- `true`: all lines are joined with `\n` into a single `input`, and `source_format`'s numbered/regex rules still run per original line (so line-numbered extraction still works), but everything feeds one shared variable set and one pass through `transform` / `output_format`.

Say a source prints 3 lines:

```
Random number:7
Line 2
Line 3
```

with

```yaml
data:
  source: random
  source_format:
    1: "Random number:{number:d}"
  output_format: "n={number}"
```

**`source_multiline: false`** runs `source_format` / `transform` / `output_format` 3 times, once per line, each with its own `input` and its own `number` (or lack of one):

| line | `input` | `number` | `output_format` result |
|---|---|---|---|
| 1 | `Random number:7` | `7` | `n=7` |
| 2 | `Line 2` | - (not extracted) | dropped - `{number}` doesn't exist on this line, see the `output_format` gotcha above |
| 3 | `Line 3` | - (not extracted) | dropped, same reason |

Final rendered output: one line, `n=7`.

**`source_multiline: true`** runs it once, for the whole block. `input` is all 3 lines joined; `number`'s numbered rule (`1: "..."`) still matches against original line 1 specifically, and lands in the single shared variable set:

| | `input` | `number` |
|---|---|---|
| (one run) | `Random number:7\nLine 2\nLine 3` | `7` |

Final rendered output: still one line, `n=7` - same result here, but because a numbered/regex `source_format` rule matched once for the whole block rather than 3 separate lines each producing their own output. The difference shows once `transform` gets involved: with `false`, a pipeline that accumulates into a `static` counter runs 3 times per refresh (once per line); with `true`, it runs once.

## `static`

Seed variables with an initial value, before anything else runs:

```yaml
static:
  last: 0
  sum: 0
```

`static` is the *only* thing in `data:` that persists between refreshes - every other variable your `transform` pipeline sets is cleared once the line it belongs to is done. See [flowline.md](flowline.md#state-across-refreshes) for why, and for the right way to guard a value that might not exist on every line.

## `transform`

A list of [flowline](flowline.md) instructions/loops. Runs once per variable set (see `source_multiline` above), with the current variable set (`input` + whatever `source_format` extracted) available as variables, plus everything `static` seeded. Whatever it outputs is merged back into that variable set.

## `output_format`

The final line(s) shown, built with Python `str.format(**variables)` against the finished variable set (post-`transform`):

```yaml
output_format: "The date is {upper}"
# or several lines from one variable set:
output_format:
  - "{value}"
  - "at {x}"
```

Default (if omitted): `"{input}"`. If a referenced variable doesn't exist, that line is silently dropped - not rendered blank, just skipped entirely. This is a real gotcha with `source_format` regex/numbered rules that don't match every line.

All final variables (after `transform`) are also published for other components to read via `!var component_name.variable` - see [components.md](components.md#property-values-and-var).

## `persist`

```yaml
persist: true
```

Normally a component's source command only runs while a screen containing it is the current one - switching away stops it. `persist: true` keeps it running (and its `data` pipeline re-evaluated every frame) regardless of which screen is shown. Used for things like charts that need to keep sampling in the background.

## Script control sequences

A source script can send commands to the app instead of, or alongside, data, by printing a line starting with the ESC byte (`\x1b`):

```
\x1b<COMMAND>[:<param1>[:<param2>...]]
```

A literal `:` inside a param must be escaped as `\:`. Recognized commands:

| command | params | effect |
|---|---|---|
| `WAKEUP` | - | wake the screen (as if a button was pressed) |
| `SLEEP` | - | force the screen to sleep now |
| `SCREEN` | `path` | jump straight to screen `path`, bypassing navigation |
| `MODAL` | `type`, `title`, `message` | queue a modal popup; `type` is `info`, `warn` or `error` |

```bash
printf '\x1bMODAL:error:Test:This is a test info modal\n'
printf '\x1bWAKEUP\n'
```

Control lines are consumed entirely - they never show up as component content. See [navigation.md](navigation.md#modal) for what a `MODAL` command actually renders and what config it requires.
