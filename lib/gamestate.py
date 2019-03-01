class GameState(object):
    def __init__(self):
        pass
    def update(self, dt):
        raise NotImplementedError("Gamestate does not implement update()")
    def draw(self, screen):
        raise NotImplementedError("Gamestate does not implement draw()")
