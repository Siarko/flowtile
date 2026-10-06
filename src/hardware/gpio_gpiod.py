import gpiod
from gpiod.line import Direction, Value

class GPIODWrapper:
    OUT = 'out'
    LOW = 0
    HIGH = 1

    def __init__(self, chip_name='/dev/gpiochip0'):
        self.chip = chip_name  # main GPIO chip
        self.lines = {}

    def setup(self, pin, direction):
        if direction.lower() == 'out':
            line = gpiod.request_lines(
		        self.chip,
		        consumer="oled",
		        config={
			        pin: gpiod.LineSettings(
				        direction=Direction.OUTPUT, output_value=Value.INACTIVE
			        )
		        }
            )
            self.lines[pin] = line
        else:
            raise NotImplementedError("Only output pins supported for OLED")

    def output(self, pin, value):
        self.lines[pin].set_value(pin, Value.ACTIVE if value else Value.INACTIVE)

    def cleanup(self):
        for line in self.lines.values():
            line.release()
        self.lines.clear()
