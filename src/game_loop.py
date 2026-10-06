import time

class GameLoop:

    def __init__(self):
        self.target_fps: int = 30
        self.animation_fps: int = 30
        self.last_time: float | None = None
        self.running: bool = True
        self.animation_mode: bool = False

    def set_animation_mode(self, flag: bool):
        self.animation_mode = flag

    def set_target_fps(self, fps: int):
        self.target_fps = fps

    def set_animation_fps(self, fps: int):
        self.animation_fps = fps


    def update(self):
        target = self.target_fps if not self.animation_mode else self.animation_fps
        now = time.time()
        if self.last_time is not None:
            elapsed = now - self.last_time
            sleep_time = (1.0 / target) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        self.last_time = time.time()

    def stop(self):
        self.running = False

    def is_running(self) -> bool:
        return self.running