from code import InteractiveInterpreter
import functools
import operator
import pygame as pg
import string
import time

class config(object):
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 600

    FRICTION = .009
    ACCELERATION = .02
    MAX_VELOCITY = .5

    DEFAULT_FONT_SIZE = 32


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

def scalegetter(scale):
    def f(image):
        xer = functools.partial(operator.mul, scale)
        return pg.transform.scale(image, tuple(map(xer, image.get_size())))
    return f

def load(path, postprocessor=None):
    image = pg.image.load(path).convert_alpha()
    if callable(postprocessor):
        image = postprocessor(image)
    return image

class Animation(object):

    def __init__(self, images, delay=250):
        if not isinstance(images, list):
            images = [images]
        self.images = images
        self.timer = 0
        self.index = 0
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
        framerate = self.clock.get_fps()
        if not framerate in self._images:
            self._images[framerate] = self._font.render(str(framerate))
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

        self.layer = 1

        self.limit = None

        self.animation = 'running'
        self.animations = {
            'standing': Animation(load('img/standing.png', postprocessor=scalegetter(4))),
            'running': Animation(list(slice_image(pg.image.load('img/running.png').convert_alpha(),
                                                  14, postprocessor=scalegetter(4))),
                                 delay=100)
        }

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

        if self.vx != 0 or self.vy != 0:
            self.animation = 'running'

            v = max(map(abs, (self.vx, self.vy)))
            r = config.MAX_VELOCITY / v

            self.animations[self.animation].delay = 50 * r
        else:
            self.animation = 'standing'

        self.animations[self.animation].update(dt)

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

    world.debug.append(player)
    world.debug.append(world.camera)
    world.debug.append(world.camera.focus)
    world.debug.append(player.rect)

    world.debug.append(lambda: 'player.ax: {:.2f}'.format(player.ax, ))
    world.debug.append(lambda: 'player.ay: {:.2f}'.format(player.ay, ))
    world.debug.append(lambda: 'player.vx: {:.2f}'.format(player.vx, ))
    world.debug.append(lambda: 'player.vy: {:.2f}'.format(player.vy, ))
    world.debug.append(lambda: 'player.limit: %s' % (player.limit, ))

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

            rv = hasattr(context, 'handle') and context.handle(event)

            if not rv and event.type == pg.KEYDOWN:
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

if __name__ == '__main__':
    main()
