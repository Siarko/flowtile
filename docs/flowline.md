# Flowline

Flowline is the small expression language behind a component's `transform:` pipeline. It reads variables (from `source_format`, `static`, or previous flowline instructions), runs function calls/arithmetic/comparisons on them, and writes the result into named output variables.

It's compiled to an AST once, when the config loads (not re-parsed every frame) - a script with a syntax error fails at startup, not at render time.

## An instruction

One line of `transform:` is one instruction:

```
[condition] expression [> output[, output...]]
```

```yaml
transform:
  - uppercase(input) > upper
```

- `expression` is evaluated.
- `> output` (optional) assigns the result to one or more named variables. Without `>`, the instruction is only useful for its side effects (e.g. `log(x)`).
- A function/expression can return multiple values at once (as a tuple), matched positionally against a comma-separated output list - see `slider_linear` below.

### Conditions

```yaml
transform:
  - if(value > 90) "HIGH" > status
```

`if(<expr>)` guards the instruction: `<expr>` must evaluate to a `bool`, and if it's false the whole instruction (including any output assignment) is skipped for this run.

To avoid repeating the same condition on consecutive lines, `...` reuses the condition from the previous instruction *in the same block* (top-level pipeline, or the same loop body):

```yaml
transform:
  - if(valid) trimmed > values[]
  - ... to_number(trimmed) > numbers[]
  - ... chars(trimmed) > cs
```

is the same as writing `if(valid)` on all three lines.

### Outputs

```
expr > a            # scalar assignment
expr > a, b         # multiple outputs (expr must return a tuple of 2)
expr > items[]      # append to a list instead of replacing it
```

`name[]` appends the result to a list variable instead of overwriting it - see loops below, where this is how you collect per-item results.

## Expressions

Literals: `123`, `1.5`, `"a string"`, `true`, `false`. Strings support `\n`, `\\`, `\"` escapes.

Variables: `name`, indexed with `name[expr]` (repeatable for nested lists, e.g. `matrix[0][1]`; index must be a non-negative `int`, out-of-range or wrong-type indices raise an evaluation error).

Function calls: `name(arg, arg, ...)`.

Operators, precedence low -> high (same row = equal precedence, left-associative unless noted):

| operator | meaning | function |
|---|---|---|
| `..` | string concatenation | `con` |
| `\|\|` | logical or | `or` |
| `&&` | logical and | `and` |
| `== ~= > >= < <=` | equality / comparison | `eq neq gt gteq lt lteq` |
| `+ -` | add / subtract | `add sub` |
| `* / %` | multiply / divide / modulo | `mul div mod` |
| `^` | power (right-associative) | `pow` |
| unary `- ~` | negate / logical not | `neg not` |

Every operator is literally sugar for a function call - `a + b` and `add(a, b)` compile to the same node, and `add` / `eq` / etc. are ordinary entries in the function registry (see below). Parentheses `(...)` group as usual.

A few gotchas:

- Not-equal is `~=`, not `!=` - `!` is not a valid token in flowline at all.
- Comparisons don't chain: `a == b == c` is a syntax error, not `(a==b)==c`. Combine with `&&`/`||` instead: `a == b && b == c`.
- `1..2` (no spaces) tokenizes fine as `con(1, 2)` - the number reader only treats a `.` as a decimal point when it's *not* immediately followed by another `.`. A single trailing dot (`1.`) or a dot before a letter (`1.x`) is still an error either way.
- `>` is both the greater-than operator and the output separator. Inside `if(...)` this is never ambiguous. As a bare value (not inside `if(...)`), a comparison needs a second `>` to disambiguate: write `x > 5 > result`, not `x > 5` (the latter is read as "assign `x` to output `5`", which then fails since `5` isn't a valid output name).

## Loops

A `transform:` entry can be a one-key mapping instead of a string: the key is a loop header, the value is the body (a nested list of instructions/loops, same rules, up to 10 levels deep):

```yaml
transform:
  - split(input, "\n") > raw_lines
  - raw_lines > line:
      - trim(line) > trimmed
      - if(neq(trimmed, "NA")) trimmed > values[]
```

Header syntax: `[condition] list_expr > item[, index]` - `list_expr` must evaluate to a list; `item` is bound to each element in turn, `index` (optional) to its 0-based position.

### Scoping

Inside a loop body, you can read every variable visible outside the loop. But a plain assignment (`x > y`) inside the loop is local to that iteration - it's gone once the loop moves on, and never visible outside the loop at all.

The one exception is `name[]` (append) targets: every iteration's append is collected, and after the loop finishes, the full list is written to `name` in the *enclosing* scope. For a nested loop, that "enclosing scope" is the outer loop's current iteration - to bubble a value all the way out of two nested loops, both levels need to append it with `[]`.

Worked example - read multi-line sensor input, keep only non-"NA" values, and also count digit characters per value, three levels of state:

```yaml
transform:
  - split(input, "\n") > raw_lines
  - raw_lines > line:
      - trim(line) > trimmed
      - neq(trimmed, "NA") > valid
      - if(valid) trimmed > values[]           # escapes the outer loop
      - if(valid) chars(trimmed) > cs
      - if(valid) cs > ch:                      # nested loop
          - neq(ch, ".") > is_digit
          - if(is_digit) ch > digit_chars[]     # escapes the inner loop only
      - if(valid) count(digit_chars) > digit_count
      - if(valid) digit_count > digit_counts[]  # escapes the outer loop
  - count(values) > value_count
```

After this runs, `values`, `digit_counts` and `value_count` exist at the top level. `digit_chars`, `cs`, `trimmed`, `line`, `ch` do not - they only ever existed inside a loop iteration.

## State across refreshes

A component's flowline environment is created once (when the component is loaded) and lives for the component's whole lifetime - but only `static:` variables actually persist in it. Every other variable is cleared right after the line it belongs to finishes (its `transform` has run and its `output_format` has been rendered), so the next line - whether that's the next line of the same refresh, or the first line of the next refresh - starts with a clean slate except for whatever `static:` seeded.

Concretely: `static:` in `data:` isn't just a starting value, it's the *only* place in `data:` that carries a value across refreshes. Anything else your `transform` outputs is scratch space for that one line.

This is what makes counters and animations possible purely in config, no Python needed:

```yaml
data:
  source: random
  static:
    last: 0
    sum: 0
  transform:
    - if(is_defined(number)) number > last
    - if(is_defined(number)) sum + number > sum
```

`last`/`sum` are `static:`, so they keep accumulating refresh after refresh. `number` isn't - it only exists on a line where `source_format` actually produced it, so both instructions are guarded with `is_defined(number)` rather than assuming it's there. Use `is_defined`, not `is_none`, for this: `is_none` evaluates its argument, so on a line where `number` was never set at all (not even to `None`), `is_none(number)` raises instead of returning `true` - see the built-ins table below.

`slider_linear(x, min, max, step)` (a bundled example custom function, see below) leans on the same persistence: it takes the current position and step as arguments, returns the next position and (possibly flipped) step as a two-value tuple, and both are written back to the same `static` variables they came from - so each refresh moves the value one step further, bouncing between `min` and `max`.

## Built-in functions

Registered by `build_core_registry()` - always available, can't be overridden by custom functions (registering a name twice is an error):

| function | arity / types | notes |
|---|---|---|
| `add sub mul mod pow` | `(numeric, numeric)` | `bool` doesn't count as numeric |
| `div` | `(numeric, numeric)` | raises on division by zero |
| `neg` | `(numeric)` | |
| `eq neq` | `(any, any)` | |
| `gt gteq lt lteq` | `(numeric, numeric)` | |
| `and or` | `(bool, bool)` | |
| `not` | `(bool)` | |
| `con` | `(any, any)` | stringifies both sides and concatenates |
| `is_none` | `(any)` | Python-`None` check |
| `is_defined` | variable reference | true if the *name* exists at all - takes the raw variable node, not its value, so `is_defined(x)` is safe even if `x` was never set |
| `log` | `(any)` | prints to stdout, prefixed with `log_prefix` (defaults to the component name) |

## Custom functions

Register your own via a decorator, in a plain Python file:

```python
# example: config/transform/format_bytes.py
from src.transform.lang.functions import ValueType
from src.transform.registry import register_function

@register_function("format_bytes", [ValueType.INT])
def run(value) -> str:
    v = int(value)
    unit = "B"
    if v > 1024:
        v /= 1024
        unit = "KB"
    return str(int(v)) + " " + unit
```

- The first decorator argument is the name used *inside flowline scripts* - it doesn't have to match the Python function's name.
- The second argument is the parameter type list (`ValueType.INT` / `FLOAT` / `NUMERIC` / `BOOL` / `STRING` / `LIST` / `ANY`); wrong arity or a type mismatch is a runtime error, not a silent coercion.
- Pass `register_function(name, types, context=True)` and add an `Environment` as the function's first parameter to get access to the running component's variables (needed for things like `is_defined` / `log` above).
- A function can return a Python `tuple` to support multi-output assignment (`> a, b`).

List these files (without `.py`) under `general.transform.functions` in `config.yaml` - see [config.md](config.md#general). Every file is executed once at startup as a plain Python module; a single file can register more than one function.
