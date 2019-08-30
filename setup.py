#!/usr/bin/env python -*- coding: utf-8 -*-
#
# Python Word Sense Disambiguation (pyWSD)
#
# Copyright (C) 2014-17 alvations
# URL:
# For license information, see LICENSE.md

from distutils.core import setup

setup(
    name='wn',
    version='0.0.21',
    packages=['wn'],
    description='Wordnet',
    long_description='',
    url = 'https://github.com/alvations/wordnet',
    package_data={'wn': ['data/omw/*',
                         'data/wordnet/*',
                         'data/wordnet_ic/*',]},
    license="MIT"
)
