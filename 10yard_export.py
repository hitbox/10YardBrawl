#!/usr/bin/python

# https://github.com/GNOME/gimp/blob/master/plug-ins/pygimp/gimpfu.py

import gtk
import logging
import os
import tempfile

from gimpfu import *

# I don't care much for gimp thinking they can clash names with the built-in debugger.
gpdb = pdb
del pdb

NAME = 'export'
LOGGING_LEVEL = logging.INFO

HELP = 'Exports the layers in a group layer named "sprites".'

class DirChooserButton(gtk.FileChooserButton):

    def __init__(self, title, backend=None):
        super(DirChooserButton, self).__init__(title, backend)
        self.set_action(gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)


class ExportWindow(gtk.Window):

    def __init__(self, image, dest):
        super(ExportWindow, self).__init__(gtk.WINDOW_TOPLEVEL)

        self.set_title('Export Sprites')

        self.image = image
        self.dest = dest
        self.log = logging.getLogger(NAME)
        self.log.setLevel(LOGGING_LEVEL)
        self.log.info('__init__')

        self.connect('delete_event', self.delete_event)
        self.connect('destroy', self.destroy)

        vbox = gtk.VBox()

        vbox.pack_start(gtk.Label(HELP))

        self.label = gtk.Label(self.dest)
        vbox.pack_start(self.label)

        button = gtk.Button('Destination Directory')
        button.connect('clicked', self.choose_dest_dir)
        vbox.pack_start(button)

        confirm = gtk.Button('OK')
        confirm.connect('clicked', self.confirm_clicked)
        vbox.pack_start(confirm)

        self.add(vbox)
        self.show_all()

    def choose_dest_dir(self, widget):
        chooser = gtk.FileChooserDialog(
                'Choose Destination Directory',
                self,
                gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_current_folder(self.dest)

        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            self.dest = chooser.get_current_folder()
        self.label.set_text(self.dest)
        chooser.destroy()

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        self.quit()

    def confirm_clicked(self, widget):
        self.export_sprites()
        self.quit()

    def error(self, text):
        message = gtk.MessageDialog(parent=self, 
                            flags=0, 
                            type=gtk.MESSAGE_INFO, 
                            buttons=gtk.BUTTONS_NONE, 
                            message_format=None)
        message.set_markup(text)
        self.log.info(text)
        message.run()

    def export_sprites(self):
        self.log.info('export_sprites')
        tempimage = self.image.duplicate()

        sprites_group = find_sprites_group(tempimage)

        if not sprites_group:
            self.error('"sprites" LayerGroup not found.')
            return

        for layer in walklayers(sprites_group):
            if isinstance(layer, gimp.GroupLayer) or ' ' in layer.name:
                continue

            tokens = layer.name.split('-')

            # copy and paste layer to new image
            gpdb.gimp_edit_copy(layer)
            export_image = gpdb.gimp_edit_paste_as_new()

            filename = '-'.join(tokens) + '.png'
            fullpath = os.path.join(self.dest, filename)

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

            self.log.info('%s exported to %s', layer, fullpath)

    def main(self):
        gtk.main()

    def quit(self):
        gtk.main_quit()


def default_directory():
    return os.path.join(tempfile.gettempdir(), '10 Yard Brawl')

def is_int(s):
    try:
        int(s)
    except ValueError:
        return False
    else:
        return True


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

    if image.filename:
        dest = os.path.join(os.path.dirname(os.path.dirname(image.filename)), 'img')
    else:
        dest = default_directory()

    logging.basicConfig(level=logging.INFO,
                        filename=os.path.join(dest, NAME + '.log'))
    logging.getLogger('').setLevel(LOGGING_LEVEL)
    log = logging.getLogger(NAME)

    try:

        log.info('started')
        log.info('image: %s', image)
        log.info('drawable: %s', drawable)

        exportwindow = ExportWindow(image, dest)
        exportwindow.main()

    except:
        log.exception('An exception occured.')
    else:
        log.info('done')

# NOTES: Gimp fails if a GroupLayer object is the drawable passed to `export`

register('export', # proc_name
         HELP, # blurb
         HELP, # help
         'CincyPy', # author
         'copyright', # copyright
         'year', # date
         '<Image>/Export/Sprites...', # label
         '*', # imagetypes
         # params
         [],
         # results
         [],
         export)

main()
