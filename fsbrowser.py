import pygame as pg

#this shouldn't work, just copied over to a new file to get it out of animation.py

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
