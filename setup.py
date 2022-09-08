from setuptools import setup
from jhsiao.namespace import make_ns

make_ns('jhsiao')
setup(
    name='jhsiao-tkutil',
    version='0.0.1',
    author='Jason Hsiao',
    author_email='oaishnosaj@gmail.com',
    description='tkinter helpers',
    packages=['jhsiao'],
    py_modules=['jhsiao.tkutil.util'],
    install_requires=[
        'jhsiao-utils @ git+https://github.com/j-hsiao/py-utils.git',
        'jhsiao-exports @ git+https://github.com/j-hsiao/py-exports.git'
    ])
