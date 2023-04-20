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
        widget.destroy()
    w = bindings.Wrapper(func)
    w.bind(r)
    r.bind('<q>', str(w))
    r.after(1000, r.event_generate, '<q>')
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
            f = tk.Frame(self)
            f.grid()
            l = tk.Label(f, text='click on me!')
            l.grid()

        @b.bind('<q>')
        def stop(widget):
            widget.success = True
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
    d.after(50000, d.stop)
    d.mainloop()
    assert(d.success)
    print('number of clicks', d.clicks)

def test_script():
    binds = bindings.Bindings()

    @binds('')
    def func(widget):
        print('got a widget:', widget)

    r = tk.Tk()
    b = tk.Button(
        r, text='click me'
    )
    b.configure(command=str(func.update(widget=(str(b), None))))
    b.grid()

    @binds[str(r)].bind('<Escape>')
    def end(widget):
        print('Escape done')
        widget.winfo_toplevel().destroy()

    binds.apply(r)

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
