from __future__ import print_function
__all__ = []

import bisect
from itertools import cycle
import sys

from .. import exports
from .scrollframe import Scrollframe, tk
from .util import subclass, class_bind, local_callbacks
from .emacsentry import EmacsEntry

if sys.version_info.major > 2:
    from tkinter import font
else:
    from itertools import izip as zip
    import tkFont as font
    range = xrange
    chr = unichr
    _max = max
    def max(*args, **kwargs):
        default = kwargs.pop('default', None)
        try:
            return _max(*args, **kwargs)
        except ValueError:
            if default is not None:
                return default
            raise

public = public(__all__)

class IDInd(object):
    def __getitem__(self, i):
        return i

idind = IDInd()

_LOWER = 0
_RAW = 1
_LABEL = 2
_LIND = 3
_RIND = 4
class ItemSelector(Scrollframe):
    """Display choices and with case (in)sensitive selection.

    Insensitive selection is used if the query.lower() == query.
    Otherwise, selection will be case sensitive.
    """
    _LABEL_PROPERTIES = dict(
        anchor='w',
        border=1,
        padx=0,
        pady=0,
        highlightthickness=0)
    def __init__(self, *args, **kwargs):
        """Initialize ItemSelector.

        Additional kwargs:
            choices: sequence of strs to choose from.
            labelstyle: dict of :
                font: font to use (TkDefaultFont)
                activebg: selected bg color (black)
                activefg: selected fg color (white)
                bg: unselected bg color (black)
                fg: unselected fg color (dark gray)
            These are not tkinter properties so they are not
            accessible via cget and so forth.
        """
        choices = kwargs.pop('choices', ())
        labelstyle = kwargs.pop('labelstyle', {})
        kwargs.setdefault('showx', False)
        kwargs.setdefault('showy', False)
        Scrollframe.__init__(self, *args, **kwargs)
        subclass(self, ItemSelector)
        class_bind(self, ItemSelector, dict(Configure=self._arrange))
        self._scrollframe = Scrollframe(self)
        self._labelstyle = labelstyle
        self._selected = dict(
            background=self._labelstyle.pop('activebg', 'black'),
            foreground=self._labelstyle.pop('activefg', 'white'))
        self._unselected = dict(
            background=self._labelstyle.pop('bg', 'black'),
            foreground=self._labelstyle.pop('fg', 'dark gray'))
        self._labelstyle.setdefault(
            'font', font.nametofont('TkDefaultFont'))
        self._labelstyle.update(self._LABEL_PROPERTIES)
        self._data = [[], [], [], [], []]
        self._longest = 0
        self.frame.configure(background=self._unselected['background'])
        self._prep_choices(choices)

    def _next_prefix(self, s):
        """Return the next string (increment last char/extend length)

        If the last char is the last representable char (sys.maxunicode)
            then append the last char until length + 1
        NOTE: could wrap around and increment second-to-last if last char
        is the last representable char, but this method is simpler
        """
        if s:
            try:
                nxt = chr(ord(s[-1]) + 1)
            except ValueError:
                return s + (s[-1] * (1 + self._longest - len(s)))
            else:
                return s[:-1] + nxt
        else:
            return chr(sys.maxunicode) * (self._longest + 1)

    def _prep_choices(self, choices):
        """Organize data into case (in)sensitive lists/labels."""
        choices = set(choices)
        lowers, raws, labels, Linds, Rinds = self._data
        if len(labels) < len(choices):
            for i in range(len(labels), len(choices)):
                labels.append(tk.Label(self.frame, **self._labelstyle))
        tmp = sorted((choice.lower(), choice) for choice in choices)
        for x, lbl in zip(tmp, labels):
            lbl.configure(text=x[_RAW], **self._selected)
        lowers[:] = (x[_LOWER] for x in tmp)
        tmp = sorted((x[_RAW], i) for i, x in enumerate(tmp))
        raws[:] = (x[0] for x in tmp)
        Linds[:] = (x[1] for x in tmp)
        Rinds[:] = Linds
        for raw, lo in enumerate(Linds):
            Rinds[lo] = raw
        self._longest = max((len(_) for _ in raws), default=0)
        for i in range(len(lowers), len(labels)):
            labels[i].grid_forget()
        self.event_generate('<Configure>')


    def configure(self, *args, **kwargs):
        """Configure widget settings. choices can also be set here."""
        #TODO: support changing fonts/bg/fg
        choices = kwargs.pop('choices', None)
        style = kwargs.pop('labelstyle', None)
        ret = tk.Frame.configure(self, *args, **kwargs)
        if choices is not None:
            self._prep_choices(choices)
        if style is not None:
            for keyp, selp in zip(('', '_un'), ('active', '_')):
                d = getattr(self, selp + 'selected')
                for keysuffix in 'bg', 'fg':
                    key = keyp + keysuffix
                    d[key] = style.pop(key, d[key])
            self.frame.configure(background=self._unselected['background'])
            if 'font' in style:
                self._labelstyle['font'] = style['font']
        return ret


    def select(self, val, exact=False):
        """Return choices which start with val.

        If val == val.lower(), then search case insensitive.
        otherwise, search case sensitive.
        If exact, then only return exact matches
        (If no match, then empty list).
        """
        lows, raws, labels, Linds, Rinds = self._data
        nitems = len(raws)
        if not nitems:
            return []
        if exact or val.lower() != val:
            if exact:
                stop = bisect.bisect_right(raws, val)
            else:
                stop = bisect.bisect_left(raws, self._next_prefix(val))
            start = bisect.bisect_left(raws, val, hi=stop)
            inds = sorted((Linds[i], i) for i in range(start, stop))
        else:
            txt = lows
            stop = bisect.bisect_left(lows, self._next_prefix(val))
            start = bisect.bisect_left(lows, val, hi=stop)
            inds = [(i, Rinds[i]) for i in range(start, stop)]
            Linds = idind
        for i in range(start):
            labels[Linds[i]].configure(**self._unselected)
        for i in range(stop, nitems):
            labels[Linds[i]].configure(**self._unselected)
        ret = []
        for (L, R) in inds:
            ret.append(raws[R])
            labels[L].configure(**self._selected)
        if inds:
            self.snap(labels[inds[0][0]], 'x')
        else:
            self.snap(labels[min(start, nitems - 1)], 'x')
        return ret

    def lineheight(self):
        """Pixel height of a single row."""
        #+2 for border of 1 on all sides.
        return self._labelstyle['font'].metrics('linespace') + 2

    @staticmethod
    def _arrange(ev):
        self = ev.widget
        H = self.winfo_height()
        rows = max(H // self.lineheight(), 1)
        labels = self._data[_LABEL]
        for i in range(len(self._data[0])):
            col, row = divmod(i, rows)
            labels[i].grid(row=row, column=col, sticky='nsew', padx=(0,10))

class ItemEntry(EmacsEntry):
    """Entry-like widget for controlling an ItemSelector."""
    def __init__(self, *args, **kwargs):
        """Initialize an ItemEntry.
        
        Additional kwargs:
            selector: The itemselector widget to control.
        """
        selector = kwargs.pop('selector')
        EmacsEntry.__init__(self, *args, **kwargs)
        subclass(self, ItemEntry)
        self._selector = selector
        self._cycling = False
        self._ind = -1
        current = self.get('1.0', 'end - 1 chars')
        self._candidates = self._selector.select(current)
        self._candidates.append(current)
        self._prefix = True

        if not self.bind_class('ItemEntry'):
            def _vcb_Modified(e):
                self = e.widget
                if self._cycling:
                    self._cycling = False
                else:
                    current = self.get('1.0', 'end - 1 chars')
                    candidates = self._selector.select(current)
                    candidates.append(current)
                    self._candidates = candidates
                    self._ind = -1
                    self._prefix = True
            def _cb_Escape(e):
                self = e.widget
                if self.tag_ranges('sel'):
                    self._cycling = True
                    self.delete('1.0', 'end')
                    self._cycling = True
                    self.insert('1.0', self._candidates[-1])
                    self._ind = -1
                    return 'break'
            def tabcb(direction):
                def tab(e):
                    self = e.widget
                    if self._prefix:
                        prefix = []
                        lowered = False
                        for chars in zip(*self._candidates[:-1]):
                            if len(set(chars)) == 1:
                                if lowered:
                                    prefix.append(chars[0].lower())
                                else:
                                    prefix.append(chars[0])
                            else:
                                check = set(''.join(chars).lower())
                                if len(check) == 1:
                                    lowered = True
                                    prefix.append(check.pop())
                                else:
                                    break
                        result = ''.join(prefix)
                        if result:
                            self._candidates[-1] = result
                            self._cycling = True
                            self.delete('1.0', 'end')
                            self._cycling = True
                            self.insert('1.0', result)
                        self._prefix = False
                    else:
                        self._ind += direction
                        self._ind %= len(self._candidates)
                        self._cycling = True
                        self.delete('1.0', 'end')
                        self._cycling = True
                        self.insert('1.0', self._candidates[self._ind])
                        if self._ind == len(self._candidates) - 1:
                            self.tag_remove('sel', '1.0', 'end')
                        else:
                            self.tag_add('sel', '1.0', 'end - 1 chars')
                return tab
            _cb_Tab = tabcb(1)
            _cb_Shift_Tab = tabcb(-1)
            class_bind(self, ItemEntry, local_callbacks(locals()))

if __name__ == '__main__':
    import argparse
    from .emacsentry import EmacsEntry
    from .util import Var
    p = argparse.ArgumentParser()
    p.add_argument('items', nargs = '*')
    args = p.parse_args()

    root = tk.Tk()
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    selector = ItemSelector(
        root, showx=True, showy=True,
        choices=args.items)
    selector.grid(row=0, column=0, sticky='nsew')

    entry = ItemEntry(root, selector=selector)
    entry.grid(row=1, column=0, sticky='ew')

    root.bind('<Escape>', lambda e : root.destroy())
    root.mainloop()
