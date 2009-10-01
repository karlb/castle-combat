"""
Script for building the example.

Usage:
    python setup.py py2app
"""
from distutils.core import setup
import py2app

NAME = 'Castle-Combat'
VERSION = '0.8.0a1'

plist = dict(
    CFBundleIconFile='castle-combat',
    CFBundleName=NAME,
    CFBundleShortVersionString=VERSION,
    CFBundleGetInfoString=' '.join([NAME, VERSION]),
    CFBundleExecutable=NAME,
    CFBundleIdentifier='com.linux-games.castle-combat',
)

setup(
    data_files=['English.lproj', '../../data'],
    app=[
        dict(script="../../src/castle-combat_bootstrap.py", plist=plist),
    ],
)
