#!/usr/bin/env python

#
#    Simple Flasher is a serial line flashing application for Renesas M16C
#    16-bit single-chip microcomputer.
#
#    Copyright (C) 2007  Simon Aittamaa <simait-2@student.ltu.se>.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from distutils.core import setup

setup(
	name='Simple-Flasher',
	version='1.0.0-pr1',
	description='A simple serial line flasher for M16C.',
	author='Simon Aittamaa',
	author_email='simait-2@student.ltu.se',
	scripts=['sm16cf'],
	packages=['m16c', 'srec']
	)
