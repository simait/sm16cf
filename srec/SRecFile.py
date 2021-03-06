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


import sys, struct, timeit, array

"""Motorola S-Record parser."""

class SRecException(Exception):
	"""Base class for S-Record exception."""

class SRecFile:
	"""Class for parsing a S-Record file."""

	def __init__(self, file):
		self.__file = file
		self.__segments = dict()
		self.__line_ending = None
		self.__load()
		self.__merge()
		self.__convert()

	def __make_segment(self, addr_len, line):
		"""For internal use ONLY!"""

		lint = int
		llen = len
		# Make sure we have at least the smallest possible entry(I think?)
		if llen(line) < (6 + 2*addr_len):
			raise SRecException('S-Record too short (%d).' % llen(line))
		
		# Validate the size entry
		try:
			size = lint(line[:2], 16)
		except:
			raise SRecException('Invalid length entry in S-Record.')

		if llen(line) != (2*size+2):
			raise SRecException('Invalid length in S-Record.')

		# Address, depends on type
		if not addr_len in (2,3):
			raise SRecException('Invalid address length of S-Record.')

		addr_start = 2
		addr_end = addr_start + 2*addr_len

		try:
			addr = lint(line[addr_start:addr_end], 16)
		except:
			raise SRecException('Invalid address entry in S-Record.')

		# Data
		data = list()
		try:
			for i in range(0,2*(size-addr_len-1),2):
				data.append(lint(line[addr_end+i:addr_end+i+2], 16))
		except:
			raise SRecException('Invalid data entry in S-Record.')

		# Checksum
		try:
			csum = lint(line[-2:], 16)
		except:
			raise SRecException('Invalid checksum entry in S-Record.')

		tmp = addr
		csum_calc = size
		csum_calc += sum(data)
		#csum_calc += sum(struct.unpack("BBBB", struct.pack("I", tmp)))
		while tmp > 0:
				csum_calc += tmp & 0xff
				tmp >>= 8
		csum_calc = (~csum_calc & 0xff)

		# Debug info...
		#print('Address: 0x%04x' % addr)
		#for i in data:
		#	print('\t0x%02x' % i)
		#print('Checksum: 0x%02x(0x%02x)' % (csum_calc, csum))

		if csum != csum_calc:
			raise SRecException('Invalid checksum in S-Record.')

		if self.__segments.has_key(addr):
			raise SRecException('Duplicate address in S-Record file.')

		self.__segments[addr] = data

	def __load(self):
		"""For internal use ONLY!"""

		line_number = 0
		for line in self.__file:

			# Determine the line ending of the file
			if self.__line_ending == None:
				# DOS
				if line[-2:] == '\r\n':
					self.__line_ending = '\r\n'
				# Linux/Unix
				elif line[-1:] == '\r':
					self.__line_ending = '\r'
				# Mac
				elif line[-1:] != '\n':
					self.__line_ending = '\n'
				else:
					raise SRecException('Invalid line ending in S-Record.')

			# Make sure it's consistant.
			else:
				if self.__line_ending != line[-len(self.__line_ending):]:
					raise SRecException(
							'Inconsistant line endings in S-Record.'
							)

			if line[0] != 'S':
				raise SRecException('Invalid record found')
			
			# Header record
			if line[1] == '0':
				if line_number != 0:
					raise SRecException(
							'Expected header but got: %c .' % line[1]
							)

			# Regular data record.
			elif line[1] in ('1', '2'):
				# Strip line ending and the 'S' and section type then pass
				# To the make segment function for further processing.
				try:
					addr_len = int(line[1])+1
				except:
					raise SRecException('BUG!!!')

				self.__make_segment(addr_len, line[2:-len(self.__line_ending)])

			# Only record types we accept right now.
			elif not line[1] in ('8', '9'):
				raise SRecException('Invalid record type: \'%s\'.' % line[:2])

			line_number += 1

		# Make sure there where at least one data record.
		if len(self.__segments) == 0:
			raise SRecException('S-Record file contained no data segments.')

	def __merge(self):
		"""For internal use ONLY!"""

		# Sort on the address, ascending
		segments = self.__segments.items()
		segments.sort(key=lambda x: x[0])

		# Merge all consecutive segments.
		cur = segments[0]
		merged = list()
		for i in segments[1:]:
			if i[0] == (cur[0] + len(cur[1])):
				cur = [cur[0],  cur[1] + i[1]]
			else:
				merged.append(cur)
				cur = i
		merged.append(cur)
		self.__segments = merged

	def __convert(self):
		"""For internal use ONLY!"""

		# Convert each segment to sequence of bytes.
		converted = list()
		for i in self.__segments:
			try:
				tmp = struct.pack(
						'B'*len(i[1]),
						*i[1]
						)
				converted.append((i[0], tmp))
			except:
				raise SRecException(
						'Internal parser error, entry out of range.'
						)

		self.__segments = converted

	def segments(self):
		return self.__segments

	def dump_segments(self):
		for i in self.__segments:
			print('Address: 0x%04x' % i[0])
			print('Data: ' + '%02x'*len(i[1]) % tuple(map(ord, i[1])))
