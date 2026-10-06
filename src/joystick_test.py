from joystick import Joystick

def main():
    joystick = Joystick({
        4: Joystick.Button.CENTER,
        17: Joystick.Button.LEFT,
        22: Joystick.Button.RIGHT,
        23: Joystick.Button.DOWN,
        27: Joystick.Button.UP,
    })
    # Joystick.debug = True

    joystick.on_button_change(lambda button, button_state, event: print(button, button_state))
    joystick.watch_events()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass