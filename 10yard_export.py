#!/usr/bin/python

from gimpfu import *

print dir()

def export():
    print "Hello, world!"
    print dir(gimp)

# register(proc_name, blurb, help, author, copyright, date, label, imagetypes,
#          params, results, function, menu=None, domain=None, on_query=None,
#          on_run=None)

register(
    "export10yardbrawl",
    "Export 10 Yard Brawl",
    """Export 10 Yard Brawl sprites.""",
    "CincyPy",
    "CincyPy",
    "2016",
    "<Toolbox>/Tools/Export/Sprites",
    "",
    [],
    [],
    export)

main()
