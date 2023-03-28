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
    state=('%s', _EvState), # state flags
    subwindow=('%S', str), # subwindow?
    time=('%t', int), # timestamp of event
    type=('%T', _EventTypes.__getitem__), # type of event
    tp=('%T', _EventTypes.__getitem__), # alias of type since it's a builtin
    widget=('%W', str), # name of widget, requires special handling
    width=('%w', int), # width of widget
    x=('%x', int), # x within widget
    y=('%y', int), # y within widget
)

class BoundScope(object):
    """Wrap a scope.

    Prefer the master's nametowidget function as conversion function
    for the 'widget' substitution.
    """
    def __init__(self, master, scope):
        self.master = master
        self.scope = scope
    def __getitem__(self, name):
        if name == 'widget':
            func = self.master.nametowidget('.').nametowidget
            return self.scope[name][0], func
        else:
            return self.scope[name]
