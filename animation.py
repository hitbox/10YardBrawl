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


def textimage(s, **kwargs):
    return Font(**kwargs).render(s)

class TextSprite(pg.sprite.Sprite):

    def __init__(self, text):
        self._text = text
        self.update_image()
        self.rect = self.image.get_rect()

    def update_image(self):
        self.image = Font().render(self.text)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = str(value)
        self.update_image()


class AnimationManager(object):

    def __init__(self, animations, current=None, delay=500):
        self.animations = list(animations)

        if current is not None:
            assert current in self.animations

        self.current = current


class DataSprite(pg.sprite.Sprite):
    """
    Sprite that packed the passed in kwargs to its own attributes.
    """

    def __init__(self, image=None, **data):
        super(DataSprite, self).__init__()

        if image is not None:
            self.image = image
            self.rect = image.get_rect()

        for key, value in data.items():
            setattr(self, key, value)


class SelectSprite(pg.sprite.Sprite):

    SELECTED_COLOR = (255,0,0)
    HOVER_COLOR = (125,50,50)

    def __init__(self, image, rect=None, background_offset=(0,0)):
        super(SelectSprite, self).__init__()
        self._image = image

        if rect is None:
            rect = self._image.get_rect()
        self.rect = rect
        self._cache = None

        self.selected_color = self.SELECTED_COLOR
        self.hovering_color = self.HOVER_COLOR

        self._selected = False
        self._hovering = False

        self.background_offset = background_offset

    def get_image(self):
        if not self._cache:
            background = pg.Surface(self.rect.size)

            if self.selected:
                background.fill(self.selected_color)
            elif self.hovering:
                background.fill(self.hovering_color)

            background.blit(self._image, self.background_offset)
            self._cache = background

        return self._cache

    @property
    def image(self):
        return self.get_image()

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, value):
        self._selected = bool(value)
        self._cache = None

    @property
    def hovering(self):
        return self._hovering

    @hovering.setter
    def hovering(self, value):
        self._hovering = bool(value)
        self._cache = None


class SelectSpriteManager(object):
    
    def __init__(self, sprites, layout='vertical', anchor=None):
        assert layout in ('vertical', )

        self.sprites = list(sprites)

        max_width = max(sprite.rect.width for sprite in self.sprites)
        for sprite in self.sprites:
            sprite.rect.width = max_width
            sprite.rect.inflate_ip(12, 2)

        if anchor is None:
            anchor = self.sprites[0]

        stack(self.sprites, anchor=anchor)

        self.selected = None

    def mousemotion(self, event):
        for sprite in self.sprites:
            sprite.hovering = sprite.rect.collidepoint(event.pos)

    def mousebuttondown(self, event):
        if event.button != 1:
            return
        for sprite in self.sprites:
            sprite.selected = sprite.rect.collidepoint(event.pos)
            if sprite.selected:
                self.selected = sprite

    def move(self, d):
        if not self.selected:
            return
        for i, sprite in enumerate(self.sprites):
            if sprite is self.selected:
                break
        i = (i + d) % len(self.sprites)
        self.selected = self.sprites[i]

    def next(self):
        self.move(1)

    def previous(self):
        self.move(-1)

    def update(self, *args):
        for sprite in self.sprites:
            sprite.update(*args)

    def draw(self, screen):
        for sprite in self.sprites:
            screen.blit(sprite.image, sprite.rect)


def rendertext(text, **kwargs):
    return Font(**kwargs).render(text)

def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def stack(sprites, anchor=None, onattr='left'):
    assert onattr in ('left', 'right')

    topattr = 'top' + onattr
    bottomattr = 'bottom' + onattr

    sprites = pairwise(sprites)

    if anchor:
        _, s2  = next(sprites)
        setattr(s2.rect, topattr, getattr(anchor.rect, bottomattr))

    for s1, s2 in sprites:
        setattr(s2.rect, topattr, getattr(s1.rect, bottomattr))

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
    """
    Split filename on dash, trying to turn the last element into an integer.
    """
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

def grouped_sprite_sheets(keyed):
    """
    :param keyed: as returned from `keyed_sprite_sheets`
    """
    def key(t):
        k = t[2]
        if isint(k[-1]):
            k = k[:-1]
        return k
    return groupby(sorted(keyed, key=key), key)

def colors(image):
    for x in range(image.get_width()):
        for y in range(image.get_height()):
            yield ((x,y), image.get_at((x,y)))

def hastransparent(image):
    return any(color[3] == 0 for coord, color in colors(image))

def build_animation_cycles(grouped):
    """
    Process a grouping of sprite sheets (as returned by
    `grouped_sprite_sheets`), as a `dict` of animation cycles.

    Frame images with any transparent pixels are considered one image, instead
    of a regularly size sprite sheet.

    Special exception for `run` and `calling` to make cycling animate
    correctly Fix this in Gimp? Could just cycle back and forth, instead of
    beginning-to-end, on all animations.
    """
    anims = {}

    make_anim_key = '-'.join
    _keyflipper = {'left': 'right', 'right': 'left'}
    def keyflipper(part):
        return _keyflipper[part] if part in _keyflipper else part

    def flipkey(keytup):
        return tuple(keyflipper(part) for part in shortkey)

    for shortkey, grouper in grouped:
        images = tuple(load(os.path.join(dirpath, fn)) for dirpath, fn, _ in grouper)

        if len(images) == 3 and any(s in shortkey for s in ('run', 'calling')):
            images += tuple(images[1], )

        if len(images) == 1 and not hastransparent(images[0]):
            images = tuple(image for image in slice_image(images[0], 16))

        anims[make_anim_key(shortkey)] = cycle(scale10x(image) for image in images)

        if set(('left', 'right')).intersection(shortkey):
            otherkey = flipkey(shortkey)
            anims[make_anim_key(otherkey)] = cycle(flip_x(scale10x(image)) for image in images)

    return anims


class Game(object):

    def __init__(self):
        pg.init()
        pg.key.set_repeat(200, 25)

        self.screen = pg.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.screenrect = self.screen.get_rect()

        self.clock = pg.time.Clock()

        self.managers = []

    def run(self):
        pg.init()
        running = True
        while running:
            dt = self.clock.tick(60)

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        pg.event.post(pg.event.Event(pg.QUIT))
                else:
                    name = pg.event.event_name(event.type).lower()
                    for manager in self.managers:
                        method = getattr(manager, name, None)
                        if method:
                            method(event)
            
            for manager in self.managers:
                manager.update(dt)

            self.screen.fill((0,0,0))

            for manager in self.managers:
                manager.draw(self.screen)

            pg.display.flip()

        pg.quit()


def main():
    game = Game()

    keyed = keyed_sprite_sheets()
    grouped = grouped_sprite_sheets(keyed)
    anims = build_animation_cycles(grouped)

    selectables = [SelectSprite(textimage(name, size=18), background_offset=(6,2)) for name in sorted(anims)]
    selectable2anim = dict(zip(selectables, sorted(anims)))
    selectmanager = SelectSpriteManager(selectables)
    selectmanager.selected = selectables[0]

    game.managers.append(selectmanager)

    game.run()

if __name__ == '__main__':
    main()
