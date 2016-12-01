import collections
import functools
import operator
import os
import pygame as pg
import sqlite3
import string
import time

from itertools import groupby, cycle, chain, tee

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


class TextSprite(pg.sprite.Sprite):

    def __init__(self, text):
        self.image = Font().render(text)
        self.rect = self.image.get_rect()


class DataSprite(pg.sprite.Sprite):

    def __init__(self, image=None, **data):
        super(DataSprite, self).__init__()

        if image is not None:
            self.image = image
            self.rect = image.get_rect()

        for key, value in data.items():
            setattr(self, key, value)


class Context(object):

    def __init__(self):
        pg.init()
        self.screen = pg.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.framerate = 60
        self.clock = pg.time.Clock()
        self.sprites = []

    def add(self, *sprites):
        self.sprites.extend(sprites)

    def draw(self, dest):
        for sprite in self.sprites:
            try:
                image, rect = sprite.image, sprite.rect
            except AttributeError:
                sprite.draw(dest)
            else:
                dest.blit(image, rect)

    def handle(self, event):
        pass

    def main(self):
        running = True
        while running:
            dt = self.clock.tick(self.framerate)

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                else:
                    self.handle(event)

            self.update(dt)

            self.screen.fill((0,0,0))
            self.draw(self.screen)

            pg.display.flip()

    def post(self, event_type):
        pg.event.post(pg.event.Event(event_type))

    def update(self, *args):
        for sprite in self.sprites:
            sprite.update(*args)


def rendertext(text, **kwargs):
    return Font(**kwargs).render(text)

class PathSprite(pg.sprite.Sprite):

    def __init__(self, path=None, showfull=False):
        super(PathSprite, self).__init__()

        if path is None:
            path = os.path.abspath(os.path.dirname(__file__))
        self.path = path

        self.showfull = showfull

        self.image = rendertext(self.path)
        self.rect = self.image.get_rect()

    def parent(self):
        self.path = os.path.dirname(self.path)
        return self

    def join(self, path):
        self.path = os.path.join(self.path, path)
        return self

    def listing(self):
        def keyfunc(item):
            return int(os.path.isdir(item))
        items = (os.path.join(self.path, item) for item in os.listdir(self.path))
        return sorted(items, key=keyfunc, reverse=True)

    def update(self, *args):
        text = self.path if self.showfull else os.path.basename(self.path)
        self.image = rendertext(text,
                                color=(75,75,255) if os.path.isdir(os.path.abspath(self.path)) else (255,255,255))
        if self.rect is None:
            self.rect = self.image.get_rect()
        else:
            self.rect.size = self.image.get_size()


class SelectDir(Context):

    def __init__(self):
        super(SelectDir, self).__init__()

        self.currentdirectory = PathSprite(showfull=True)
        self.selected = None

        self.refresh()

    def refresh(self):
        self.sprites = [PathSprite(item) for item in self.currentdirectory.listing()]

        if self.sprites:
            self.selected = self.sprites[0]
            self.selected.rect.topleft = self.currentdirectory.rect.bottomleft

            stack(self.sprites)
        else:
            self.selected = None

    def handle(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                self.post(pg.QUIT)
            elif event.key in (pg.K_UP, pg.K_DOWN):
                if self.selected:
                    x = -1 if event.key == pg.K_UP else 1
                    i = (self.sprites.index(self.selected) + x) % len(self.sprites)
                    while True:
                        if self.sprites[i] is not self.currentdirectory:
                            break
                        i = (i + x) % len(self.sprites)
                    self.selected = self.sprites[i]
            elif event.key == pg.K_BACKSPACE:
                self.currentdirectory.parent()
                self.refresh()
            elif event.key == pg.K_RETURN:
                if self.selected and os.path.isdir(self.selected.path):
                    self.currentdirectory.join(self.selected.path)
                    self.refresh()

    def draw(self, dest):
        if self.selected:
            pg.draw.rect(dest,(255,0,0),self.selected.rect.inflate(12,2), 1)
        dest.blit(self.currentdirectory.image, self.currentdirectory.rect)
        super(SelectDir, self).draw(dest)

    def update(self, *args):
        super(SelectDir, self).update(*args)
        self.currentdirectory.update(*args)


def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def stack(sprites, onattr='left'):
    topattr, bottomattr = {
            'left': ('bottomleft', 'topleft'),
            'right': ('bottomright', 'topright')}[onattr]
    for s1, s2 in pairwise(sprites):
        setattr(s2.rect, bottomattr, getattr(s1.rect, topattr))

def hasattrs(obj, *attrs):
    return any(hasattr(atter) for attr in attrs)

def hasallattrs(obj, *attrs):
    return all(hasattr(atter) for attr in attrs)

def alpha_surface(width, height):
    return pg.Surface((width, height), flags=pg.SRCALPHA)

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

def load(path, postprocessor=None):
    image = pg.image.load(path).convert_alpha()
    if callable(postprocessor):
        image = postprocessor(image)
    return image

def flip_x(image):
    return pg.transform.flip(image, True, False)

def flip_x_anim(a):
    return Animation([flip_x(image) for image in a.images])

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

def hastransparent(image):
    return any(color[3] == 0 for coord, color in colors(image))

def frames(images):
    return cycle(map(scale10x, slice_image(image, 16, image.get_height())))

def get_animations():
    anims = {}

    for shortkey, grouper in grouped_sprite_sheets():
        images = tuple(load(os.path.join(dirpath, fn)) for dirpath, fn, _ in grouper)

        if len(images) == 3 and any(s in shortkey for s in ('run', 'calling')):
            images += (images[1], )

        if len(images) == 1 and not hastransparent(images[0]):
            images = (image for image in slice_image(images[0], 16))

        #TODO: left/right flipper
        anims['-'.join(shortkey)] = cycle(scale10x(image) for image in images)

    return anims

def main():
    filebrowser = SelectDir()
    filebrowser.main()
    pg.quit()

def main2():
    pg.init()

    screen = pg.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    screenrect = screen.get_rect()

    anims = get_animations()

    f = Font(size=20).render
    datasprites = [DataSprite(f(name), name=name) for name in sorted(anims)]

    active = datasprites[0]

    for datasprite in datasprites:
        datasprite.rect.x += 8

    y = datasprites[0].rect.bottom
    for datasprite in datasprites[1:]:
        datasprite.rect.y = y
        y = datasprite.rect.bottom

    index = 0
    images = anims[active.name]
    image = next(images)

    helpsprite = TextSprite('UP/DOWN Select Animation')
    helpsprite.rect.topright = screen.get_rect().topright

    delaysprite = DataSprite(Font().render('a/z delay'), delay=250)
    delaysprite.rect.topright = helpsprite.rect.bottomright

    timer = 0

    clock = pg.time.Clock()

    running = True
    while running:
        dt = clock.tick(60)

        timer += dt
        if timer >= delaysprite.delay:
            timer = 0
            image = next(images)

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    pg.event.post(pg.event.Event(pg.QUIT))
                elif event.key in (pg.K_UP, pg.K_DOWN):
                    for i,datasprite in enumerate(datasprites):
                        if datasprite is active:
                            x = -1 if event.key == pg.K_UP else 1
                            active = datasprites[(i + x) % len(datasprites)]
                            images = anims[active.name]
                            break
                elif event.key in (pg.K_a, pg.K_z):
                    delaysprite.delay += 10 if event.key == pg.K_a else -10
                    if delaysprite.delay < 0:
                        delaysprite.delay = 0
                    elif delaysprite.delay > 1000:
                        delaysprite.delay = 1000

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for datasprite in datasprites:
                        if datasprite.rect.collidepoint(event.pos):
                            images = anims[datasprite.name]
                            active = datasprite
                            break

        screen.fill((0,0,0))
        rect = image.get_rect()
        rect.center = screen.get_rect().center
        screen.blit(image, rect)

        pg.draw.rect(screen,(255,0,0),active.rect.inflate(12,2))
        for datasprite in datasprites:
            screen.blit(datasprite.image, datasprite.rect)

        screen.blit(helpsprite.image, helpsprite.rect)
        screen.blit(delaysprite.image, delaysprite.rect)

        pg.display.flip()

    pg.quit()

if __name__ == '__main__':
    main()
