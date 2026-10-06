from functools import partial
from queue import Empty

import src.ExecMode as ExecMode
import src.command_runner as command_runner
import src.data_source_collection as DataSourceCollection
import src.screens as screens
from src.command_runner import ProcessEvent
from src.data_source import DataSource
from src.screens_schema import Key


def _on_process_stop(runner: command_runner.CommandRunner, event_type: ProcessEvent, command_id: str):
    last_error_code = runner.get_exit_code(command_id)
    if last_error_code != 0:
        print(f"Process {command_id} errored with code {last_error_code}")
        error_queue = runner.get_error_output(command_id)
        try:
            while True:
                line: bytes = error_queue.get_nowait()
                print(f"  [{command_id}] {line.decode('utf-8', errors='replace')}")
        except Empty:
            pass


def setup(config: dict, runner: command_runner.CommandRunner, command_dir: str):
    runner.set_cwd(command_dir)
    commands_data = config[Key.SOURCES]

    print("=== LOADING COMMANDS ===")
    for command_id, command_data in commands_data.items():
        interval = None
        eof_string = command_data[Key.SOURCES_EOF_STRING]
        if command_data[Key.SOURCES_EXEC_MODE] == ExecMode.ExecMode.REPEAT:
            interval = command_data[Key.SOURCES_REFRESH]
        runner.add_command(
            command_id=command_id,
            command=command_data[Key.SOURCES_SCRIPT],
            interval=interval,
            eof_string=eof_string
        )
        print(f"Added command {command_id}")
        print(f"\tCommand ID: {command_id}")
        print(f"\tCommand: {command_data[Key.SOURCES_SCRIPT]}")
        print(f"\tExec Mode: {command_data[Key.SOURCES_EXEC_MODE]}")
        print(f"\tInterval: {interval}")
        print(f"\tEOF: {eof_string}")

    runner.add_process_event_handler(
        ProcessEvent.STOP,
        partial(_on_process_stop, runner)
    )

    for command_id in runner.get_all_commands():
        source = DataSource(command_id)
        source.set_callback(runner.create_source_callback(command_id))
        DataSourceCollection.register(source)

    for command_id, command_data in commands_data.items():
        if not command_data[Key.SOURCES_AUTOSTART]:
            continue
        runner.process_start(command_id)
        print(f"Started boot command {command_id}")


def make_screen_change_handler(runner: command_runner.CommandRunner):
    def manage_screen_commands(old_screen: screens.Screen | None, new_screen: screens.Screen):
        if old_screen is not None:
            print(f"Unloading processes for screen {old_screen.screen_id}")
            for command in old_screen.get_all_commands():
                if not command["persistent"]:
                    runner.process_stop(command["name"])
        print(f"Loading processes for screen {new_screen.screen_id}")
        for command in new_screen.get_all_commands():
            runner.process_start(command["name"])

    return manage_screen_commands
