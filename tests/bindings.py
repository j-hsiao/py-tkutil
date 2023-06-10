"""Test bindings."""
from __future__ import print_function
import sys

from jhsiao.tkutil import bindings, tk


def test_argnames():
    """Test getting argument names of function."""
    class dummy(object):

        @staticmethod
        def static(x, y):
            pass

        @classmethod
        def clss(cls, x, y):
            pass

        def method(self, x, y):
            pass

        def __call__(self, x, y):
            pass
    def standalone(x, y):
        pass
    inst = dummy()
    expect = ['x', 'y']
    assert list(bindings.argnames(inst)) == expect
    assert list(bindings.argnames(inst.static)) == expect
    assert list(bindings.argnames(dummy.static)) == expect
    assert list(bindings.argnames(inst.clss)) == expect
    assert list(bindings.argnames(dummy.clss)) == expect
    assert list(bindings.argnames(standalone)) == expect


def test_wrapper():
    r = tk.Tk()
    succeeded = []
    def func(widget, x, y):
        succeeded.extend(
            ('widget', widget, 'event successfully fired at', x, y))
        widget.after_cancel(warnid)
        widget.destroy()
    w = bindings.Wrapper(func)
    w.bind(r)
    l = tk.Label(
        r,
        text=(
            'Please give this window focus if it does not have it.'
            ' Otherwise, press q to end the test.'))
    l.grid(row=0, column=0)
    r.grid_rowconfigure(0, minsize=300)
    r.grid_columnconfigure(0, minsize=300)
    r.bind('<q>', str(w))
    r.after(3000, r.event_generate, '<q>')
    warnid = r.after(5000, print, 'press q to end test, focus probably was not given in time')
    r.mainloop()
    assert succeeded
    print(*succeeded)


def test_bindings():
    allbinds = bindings.Bindings()

    class Dummy(tk.Tk, object):
        b = allbinds['.']
        def __init__(self, *args, **kwargs):
            super(Dummy, self).__init__(*args, **kwargs)
            allbinds.apply(self)
            self.success = False
            self.clicks = 0
            self.grid_rowconfigure(0, minsize=300, weight=1)
            self.grid_columnconfigure(0, minsize=300, weight=1)
            f = tk.Frame(self)
            f.grid(row=0, column=0, sticky='nsew')
            f.grid_rowconfigure(0, weight=1)
            f.grid_columnconfigure(0, weight=1)
            l = tk.Label(
                f,
                text='click on me!, press q to stop test if not focused in 3 secs')
            l.grid(sticky='nsew')


        @b.bind('<q>')
        def stop(widget):
            widget.success = True
            widget.after_cancel(warnid)
            widget.destroy()

        @staticmethod
        @b.bind('<Button-1>', '<Button-3>')
        def clicked(widget):
            print('clicked on', repr(widget))
            widget.nametowidget('.').clicks += 1

    d = Dummy()
    # It seems event_generate does not do anything
    # if the tk app does not have focus.
    d.after(3000, d.event_generate, '<q>')
    warnid = d.after(5000, print, 'Focus was not given, press q to exit test')
    d.after(50000, d.stop)
    d.mainloop()
    assert(d.success)
    print('number of clicks', d.clicks)

def test_script():
    binds = bindings.Bindings()

    @binds()
    def func(widget):
        print('got a widget:', widget)

    r = tk.Tk()
    r.grid_rowconfigure(0, minsize=300, weight=1)
    r.grid_columnconfigure(0, minsize=300, weight=1)
    b = tk.Button(
        r, text='click me'
    )
    b.configure(command=str(func.update(widget=(str(b), None))))
    b.grid(row=0, column=0, sticky='nsew')

    @binds(str(r), '<Escape>')
    def end(widget):
        print('Escape done')
        widget.after_cancel(warnid)
        widget.winfo_toplevel().destroy()

    binds.apply(r)
    r.after(5000, r.event_generate, '<Escape>')
    warnid = r.after(6000, lambda : b.configure(text='unfocused, press escape to exit'))

    r.mainloop()

if __name__ == '__main__':
    for k, v in list(locals().items()):
        if k.startswith('test_'):
            print('testing', k.split('_', 1)[-1], end=': ', file=sys.stderr)
            try:
                v()
            except Exception:
                print('fail', file=sys.stderr)
                raise
            else:
                print('pass', file=sys.stderr)
