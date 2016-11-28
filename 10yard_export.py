#!/usr/bin/python

# https://github.com/GNOME/gimp/blob/master/plug-ins/pygimp/gimpfu.py

import gtk
import logging
import os
import tempfile

from gimpfu import *

# I don't care much for gimp thinking they clash names with the built-in debugger.
gpdb = pdb
del pdb

#TODO: ensure dir exists
tempdir = os.path.join(tempfile.gettempdir(), '10 Yard Brawl')

class Window(gtk.Window):
    """
    Convenience window class.
    """

    def __init__(self):
        super(Window, self).__init__(gtk.WINDOW_TOPLEVEL)

        self.connect('delete_event', self.delete_event)
        self.connect('destroy', self.destroy)

        self.show_all()

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def main(self):
        gtk.main()


def is_int(s):
    try:
        int(s)
    except ValueError:
        return False
    else:
        return True

class ExportWindow(Window):

    def __init__(self, image):
        super(ExportWindow, self).__init__()
        self.image = image
        self.log = logging.getLogger('10yardbrawl.ExportWindow')
        self.log.setLevel(logging.INFO)

        self.button = gtk.Button('Debug')
        self.button.connect('clicked', self.debug, None)
        self.add(self.button)

        self.show_all()

    def debug(self, widget, data=None):
        try:
            return self._debug()
        except:
            self.log.exception('Exception')

    def _debug(self):
        tempimage = self.image.duplicate()

        sprites_group = find_sprites_group(tempimage)

        if not sprites_group:
            self.log.info('"sprites" LayerGroup not found.')
            return

        for dirpath, dirnames, filenames in os.walk(tempdir):
            for filename in filenames:
                if filename.endswith('.png'):
                    os.remove(os.path.join(dirpath, filename))
                    self.log.info('removed: %s', os.path.join(dirpath, filename))

        for layer in walklayers(sprites_group):
            if isinstance(layer, gimp.GroupLayer) or ' ' in layer.name:
                continue

            tokens = layer.name.split('-')

            if is_int(tokens[-1]):
                # XXX: Not dealing with layers that need to be combined and aligned yet.
                continue

            # copy and paste layer to new image
            gpdb.gimp_edit_copy(layer)
            export_image = gpdb.gimp_edit_paste_as_new()

            filename = '-'.join(tokens) + '.png'
            fullpath = os.path.join(tempdir, filename)

            #gpdb.plug_in_zealouscrop(export_image, export_image.layers[0])

            INTERLACE = False
            COMPRESSION = 9
            SAVE_BACKGROUND_COLOR = True
            SAVE_GAMMA = False
            SAVE_LAYER_OFFSET = False
            SAVE_CREATION_TIME = False
            SAVE_COLOR_TRANSPARENT = False
            gpdb.file_png_save(export_image, export_image.layers[0], fullpath,
                               filename, INTERLACE, COMPRESSION,
                               SAVE_BACKGROUND_COLOR, SAVE_GAMMA,
                               SAVE_LAYER_OFFSET, SAVE_CREATION_TIME,
                               SAVE_COLOR_TRANSPARENT)


def find_sprites_group(image_or_layers):
    for layer in walklayers(image_or_layers):
        if layer.name == 'sprites':
            return layer

def walklayers(arg):
    """
    Generator to get all the layers recursively.

    :param arg: Either an iterable of gimp.Layer objects or something with a `layers` attribute.
    """
    layers = arg.layers if hasattr(arg, 'layers') else arg

    for layer in layers:
        yield layer
        if hasattr(layer, 'layers'):
            for layer in walklayers(layer.layers):
                yield layer

def export(image, drawable):
    logging.basicConfig(level=logging.INFO,
                        filename=os.path.join(tempdir, '10yardbrawl.txt'))
    logging.getLogger('10yardbrawl').setLevel(logging.INFO)
    log = logging.getLogger('10yardbrawl.export')

    log.info('started')

    try:
        window = ExportWindow(image)
        window.main()
    except:
        log.exception('Exception')

    log.info('done')

# register(proc_name, blurb, help, author, copyright, date, label, imagetypes,
#          params, results, function, menu=None, domain=None, on_query=None,
#          on_run=None)

# NOTES: 1. image and drawable seem to be automatically passed
#        2.
#
# TODO: 1. Selectable layer, automatically picking one named "sprites".
#       2. Get rid of custom GTK Window, this should be possible with the register interface.
#       3. Handle irregular layers.

register("export", # proc_name
         "ExportWindow 10 Yard Brawl", # blurb
         "ExportWindow 10 Yard Brawl sprites.", # help
         "CincyPy", # author
         "copyright", # copyright
         "year", # date
         "<Image>/Sprites/Export...", # label
         "*", # imagetypes
         [], # params
         [], # results
         export, # function
         )

main()
