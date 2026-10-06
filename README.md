# FlowTile

Config-driven status display for small monochrome screens. 
Runs shell scripts, transforms their output with a small expression language, and 
draws the results as a grid of tiles on attached display.
Navigation via a 5-button GPIO joystick.

Both display and joystick can be configured (custom initializers if necessary)

Designed for Raspberry Pi on OpenWrt, but works anywhere you have a supported display and GPIO.

## Documentation

- [Overview & architecture](docs/overview.md)
- [Examples](docs/examples.md)
- [Config files](docs/config.md)
- [Components](docs/components.md)
- [Data pipeline](docs/data.md)
- [Flowline expression language](docs/flowline.md)
- [Navigation](docs/navigation.md)
- [General settings](docs/general.md)
- [Development](docs/development.md)
