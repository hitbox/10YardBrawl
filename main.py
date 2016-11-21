import pygame
import time

pygame.init()

SCREEN_WIDTH=800
SCREEN_HEIGHT=600
FRICTION = .02

LAYER_OVERLAY = 1
LAYER_CAMERA = 2

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

def Font(size=32):
    return pygame.font.Font(None, size)


class World(object):

    def __init__(self, camera=None, *sprites):
        if camera is None:
            camera = Camera()
        self.camera = camera
        self.sprites = []
        self.add(*sprites)
        self.debug = []

    def add(self, *sprites):
        for sprite in sprites:
            self.sprites.append(sprite)

    def ordered_sprites(self):
        def layer(sprite):
            if hasattr(sprite, 'layer'):
                return sprite.layer
            return 0

        return sorted(self.sprites, key=layer)

    def draw(self, surface):
        offset = -self.camera.rect.x, -self.camera.rect.y

        messages = []
        messages.append('offset %s' % (offset, ))

        screen_rect = surface.get_rect()
        if self.debug:
            debugfont = Font(24)

        for sprite in self.ordered_sprites():
            if hasattr(sprite, 'image') and hasattr(sprite, 'rect'):
                if hasattr(sprite, 'overlay') and sprite.overlay:
                    rect = sprite.rect
                else:
                    rect = sprite.rect.move(offset)

                surface.blit(sprite.image, rect)

                if sprite in self.debug:
                    s = 'world: %s, screen: %s' % (sprite.rect.topleft, sprite.rect.move(offset).topleft)
                    image = debugfont.render(s, True, (255, 255, 255))
                    rect.size = image.get_rect().size
                    surface.blit(image, rect.clamp(screen_rect))

        for obj in self.debug:
            if isinstance(obj, pygame.Rect):
                pygame.draw.rect(surface, (255, 255, 255), obj.move(offset), 1)

        if self.camera in self.debug:
            messages.append('camera: ' + str(self.camera.rect))

        for obj in self.debug:
            if callable(obj):
                messages.append(obj())

        y = 0
        for msg in messages:
            image = debugfont.render(msg, True, (255, 100, 100))
            rect = image.get_rect()
            rect.right = screen_rect.right - 10
            rect.y = y

            surface.blit(image, rect)
            y += rect.height

    def update(self, *args):
        for sprite in self.sprites:
            sprite.update(*args)
        self.camera.update(*args)


class FramerateSprite(pygame.sprite.Sprite):

    def __init__(self, clock, *groups):
        super(FramerateSprite, self).__init__(*groups)
        self.rect = pygame.Rect(0, 0, 0, 0)
        self._images = {}
        self._font = Font()
        self.clock = clock
        self.layer = 99
        self.overlay = True

    @property
    def image(self):
        framerate = self.clock.get_fps()
        if not framerate in self._images:
            self._images[framerate] = self._font.render(str(framerate), True, (255,255,255))
        return self._images[framerate]


class TextSprite(pygame.sprite.Sprite):

    def __init__(self, text):
        self.text = text
        self.position = (0, 0)

    def update(self, dt):
        self.image = Font().render(text, True, (255, 255, 255))
        self.rect = self.image.get_rect()
        self.rect.topleft = self.position


class Camera(pygame.sprite.Sprite):

    def __init__(self, limit=None):
        super(Camera, self).__init__()
        self.rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.lock = None

        self.focus = pygame.Rect(0, 0, 300, 100)
        self.focus.center = self.rect.center

        self.limit = limit

    def update(self, dt):
        if self.lock is None:
            return

        if self.focus.contains(self.lock.rect):
            return

        if self.focus.left > self.lock.rect.left:
            self.focus.left = self.lock.rect.left

        elif self.focus.right < self.lock.rect.right:
            self.focus.right = self.lock.rect.right

        if self.focus.top > self.lock.rect.top:
            self.focus.top = self.lock.rect.top

        elif self.focus.bottom < self.lock.rect.bottom:
            self.focus.bottom = self.lock.rect.bottom

        self.rect.center = self.focus.center

        if self.limit is not None:
            self.rect.clamp_ip(self.limit)


class Field(pygame.sprite.Sprite):

    def __init__(self):
        self.image = pygame.image.load("img/field.png").convert()
        self.rect = self.image.get_rect()


class Player(pygame.sprite.Sprite):

    def __init__(self):
        super(Player, self).__init__()
        self.px = 400
        self.py = 300
        self.vx = 0
        self.vy = 0
        self.ax = 0
        self.ay = 0

        self.image = pygame.image.load("img/player.png").convert_alpha()
        self.rect = self.image.get_rect()
        
        self.layer = 1

        self.limit = None

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

        self.rect.topleft = (self.px, self.py)

        if self.limit:
            if not self.limit.contains(self.rect):
                if self.rect.left < self.limit.left or self.rect.right > self.limit.right:
                    self.vx = 0
                if self.rect.top < self.limit.top or self.rect.bottom > self.limit.bottom:
                    self.vy = 0
                self.rect.clamp_ip(self.limit)
                self.px = self.rect.x
                self.py = self.rect.y

    def render(self, screen):
        screen.blit(self.image, (self.px, self.py))


world = World()

#background = pygame.image.load("img/field.png").convert()
field = Field()

player = Player()
player.limit = pygame.Rect(24, 0, 644 - 24, 2440)

world.camera.lock = player
world.camera.limit = field.rect.inflate(250, 250)

clock = pygame.time.Clock()

framerate = FramerateSprite(clock)

world.add(player, framerate, field)

world.debug.append(player)
world.debug.append(world.camera)
world.debug.append(world.camera.focus)
world.debug.append(player.rect)

world.debug.append(lambda: 'player.vx: {:.2f}'.format(player.vx, ))
world.debug.append(lambda: 'player.vy: {:.2f}'.format(player.vy, ))
world.debug.append(lambda: 'player.limit: %s' % (player.limit, ))

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
    
    
    #logic phase
    #world.clear(screen, background)
    world.update(dt)
    #player.update(dt)
    #camera.update(dt)
    
    #render phase
    screen.fill((0,0,0))
    world.draw(screen)
    #player.render(screen)
    
    pygame.display.flip()


pygame.display.quit()
