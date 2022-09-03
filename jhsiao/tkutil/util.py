"""This contains some tkinter utility functions.

Extra bindtags info:
    With tkinter, callbacks are actually bound to a bindtag.  Each
    widget has a list of bindtags that indicate what callbacks
    will be called on that widget whenever an event applies to it.

    By default, the bindtags are the widget's namepath(widget instance),
    widget class, and 'all'.  When a widget receives an event, the
    bindtags() are searched in order for callbacks so instance
    callbacks are called, then class callbacks, then 'all' callbacks.
    If any of the callbacks return 'break', then searching for callbacks
    ends (not a Tcl, but tkinter code).  Subclass callbacks should
    return 'break' to overwrite the parent widget behavior, or not if
    the parent widget behavior is also desired.

    This module simulates subclassing widgets by inserting the name
    of the subclass at a default index of 1 after the instance tag
    and before the tk widget class.  Bindings are also simplified with
    the Bindings() decorator.

"""
from __future__ import print_function
__all__ = []

from functools import wraps, partial
import re
import sys
import inspect
import traceback
from itertools import chain


if sys.version_info.major > 2:
    import tkinter as tk
    def argnames(func):
        """Return a list of names of args."""
        return tuple(inspect.signature(func).parameters)
else:
    import Tkinter as tk
    from itertools import imap as map
    from itertools import izip as zip
    from itertools import ifilter as filter
    def argnames(func):
        """Return a list of names of args."""
        try:
            offset = int(inspect.ismethod(func))
        except Exception:
            offset = 0
        try:
            ret = inspect.getargspec(func).args
        except Exception:
            ret = inspect.getargspec(func.__call__).args
        return ret[offset:]

from ..exports import PublicScope
from ..utils.strutils import splitlines
from ..utils.chainmap import ChainMap

with PublicScope(state=globals()):
    def callback_funcid(func):
        """Return a string to be used as the Tcl command name.

        instance methods:
            id of bound method with function name
        class methods:
            id of underlying func and class with function name
            (class methods only depend on the class on which it is called
            but can have different ids)
        others:
            id of func with a __name__ (
                tries func.__name__, func.__func__.__name__,
                func.func.__name__, and finally type(func).__name__)
        """
        if inspect.ismethod(func):
            if isinstance(func.__self__, type):
                # class method
                return ''.join((
                    repr(id(func.__func__)),
                    repr(id(func.__self__)),
                    func.__name__))
            else:
                # instance method
                return repr(id(func))+func.__name__
        else:
            try:
                name = func.__name__
            except AttributeError:
                try:
                    name = func.__func__.__name__
                except AttributeError:
                    try:
                        # a partial?
                        name = func.func.__name__
                    except AttributeError:
                        name = type(func).__name__
            return repr(id(func)) + name

    # Sample line from a single bind call:
    # if {"[2235275164928callback %# %b %f %h %k %s %t %w %x %y %A %E %K %N %W %T %X %Y %D] == "break"} break\n\n
    _FUNCID_PATTERN = re.compile(r'\[(?P<funcid>\S+)')
    def unbind(widget, evseq, funcids=(), tag=None, delete=True):
        """Unbind specified callbacks.

        The tkinter widget.unbind(funcid) is misleading (as of version 8.6).
        The only difference between unbind(funcid) and unbind() is that
        unbind(funcid) also calls deletecommand(funcid). That is to say,
        both will unbind everything.

        If delete, then unbound funcids will also be deleted via
        widget.deletecommand.  (if functions are constantly
        bound and then unbound, not calling deletecommand will result
        in using more and more memory as more tcl/python commands are
        linked together.)  However, also note that the same command
        may be used for other bindings.  If this is the case, delete
        will also affect that binding which may be undesirable.

        funcids: A sequence of funcids to unbind. If empty, unbind all.
             Unfound funcids will be ignored.
        tag: the tag to use, default to str(widget).
        evseq: The event sequence to unbind from.
        """
        if tag is None:
            tag = str(widget)
        info = widget.bind_class(tag, evseq).splitlines()
        keep = []
        todelete = []
        if funcids:
            if isinstance(funcids, str):
                funcids = (funcids,)
            targets = set(funcids)
            for line in filter(None, info):
                try:
                    fid = _FUNCID_PATTERN.search(line).group('funcid')
                    if fid in targets:
                        todelete.append(fid)
                    else:
                        keep.append(line)
                except Exception:
                    keep.append(line)
        else:
            for line in filter(None, info):
                try:
                    todelete.append(
                        _FUNCID_PATTERN.search(line).group('funcid'))
                except Exception:
                    pass
        if keep:
            widget.bind_class(tag, evseq, '\n\n'.join(keep)+'\n')
        else:
            widget.bind_class(tag, evseq, '')
        if delete:
            otherinfo = [
                widget.bind_class(tag, seq)
                for seq in widget.bind_class(tag)]
            for funcid in todelete:
                if all(funcid not in oinfo for oinfo in otherinfo):
                    try:
                        widget.deletecommand(funcid)
                    except Exception:
                        pass


    def subclass(widget, tag=None, after=None, before=None):
        """Add a tag to bindtags for the widget.

        tag: The bind tag to add. Defaults to type(widget).__name__.
        after/before: insert the tag directly after/before the given
            tag.  Only one should be given.  If neither is given, then
            default to after str(widget)
        Notes:
            In python2, tkinter classes do not subclass object so
            type(self) would give instance instead of the class.
            Subclasses should add object to the inheritance or use the
            tag argument explicitly.  Also, type will give the name of
            the most derived class so the None behavior is only valid if
            there are no subclasses.
        """
        if tag is None:
            tag = type(widget).__name__
        tags = list(widget.bindtags())
        if before:
            idx = tags.index(before)
        else:
            if after is None:
                after = str(widget)
            idx = tags.index(str(widget))+1
        tags.insert(idx, tag)
        widget.bindtags(tuple(tags))


    def _make_types():
        """Generate EvTypes class."""
        lines = ['class EvTypes(object):']
        types = {
            '2': 'KeyPress',
            '3': 'KeyRelease',
            '4': 'ButtonPress',
            '5': 'ButtonRelease',
            '6': 'Motion',
            '7': 'Enter',
            '8': 'Leave',
            '9': 'FocusIn',
            '10': 'FocusOut',
            '11': 'Keymap',
            '12': 'Expose',
            '13': 'GraphicsExpose',
            '14': 'NoExpose',
            '15': 'Visibility',
            '16': 'Create',
            '17': 'Destroy',
            '18': 'Unmap',
            '19': 'Map',
            '20': 'MapRequest',
            '21': 'Reparent',
            '22': 'Configure',
            '23': 'ConfigureRequest',
            '24': 'Gravity',
            '25': 'ResizeRequest',
            '26': 'Circulate',
            '27': 'CirculateRequest',
            '28': 'Property',
            '29': 'SelectionClear',
            '30': 'SelectionRequest',
            '31': 'Selection',
            '32': 'Colormap',
            '33': 'ClientMessage',
            '34': 'Mapping',
            '35': 'VirtualEvent',
            '36': 'Activate',
            '37': 'Deactivate',
            '38': 'MouseWheel'}
        lines.append('"""Tkinter Event types.')
        lines.append('')
        lines.append('compare with a str (event num or name), or the class')
        lines.append('num to class mapping:')
        for num, cls in types.items():
            lines.append('    {}: {}'.format(num, cls))
        lines.append('"""')
        for num, cls in types.items():
            lines.extend((
                'class {}(object):'.format(cls),
                '    def __eq__(self, t):'))
            if cls.endswith('Press'):
                short = cls[:-len('Press')]
                lines.append((
                    '        return t is EvTypes.{cls}'
                    ' or isinstance(t, EvTypes.{cls})'
                    ' or t == "{cls}" or t == "{num}"'
                    ' or t == "{short}"').format(
                        cls=cls, num=num, short=short))
                lines.append('{} = {}'.format(short, cls))
            else:
                lines.append((
                    '        return t is EvTypes.{cls} '
                    ' or isinstance(t, EvTypes.{cls}) or t == "{cls}"'
                    ' or t == "{num}"').format(cls=cls, num=num))
        mapping = ['mapping = {']
        mapping.extend("'{}': {},".format(k, v) for k, v in types.items())
        mapping.append('}')
        lines.append(''.join(mapping))
        lines.extend((
            'def __call__(self, name):',
            '    return self.mapping[name]()'))
        return '\n    '.join(lines)
    exec(_make_types(), globals())
    del _make_types

    class EvState(object):
        """tcl state bitflag checker."""
        bits = dict(
            Shift = 1<<0,
            Caps_Lock = 1<<1,
            Control = 1<<2,
            Mod1 = 1<<3, # numlock
            Mod2 = 1<<4,
            Mod3 = 1<<5, # scrolllock
            Mod4 = 1<<6,
            Mod5 = 1<<7,
            B1 = 1<<8,
            B2 = 1<<9,
            B3 = 1<<10,
            B4 = 1<<11,
            B5 = 1<<12,
            Alt = 1<<17)
        def __init__(self, state):
            self.state = int(state)
        def __repr__(self):
            return 'EvState: ' + ' | '.join(
                k for k, b in self.bits.items()
                if self.state&b)

        def __getattr__(self, name):
            result = self.bits[name] & self.state
            setattr(self, name, result)
            return result


    class Subber(object):
        """Base class for handling substitution tcl commands.

        Subclasses are expected to have a "subs" class attribute dict.
        The dict should be <sub name>: (substitution,
        conversionfunc).  "widget" conversion function should be None
        since it requires a tk instance to convert.  The instance should
        be passed either in __init__ or separately.
        """
        subs = {}
        def __init__(self, *subnames, **subs):
            """Initialize Subber

            argnames: names of tcl arguments to use. If not found,
            then use the name as is.
            <subs> will override class subs mapping.
            The values should be a pair (sub, converter), or a str
                (just the sub) in which case the same converter will
                be used.
            """
            self.names = subnames
            csubs = type(self).subs
            for k, v in subs:
                if isinstance(v, str):
                    subs[k] = (v, csubs.get(k, (None,None))[1])
            self.subs = subs


        @classmethod
        def info(cls, widget, subnames, subs=None):
            """Return the sequences of substitutions and converters.

            Substitutions are used in Tcl scripts and generally have
            the form '%X' where X is some char.  Converters convert the
            corresponding Tcl return value from str to an appropriate
            type.  Special handling for subname 'widget' which requires
            <widget>'s nametowidget method
            """
            if widget is None:
                nametowidget = None
            else:
                master = widget.master
                while master is not None:
                    widget = master
                    master = widget.master
                nametowidget = widget.nametowidget
            items = []
            subs = ChainMap(subs, cls.subs) if subs else cls.subs
            for k in subnames:
                item = subs.get(k)
                if item is None:
                    items.append((k, None))
                else:
                    if not isinstance(item, (list, tuple)):
                        item = (item, cls.subs.get(k, (None,None))[1])
                    if k == 'widget' and item[1] is None:
                        items.append((str(item[0]), nametowidget))
                    else:
                        if not isinstance(item[0], str):
                            item = (str(item[0]), item[1])
                        items.append(item)
            return tuple(zip(*items)) or ((),())

        @staticmethod
        def _cvt(item, converter):
            """Try to apply a converter.

            item: the string argument from Tcl.
            converter: a callable to convert item.
            Return '??<original_value>' on failure.
            """
            if converter is None:
                return item
            try:
                return converter(item)
            except Exception:
                if item == '??':
                    return None
                else:
                    traceback.print_exc()
                    return '??'+item

        @staticmethod
        def _sub_args(cvt, cvts, *data):
            """Apply each item in cvts to corresponding item in data.

            Return tuple of results
            """
            return map(cvt, data, cvts)
        @staticmethod
        def _sub_tuple(cvt, cvts, *data):
            """Apply each item in cvts to corresponding item in data.

            Return a 1-tuple containing a tuple of results
            """
            return (tuple(map(cvt, data, cvts)),)
        @staticmethod
        def _sub_dict(cvt, cvts, subnames, *data):
            """Apply eahc item in cvts to corresponding item in data.

            Return a dict of subname: result
            """
            return (dict(zip(subnames, map(cvt, data, cvts))),)

        # substitution methods suitable as subst for widget.register()
        def sub_args(self, widget):
            """Return parser returning a tuple of arguments.

            Use this as subst when calling widget.register() if the func
            takes a sequence of arguents.
            """
            subs, cvts = self.info(widget, self.names, self.subs)
            return partial(self._sub_args, self._cvt, cvts)

        def sub_tuple(self, widget):
            """Return parser returning a tuple.

            Use this as subst when calling widget.register() if the func
            takes a single tuple of arguments.
            """
            subs, cvts = self.info(widget, self.names, self.subs)
            return partial(self._sub_tuple, self._cvt, cvts)

        def sub_dict(self, widget):
            """Return a parser returning a dict.

            Use this as subst when calling widget.register() if the func
            takes a single dict of arguments.  The keys match the
            names in self.props.
            """
            subs, cvts = self.info(widget, self.names, self.subs)
            return partial(self._sub_dict, self._cvt, cvts, self.names)

        # wrap different calling conventions, suitable for create_command
        @classmethod
        def wrap_args_(cls, widget, func, subnames=None, subs=None):
            """Add a parsing wrapper.

            Parse and call func as func(arg1, arg2,...).
            Func should take positional arguments.
            subnames defaults to func's argument names.
            """
            if subnames is None:
                subnames = argnames(func)
            subs, cvts = cls.info(widget, subnames, subs)
            cvt = cls._cvt

            @wraps(func)
            def wrapped(*args):
                try:
                    return func(*map(cvt, args, cvts))
                except Exception:
                    traceback.print_exc()
            return wrapped

        @classmethod
        def wrap_tuple_(cls, widget, func, subnames=None, subs=None):
            """Add parsing wrapper to pass a tuple.

            Parse and call func as func((arg1, arg2,...)).
            subnames defaults to func's argument names.
            """
            if subnames is None:
                subnames = argnames(func)
            subs, cvts = cls.info(widget, subnames, subs)
            cvt = cls._cvt

            @wraps(func)
            def wrapped(*args):
                try:
                    return func(tuple(map(cvt, args, cvts)))
                except Exception:
                    traceback.print_exc()
            return wrapped

        @classmethod
        def wrap_dict_(cls, widget, func, subnames=None, subs=None):
            """Add a parsing wrapper to pass a dict.

            Parse and call func as func({argname: argval, ...}).
            subnames defaults to func's argument names.
            """
            if subnames is None:
                subnames = argnames(func)
            subs, cvts = cls.info(widget, subnames, subs)
            cvt = cls._cvt

            @wraps(func)
            def wrapped(*data):
                try:
                    return func(dict(zip(subnames, map(cvt, data, cvts))))
                except Exception:
                    traceback.print_exc()
            return wrapped

        @classmethod
        def wrap_kwargs_(cls, widget, func, subnames=None, subs=None):
            """Add a parsing wrapper to pass in kwargs.

            Parse and call func as func(argname=argval, ...)
            subnames defaults to func's argument names.
            """
            if subnames is None:
                subnames = argnames(func)
            subs, cvts = cls.info(widget, subnames, subs)
            cvt = cls._cvt

            @wraps(func)
            def wrapped(*data):
                try:
                    return func(**dict(zip(subnames, map(cvt, data, cvts))))
                except Exception:
                    traceback.print_exc()
            return wrapped

        def wrap_args(self, widget, func):
            """wrap_args_ using self.names."""
            return self.wrap_args_(widget, func, self.names, self.subs)
        def wrap_tuple(self, widget, func):
            """wrap_tuple_ using self.names."""
            return self.wrap_tuple_(widget, func, self.names, self.subs)
        def wrap_dict(self, widget, func):
            """wrap_dict_ using self.names."""
            return self.wrap_dict_(widget, func, self.names, self.subs)
        def wrap_kwargs(self, widget, func):
            """wrap_kwargs_ using self.names."""
            return self.wrap_kwargs_(widget, func, self.names, self.subs)

        @classmethod
        def script_(
            cls, func=None, funcid=None, subnames=None,
            add=False, withbreak=True, subs=None):
            """Return a single-line tcl script string.

            If any of funcid or subnames is not given, then func is
            required and will be used to calculate the respective
            values.  If add, then '+' will be prepended to the script.
            If withbreak, then the script will be wrapped in a Tcl if
            statement to break if the command returns "break".
            """
            subs = ChainMap(subs, cls.subs) if subs else cls.subs
            substrs = []
            for name in (subnames or argnames(func)):
                thing = subs.get(name)
                if thing is None:
                    substrs.append(name)
                elif isinstance(thing, (list, tuple)):
                    substrs.append(str(thing[0]))
                else:
                    substrs.append(str(thing))
            funcid = funcid or callback_funcid(func)
            if withbreak:
                pattern = '{add}if {{"[{basescript}]" == "break"}} break\n'
            else:
                pattern = '{add}{basescript}\n'
            return pattern.format(
                add=('+' if add else ''),
                basescript=' '.join(chain((funcid,), substrs)))

        def script(self, func=None, funcid=None, add=False, withbreak=True):
            """Return a single-line tcl script usable with bind.

            funcid: the name of command (from register() or used with
                tk.createcommand())
            add: add instead of overwrite (prefix script with a '+')
            withbreak: add the if/break guard to allow returning 'break'
                to halt processing of an event.
            """
            return self.script_(
                func, funcid, self.names, add, withbreak, self.subs)

        @classmethod
        def createcommand(
            cls, widget, func, funcid=None, wrapper='args', subnames=None,
            override=False, cleanup=False, subs=None):
            """Wrap func and create (maybe). Return (created?, funcid).

            If wrapper is None, use func as is.  Otherwise, default to
                wrap_args_.  Should have signature:
                wrapper(widget, func, subnames)
                Alternatively, it can be 'args', 'dict', or 'tuple' in
                which case the appropriate wrapper is used.
            If funcid is None, calculate it.
            If override, then override the existing command if it
            already exists.
            If cleanup, add funcid to widget._tclCommands (internal impl
                detail...)
            """
            if wrapper is None:
                wrapped = func
            else:
                if not callable(wrapper):
                    if not wrapper:
                        wrapper = 'args'
                    wrapper = getattr(
                        cls, 'wrap_{}_'.format(wrapper), cls.wrap_args_)
                wrapped = wrapper(widget, func, subnames, subs)
            funcid = funcid or callback_funcid(func)
            if override or not widget.tk.call('info', 'commands', funcid):
                widget.tk.createcommand(funcid, wrapped)
                if cleanup and created:
                    # This relies on a tk internal implementation...
                    if widget._tclCommands is not None:
                        widget._tclCommands.append(funcid)
                    else:
                        widget._tclCommands = [funcid]
                return True, funcid
            return False, funcid

        @classmethod
        def make_script_(
            cls, widget, func, funcid=None, wrapper='args',
            subnames=None, override=False, add=False, withbreak=False,
            cleanup=False, subs=None):
            """Call createcommand if needed and then call script_.

            Return if created and the script.
            See createcommand() and script() for args.
            """
            if subnames is None:
                subnames = argnames(func)
            created, funcid = cls.createcommand(
                widget, func, funcid, wrapper, subnames, override,
                cleanup, subs)
            return cls.script_(func, funcid, subnames, add, withbreak, subs)

        def make_script(
            self, widget, func, funcid=None, wrapper='args', override=False,
            add=False, withbreak=False, cleanup=False):
            """Use self.names as subnames."""
            return self.make_script_(
                widget, func, funcid, wrapper, self.names,
                override, add, withbreak, cleanup, self.subs)


    class ValSubs(Subber):
        """Tcl substitutions focused on validation."""
        subs = dict(
            action=('%d', int), #0=delete, 1=add, -1=other
            idx=('%i', int), #index of the change
            pending=('%P', None), #the string if valid
            current=('%s', None), #the string before the change
            change=('%S', None), # the change (added or deleted char if any)
            valstate=('%v', None), # widget.cget('validate')
            valtype=('%V', None), # the validation trigger
            widget=('%W', None)
        )
    ValSubs.__doc__ += '\n\n' + '\n'.join(splitlines(', '.join(sorted(ValSubs.subs))))


    class EvSubs(Subber):
        """Manage Tcl Event bindings."""
        subs= dict(
            above=('%a', None),
            borderwidth=('%B', int), #?? screen dist
            button=('%b', int), # mouse button
            char=('%A', None), # printable character or esc sequence (Escape 0x1b, backspace 0x08)
            count=('%c', int),
            data=('%d', None), # user data for virtual events
            delta=('%D', int), # scrolling amount (windows)
            detail=('%d', None), # detail for enter/leave, focus in/out
            focus=('%f', bool), # bool, has focus?
            height=('%h', int), # screendist
            keycode=('%k', int), # uint8
            keysym=('%K', None), # chr?
            keysym_num=('%N', int), # uint16? (keysym_num&0xFF = keycode?)
            mode=('%m', None), # 
            override=('%o', bool), # bool for Map, Reparent, Configure events
            place=('%p', None), # PlaceOn[Top|Bottom] for circulate events
            root=('%R', None), # root name
            rootx=('%X', int), # x on screen
            rooty=('%Y', int), # y on screen
            sendevent=('%E', None), # ?
            serial=('%#', int), # event count
            state=('%s', EvState), # state flags
            subwindow=('%S', None), # subwindow?
            time=('%t', int), # timestamp of event
            type=('%T', EvTypes()), # type of event
            tp=('%T', EvTypes()), # alias of type since it's a builtin
            widget=('%W', None), # name of widget, requires special handling
            width=('%w', int), # width of widget
            x=('%x', int), # x within widget
            y=('%y', int), # y within widget
        )
    EvSubs.__doc__ += '\n\n' + '\n'.join(splitlines(', '.join(sorted(EvSubs.subs))))

    class Validator(object):
        def __init__(self, wrap='args'):
            self.wrap = wrap
            self.__func__ = None
            self.getter = None

        def __call__(self, func):
            self.__func__ = func
            self.getter = getattr(func, '__get__', self._get)
            return self

        def _get(self, inst, cls):
            return self.__func__

        def __get__(self, inst, cls=None):
            return _BoundValidator(self, self.getter(inst, cls), inst)

    class _BoundValidator(Validator):
        def __init__(self, par, func, widget):
            self.pref = par.wrap
            self.widget = widget
            self.__func__ = func

        def __repr__(self):
            return 'Bound Validator on {}'.format(self.__func__)

        def __call__(self, *args, **kwargs):
            return self.__func__(*args, **kwargs)

        def script(
            self, widget=None, funcid=None, wrapper='',
            subnames=None, override=False,
            add=False, withbreak=False, cleanup=False):
            """Make and return a script."""
            if widget is None:
                widget = self.widget
            if wrapper is not None and not wrapper:
                wrapper = self.pref
            return ValSubs.make_script_(
                widget, self.__func__, funcid, wrapper, subnames, override,
                add, withbreak, cleanup)

    class Bindings(object):
        """Wrap a function and specify bindings for it.

        Use as a decorator. bind_members and bind_dict will search for
        Bindings instances.
        """
        def __init__(self, *bindings, **kwargs):
            """Initialize list of bindings.

            bindings: sequence of str (bind sequences)
            kwargs:
                wrap: ['args'|'tuple'|'dict'|'kwargs']: the wrapping
                    method to be used on the decorated function.
            """
            self.bindings = bindings
            self.__func__ = None
            self.getter = None
            self.pref = kwargs.get('wrap', 'args')

        def __call__(self, func):
            """Decorate a member."""
            self.__func__ = func
            self.getter = getattr(func, '__get__', self._getter)
            return self

        def f(self, func):
            """Decorate a non-member."""
            self.__func__ = func
            return _BoundBindings(self, func, None)

        def _getter(self, inst, cls):
            """Use this if self.__func__ has no __get__."""
            return self.__func__

        def __get__(self, inst, cls=None):
            """Bind function."""
            return _BoundBindings(self, self.getter(inst, cls), inst)


    class _BoundBindings(object):
        """Bound functions."""
        def __init__(self, obinds, func, widget):
            """Initialize _BoundBindings.

            bindings: sequence of bind sequences (<...> or virtual <<...>>)
            func: the function to wrap/bind
            preference: name of preferred binding method
            """
            self.bindings = obinds.bindings
            self.pref = obinds.pref
            self.__func__ = func
            self.widget = widget

        def __repr__(self):
            return 'Bound Bindings on {}: {}'.format(repr(self.__func__), self.bindings)

        def __call__(self, *args, **kwargs):
            """Forward arguments to call __func__."""
            return self.__func__(*args, **kwargs)

        def name(self):
            return callback_funcid(self.__func__)

        def bind_(
            self, bindname, widget=None, tag=None,
            funcid=None, wrapper='', subnames=None, override=False,
            add=False, withbreak=True, cleanup=False, subs=None):
            """Highest level of control for binding.

            Bind to a widget for each sequence in self.bindings.
            wrapper will default to args
            valid values:
                args, dict, kwargs, tuple
            """
            if widget is None:
                widget = self.widget
            if tag is None:
                tag = str(widget)
            if wrapper is not None and not wrapper:
                wrapper = self.pref
            script = EvSubs.make_script_(
                widget, self.__func__, funcid, wrapper, subnames, override,
                add, withbreak, cleanup, subs)
            bindfunc = getattr(widget, bindname)
            for binding in self.bindings:
                bindfunc(tag, binding, script)

        def bind(
            self, widget=None, tag=None,
            funcid=None, wrapper='', subnames=None, override=False,
            add=False, withbreak=True, cleanup=False, subs=None):
            return self.bind_(
                'bind_class', widget, tag,
                funcid, wrapper, subnames, override,
                add, withbreak, cleanup, subs)

        def tag_bind(
            self, widget=None, tag=None,
            funcid=None, wrapper='', subnames=None, override=False,
            add=False, withbreak=True, cleanup=False, subs=None):
            return self.bind_(
                'tag_bind', widget, tag,
                funcid, wrapper, subnames, override,
                add, withbreak, cleanup, subs)


    def memberit(item, keys=None):
        """Iterate on members.
        keys: list of attr names to search through.  Default to
        item.__dict__ if item is a class.  Otherwise, use
        type(item).__dict__.  This allows classes to have
        static/class/instance methods but won't double-bind if parent
        class already binds its methods to some tag.
        """
        if keys is None:
            if isinstance(item, type):
                keys = item.__dict__
            else:
                keys = type(item).__dict__
        it = zip(keys, map(partial(getattr, item), keys))
        for thing in it:
            yield thing

    def filterclass(cls):
        """Return filter for dictitem values that are instances of cls."""
        def filt(thing):
            return isinstance(thing[1], cls)
        return filt

    def filterprefix(prefix):
        """Return filter for dictitem keys that start with prefix."""
        def filt(thing):
            return thing[0].startswith(prefix)
        return filt

    def root(widget):
        """Get widget root.

        widget._root is documented as "Internal function."
        """
        master = widget.master
        while master is not None:
            widget = master
            master = widget.master
        return widget

    def add_bindings(
        widget, tag=None, first=True, bindfunc='bind_class',
        tupit=None, filt=filterclass(_BoundBindings), **kwargs):
        """Bind Binding instances.

        widget: widget to use for binding.
        tupit: iterator of tuple: name to Bindings instance.  Defaults
            to memberit(widget)
        tag: bind tag to use, defaults to str(widget).
        first: If bindings already exist for the tag, do nothing.
        kwargs: see Bindings.[tag_]bind()
        """
        if tupit is None:
            tupit = memberit(widget)
        if tag is None:
            tag = str(widget)
        if first and getattr(widget, bindfunc)(tag):
            return
        for name, item in filter(filt, tupit):
            item.bind_(bindfunc, widget, tag, **kwargs)

    class Behavior(object):
        """Class for acting as a namespace containing Bindings callbacks."""

        @classmethod
        def bind(
            cls, widget, tag=None, first=True, bindfunc='bind_class',
            tupit=None, filt=filterclass(_BoundBindings), **kwargs):
            """Call add_bindings on this class."""
            if tupit is None:
                tupit = memberit(cls)
            if bindfunc == 'tag_bind':
                if tag is None:
                    tag = cls.__name__
            return add_bindings(
                widget, tag, first, bindfunc, tupit, filt, **kwargs)


    class Var(object):
        """Wrap a Var, call appropriate trace method."""
        def __init__(self, var):
            self._var = var

        def __str__(self):
            return str(self._var)
        def __repr__(self):
            return repr(self._var)

        def __getattr__(self, name):
            try:
                ret = getattr(self._var, name)
            except AttributeError:
                if name == 'trace_add':
                    def trace_add(mode, callback):
                        return self.trace(mode[:1], callback)
                    self.trace_add = trace_add
                    return trace_add
                raise
            if callable(ret):
                setattr(self, name, ret)
            return ret

    class App(tk.Tk, object):
        """A tkinter.Tk() with binding to escape for exit.

        Does not use any of the subclass methods because
        tk widgets do not add those to bindtags automatically
        instead, the exit should be bound to the instance.
        """
        def __init__(self, *args, **kwargs):
            tk.Tk.__init__(self, *args, **kwargs)
            # tk.Tk should generally be the only one
            # so bindings would be on self bindtag
            # whether member or not
            add_bindings(self)

        @Bindings('<Escape>')
        def __destroy(self):
            self.destroy()

    def get_window_xoffset(widget):
        """Return a delta that places the window on left of screen.

        Because of the window manager, 0 is not necessarily at the left
        edge of the screen.  This doesn't seem to happen for y
        """
        tl = tk.Toplevel(widget)
        try:
            tl.update_idletasks()
            return tl.winfo_x() - tl.winfo_rootx()
        except Exception:
            traceback.print_exc()
            return 0
        finally:
            tl.destroy()

if __name__ == '__main__':
    r = App()

    class SingleText(tk.Text):
        """text with return key doing nothing"""
        def __init__(self, *args, **kwargs):
            kwargs.setdefault('height', 1)
            tk.Text.__init__(self, *args, **kwargs)
            subclass(self, SingleText)
            self.bind_class('SingleText', '<Return>', (lambda e : 'break'))

    t = SingleText(r)
    t.grid(row = 0, column = 0)
    t.bind('<Return>', lambda e : print(repr(t.get('1.0', 'end - 1 c'))))

    def dum(e):
        pass
    func1 = r.bind('<Return>', lambda e : None)
    data1 = r.bind('<Return>')
    func2 = r.bind('<Return>', dum, add=1)
    data2 = r.bind('<Return>')
    unbind(r, '<Return>', func2)
    data3 = r.bind('<Return>')

    assert func1 in data1 and func2 not in data1
    assert func1 in data2 and func2 in data2
    assert func1 in data3 and func2 not in data3
    assert data3 == data1

    def something(widget):
        pass

    print(EvSubs.make_script_(
        r, something, subs=dict(widget=t)))

    r.mainloop()
