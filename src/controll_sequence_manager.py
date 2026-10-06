from _queue import Empty
from queue import Queue
from typing import Callable

from src.command_runner import ControlCommand


class ControlSequenceManager:
    def __init__(self):
        self.handlers = {}

    def register_handler(self, command_name: str, handler: Callable[[ControlCommand], None]):
        self.handlers[command_name] = handler

    def consume(self, command_queue: Queue):
        try:
            while True:
                cmd: ControlCommand = command_queue.get_nowait()
                if cmd.name in self.handlers:
                    self.handlers[cmd.name](cmd)
                else:
                    print(f"Unknown control command {cmd.name}")
        except Empty:
            pass