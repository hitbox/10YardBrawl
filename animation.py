from code import InteractiveInterpreter
import os
from itertools import groupby, cycle
import collections
import functools
import operator
import pygame as pg
import string
import time

from pprint import pprint as pp

PROJECT_DIR = os.path.dirname(__file__)

IMAGE_DIR = os.path.join(PROJECT_DIR, 'img')

class config(object):
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600

    FRICTION = .009
    ACCELERATION = .02
    MAX_VELOCITY = .5

    SPRITE_WIDTH = 8
    SPRITE_HEIGHT = 16

    DEFAULT_FONT_SIZE = 32
    DEFAULT_FRAME_DELAY = 250

    MIN_FRAME_DELAY = 25


class Font(object):

    def __init__(self, antialias=True, color=(255, 255, 255), size=None):
        if size is None:
            size = config.DEFAULT_FONT_SIZE
        self._font = pg.font.Font(None, size)
        self.antialias = antialias
        self.color = color

    def __getattr__(self, name):
        return getattr(self._font, name)

    def size(self, text):
        if text is None:
            return (0, 0)
        return self._font.size(text)

    def sizerect(self, text):
        return pg.Rect((0,0), self.size(text))

    def render(self, text, antialias=None, color=None):
        if antialias is None:
            antialias = self.antialias

        if color is None:
            color = self.color

        return self._font.render(text, antialias, color)


def alpha_surface(width, height):
    return pg.Surface((width, height), flags=pg.SRCALPHA)

def slice_image(source, width, height=None, postprocessor=None):
    if height is None:
        height = source.get_height()

    for y in range(0, source.get_height(), height):
        for x in range(0, source.get_width(), width):
            image = pg.Surface((width, height), flags=pg.SRCALPHA)
            image.blit(source, (0, 0), pg.Rect(x, y, width, height))

            if callable(postprocessor):
                image = postprocessor(image)

            yield image

def image_rows(source, height):
    width = source.get_width()
    for y in range(0, source.get_height(), height):
        dest = alpha_surface(width, height)
        dest.blit(source, (0,0), pg.Rect(0,y,width,height))
        yield dest

def image_cols(source, width):
    height = source.get_height()
    for x in range(0, source.get_width(), width):
        dest = alpha_surface(width, height)
        dest.blit(source, (0, 0), pg.Rect(x,0,width,height))
        yield dest

def scalegetter(scale):
    def f(image):
        xer = functools.partial(operator.mul, scale)
        return pg.transform.scale(image, tuple(map(xer, image.get_size())))
    return f

scale4x = scalegetter(4)
scale10x = scalegetter(10)

def load(path, postprocessor=None):
    image = pg.image.load(path).convert_alpha()
    if callable(postprocessor):
        image = postprocessor(image)
    return image

def flip_x(image):
    return pg.transform.flip(image, True, False)

def flip_x_anim(a):
    return Animation([flip_x(image) for image in a.images])

def player_frame_postprocesser(image):
    scaler = scalegetter(4)
    return scaler(image)

def player_running_animations():
    sheet = load('img/player-run.png')

    keys = ['run-%s' % key for key in 'up up-right right down-right down'.split()]
    anims = {}

    width, height = config.SPRITE_WIDTH, config.SPRITE_HEIGHT

    scaler = scalegetter(4)

    for key, y in zip(keys, range(0, sheet.get_height(), height)):
        frames = []
        for x in range(0, sheet.get_width(), width):
            frame = pg.Surface((width, height), flags=pg.SRCALPHA)
            frame.blit(sheet, (0,0), pg.Rect(x,y,width,height))
            frames.append(player_frame_postprocesser(frame))
        anims[key] = Animation(frames)

    anims['run-up-left'] = flip_x_anim(anims['run-up-right'])
    anims['run-left'] = flip_x_anim(anims['run-right'])
    anims['run-down-left'] = flip_x_anim(anims['run-down-right'])

    return anims

def player_stance_animations():
    sheet = load('img/player-stance.png')

    images = list(map(player_frame_postprocesser, image_rows(sheet, config.SPRITE_HEIGHT)))

    anims = {'stance-down': Animation([images[0]]),
             'stance-up': Animation([images[1]])}
    return anims

def player_animations():
    anims = player_running_animations()
    anims.update(player_stance_animations())
    return anims

class Animation(object):

    def __init__(self, images, delay=None):
        self.images = images
        self.timer = 0
        self.index = 0
        if delay is None:
            delay = config.DEFAULT_FRAME_DELAY
        self.delay = delay

    @property
    def image(self):
        return self.images[self.index]

    def update(self, dt):
        self.timer += dt
        if self.timer > self.delay:
            self.timer = 0
            self.index = (self.index + 1) % len(self.images)


def load_animation(path, width, height=None, postprocessor=None):
    return Animation(pg.image.load(path).convert_alpha(), width, height, postprocessor)


class Control(object):

    def __init__(self, target, attrname):
        self.label = pg.sprite.Sprite()
        self.label.image = Font().render(attrname)
        self.label.rect = self.label.image.get_rect()

        self.value = pg.sprite.Sprite()
        self.value.image = Font().render(str(getattr(target, attrname)))
        self.value.rect = self.value.image.get_rect()

        self.rect = self.label.rect.union(self.value.rect).inflate(50, 0).move(25, 0)

    def update(self, dt):
        self.label.rect = self.rect
        self.value.rect.topright = self.rect.topright

    def draw(self, surface):
        surface.blit(self.label.image, self.label.rect)
        surface.blit(self.value.image, self.value.rect)


class Textbox(pg.sprite.Sprite):

    def __init__(self, text_or_target=None, attrname=None):
        """
        :param text_or_target: None or a string to store the textbox text in
                               the instance; or a pair (target, attribute_name)
                               to get text from target.attribute_name.
        """
        super(Textbox, self).__init__()

        if text_or_target is None or isinstance(text_or_target, str):
            target = self
            attrname = '_text'
            self._text = text_or_target
        elif attrname is not None:
            target = text_or_target

        self.target = target
        self.attrname = attrname

        self.font = Font()
        self.rect = self.font.sizerect(self._text).inflate(10,10)
        self.rect.width = max(100, self.rect.width)
        self.rect.height = 25
        self.rect.topleft = (0,0)

    @property
    def text(self):
        rv = getattr(self.target, self.attrname)
        if rv is None:
            rv = ''
        return rv

    @text.setter
    def text(self, text):
        setattr(self.target, self.attrname, text)

    def handle(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            elif event.unicode in string.ascii_letters + string.digits + """ "';._:()=-+*/""":
                self.text += event.unicode
                return True

    def draw(self, surface):
        image = self.font.render(self.text)
        pg.draw.rect(surface, (255, 255, 255), self.rect, 1)
        surface.blit(image, self.rect.move(5, 5))

    def update(self, dt):
        self.rect.width = max(100, self.font.size(self.text)[0] + 10)


class Console(Textbox):

    def __init__(self, command, extragetter=None):
        super(Console, self).__init__(command)
        self.extragetter = extragetter

    def handle(self, event):
        if not super(Console, self).handle(event):
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN:

                context = globals()
                if callable(self.extragetter):
                    context.update(self.extragetter())

                interpreter = InteractiveInterpreter(context)

                code = interpreter.runsource(self.text)
                rv = interpreter.runcode(code)

                return True


class ConfigEditor(object):
    # This is like World. Now just a sort of way to switch context in the main loop.

    def __init__(self):
        self.active = False
        #self.objects = [Control(config, name) for name in dir(config) if not name.startswith('_')]
        self.objects = []

        self.position()

    def draw(self, surface):
        for obj in self.objects:
            if hasattr(obj, 'draw'):
                obj.draw(surface)

    def handle(self, event):
        for obj in self.objects:
            if hasattr(obj, 'handle'):
                rv = obj.handle(event)
                if rv:
                    return rv

    def position(self):
        y = 0
        for obj in self.objects:
            obj.rect.y = y
            y += obj.rect.height

    def update(self, dt):
        for obj in self.objects:
            obj.update(dt)


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
            debugfont = Font(24, color=(255, 100, 100))

        for sprite in self.ordered_sprites():
            if hasattr(sprite, 'image') and hasattr(sprite, 'rect'):
                if hasattr(sprite, 'overlay') and sprite.overlay:
                    rect = sprite.rect
                else:
                    rect = sprite.rect.move(offset)

                surface.blit(sprite.image, rect)

                if sprite in self.debug:
                    s = 'world: %s, screen: %s' % (sprite.rect.topleft, sprite.rect.move(offset).topleft)
                    image = debugfont.render(s)
                    rect.size = image.get_rect().size
                    rect.bottomleft = rect.topleft
                    surface.blit(image, rect.clamp(screen_rect))

        for obj in self.debug:
            if isinstance(obj, pg.Rect):
                pg.draw.rect(surface, (255, 255, 255), obj.move(offset), 1)

        if self.camera in self.debug:
            messages.append('camera: ' + str(self.camera.rect))

        for obj in self.debug:
            if callable(obj):
                messages.append(obj())

        if self.debug:
            y = 0
            for msg in messages:
                image = debugfont.render(msg)
                rect = image.get_rect()
                rect.right = screen_rect.right - 10
                rect.y = y

                surface.blit(image, rect)
                y += rect.height

    def update(self, *args):
        for sprite in self.sprites:
            sprite.update(*args)
        self.camera.update(*args)


class FramerateSprite(pg.sprite.Sprite):

    def __init__(self, clock, *groups):
        super(FramerateSprite, self).__init__(*groups)
        self.rect = pg.Rect(0, 0, 0, 0)
        self._images = {}
        self._font = Font()
        self.clock = clock
        self.layer = 99
        self.overlay = True

    @property
    def image(self):
        framerate = '{:.2f}'.format(self.clock.get_fps())
        if not framerate in self._images:
            self._images[framerate] = self._font.render(framerate)
        return self._images[framerate]


class TextSprite(pg.sprite.Sprite):

    def __init__(self, text):
        self.text = text
        self.position = (0, 0)

    def update(self, dt):
        self.image = Font().render(self.text)
        self.rect = self.image.get_rect()
        self.rect.topleft = self.position


class Camera(pg.sprite.Sprite):

    def __init__(self, limit=None):
        super(Camera, self).__init__()
        self.rect = pg.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        self.lock = None

        self.focus = pg.Rect(0, 0, 250, 250)
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


class FootballField(pg.sprite.Sprite):

    def __init__(self):
        self.image = pg.image.load("img/field.png").convert()
        self.rect = self.image.get_rect()


class Player(pg.sprite.Sprite):

    def __init__(self):
        super(Player, self).__init__()
        self.px = config.SCREEN_WIDTH / 2
        self.py = config.SCREEN_HEIGHT / 2
        self.vx = 0
        self.vy = 0
        self.ax = 0
        self.ay = 0

        self.lx = self.px
        self.ly = self.py

        self.layer = 1

        self.limit = None

        self.animation = 'stance-up'
        self.animations = player_animations()

        self.rect = self.animations[self.animation].image.get_rect()

    @property
    def image(self):
        return self.animations[self.animation].image

    def get_input(self, dt):
        keystate = pg.key.get_pressed()
        if keystate[pg.K_UP]:
            self.ay = -config.ACCELERATION
        if keystate[pg.K_DOWN]:
            self.ay = config.ACCELERATION
        if keystate[pg.K_LEFT]:
            self.ax = -config.ACCELERATION
        if keystate[pg.K_RIGHT]:
            self.ax = config.ACCELERATION

    def update_limit(self):
        if self.limit:
            if not self.limit.contains(self.rect):
                if self.rect.left < self.limit.left or self.rect.right > self.limit.right:
                    self.vx = 0
                if self.rect.top < self.limit.top or self.rect.bottom > self.limit.bottom:
                    self.vy = 0
                self.rect.clamp_ip(self.limit)
                self.px = self.rect.x
                self.py = self.rect.y

    def update_animation(self, dt):
        delay = config.DEFAULT_FRAME_DELAY
        if self.vx == 0 and self.vy == 0:
            self.animation = 'stance-up'
        else:
            tokens = ['run']

            if self.vy != 0:
                tokens.append('up' if self.vy < 0 else 'down')
            if self.vx != 0:
                tokens.append('left' if self.vx < 0 else 'right')

            self.animation = '-'.join(tokens)

            v = max(map(abs, (self.vx, self.vy)))
            r = 1 - (v / config.MAX_VELOCITY)
            if r > 0:
                delay *= r
            else:
                delay = 0

            if delay < config.MIN_FRAME_DELAY:
                delay = config.MIN_FRAME_DELAY

        self.animations[self.animation].delay = delay

        self.animations[self.animation].update(dt)

    def update(self, dt):

        self.ax = 0
        self.ay = 0

        self.get_input(dt)

        if self.vx > 0:
            self.vx -= config.FRICTION
        elif self.vx < 0:
            self.vx += config.FRICTION
        self.vx += self.ax
        if self.vx > config.MAX_VELOCITY:
            self.vx = config.MAX_VELOCITY
        if self.vx < -config.MAX_VELOCITY:
            self.vx = -config.MAX_VELOCITY

        if self.vy > 0:
            self.vy -= config.FRICTION
        elif self.vy < 0:
            self.vy += config.FRICTION
        self.vy += self.ay
        if self.vy > config.MAX_VELOCITY:
            self.vy = config.MAX_VELOCITY
        if self.vy < -config.MAX_VELOCITY:
            self.vy = -config.MAX_VELOCITY

        if self.vx > -config.FRICTION and self.vx < config.FRICTION:
            self.vx = 0
            self.ax = 0
        if self.vy > -config.FRICTION and self.vy < config.FRICTION:
            self.vy = 0
            self.ay = 0

        self.lx = self.px
        self.ly = self.py

        self.px += self.vx * dt
        self.py += self.vy * dt

        self.rect.topleft = (self.px, self.py)

        self.update_limit()
        self.update_animation(dt)

    def render(self, screen):
        screen.blit(self.image, (self.px, self.py))


def main():
    pg.init()
    screen = pg.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))

    world = World()

    footballfield = FootballField()

    player = Player()
    player.limit = pg.Rect(24, 0, 644 - 24, 2440)

    world.camera.lock = player
    world.camera.limit = footballfield.rect.inflate(250, 250)

    clock = pg.time.Clock()

    framerate = FramerateSprite(clock)

    namesprite = TextSprite('PLAYER NAME')

    world.add(player, framerate, footballfield, namesprite)

    debug_boxes = [player, world.camera, world.camera.focus, player.rect]

    debug_player = [
        lambda: 'ax: {:03.2f}'.format(player.ax, ),
        lambda: 'ay: {:03.2f}'.format(player.ay, ),
        lambda: 'vx: {:03.2f}'.format(player.vx, ),
        lambda: 'vy: {:03.2f}'.format(player.vy, ),
        lambda: 'limit: %s' % (player.limit, ),
        lambda: 'anim.delay: {:03.0f}'.format(player.animations[player.animation].delay, ),
    ]

    configeditor = ConfigEditor()

    configeditor.objects.append(Console('import pdb; pdb.set_trace()'))

    context = world

    done = False
    while not done:
        #timing
        dt = clock.tick(60)

        #input
        evtlst = pg.event.get()
        for event in evtlst:
            #print(event)
            if event.type == pg.QUIT:
                done = True

            other_handled = hasattr(context, 'handle') and context.handle(event)

            if not other_handled and event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    if context is world:
                        done = True
                    elif context is configeditor:
                        pg.key.set_repeat()
                        context = world
                elif event.key == pg.K_TAB:
                    if context is world:
                        context = configeditor
                    elif context is configeditor:
                        context = world
                elif event.unicode == '?':
                    if world.debug:
                        world.debug.clear()
                    else:
                        world.debug.extend(debug_boxes)
                        world.debug.extend(debug_player)


        #logic phase
        #world.clear(screen, background)
        context.update(dt)
        #player.update(dt)
        #camera.update(dt)

        #render phase
        screen.fill((0,0,0))
        context.draw(screen)
        #player.render(screen)

        pg.display.flip()

def pngs():
    "generator to return all the png paths"
    for dirpath, dirnames, filenames in os.walk(IMAGE_DIR):
        for filename in filenames:
            if filename.endswith('.png'):
                yield (dirpath, filename)

def sprite_sheets():
    exclude = ('background.png', 'background.bmp', 'player-run.png', 'player-stance', 'field.png')
    for dirpath, filename in pngs():
        if filename in exclude:
            continue
        yield (dirpath, filename)

def keyed_sprite_sheets():
    for dirpath, filename in sprite_sheets():
        root, ext = os.path.splitext(filename)
        yield (dirpath, filename, root)

def grouped_sprite_sheets():
    third = operator.itemgetter(2)
    return groupby(sorted(keyed_sprite_sheets(), key=third), third)

def colors(image):
    for x in range(image.get_width()):
        for y in range(image.get_height()):
            yield ((x,y), image.get_at((x,y)))

def frames(image):
    for coord, color in colors(image):
        alpha = color[3]
        if alpha == 0:
            print(image)
            break

# NOTES: Trying to work out a way to automatically deal with the irregullarly
#        sized frames inside some of the sprite sheets.
#        Detect transparent pixels
#          Find the transparent box and determine that frame's size and the others.
#        Make the frames the same size as the biggest frame and crop the transparencies.

def main():
    pg.init()

    screen = pg.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))

    d = {}
    for key, grouper in grouped_sprite_sheets():
        dirpath, filename, _ = next(grouper)
        d[key] = load(os.path.join(dirpath, filename))

    for key, image in d.items():
        d[key] = frames(image)
        #d[key] = cycle(map(scale10x, slice_image(image, 16, image.get_height())))

    return

    def next_images(index):
        return d[list(d.keys())[index]]

    index = 0
    images = next_images(index)

    timer = 0

    clock = pg.time.Clock()

    running = True
    while running:
        dt = clock.tick(60)

        timer += dt
        if timer >= 500:
            timer = 0
            image = next(images)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.event.post(pg.event.Event(pg.QUIT))
                elif event.key == pg.K_n:
                    index = (index + 1) % len(d)
                    images = next_images(index)

        screen.fill((0,0,0))
        rect = image.get_rect()
        rect.center = screen.get_rect().center
        screen.blit(image, rect)
        pg.display.flip()

if __name__ == '__main__':
    main()
