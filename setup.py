from setuptools import setup
from jhsiao.namespace import make_ns

make_ns('jhsiao')
setup(
    name='jhsiao-tkutil',
    version='0.0.2',
    author='Jason Hsiao',
    author_email='oaishnosaj@gmail.com',
    description='tkinter helpers',
    packages=['jhsiao.tkutil', 'jhsiao.tkutil.bindings'],
)
