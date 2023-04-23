from jhsiao.tkutil import tk, add_bindtags

def test_bindtags():
    r = tk.Tk()
    l = tk.Label(r)
    print(l.bindtags())
    print('adding after self')
    add_bindtags(l, 'afterself')
    print(l.bindtags())
    print('before class')
    add_bindtags(l, 'beforeclass', before=type(l).__name__)
    print(l.bindtags())
    print('after all')
    add_bindtags(l, 'afterall', after='all')
    print(l.bindtags())
