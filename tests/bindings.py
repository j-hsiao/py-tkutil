"""Test bindings."""
from __future__ import print_function
import sys

from jhsiao.tkutil import bindings

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
