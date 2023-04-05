"""Class for grouping bindings.

Bindings should be by tag, and so not be instance methods.  As a
result, The callbacks should only be added once to each Tk instance.
The goal is a simpler interface with decorator notation.  util
is probably overcomplicated.

Bindings can use the default tkinter binding mechanic where a function
is used.  However, this has the drawback that not all possible tcl
substitutions are available for use.  It also passes every single
tkinter subsitution even if some are not necessary.
"""
from __future__ import print_function
import inspect
import sys
import traceback

from . import scopes

if sys.version_info.major > 2:
    import tkinter as tk
    def argnames(func):
        """A list of argument names.

        Do not include the cls or self for class/instance methods.
        """
        return tuple(inspect.signature(func).parameters)
else:
    import Tkinter as tk
    def argnames(func):
        """A list of argument names.

        Do not include the cls or self for class/instance methods.
        """
        try:
            offset = int(inspect.ismethod(func))
        except Exception:
            offset = 0
        try:
            ret = inspect.getargspec(func).args
        except Exception:
            ret = inspect.getargspec(func.__call__).args
            offset = 1
        return ret[offset:]


class Wrapper(object):
    """Wrap a function and convert tcl args to appropriate type.

    This should be converted to str to use it as binding (with str()).
    """
    def __init__(self, func, names=None, scope=scopes.EVENT, master=None, dobreak=False):
        """Initialize the wrapper and create corresponding tk command.

        func: the function to wrap.
        names: The names of the function arguments.  Use `argnames` if
            omitted.
        scope: scope of the binding (scopes.VALIDATION or scopes.EVENT)
        master: The master widget to use for binding.  Default to
            tk._get_default_root()
        dobreak: bool
            Wrap the script in a break
        """
        if master is None:
            try:
                master = tk._get_default_root()
            except AttributeError:
                master = tk._default_root
        if names is None:
            names = argnames(func)
        try:
            self.name = str(id(func)) + func.__name__
        except AttributeError:
            self.name = str(id(func)) + type(func).__name__
        if not master.tk.call('info', 'commands', self.name):
            master.tk.createcommand(self.name, self)
        self.func = func
        self.script = [self.name]
        self.converters = []
        scope = scopes.BoundScope(master, scope)
        for k in names:
            sub, cvt = scope[k]
            self.script.append(sub)
            self.converters.append(cvt)
        self.dobreak = dobreak

    def __repr__(self):
        return 'Wrapper({})'.format(self.name)

    def __str__(self):
        """Return the tcl script to use for binding."""
        if self.dobreak:
            return 'if {{"[{}]" == "break"}} break\n'.format(' '.join(self.script))
        else:
            return ' '.join(self.script) + '\n'

    def __call__(self, *args):
        """Call the underlying function with converted args."""
        nargs = []
        for c, arg in zip(self.converters, args):
            try:
                arg = c(arg)
            except Exception as e:
                print(e, file=sys.stderr)
            nargs.append(arg)
        try:
            return self.func(*nargs)
        except Exception:
            traceback.print_exc()

class Bindings(object):
    """Class for handling all bindings."""
    class Decorator(object):
        """Hold bindings meant for a single tag."""
        def __init__(self):
            self.seqs = []
            self.funcs = []
        def bind(self, *seqs, **kwargs):
            self.seqs.append((seqs, kwargs))
            return self
        def __call__(self, func):
            self.funcs.append(func)
            return func
        def __iter__(self):
            return iter(zip(self.seqs, self.funcs))

    def __init__(self, method='bind_class', scope=scopes.EVENT):
        self.bindings = {}
        self.method = method
        self.scope = scope

    def __getitem__(self, tag):
        """Return an item to be used as a decorator for bindings."""
        try:
            return self.bindings[tag]
        except KeyError:
            ret = self.bindings[tag] = self.Decorator()
            return ret

    def apply(self, master, *tags):
        """Apply bindings to a master widget.

        master: tk widget.
        tags: list of str
            If given, then only apply the given tags. Otherwise, apply
            all bindings.
        """
        bind = getattr(master, self.method)
        bindings = self.bindings
        for tag in (tags if tags else bindings):
            for (seqs, kwargs), func in bindings[tag]:
                if not isinstance(func, str):
                    k = dict(scope=self.scope, master=master)
                    k.update(kwargs)
                    func = str(Wrapper(func, **kwargs))
                for seq in seqs:
                    bind(tag, seq, func)
