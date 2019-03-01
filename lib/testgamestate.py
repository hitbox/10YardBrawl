import pygame
from .gamestate import GameState

class TestGameState(GameState):
    def __init__(self, player):
        self.background = pygame.image.load("img/background.bmp").convert()
        self.player = player

    def update(self, dt):
        self.player.update(dt)

    def draw(self, screen):
        screen.blit(self.background, (0,0))
        self.player.render(screen)
