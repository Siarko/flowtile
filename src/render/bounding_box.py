
class BoundingBox:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.x2 = x + w
        self.y = y
        self.y2 = y + h
        self.w = w
        self.h = h
