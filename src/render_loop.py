import src.component_registry as component_registry
from luma.core.render import canvas


def run(game_loop, runner, screen_manager, sleep_controller, modal_renderer, control_manager, device):
    while game_loop.is_running():
        for ctrl_queue in runner.get_all_ctrl_outputs():
            control_manager.consume(ctrl_queue)

        prepared = []
        for component in component_registry.get_persistent_components():
            component.prepare([])
            prepared.append(component.name)

        current_screen = screen_manager.get_current_screen()
        current_screen.prepare(prepared)

        if sleep_controller.update():
            with canvas(device) as draw:
                screen_manager.draw(draw, device)
                if modal_renderer.is_active():
                    modal_renderer.render(draw, device)

        game_loop.update()
