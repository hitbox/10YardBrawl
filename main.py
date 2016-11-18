import pygame
import time

pygame.init()

SCREEN_WIDTH=800
SCREEN_HEIGHT=600
FRICTION = .02
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

background = pygame.image.load("img/background.bmp").convert()

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
            self.vx -= FRICTION
        elif self.vx < 0:
            self.vx += FRICTION
        self.vx += self.ax
        if self.vx > 3:
            self.vx = 3
        if self.vx < -3:
            self.vx = -3

        if self.vy > 0:
            self.vy -= FRICTION
        elif self.vy < 0:
            self.vy += FRICTION
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

player = Player()
clock = pygame.time.Clock()

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
            #elif e.key == pygame.K_UP:
                #player.vy = -1
            #    player.ay = -.05
            #elif e.key == pygame.K_DOWN:
                #player.vy = 1
                #player.ay = .05
            #elif e.key == pygame.K_LEFT:
                #player.vx = -1
            #    player.ax = -.05
            #elif e.key == pygame.K_RIGHT:
                #player.vx = 1
            #    player.ax = .05
        if e.type == pygame.KEYUP:
            pass
            #if e.key == pygame.K_UP:
                #player.vy = - 0
            #    player.ay = 0
            #if e.key == pygame.K_DOWN:
                #player.vy = 0
            #    player.ay = 0
            #if e.key == pygame.K_LEFT:
                #player.vx = 0
            #    player.ax = 0
            #if e.key == pygame.K_RIGHT:
                #player.vx = 0
            #    player.ax = 0
    
    
    #render phase
    screen.blit(background, (0,0))
    player.render(screen)
    
    #logic phase
    player.update(dt)
    
    pygame.display.flip()


pygame.display.quit()
