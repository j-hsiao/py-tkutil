from __future__ import print_function
__all__ = []
import re
import sys
import bisect
from .util import subclass, class_bind, local_callbacks
from .. import exports
import functools

if sys.version_info.major > 2:
    import tkinter as tk
else:
    import Tkinter as tk

public = exports.public(__all__)

@public
class EmacsText(tk.Text):
    """tkinter Entry widget with some emacs-like bindings:

    C-
        a: to beginning
        e: to end
        f: forward 1 char
        b: back 1 char
        n: next line
        p: previous line
        w: delete to beginning of word and clipboard
        space: set mark/unset mark
        k: delete to end of line and clipboard
        d: delete current char
    M-
        f: to next word
        b: to previous word/beginning of word
    
    modify <<Modified>> to only be called when
    it's actually modified, and not just when
    the modified flag is called
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('wrap', 'none')
        tk.Text.__init__(self, *args, **kwargs)
        subclass(self, EmacsText)
        if not self.bind_class(EmacsText.__name__):
            class_bind(self, EmacsText, EmacsText.__behavior())

    @staticmethod
    def __wrap(sequence, func):
        """wrap func to ignore when not self.edit('modified')."""
        if (
            sequence is not None
            and sequence == '<<Modified>>'
            and func is not None):

            _func = func
            def func(e):
                if e.widget.edit('modified'):
                    return _func(e)
            try:
                func = functools.wraps(_func)(func)
            except:
                pass
        return func
    def bind(self, sequence=None, func=None, add=None):
        tk.Text.bind(self, sequence, self.__wrap(sequence, func), add)
    def bind_class(self, className, sequence=None, func=None, add=None):
        tk.Text.bind_class(
            self, className, sequence, self.__wrap(sequence, func), add)

    @staticmethod
    def __behavior():
        _MARK = '_mark'
        def keypress_callback(callback):
            """Decorate callback to make cursor visible, return 'break'"""
            def keypress(event):
                self = event.widget
                callback(self)
                self.see('insert')
                return 'break'
            return keypress

        def update_selection(self):
            """Select from insert to mark."""
            if _MARK not in self.mark_names():
                return
            if self.compare('insert', '<', _MARK):
                sel = ('insert', _MARK)
            else:
                sel = (_MARK, 'insert')
            if self.tag_ranges('sel'):
                self.tag_remove('sel', 'sel.first', 'sel.last')
            self.tag_add('sel', *sel)

        def _prev_word(self):
            nxtw = self.search(r'\w', 'insert', '1.0', regexp=True, backwards=True)
            return nxtw + ' wordstart' if nxtw else '1.0'

        def _next_word(self):
            nxtw = self.search(r'\w', 'insert', 'end', regexp=True)
            return nxtw + ' wordend' if nxtw else 'end'

        def _vcb_Modified(event):
            """Clear mark and selection if modified."""
            # Clearing the modified flag causes another
            # <<Modified>> event to be fired.
            self = event.widget
            self.mark_unset(_MARK)
            self.edit('modified', 0)

        def _vcb_Selection(event):
            """Clear mark if selection changed externally."""
            self = event.widget
            if _MARK not in self.mark_names():
                return
            if self.tag_ranges('sel'):
                mismatched_first = (
                    self.compare(_MARK, '!=', 'sel.first')
                    and self.compare('insert', '!=', 'sel.first'))
                mismatched_last = (
                    self.compare(_MARK, '!=', 'sel.last')
                    and self.compare('insert', '!=', 'sel.last'))
                if mismatched_first or mismatched_last:
                    self.mark_unset(_MARK)

        @keypress_callback
        def _cb_Control_y(self):
            self.insert('insert', self.clipboard_get())

        @keypress_callback
        def _cb_Control_w(self):
            if self.tag_ranges('sel'):
                self.clipboard_clear()
                self.clipboard_append(
                    self.get('sel.first', 'sel.last'))
                self.delete('sel.first', 'sel.last')
            else:
                prev = _prev_word(self)
                data = self.get(prev, 'insert')
                if data:
                    self.clipboard_clear()
                    self.clipboard_append(data)
                    self.delete(prev, 'insert')

        @keypress_callback
        def _cb_Control_k(self):
            data = self.get('insert', 'insert lineend')
            if data:
                self.clipboard_clear()
                self.clipboard_append(data)
                self.delete('insert', 'insert lineend')

        @keypress_callback
        def _cb_Control_d(self):
            self.delete('insert')

        @keypress_callback
        def _cb_Control_space(self):
            if (
                _MARK in self.mark_names()
                and self.compare(_MARK, '==', 'insert')):

                self.mark_unset(_MARK)
            else:
                self.mark_set(_MARK, 'insert')
                update_selection(self)

        def move(dst):
            @keypress_callback
            def func(self):
                self.mark_set('insert', dst)
                update_selection(self)
            return func

        _cb_Control_e = move('insert lineend')
        _cb_Control_a = move('insert linestart')
        _cb_Control_f = move('insert + 1 chars')
        _cb_Control_b = move('insert - 1 chars')
        _cb_Control_n = move('insert + 1 lines')
        _cb_Control_p = move('insert - 1 lines')

        @keypress_callback
        def _cb_Alt_f(self):
            self.mark_set('insert', _next_word(self))
            update_selection(self)

        @keypress_callback
        def _cb_Alt_b(self):
            self.mark_set('insert', _prev_word(self))
            update_selection(self)

        @keypress_callback
        def _cb_Alt_d(self):
            nxt = _next_word(self)
            data = self.get('insert', nxt)
            if data:
                self.clipboard_clear()
                self.clipboard_append(data)
                self.delete('insert', nxt)
        return local_callbacks(locals())

@public
class EmacsEntry(EmacsText):
    """Single-line EmacsText widget

    This just binds Return to do nothing. and Tab
    to tk_focusNext().focus()
    No textvariable because you can just bind
    """
    def __init__(self, *args, **kwargs):
        kwargs['height'] = 1
        EmacsText.__init__(self, *args, **kwargs)
        subclass(self, EmacsEntry)

        if not self.bind_class(EmacsEntry.__name__):
            def _cb_Tab(e):
                e.widget.tk_focusNext().focus()
                return 'break'
            def _cb_Shift_Tab(e):
                e.widget.tk_focusPrev().focus()
                return 'break'
            def _cb_Return(e):
                return 'break'
            class_bind(self, EmacsEntry, local_callbacks(locals()))

    def configure(self, *args, **kwargs):
        kwargs.pop('height', None)
        return EmacsText.configure(self, *args, **kwargs)


if __name__ == '__main__':
    r = tk.Tk()
    r.grid_columnconfigure(0, weight=1)
    r.grid_rowconfigure(1, weight=1)

    entry = EmacsEntry(r)
    entry.grid(row=0, column=0, sticky='ew')
    entry.insert('1.0', 'hello world goodbye world')
    entry.focus()
    entry.bind('<<Modified>>', lambda e : print(e.widget.get('1.0', 'end - 1 c')))

    text = EmacsText(r)
    text.grid(row=1, column=0, sticky='nsew')
    text.bind('<Shift-Return>', lambda e : print(text.get('1.0', 'end').replace('\n', '\\n\n')) or 'break')

    r.bind('<Escape>', lambda e : r.destroy())
    r.mainloop()
