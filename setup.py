#!/usr/bin/env python

from distutils.core import setup

setup(
	name='Simple/Serial Flasher',
	version='0.1.0',
	description='A simple serial line flasher for M16C.',
	author='Simon Aittamaa',
	author_email='simait-2@student.ltu.se',
	scripts=['sf'],
	packages=['m16c', 'srec']
	)
