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
import inspect
import sys

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
            k for k in self.bits if getattr(self, k))
    def __getattr__(self, name):
        """Return truthy value if flag is set."""
        result = self.bits[name] & self.state
        setattr(self, name, result)
        return result

EventTypes = {
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

VALIDATION = dict(
    action=('%d', int), #0=delete, 1=add, -1=other
    idx=('%i', int), #index of the change
    pending=('%P', str), #the string if valid
    current=('%s', str), #the string before the change
    change=('%S', str), # the change (added or deleted char if any)
    valstate=('%v', str), # widget.cget('validate')
    valtype=('%V', str), # the validation trigger
    widget=('%W', str)
)
EVENT = dict(
    above=('%a', str),
    borderwidth=('%B', int), #?? screen dist
    button=('%b', int), # mouse button
    char=('%A', str), # printable character or esc sequence (Escape 0x1b, backspace 0x08)
    count=('%c', int),
    data=('%d', str), # user data for virtual events
    delta=('%D', int), # scrolling amount (windows)
    detail=('%d', str), # detail for enter/leave, focus in/out
    focus=('%f', bool), # bool, has focus?
    height=('%h', int), # screendist
    keycode=('%k', int), # uint8
    keysym=('%K', str), # chr?
    keysym_num=('%N', int), # uint16? (keysym_num&0xFF = keycode?)
    mode=('%m', str), # 
    override=('%o', bool), # bool for Map, Reparent, Configure events
    place=('%p', str), # PlaceOn[Top|Bottom] for circulate events
    root=('%R', str), # root name
    rootx=('%X', int), # x on screen
    rooty=('%Y', int), # y on screen
    sendevent=('%E', str), # ?
    serial=('%#', int), # event count
    state=('%s', EvState), # state flags
    subwindow=('%S', str), # subwindow?
    time=('%t', int), # timestamp of event
    type=('%T', EventTypes.__getitem__), # type of event
    tp=('%T', EventTypes.__getitem__), # alias of type since it's a builtin
    widget=('%W', str), # name of widget, requires special handling
    width=('%w', int), # width of widget
    x=('%x', int), # x within widget
    y=('%y', int), # y within widget
)

class Wrapper(object):
    """Wrap a function and convert tcl args to appropriate type."""
    def __init__(self, func, names, scope, master=None):
        self.func = func
        self.subs = []
        self.converters = []
        for k in names:
            sub, cvt = scope[k]
            self.subs.append(sub)
            self.converters.append(cvt)
        try:
            self.name = func.__name__ + str(id(func))
        except Exception:
            self.name = type(func).__name__ + str(id(func))
        if master is not None and 'widget' in names:
            self.converters[names.index('widget')] = master.nametowidget(
                '.').nametowidget

    def script(self):
        return ' '.join([self.name] + self.subs)

    def __call__(self, *args):
        nargs = []
        for c, a in zip(self.converters):
            try:
                nargs.append(c(a))
            except Exception as e:
                print(e, file=sys.stderr)
                nargs.append(a)
        return self.func(*nargs)

class Bindings(object):
    """Represent a set of bindings for some bind tag."""
    def __init__(self, tag, method='bind', scope=EVENT):
        """Initialize a Bindings instance.

        method: bind or tag_bind if a canvas item.
        """
        self.tag = tag
        self.method = method
        self.info = []

    def bind(self, *keyseqs):
        self.info.append(keyseqs)
        return self

    def __call__(self, scriptOrCallback):
        """Register as callback for this bindings instance.

        Because this is intended to be used as a decorator,
        It is assumed that these functions will only ever be
        added once.
        """
        if isinstance(scriptOrCallback, str):
            self.info.append(scriptOrCallback)
        else:
            names = argnames(scriptOrCallback)


        return scriptOrCallback
