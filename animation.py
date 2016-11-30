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
scale15x = scalegetter(15)

def load(path, postprocessor=None):
    image = pg.image.load(path).convert_alpha()
    if callable(postprocessor):
        image = postprocessor(image)
    return image

def flip_x(image):
    return pg.transform.flip(image, True, False)

def flip_x_anim(a):
    return Animation([flip_x(image) for image in a.images])

class SimpleTextSprite(pg.sprite.Sprite):

    def __init__(self, text):
        self.image = Font().render(text)
        self.rect = self.image.get_rect()


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

def filename_key(fn):
    root, ext = os.path.splitext(fn)
    key = root.split('-')
    try:
        key[-1] = int(key[-1])
    except ValueError:
        pass
    return tuple(key)

def keyed_sprite_sheets():
    for dirpath, filename in sprite_sheets():
        yield (dirpath, filename, filename_key(filename))

def isint(v):
    try:
        int(v)
    except ValueError:
        return False
    else:
        return True

def grouped_sprite_sheets():
    def key(t):
        k = t[2]
        if isint(k[-1]):
            k = k[:-1]
        return k
    return groupby(sorted(keyed_sprite_sheets(), key=key), key)

def colors(image):
    for x in range(image.get_width()):
        for y in range(image.get_height()):
            yield ((x,y), image.get_at((x,y)))

def frames_debug_transparency(image):
    for coord, color in colors(image):
        alpha = color[3]
        if alpha == 0:
            print(image)
            break

def frames(images):
    return cycle(map(scale10x, slice_image(image, 16, image.get_height())))

class ClickSprite(pg.sprite.Sprite):

    def __init__(self, image, **data):
        super(ClickSprite, self).__init__()
        self.image = image
        self.rect = image.get_rect()

        for key, value in data.items():
            setattr(self, key, value)


def main():
    pg.init()

    screen = pg.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    screenrect = screen.get_rect()

    d = {}

    for shortkey, grouper in grouped_sprite_sheets():
        groups = list(grouper)

        images = (load(os.path.join(dirpath, fn)) for dirpath, fn, _ in groups)

        _, _, fullkey = groups[0]
        if not isint(fullkey[-1]):
            # should be only one simple sheet that can be split into sprites.
            #TODO: * left/right flipper
            #      * fix ref-first-down-left
            images = (image for image in slice_image(next(images), 16))

        d['-'.join(shortkey)] = cycle(scale15x(image) for image in images)

    f = Font(size=20).render
    clicksprites = [ClickSprite(f(name), name=name) for name in sorted(d)]

    active = clicksprites[0]

    y = clicksprites[0].rect.bottom
    for clicksprite in clicksprites[1:]:
        clicksprite.rect.y = y
        y = clicksprite.rect.bottom

    index = 0
    images = d[active.name]
    image = next(images)

    helpsprite = SimpleTextSprite('n/N select animation')
    helpsprite.rect.topright = screen.get_rect().topright

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
                    for i,clicksprite in enumerate(clicksprites):
                        if clicksprite is active:
                            # shift+n for backwards
                            x = -1 if event.unicode == 'N' else 1
                            active = clicksprites[(i + x) % len(clicksprites)]
                            images = d[active.name]
                            break
            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for clicksprite in clicksprites:
                        if clicksprite.rect.collidepoint(event.pos):
                            images = d[clicksprite.name]
                            active = clicksprite
                            break

        screen.fill((0,0,0))
        rect = image.get_rect()
        rect.center = screen.get_rect().center
        screen.blit(image, rect)

        for clicksprite in clicksprites:
            if clicksprite is active:
                pg.draw.rect(screen,(255,0,0),clicksprite.rect)
            screen.blit(clicksprite.image, clicksprite.rect)

        screen.blit(helpsprite.image, helpsprite.rect)

        pg.display.flip()

    pg.quit()

if __name__ == '__main__':
    main()
