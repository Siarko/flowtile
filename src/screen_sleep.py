import time
from collections.abc import Callable


class ScreenSleep:
    def __init__(self):
        self.active = True
        self.wake_until = 0.0
        self.sleep_time = -1
        self.change_handler: Callable[[bool], None] | None = None

    def set_sleep_time(self, sleep_time: int):
        self.sleep_time = sleep_time

    def set_on_change(self, handler):
        self.change_handler = handler

    def call_change_handler(self, state: bool):
        print(f"ScreenSleep event: {state}")
        if self.change_handler is not None:
            self.change_handler(state)

    def start(self, sleep_time: int | None = None):
        if sleep_time is not None:
            duration = sleep_time
        else:
            duration = self.sleep_time
        self.wake_until = time.time() + duration
        if not self.active:
            self.active = True
            self.call_change_handler(True)

    def stop(self):
        self.wake_until = 0.0
        if self.active:
            self.active = False
            self.call_change_handler(False)

    def update(self) -> bool:
        if self.sleep_time == -1:
            return True
        if time.time() < self.wake_until:
            return True
        if self.active:
            self.active = False
            self.call_change_handler(False)
        return False