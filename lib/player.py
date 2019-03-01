import pygame

from .settings import Settings

class Player(object):

    def __init__(self):
        self.px = 400
        self.py = 300
        self.vx = 0
        self.vy = 0
        self.ax = 0
        self.ay = 0

        self.image = pygame.image.load("img/player.bmp").convert()

    def get_input(self, dt):
        keystate = pygame.key.get_pressed()
        if keystate[pygame.K_UP]:
            self.ay = -.05
        if keystate[pygame.K_DOWN]:
            self.ay = .05
        if keystate[pygame.K_LEFT]:
            self.ax = -.05
        if keystate[pygame.K_RIGHT]:
            self.ax = .05
            
    def update(self, dt):

        self.ax = 0
        self.ay = 0
        
        self.get_input(dt)
        
        if self.vx > 0:
            self.vx -= Settings.FRICTION
        elif self.vx < 0:
            self.vx += Settings.FRICTION
        self.vx += self.ax
        if self.vx > 3:
            self.vx = 3
        if self.vx < -3:
            self.vx = -3

        if self.vy > 0:
            self.vy -= Settings.FRICTION
        elif self.vy < 0:
            self.vy += Settings.FRICTION
        self.vy += self.ay
        if self.vy > 3:
            self.vy = 3
        if self.vy < -3:
            self.vy = -3

        if self.vx > -.001 and self.vx < .001:
            self.vx = 0
            self.ax = 0
        if self.vy > -.001 and self.vy < .001:
            self.vy = 0
            self.ay = 0
            
        self.px += self.vx * dt
        self.py += self.vy * dt

    def render(self, screen):
        screen.blit(self.image, (self.px, self.py))

