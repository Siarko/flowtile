# Screens, navigation, input

## Screens

```yaml
screens:
  <screen_id>:
    label: str                       # optional, shown wherever screen labels are used
    component: str | {name: {...}}   # the screen's single root component
```

`component` is either a name (referencing `components:`) or an inline component definition (same schema as [components.md](components.md)) - inline components defined this way are still flattened into the global component namespace under whatever name you give them.

## Navigation axes

Screens don't wire directly to each other. Instead, they sit on **axes** - ordered 1D lists the joystick moves along:

```yaml
navigation:
  main:
    root: true
    default: home
    direction: row      # row: left/right moves along this axis. column: up/down
    wrap: false          # wrap from last element back to first (and vice versa)
    elements:
      - home
      - wan
  horizontals:
    direction: column
    elements:
      - !axis top          # nest another axis as an element
      - !axis bottom
```

- Exactly one axis has `root: true`; its `default` screen is where the app opens.
- `elements` are screen names by default, or `!axis <name>` to cross into another axis.
- Two axes that intersect (share an element via `!axis`) must run in perpendicular directions - checked at startup.
- A screen can sit on at most 2 axes total - also checked at startup.
- Moving off an axis's end (with `wrap: false`) does nothing; the joystick press is just absorbed.

Given a current screen, the joystick looks for an axis running in the pressed direction that contains the current screen directly; if none does, it falls back to whatever axis the *current axis* is nested inside (via `!axis`), so pressing perpendicular to your current axis climbs "out" to the containing axis instead.

## Joystick

5 buttons (center/left/right/up/down), read over `gpiod` with pull-down bias and 10ms debounce. GPIO pin numbers are configured in the joystick initializer.

- Left/right move along `row` axes, up/down along `column` axes.
- Any button press resets the screen sleep timer.
- `Joystick.on_button_change(handler, button=ANY, state=ANY)` supports wildcards on both button and state, so you can register one handler for "any button, pressed" separately from per-button handlers.

## Screen sleep

```yaml
general:
  sleep_after: 60   # seconds of no input before the screen turns off. -1 = never sleep
```

Sleeping just calls `device.hide()` / `device.show()` - the render loop keeps running underneath, nothing stops. A `WAKEUP` / `SLEEP` script control sequence (see [data.md](data.md#script-control-sequences)) can also drive this, independent of button presses.

## Screen transitions

Switching screens slides the old one out and the new one in (direction depends on which way you navigated), over consecutive frames - this is purely visual, the new screen's components are already prepared/drawn during the slide.

## Modal

A modal is a popup overlay, queued by a script's `MODAL` control sequence (see [data.md](data.md#script-control-sequences)) and drawn on top of whatever screen is current for a few seconds (fixed at 5s - not configurable from the escape sequence itself).

To enable it, a deployment needs a screen and component literally named `modal`, and three reserved data sources are auto-registered by the app (don't define these in `sources:` yourself) that supply the popup's icon/title/message:

- `modal.type` - resolves to `images/modal/{info,warn,error}.png`
- `modal.title`
- `modal.message`

```yaml
screens:
  modal:
    component: modal

components:
  modal:
    direction: row
    children:
      modal.icon:
        size: "50px"
        data: {source: modal.type}
        align: center
        align_v: middle
      modal.content:
        direction: column
        children:
          modal.content.title:
            size: "20px"
            data: {source: modal.title}
          modal.content.text:
            data: {source: modal.message}
```

This is boilerplate you write once per deployment - the app doesn't ship a default modal layout.
