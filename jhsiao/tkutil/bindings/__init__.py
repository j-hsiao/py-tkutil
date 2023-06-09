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
    """Class for handling all bindings.

    Bindings have 2 levels of keys: method and tag.
    Iterating yields (seq, kwargs), func.  seq is a sequence of bind
    tags such as '<Button-1>' to bind the func to.  The kwargs is a
    dict for Wrapper instantiation.

    Bindings under the empty method ('') are exceptions and indicate
    functions that shouldn't be bound by tag, but rather are to be
    used as scripts such as for a `tk.Button`'s command argument or
    various widgets' validation commands.
    """
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
        """Return wrapper for script generation."""
        def __call__(self, func):
            self.funcs.append(func)
            return Wrapper(func, **self.seqs[-1][1])

    def __init__(self):
        self.bindings = defaultdict(partial(defaultdict, self.Decorator))
        self.bindings[''] = self.WrapperDecorator()

    def __getitem__(self, tag):
        """Return corresponding decorator.

        tag:
            str: The tag to use. method defaults to bind_class.
            tuple: pair of method, tag strs.  If method is '', it is
                replaced with tag_bind.
        If the tag is empty, then assume method is empty too.
        """
        if tag:
            if isinstance(tag, str):
                method = 'bind_class'
            elif isinstance(tag, tuple):
                method, tag = tag
            else:
                raise KeyError(repr(tag))
            if not method:
                method = 'tag_bind'
            return self.bindings[method][tag]
        else:
            return self.bindings['']

    def __call__(self, *args, **kwargs):
        """Return a dict or WrapperDecorator.

        Positional args:
            Sequence of method, tag, and binding sequences.
            If method is empty, it will be replaced with 'tag_bind'.
            If method is omitted, it will be defaulted to 'bind_class'.
            A tag should always be given for methods intended to be
            bound. If method and tag are both omitted, then a
            WrapperDecorator is returned for creating Wrappers.
            The binding sequences are sequences of strings beginning
            with '<' and ending in '>'.  These indicate the events
            to bind to.  If given, then they will be given to
            the Decorator.bind() method and the result is returned.
            Otherwise, the Decorator itself is returned.
        kwargs:
            These are keyword arguments for Wrapper instantiation.

        Summary:
            'method', 'tag', '<bindings>'...:
                Return decorator.bind(<bindings>..., **kwargs).  If
                method is '', then method is replaced with 'tag_bind'.
            'tag', '<binding>'...:
                Same as above, but method='bind_class'.
            'method', 'tag':
                Return the decorator.  Again, if method == '', then
                'tag_bind' will be used.
                eg.
                dec = bindings_instance('method', 'tag')
                @dec.bind(...)
                def func1(...):
                    ...
                @dec.bind(...)
                def func2(...):
                    ...
            'tag':
                Same as above, but method defaults to 'bind_class'.
            :
                No args returns a WrapperDecorator primed with the
                kwargs ready for creating a Wrapper.
        """
        if args:
            for i, item in enumerate(args):
                if item.startswith('<'):
                    bindseqs = args[i:]
                    methodtag = args[:i]
                    break
            else:
                bindseqs = ()
                methodtag = args
            if len(methodtag) == 1:
                method = 'bind_class'
                tag = methodtag[0]
            elif len(methodtag) == 2:
                method, tag = methodtag
            else:
                raise ValueError('Invalid arguments')
            if not method:
                method = 'tag_bind'
            ret = self.bindings[method][tag]
            if bindseqs:
                return ret.bind(*bindseqs, **kwargs)
            else:
                return ret
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
