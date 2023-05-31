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
from collections import defaultdict
from functools import partial

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
    def __init__(self, func, names=None, scope=scopes.Event, dobreak=False, **overrides):
        """Initialize the wrapper and create corresponding tk command.

        func: the function to wrap.
        names: The names of the function arguments.  Use `argnames` if
            omitted.
        scope: scope of the binding (see `scopes`)
        dobreak: bool
            Wrap the script and break if returned 'break'
        overrides: overrides for scope.
        """
        if names is None:
            names = argnames(func)
        self.argnames = names
        try:
            self.name = str(id(func)) + func.__name__
        except AttributeError:
            self.name = str(id(func)) + type(func).__name__
        self.func = func
        if isinstance(scope, scopes.Scope):
            self.scope = scope
        else:
            self.scope = scope(overrides=overrides)
        self.dobreak = dobreak
        self.converters = []

    def str(self, **overrides):
        """Update and return str script."""
        return str(self.update(**overrides))

    def update(self, **overrides):
        """Return new wrapper with updated scope."""
        ret = type(self)(
            self.func, self.argnames,
            self.scope.update(overrides), self.dobreak)
        return ret

    def bind(self, master=None):
        """Bind wrapped function to a widget.

        Set master widget.  Create the command.  Calculate converters.
        """
        if master is None:
            try:
                master = tk._get_default_root()
            except AttributeError:
                master = tk._default_root
        self.scope.master = master.nametowidget('.')
        if self.converters:
            raise Exception('Wrapper should only be bound once')
        if master.tk.call('info', 'commands', self.name):
            print(
                'Warning, command {} already exists'.format(self.name),
                file=sys.stderr)
        else:
            master.tk.createcommand(self.name, self)
        for k in self.argnames:
            sub, cvt = self.scope[k]
            self.converters = [self.scope[name][1] for name in self.argnames]

    def trace(self, widget, var, mode):
        """Compatible for py2/3.

        var: the variable object to add trace to.
        mode: 'read', 'write', 'unset'
        """
        widget.tk.call(
            'trace', 'add', 'variable',
            str(var), mode, str(self).split())

    def __repr__(self):
        return 'Wrapper({})'.format(self.name)

    def __str__(self):
        """Return the tcl script to use for binding."""
        items = [self.name]
        items.extend([self.scope[name][0] for name in self.argnames])
        if self.dobreak:
            return 'if {{"[{}]" == "break"}} break\n'.format(' '.join(items))
        else:
            return ' '.join(items) + '\n'

    def __call__(self, *args):
        """Call the underlying function with converted args."""
        if len(args) != len(self.converters):
            raise ValueError(
                'Mismatch arguments and converters for {}'.format(self.name))
        nargs = []
        for c, arg in zip(self.converters, args):
            try:
                arg = c(arg)
            except Exception:
                traceback.print_exc()
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
        def __repr__(self):
            return repr(list(zip(self.funcs, self.seqs)))

    class WrapperDecorator(Decorator):
        def __call__(self, func):
            self.funcs.append(func)
            return Wrapper(func, **self.seqs[-1][1])

    def __init__(self):
        self.bindings = defaultdict(partial(defaultdict, self.Decorator))
        self.bindings[''] = self.WrapperDecorator()

    def __getitem__(self, tag):
        """Return self('bind_class') or self('') if tag is None"""
        if tag:
            return self.bindings['bind_class'][tag]
        else:
            return self.bindings[''].bind()

    def __call__(self, *args, **kwargs):
        """Return a dict or WrapperDecorator.

        Positional args:
        method: The method to use.  It defaults to 'tag_bind'.
            If empty, returns a WrapperDecorator.bind(**kwargs).  Use
            this as a decorator for a function that needs to have a
            command created, but not bound.  These are used to generate
            scripts for validation or a button command, etc.  Otherwise
            return a dict for the given method.  Index it with the
            desired tag to obtain a Decorator for that specific tag.
        """
        if args:
            method = args[0]
        else:
            method = 'tag_bind'
        if method:
            return self.bindings[method]
        else:
            return self.bindings[''].bind(**kwargs)

    def apply(self, master, tags=None, methods=None, create=True):
        """Apply bindings to a master widget.

        master: tk widget.
        tags: list of str
            If given, then only apply the given tags. Otherwise, apply
            all bindings.
        """
        bindings = self.bindings
        for method in (methods if methods else bindings):
            if method:
                bind = getattr(master, method, None)
                info = bindings[method]
                for tag in (tags if tags else info):
                    for (keyseqs, kwargs), func in info[tag]:
                        if not isinstance(func, str):
                            w = Wrapper(func, **kwargs)
                            if create:
                                w.bind(master)
                            func = str(w)
                        if bind is not None:
                            for seq in keyseqs:
                                bind(tag, seq, func)
            else:
                for (_, kwargs), func in bindings[method]:
                    Wrapper(func, **kwargs).bind(master)
