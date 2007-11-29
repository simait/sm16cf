#!/usr/bin/env python

import struct

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

	def __make_segment(self, line):
		"""For internal use ONLY!"""


		# Make sure we have at least the smallest possible entry(I think?)
		if len(line) < 10:
			raise SRecException('S-Record too short (%d).' % len(line))
		
		# Validate the size entry
		try:
			size = int(line[:2], 16)
		except:
			raise SRecException('Invalid length entry in S-Record.')

		if len(line) != (2*size+2):
			raise SRecException('Invalid length in S-Record.')

		# Address
		try:
			addr = int(line[2:6], 16)
		except:
			raise SRecException('Invalid address entry in S-Record.')

		# Data
		data = list()
		try:
			for i in range(0,2*(size-3),2):
				data.append(int(line[6+i:8+i], 16))
		except:
			raise SRecException('Invalid data entry in S-Record.')

		# Checksum
		try:
			csum = int(line[-2:], 16)
		except:
			raise SRecException('Invalid checksum entry in S-Record.')

		csum_calc = size + (addr & 0xff) + ((addr >> 8) & 0xff)
		for i in data:
			csum_calc += (i & 0xff)
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
		while True:
			line = self.__file.readline()
			if len(line) == 0:
				raise SRecException('Unexpected end of file.')

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
			elif line[1] == '1':
				# Strip line ending and the 'S' and section type then pass
				# To the make segment function for further processing.
				self.__make_segment(line[2:-len(self.__line_ending)])

			# Last record in the file.
			elif line[1] == '9':
				if len(self.__file.readline()) != 0:
					raise SRecException('Garbage at the end of the file.')
				break

			# No other record types(are others but they are not parsed).
			else:
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
		for i in range(1, len(segments)):
			tmp = segments[i]
			if tmp[0] == (cur[0] + len(cur[1])):
				cur = [cur[0],  cur[1] + tmp[1]]
			else:
				merged.append(cur)
				cur = tmp
		merged.append(cur)

		# Let's use a sorted list instead...
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
