#!/usr/bin/env python
# encoding: utf-8
#import codecs
#try:
#    codecs.lookup('mbcs')
#except LookupError:
#    ascii = codecs.lookup('ascii')
#    func = lambda name, enc=ascii: {True: enc}.get(name == 'mbcs')
#    codecs.register(func)

import topaz
from setuptools import setup

#from distutils.core import setup

setup(
    name="topaz_bi",
    version=topaz.__version__,
    package_dir={'': 'src'},
    packages=["topaz",
              "topaz/fsm"],
    package_data={'': ['*.xml', '*.dll', '*.so']},
    author="qibo",
    description='Agigatech Topaz Burnin Program',
    platforms="any",
    entry_points={
        "console_scripts": [
            'burnin = topaz.burnin:main'
        ]
    }
)
