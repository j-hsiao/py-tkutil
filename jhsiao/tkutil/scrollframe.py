from __future__ import print_function
__all__ = []

import sys
import traceback

if sys.version_info.major > 2:
    import tkinter as tk
else:
    import Tkinter as tk

from .. import exports
from .util import unbind, subclass, class_bind
public = exports.public(__all__)


class HiddenScrollbar(tk.Scrollbar):
    def __init__(self, *args, **kwargs):
        tk.Scrollbar.__init__(self, *args, **kwargs)
        subclass(self, HiddenScrollbar)
        self._ref = None
        self.lifted = False

        if not self.bind_class(HiddenScrollbar.__name__):
            def hide(e):
                e.widget.lower()
                e.widget._ref = e.widget.bind('<Motion>', reshow)
            def reshow(e):
                unbind(e.widget, '<Motion>', e.widget._ref)
                e.widget.lift()
            self.bind_class(HiddenScrollbar.__name__, '<Leave>', hide)

    def lift(self, *args):
        tk.Scrollbar.lift(self, *args)
        self.lifted = True
    def lower(self, *args):
        tk.Scrollbar.lower(self, *args)
        self.lifted = False

@public
class Scrollframe(tk.Frame):
    """Scrollable frame."""
    def __init__(self, root, showx = True, showy = True, **kwargs):
        """show(x/y): show scrollbar on mouse-over"""
        self.root = root
        self._showx = showx
        self._showy = showy
        kwargs.setdefault('borderwidth', 0)
        kwargs.setdefault('highlightthickness', 0)
        tk.Frame.__init__(self, root, **kwargs)
        subclass(self, 'Scrollframe')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._canv = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        subclass(self._canv, 'ScrollframeCanvas')
        self._xscroll = HiddenScrollbar(
            self, orient='horizontal', command=self._canv.xview)
        self._yscroll = HiddenScrollbar(
            self, orient='vertical', command=self._canv.yview)
        self._canv.configure(
            xscrollcommand=self._xscroll.set,
            yscrollcommand=self._yscroll.set)
        self._canv.grid(row=0, column=0, sticky='nsew')
        self._xscroll.grid(row=0, column=0, sticky='sew')
        self._yscroll.grid(row=0, column=0, sticky='nse')
        self._xscroll.lower(self._canv)
        self._yscroll.lower(self._canv)

        # Grid row/column configure can control minsize allowing for effective
        # 'nsew' sticky.
        self._minsize = tk.Frame(self._canv, border=0)
        subclass(self._minsize, 'ScrollframeMinsize')
        self._itemind = self._canv.create_window(
            (0,0), anchor='nw', window=self._minsize)
        self.frame = tk.Frame(self._minsize, border=0)
        self.frame.grid(row=0, column=0, sticky='nsew')

        self._showref = None
        if not self.bind_class('ScrollframeCanvas'):
            def sync_size(e):
                """Sync minsize with canv size."""
                canv = e.widget
                self = canv.nametowidget(canv.winfo_parent())
                self._minsize.grid_rowconfigure(0, minsize=canv.winfo_height())
                self._minsize.grid_columnconfigure(0, minsize=canv.winfo_width())
            def sync_region(e):
                """Sync the scrollregion when frame contents change."""
                canv = e.widget.nametowidget(e.widget.winfo_parent())
                self = canv.nametowidget(canv.winfo_parent())
                canv.configure(scrollregion=canv.bbox(self._itemind))

            def entered(e):
                """Start tracking mouse when enter scrollframe.

                Bind mouse-tracking to see if scrollbars should
                be shown.
                """
                w = e.widget.nametowidget(e.widget.winfo_parent())
                if w._showx or w._showy:
                    top = w.winfo_toplevel()
                    w._showref = w.bind_class(top, '<Motion>', w._show, add='+')
                else:
                    w._showref = None
            def leave(e):
                """Stop mouse-tracking."""
                w = e.widget.nametowidget(e.widget.winfo_parent())
                if w._showref:
                    top = w.winfo_toplevel()
                    unbind(w, '<Motion>', w._showref, tag=top)
            # This addresses the issue in _show, except when
            # mouse leaves the frame.
            def reset(e):
                """Reset scrollbars to hidden state.

                This is safe because it will never fire
                if the scrollbar is being dragged while the
                mouse is outside.  The scrollbar still has focus
                in that case, which means that the mouse isn't
                considered as having left the scrollframe yet.
                """
                if e.widget._xscroll.lifted:
                    e.widget._xscroll.lower()
                if e.widget._yscroll.lifted:
                    e.widget._yscroll.lower()
            class_bind(self, 'Scrollframe', Leave=reset)
            class_bind(
                self, 'ScrollframeCanvas',
                dict(Enter=entered, Leave=leave, Configure=sync_size))
            self.bind_class('ScrollframeMinsize', '<Configure>', sync_region)
        self.xview = self._canv.xview
        self.yview = self._canv.yview


    def _show(self, ev):
        """Show scrollbar if moused over and needed."""
        ex = ev.x_root
        ey = ev.y_root
        xscroll = self._xscroll
        if self._showx and xscroll.get() != (0.0, 1.0):
            x = xscroll.winfo_rootx()
            y = xscroll.winfo_rooty()
            w = xscroll.winfo_width()
            h = xscroll.winfo_height()
            if ((x < ex < x+w) and (y < ey < y+h)):
                xscroll.lift()
                return
        yscroll = self._yscroll
        if self._showy and yscroll.get() != (0.0, 1.0):
            x = yscroll.winfo_rootx()
            y = yscroll.winfo_rooty()
            w = yscroll.winfo_width()
            h = yscroll.winfo_height()
            if ((x < ex < x+w) and (y < ey < y+h)):
                yscroll.lift()
                return
        # Need this because if move mouse too fast, may lift the
        # scrollbar, but next instant, mouse is no longer in the
        # scrollbar so <Enter> (and <Leave>) never fires, leaving
        # the scrollbar in a lifted instead of hidden state.
        if xscroll.lifted:
            xscroll.lower()
        if yscroll.lifted:
            yscroll.lower()


    def xview(self, *args):
        """Forward to canvas's xview."""
        pass
    def yview(self, *args):
        """Forward to canvas's yview."""
        pass

    def showx(self, v):
        """Show x scroll?"""
        self._showx = v

    def showy(self, v):
        """Show y scroll?"""
        self._showy = v

    def snap(self, widget, method = 'xy'):
        """Show widget in canvas.

        Widget should be a child of self.frame.
        method: 'x' | 'y' | 'xy'
            scroll to the widget's x/y value if x/y in method
        """
        if 'x' in method:
            w = float(self.frame.winfo_width())
            if w:
                x = (widget.winfo_rootx() - self.frame.winfo_rootx()) / w
            else:
                x = 0
            self.xview(tk.MOVETO, max(min(x, 1), 0))
        if 'y' in method:
            h = float(self.frame.winfo_height())
            if h:
                y = (widget.winfo_rooty() - self.frame.winfo_rooty()) / h
            else:
                y = 0
            self.yview(tk.MOVETO, max(min(y, 1),0))

if __name__ == '__main__':
    r = tk.Tk()

    r.grid_rowconfigure(0, weight = 1)
    r.grid_columnconfigure(0, weight = 1)

    sf = Scrollframe(r)
    sf.grid(row = 0, column = 0, sticky = 'nswe')
    sf.frame.configure(background = 'blue')

    f = sf.frame
    #f = tk.Frame(sf.frame)
    f.grid(row = 0, column = 0, sticky = 'nsew')
    sf.grid_columnconfigure(0, weight = 1)
    sf.grid_rowconfigure(0, weight = 1)

    def p(widget):
        print('shape', widget.winfo_width(), widget.winfo_height())
        print('pos', widget.winfo_x(), widget.winfo_y())

    sf.frame.configure(bd = 30)

    f1 = tk.Frame(f)
    f2 = tk.Frame(f)
    f3 = tk.Frame(f)
    f4 = tk.Frame(f)
    f1.configure(background = 'black', width = 200, height = 200)
    f2.configure(background = 'pink', width = 400, height = 200)
    f3.configure(background = 'purple', width = 200, height = 400)
    f4.configure(background = 'cyan', width = 200, height = 200)

    r.bind('u', lambda e : sf.snap(f1))
    r.bind('i', lambda e : sf.snap(f2))
    r.bind('j', lambda e : sf.snap(f3))
    r.bind('k', lambda e : sf.snap(f4))

    f1.grid(row = 0, column = 0, sticky = 'nsew')
    f2.grid(row = 0, column = 1, sticky = 'nsew')

    f.configure(background = 'yellow')
    r.after(1000, lambda : f3.grid(row = 1, column = 0, sticky = 'nsew'))
    r.after(1000, lambda : f4.grid(row = 5, column = 5, sticky = 'nsew'))

    def check(e):
        l, r = sf.canv.xview()
        t, b = sf.canv.yview()
        w = sf.frame.winfo_width()
        h = sf.frame.winfo_height()

        print('view', l, t, r, b)
        print('frame', w, h)
        x = int((l * w) + .5)
        y = int((t * h) + .5)
        print('xy', x, y)
        col, row = sf.frame.grid_location(x, y)
        print('cr', col, row)
        print('bbox', sf.frame.grid_bbox(col, row))

        print(sf.frame.grid_bbox(-1, -1))

    r.bind('p', check)

    r.bind('n', lambda e : sf.xview('moveto', -50))
    r.bind('m', lambda e : sf.xview('moveto', 256))

    r.bind('q', lambda e : r.destroy())
    r.mainloop()
