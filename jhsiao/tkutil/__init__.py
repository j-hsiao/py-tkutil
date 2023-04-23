import sys
if sys.version_info.major > 2:
    import tkinter as tk
else:
    import Tkinter as tk
# from .util import *

def add_bindtags(widget, *tags, **kwargs):
    """Add bind tags to widget.

    kwargs
    ======
    before: str
        Name of a tag in the current bindtags.  `tags` will be added
        before this tag.
    after: str
        Name of a tag in the current bindtags.  `tags` will be added
        after this tag.  This defaults to str(widget).
    """
    curtags = widget.bindtags()
    if kwargs.get('before'):
        position = curtags.index(kwargs['before'])
    elif kwargs.get('after', str(widget)):
        position = curtags.index(kwargs.get('after', str(widget))) + 1
    widget.bindtags(curtags[:position] + tags + curtags[position:])
