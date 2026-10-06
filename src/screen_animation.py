from src.render.bounding_box import BoundingBox


class ScreenAnimation:
    def __init__(self, delta_x = 0, delta_y = 0):
        self.delta_x = delta_x
        self.delta_y = delta_y
        self.target_x = None
        self.current_x = None
        self.target_y = None
        self.current_y = None

    def init(self, bb: BoundingBox):
        if self.delta_x != 0:
            self.target_x = bb.w if self.delta_x > 0 else -bb.w
        self.current_x = bb.x

        if self.delta_y != 0:
            self.target_y = bb.h if self.delta_y > 0 else -bb.h
        self.current_y = bb.y


    def step(self, screen_bb: BoundingBox) -> tuple[BoundingBox | None, BoundingBox]:
        if self.delta_x == 0 and self.delta_y == 0:
            return None, screen_bb
        if self.current_x is None or self.current_y is None:
            self.init(screen_bb)

        if self.delta_x != 0 and self.current_x != self.target_x:
            new_x = self.current_x + self.delta_x
            self.current_x = min(new_x, self.target_x) if self.delta_x > 0 else max(new_x, self.target_x)

        if self.delta_y != 0 and self.current_y != self.target_y:
            new_y = self.current_y + self.delta_y
            self.current_y = min(new_y, self.target_y) if self.delta_y > 0 else max(new_y, self.target_y)

        cx = self.current_x if self.current_x is not None else 0
        cy = self.current_y if self.current_y is not None else 0
        tx = self.target_x if self.target_x is not None else 0
        ty = self.target_y if self.target_y is not None else 0

        if cx == tx and cy == ty:
            return None, screen_bb

        old_bb = BoundingBox(screen_bb.x + cx, screen_bb.y + cy, screen_bb.w, screen_bb.h)
        new_bb = BoundingBox(screen_bb.x + cx - tx, screen_bb.y + cy - ty, screen_bb.w, screen_bb.h)
        return old_bb, new_bb