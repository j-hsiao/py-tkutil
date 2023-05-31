"""Binding scopes.

Scopes are pairs of tk substitution code and conversion function.
"""
class _EvState(object):
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
        s = self.state
        return ' | '.join(
            k for k, v in self.bits.items() if s & v )
    def __getattr__(self, name):
        """Return truthy value if flag is set."""
        try:
            result = self.bits[name] & self.state
        except KeyError:
            raise AttributeError(name)
        setattr(self, name, result)
        return result

_EventTypes = {
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

class Scope(object):
    def __init__(self, master=None, overrides={}):
        """Initialize a script/binding scope.

        master: the master widget.
        overrides: dict of key: (sub, func), where sub is a substitution
            for the script and func is a translation function to parse
            the argument.  If either is None, then it will fall back to
            the original subs.
        """
        self.overrides = overrides
        self.master = master

    def update(self, overrides):
        """Return new scope with updated overrides.

        If the value is not a tuple, replace it with (value, None).
        """
        for k, v in overrides.items():
            if not isinstance(v, tuple):
                overrides[k] = (v, None)
        cp = self.overrides.copy()
        cp.update(overrides)
        return type(self)(self.master, cp)

    def func(self, name, func, default):
        """Retrieve the bound func.

        name: name of argument.
        func: overridden func.
        default: the default function.

        Prioritize the func value.  If a str, then if func is:
            'widget': nametowidget
            any other str: self.master.<func>
        Otherwise, use the default func() for name:
            'widget': nametowidget
        """
        if self.master is not None:
            if isinstance(func, str):
                if func == 'widget':
                    return self.master.nametowidget
                return getattr(self.master, func)
            elif name == 'widget':
                return self.master.nametowidget
        return default

    def __getitem__(self, k):
        sub, func = self.overrides.get(k, (None, None))
        osub, ofunc = self.subs.get(k, (None, None))
        if sub is None:
            sub = osub
        else:
            sub = str(sub)
        if not callable(func):
            func = self.func(k, func, ofunc)
        return sub, func

class Trace(Scope):
    """Variable trace functions.

    trace add variable command var index op

    widget: name of widget to add.  Note that tcl does not add this
        name itself, so it MUST be overriden
    data: any data to pass to the callback.  This is also not added by
        tcl and so must be overriden if used.
    var: name of variable or array
    index: index if array or empty (-1)
    op: read write or unset

    Because of this, var, index, op are REQUIRED and MUST be the last
    arguments of the function.
    """
    subs = dict(
        widget=(None, str),
        data=(None, str),
        var=('', str),
        index=('', str),
        op=('', str)
    )


class Validation(Scope):
    """Validation function substitution scope.

    action: the action, 0=delete, 1=add, -1=other
    idx: index of the change
    pending: the pending string
    current: the current string before change
    change: the change (added or deleted char)
    valstate: widget.cget('validate')
    valtype: trigger: none, focus, focusin, focusout, key, or all
    widget: the widget.
    """
    subs = dict(
        action=('%d', int), #0=delete, 1=add, -1=other
        idx=('%i', int), #index of the change
        pending=('%P', str), #the string if valid
        current=('%s', str), #the string before the change
        change=('%S', str), # the change (added or deleted char if any)
        valstate=('%v', str), # widget.cget('validate')
        valtype=('%V', str), # the validation trigger
        widget=('%W', str),
        data=(None, str),
    )

class Event(Scope):
    """Event binding scope.

    above: above widget (for <Configure>)
    borderwidth: width? (for <Configure>)
    button: mouse button
    char: printable character or esc sequence (Escape 0x1b, backspace 0x08)
    count: count (for <Expose>)
    data: user data for virtual events
    delta: scrolling amount (windows)
    detail: detail for enter/leave, focus in/out
    focus: bool, has focus?
    height: screendist
    keycode: int key uchar?
    keysym: chr? name?
    keysym_num: uint16? (keysym_num&0xFF = keycode?)
    mode: <Enter/Leave/Focus[In/Out]> Notify[Normal|Grab|Ungrab|WhileGrabbed]
    override: bool for Map, Reparent, Configure events
    place: PlaceOn[Top|Bottom] for circulate events
    root: root name
    rootx: x on screen
    rooty: y on screen
    sendevent: bool, ??
    serial: event count
    state: state flags
    subwindow: subwindow?
    time: timestamp of event
    type: type of event
    tp: alias of type since it's a builtin
    widget: name of widget, requires special handling
    width: width of widget
    x: x within widget
    y: y within widget
    """
    subs = dict(
        above=('%a', str),
        borderwidth=('%B', int),
        button=('%b', int),
        char=('%A', str),
        count=('%c', int),
        data=('%d', str),
        delta=('%D', int),
        detail=('%d', str),
        focus=('%f', bool),
        height=('%h', int),
        keycode=('%k', int),
        keysym=('%K', str),
        keysym_num=('%N', int),
        mode=('%m', str),
        override=('%o', bool),
        place=('%p', str),
        root=('%R', str),
        rootx=('%X', int),
        rooty=('%Y', int),
        sendevent=('%E', bool),
        serial=('%#', int),
        state=('%s', _EvState),
        subwindow=('%S', str),
        time=('%t', int),
        type=('%T', _EventTypes.__getitem__),
        tp=('%T', _EventTypes.__getitem__),
        widget=('%W', str),
        width=('%w', int),
        x=('%x', int),
        y=('%y', int),
    )
