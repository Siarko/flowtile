import threading
import gpiod
from typing import Callable
from enum import Enum
from gpiod.line import Bias, Edge, Direction
from datetime import timedelta

class Joystick:

    class Button(Enum):
        CENTER = 0
        LEFT = 1
        RIGHT = 2
        UP = 3
        DOWN = 4
        ANY = 5

    class ButtonState(Enum):
        UP = 0
        DOWN = 1
        ANY = 2

    debug = False
    HANDLER_TYPE = Callable[[Button, ButtonState, gpiod.EdgeEvent], None]

    def __init__(self, lines: dict[int, Button], gpio_chip = "/dev/gpiochip0"):
        self.line_mapping = lines.copy()
        self.handlers: dict[str, list[Joystick.HANDLER_TYPE]] = {}
        self.request = gpiod.request_lines(
            gpio_chip,
            consumer="joystick",
            config={
                tuple(lines.keys()): gpiod.LineSettings(
                    edge_detection=Edge.BOTH,
                    bias=Bias.PULL_DOWN,
                    direction=Direction.INPUT,
                    debounce_period=timedelta(milliseconds=10),
                )
            }
        )

    def on_button_change(
            self,
            handler: HANDLER_TYPE,
            button: Button = Button.ANY,
            state: ButtonState = ButtonState.ANY
    ):
        handler_id = self._get_handler_id(button, state)
        if handler_id not in self.handlers:
            self.handlers[handler_id] = []
        self.handlers[handler_id].append(handler)
        self._print(f"Added Handler for ID {handler_id}")

    def _call_event(
            self,
            button: Button,
            button_state: ButtonState,
            event: gpiod.EdgeEvent,
            pass_button = None,
            pass_state = None
    ):
        handler_id = self._get_handler_id(button, button_state)
        event_button = pass_button if pass_button else button
        event_state = pass_state if pass_state else button_state

        self._print(f"Handler ID: {handler_id}")
        if handler_id in self.handlers:
            self._print(f"Handler Count: {len(self.handlers[handler_id])}")
            for handler in self.handlers[handler_id]:
                handler(event_button, event_state, event)
        else:
            self._print(f"No handler found for handler ID: {handler_id}")

    def update(self):
        for event in self.request.read_edge_events():
            button = self.line_mapping[event.line_offset] or None
            button_state = self.ButtonState.DOWN if event.event_type == event.Type.RISING_EDGE else self.ButtonState.UP
            if Joystick.debug and button is not None:
                self._event_print_debug(button, button_state, event)
            if button is None:
                continue
            self._call_event(button, button_state, event)
            self._call_event(self.Button.ANY, button_state, event, button, button_state)
            self._call_event(button, self.ButtonState.ANY, event, button, button_state)
            self._call_event(self.Button.ANY, self.ButtonState.ANY, event, button, button_state)

    def watch_events(self):
        thread = threading.Thread(target=self._watch_loop, daemon=True)
        thread.start()

    def _watch_loop(self):
        while True:
            self.update()


    @staticmethod
    def _get_handler_id(button: Button, state: ButtonState):
        return "{}.{}".format(button.name, state.name)

    @staticmethod
    def _event_print_debug(button: Button, button_state: ButtonState, event):
        print("-- Event Received")
        native_edge = "Unknown"
        if event.event_type is event.Type.RISING_EDGE:
            native_edge = "Rising"
        if event.event_type is event.Type.FALLING_EDGE:
            native_edge = "Falling"
        print(
            "NATIVE: line: {}  type: {:<7}  event #{}".format(
                event.line_offset, native_edge, event.line_seqno
            )
        )
        print(f"BOUND: button: {button} state: {button_state}")

    @staticmethod
    def _print(*args):
        if Joystick.debug:
            print(*args)