# Components

A component is one rectangle of screen: it has a size, optional styling, and either child components or content (text/image/progressbar/chart) fed by a data source.

## Where components are defined

Two places:

- Top-level `components:` - reusable, and required if you want to `parent:` from it or reference the same component from multiple screens.
- Inline as a screen's `component:` tree (see [navigation.md](navigation.md)), or nested under another component's `children:`.

Either way, every component gets a globally unique name - component names are flattened into one namespace, so a name used once anywhere in `children:` or `components:` can't be reused.

```yaml
components:
  label:
    align: center
    align_v: middle
    color: 0
    color_bg: 100
```

## Inheritance (`parent`)

```yaml
components:
  uptime.label:
    parent: label
    data:
      source: !type:text UPTIME
```

`uptime.label` starts as a deep copy of `label`, then only the keys you explicitly wrote (`data` here) are overwritten on top. Parents are resolved before children are instantiated, so a chain of `parent`s works, but there's no diamond/multiple inheritance - one `parent` per component.

## Layout

```yaml
<component_name>:
  direction: row | column   # layout direction for this component's children
  size: int | "50px"        # this component's size *within its parent*
  padding: int | {top, bottom, left, right}
  children:
    child_a: {...}
    child_b: {...}
```

- `direction` on a component controls how *its children* are arranged, not how the component itself is placed (that's controlled by the parent's `direction`).
- `size` is read along the parent's layout axis (width if the parent is `row`, height if `column`):
  - plain `int` - percentage of the *remaining* space after fixed-size and other percentage siblings are subtracted, e.g. `size: 50` next to another `size: 50` splits what's left 50/50.
  - `"Npx"` - a fixed pixel size, taken off the top before percentages are computed.
  - omitted - split whatever's left over after fixed/percentage siblings, evenly among all unsized siblings.
- `padding` shrinks the drawable area inside the component (content and children are laid out inside padding + border).
- A component either has `children` or content (data-driven), not both - if it has `children`, its own `data` / content renderer are ignored, only leaf components render content.

## Styling

```yaml
<component_name>:
  align: left | center | right       # horizontal text/image alignment
  align_v: top | middle | bottom     # vertical text/image alignment
  color: Color                       # text/foreground color
  color_bg: Color                    # background fill; omit/-1 = transparent
  visible: bool
  font_size: int
  font: str                          # font filename in flowtile/font/, default Tiny5-Regular.ttf
  border: int | {top, bottom, left, right}
  border_color: Color | {top, bottom, left, right}
```

`Color` is a greyscale/RGB value: an `int` 0-255 is shorthand for `rgb(v,v,v)` (a grey level), or write any Pillow-style color string (`"rgb(100,100,100)"`, `"rgba(0,0,0,0)"`, ...). `-1` (or `color_bg` omitted) means transparent background.

## Property values and `!var`

`align`, `align_v`, `color`, `color_bg`, `border`, `border_color`, `font_size` and `visible` don't have to be literal values - they can point at a variable produced by another component's (or the same component's) data pipeline:

```yaml
border:
  left: !var border   # read this component's own "border" transform-pipeline output
```

```yaml
color: !var other_component.value   # read another component's "value" variable
```

`!var name` reads `name` from the current component's own variables (whatever its `transform` pipeline last output, plus anything `output_format`-visible). `!var component.name` reads it from a different component by name. These are re-evaluated on every draw, so a value your `transform` pipeline recomputes each refresh can drive another component's styling directly - see the growing-border example in [flowline.md](flowline.md#state-across-refreshes).

## Content renderers

A leaf component (no `children`) shows the output of its data pipeline through a content renderer:

```yaml
content_render: chart              # shorthand for {type: chart}
# or
content_render:
  type: chart
  <renderer_option>: <value>
```

If you don't set one, the app picks `text` or `image` automatically based on the data source's content type (image data sources - currently only the modal icon, see [navigation.md](navigation.md#modal) - default to `image`, everything else defaults to `text`).

### `text`

Draws each output line as text, using `align` / `align_v` / `color` / `font_size` / `font`.

| option | default | meaning |
|---|---|---|
| `line_space` | `0` | extra pixels between lines, on top of `font_size` |

### `image`

Treats each output line as a path relative to `..`, loads it, converts to greyscale, scales to fit (keeping aspect ratio), and aligns it with `align` / `align_v`. No options.

### `progressbar`

Draws a filled bar per output line/variable set. Reads `value` (and optionally `max`) **by variable name** from the pipeline's output variables - not from the rendered text - so your `transform` / `source_format` needs to actually produce a variable literally called `value` (and `max`, if you want a per-line max).

| option | default | meaning |
|---|---|---|
| `min` | `0` | value corresponding to an empty bar |
| `max` | `100` | value corresponding to a full bar, unless overridden per-line by a `max` variable |
| `format` | `"{value:d}"` | accepted by the schema, currently unused by this renderer |

### `chart`

Plots a scrolling line chart, sampling one value per render from the component's *rendered output text*, matched against `format`.

| option | default | meaning |
|---|---|---|
| `format` | `"{value:d}"` | parsed against each output line (`parse` library) to pull out `value` |
| `min` / `max` | `0` / `100` | fixed value range |
| `autoscale` | `false` | ignore `min` / `max` and scale to the observed min/max instead (smoothed over `scale_time` seconds, default `1.0`, not schema-configurable) |
| `sample_count` | `20` | how many samples the scrolling window keeps |
| `background` | `100` | fill color under the line; `-1` disables the fill |
| `line_size` | `1` | line thickness in px |
| `grid_values` / `grid_time` | `5` / `7` | number of horizontal/vertical grid lines |
| `show_max_value` | `false` | label the peak value on the chart |

Unlike `progressbar`, `chart` needs `format` to match your `output_format`, since it parses the finished text - e.g. `output_format: "{value}/{x}"` pairs with `content_render: {type: chart, format: "{value}/{x}"}`.
