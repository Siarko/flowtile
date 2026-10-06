import queue

import os
import re

import select
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from psutil import NoSuchProcess
from queue import Queue, Empty
import threading
import time
from subprocess import Popen

import psutil
from typing import Callable

from src.screens import Component


@dataclass
class ControlCommand:
    name: str
    params: dict[str, str] = field(default_factory=dict)

class ProcessEvent(Enum):
    ALL = "all"
    START = "start"
    STOP = "stop"

ProcessEventHandler = Callable[[ProcessEvent, str], None]

class CommandRunner:
    # Keys used in commands dict
    COMMAND = 'command'
    RESTART_INTERVAL = 'restart_interval'
    BUFFERS = 'buffers'
    STDOUT = 'stdout'
    STDOUT_BUFF = 'stdout_buff'
    STDERR = 'stderr'
    EOF = 'eof'
    PROCESS = 'process'
    STARTED = 'started'
    TERMINATED_TS = 'terminated_ts'
    EXIT_CODE = 'exit_code'
    CTRL_QUEUE = 'ctrl_queue'

    # Control sequences
    CTRL_ESC = 0x1b
    CTRL_PARAMS: dict[str, list[str]] = {
        'WAKEUP': [],
        'SLEEP':  [],
        'SCREEN': ['path'],
        'MODAL':  ['type', 'title', 'message'],
    }

    def __init__(self):
        self.commands: dict[str, dict] = {}
        self.output_collection_threads = {}
        self.stop_requested = False
        self.cwd: str | None = None
        self.process_event_handlers: dict[str, list[ProcessEventHandler]] = {
            ProcessEvent.ALL.value: [],
            ProcessEvent.START.value: [],
            ProcessEvent.STOP.value: [],
        }

    def set_cwd(self, path: str | None):
        self.cwd = path

    def add_process_event_handler(self, event_type: ProcessEvent, handler: ProcessEventHandler):
        self.process_event_handlers[event_type.value].append(handler)

    # Also kills all children processes. Works with popen shell=True processes.
    @staticmethod
    def kill(native_process: Popen):
        process = psutil.Process(native_process.pid)
        try:
            for proc in process.children(recursive=True):
                proc.kill()
            process.kill()
        except NoSuchProcess:
            print(f"Process could not be killed - not found")


    # command_id: str - identifies the command
    # command: list[str] - command and arguments
    # interval: int - how long to wait before restarting process. If None, process will not be restarted.
    # Also, if process is stopped manually, it won't be restarted after given interval. Must be started manually.
    # eof_string: str - EOF string - once detected, temporary output buffer is moved to output queue and available for reading
    def add_command(self, command_id: str, command: list[str], interval = None, eof_string = None):
        self.commands[command_id] = {
            self.COMMAND: command, # list with command and arguments
            self.RESTART_INTERVAL: interval, # how long to wait before restarting process
            self.EOF: eof_string, # EOF string - once detected, temporary output buffer is moved to output queue
            self.BUFFERS: {
                self.STDOUT: Queue(), # queue with output lines
                self.STDOUT_BUFF: Queue(), # queue with output lines - used to buffer lines before receiving EOF
                self.STDERR: Queue() # Error output queue
            },
            self.PROCESS: None, # subprocess object
            self.STARTED: False, # if process should run
            self.TERMINATED_TS: None, # timestamp of last process termination
            self.EXIT_CODE: None, # Last process exit code
            self.CTRL_QUEUE: Queue() # queue for control commands
        }
        self._start_output_collection(command_id)

    def command_exists(self, command_id: str):
        if command_id not in self.commands:
            return False
        return True

    def _start_output_collection(self, command_id):
        if command_id in self.output_collection_threads:
            return
        thread = threading.Thread(
            target = self._run_output_collection,
            args = (command_id,)
        )
        thread.daemon = True
        self.output_collection_threads[command_id] = thread
        thread.start()

    def _run_output_collection(self, command_id):
        while True:
            if self.stop_requested:
                break
            time.sleep(0.01) # Avoid high CPU usage
            command_data = self.commands[command_id]
            process = command_data[self.PROCESS]
            if process is None:
                continue
            eof_string = command_data[self.EOF]
            ready_stream, _, _ = select.select([process.stdout, process.stderr], [], [], 0)
            if process.stdout in ready_stream:
                line: bytes = process.stdout.readline().rstrip()
                if len(line) > 0:
                    if line[0] == self.CTRL_ESC:
                        control_command = self.process_escape_seq(line)
                        if control_command is not None:
                            command_data[self.CTRL_QUEUE].put(control_command)
                    elif eof_string is not None:
                        if line.decode("utf-8") == eof_string:
                            lines = []
                            while True:
                                try:
                                    e = command_data[self.BUFFERS][self.STDOUT_BUFF].get_nowait()
                                    lines.append(e)
                                except queue.Empty:
                                    break
                            command_data[self.BUFFERS][self.STDOUT].put(lines)

                        else:
                            command_data[self.BUFFERS][self.STDOUT_BUFF].put(line)
                    else:
                        command_data[self.BUFFERS][self.STDOUT].put([line])

            if process.stderr in ready_stream:
                line: bytes = process.stderr.readline().rstrip()
                if len(line) > 0:
                    command_data[self.BUFFERS][self.STDERR].put(line)

            exit_code = process.poll()
            if exit_code is not None: # process has terminated
                if command_data[self.TERMINATED_TS] is None:
                    self.commands[command_id][self.TERMINATED_TS] = time.time()
                    self.commands[command_id][self.EXIT_CODE] = exit_code
                    self.dispatch_event(ProcessEvent.STOP, command_id)
                else:
                    if not self.commands[command_id][self.STARTED]:
                        continue
                    interval = command_data[self.RESTART_INTERVAL]
                    if interval is None or time.time() - command_data[self.TERMINATED_TS] > interval:
                        command_data[self.TERMINATED_TS] = None
                        self.process_start(command_id)
                        continue

    @staticmethod
    def process_escape_seq(line: bytes) -> ControlCommand | None:
        text = line[1:].decode("utf-8")  # strip \x1b
        parts = re.split(r'(?<!\\):', text)
        name = parts[0]
        if name not in CommandRunner.CTRL_PARAMS:
            return None
        param_names = CommandRunner.CTRL_PARAMS[name]
        values = [p.replace('\\:', ':') for p in parts[1:]]
        params = dict(zip(param_names, values))
        return ControlCommand(name=name, params=params)

    def process_is_running(self, command_id: str):
        if not self.command_exists(command_id):
            return False
        if self.commands[command_id][self.PROCESS] is None:
            return False
        return self.commands[command_id][self.PROCESS].poll() is None

    def process_start(self, command_id):
        if self.process_is_running(command_id):
            return
        if command_id not in self.commands:
            raise Exception(f"Command {command_id} not found")
        self.commands[command_id][self.PROCESS] = subprocess.Popen(
            args=self.commands[command_id][self.COMMAND],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd
        )
        self.commands[command_id][self.STARTED] = True
        self.commands[command_id][self.EXIT_CODE] = None
        self.commands[command_id][self.TERMINATED_TS] = None
        self.dispatch_event(ProcessEvent.START, command_id)

    def process_stop(self, command_id):
        self.commands[command_id][self.STARTED] = False
        if not self.process_is_running(command_id):
            return
        self.kill(self.commands[command_id][self.PROCESS])
        self.dispatch_event(ProcessEvent.STOP, command_id)

    # returns output queue for given command_id
    def get_output(self, command_id) -> Queue:
        return self.commands[command_id][self.BUFFERS][self.STDOUT]

    def get_error_output(self, command_id) -> Queue:
        return self.commands[command_id][self.BUFFERS][self.STDERR]

    def get_all_commands(self) -> list[str]:
        return list(self.commands.keys())

    # returns dict with command_id: output_queue
    def get_all_outputs(self) -> dict[str, Queue]:
        result = {}
        for command_id in self.commands:
            o = self.get_output(command_id)
            if not o.empty():
                result[command_id] = o
        return result

    def get_all_ctrl_outputs(self) -> list[Queue]:
        return [self.commands[cid][self.CTRL_QUEUE] for cid in self.commands]

    def create_source_callback(self, command_id: str):
        cached = []
        def callback(component: Component):
            nonlocal cached
            queue = self.get_output(command_id)
            new_lines = []
            try:
                line_set = queue.get_nowait()
                for line in line_set:
                    new_lines.append(line.decode('utf-8'))
            except Empty:
                pass
            if new_lines:
                cached = new_lines
            return cached
        return callback

    # Stop all processes and output collection threads
    def stop(self):
        self.stop_requested = True
        for command_id in self.commands:
            self.process_stop(command_id)

    def get_exit_code(self, command_id: str) -> int | None:
        return self.commands[command_id][self.EXIT_CODE]

    def dispatch_event(self, event_type: ProcessEvent, command_id: str):
        handlers = []
        handlers.extend(self.process_event_handlers[ProcessEvent.ALL.value])
        handlers.extend(self.process_event_handlers[event_type.value])
        for handler in handlers:
            handler(event_type, command_id)
