import pygame
import time

from lib.player import Player
from lib.settings import Settings
from lib.testgamestate import TestGameState

pygame.init()
screen = pygame.display.set_mode((Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT))
clock = pygame.time.Clock()

player = Player()
current_gamestate = TestGameState(player)

done = False
while not done:
    #timing
    dt = clock.tick(60)
    dt = dt / 10
    
    #input
    evtlst=pygame.event.get()
    for e in evtlst:
        if e.type == pygame.QUIT:
            done = True
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                done = True
    
    #render phase
    current_gamestate.draw(screen)
     
    #logic phase
    current_gamestate.update(dt)
    
    pygame.display.flip()


pygame.display.quit()
