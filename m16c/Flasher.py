#!/usr/bin/env python
"""Serial line flasher for m16c microcontrollers."""

import time
import struct

class FlasherException(Exception):
	"""Base class for Flasher exceptions."""

class Flasher:
	def __init__(self, device, clock_validated=False):
		self.__device = device
		self.__clock_validated = clock_validated


	def __sanity(self, id_validation=True, clock_validation=True):
		"""For internal use ONLY!"""

		if clock_validation:
			if not self.__clock_validated:
				raise FlasherException('Clock validation required.')
		if id_validation:
			if not self.id_validated():
				raise FlasherException('Device id validation required.')

	def clock_validate(self):

		# Note, __sanity does not work here...
		if self.__clock_validated:
			raise FlasherException('Clock already validated.')

		zero = struct.pack("B", 0x00)
		cmd_clock = struct.pack("B", 0xb0)
		self.__device.write(cmd_clock)
		if self.__device.read() != cmd_clock:
			raise FlasherException(
					'Could not connect: Clock valiadation failed.'
					)

		for i in range(16):
			self.__device.write(zero)
			time.sleep(0.02)

		if self.__device.read() != cmd_clock:
			raise FlasherException(
					'Could not connect: Clock valiadation failed.'
					)

		self.__clock_validated = True

	def clock_validated(self):

		return self.__clock_validated

	def id_validate(self, device_id, device_id_addr=0xffff):

		self.__sanity(id_validation=False, clock_validation=True)

		status = self.status_read()
		if ((status >> 10) & 0x3) == 0x3:
			raise FlasherException('Trying to validate when already validated.')

		elif len(device_id) > 7:
			raise FlasherException('Device id too long (%d).' % len(device_id))

		cmd_id_check = struct.pack(
				"BBBBB",
				0xf5,
				device_id_addr & 0xff,
				(device_id_addr >> 8) & 0xff,
				(device_id_addr >> 16) & 0xff,
				len(device_id)
				)
		cmd_id_check += struct.pack('B'*len(device_id), *device_id)

		self.__device.write(cmd_id_check)
		
		status = self.status_read()
		print('0x%04x (%s)' % (status, str(self.id_validated())))

	def id_validated(self):
		
		return (self.status_read() & 0xc00) == 0xc00

	def status_read(self):

		self.__sanity(id_validation=False, clock_validation=True)

		cmd_status_read = struct.pack("B", 0x70)
		self.__device.write(cmd_status_read)
		status = self.__device.read(2)
		return struct.unpack("<H", status)[0]

	def version_read(self):

		self.__sanity(id_validation=False, clock_validation=True)

		cmd_version_read = struct.pack("B", 0xfb)
		self.__device.write(cmd_version_read)
		version = self.__device.read(8)
		return version

	def page_read(self, addr):

		self.__sanity(id_validation=True, clock_validation=True)

		cmd_page_read = struct.pack(
				"BBB",
				0xff,
				(addr >> 8) & 0xff,
				(addr >> 16) & 0xff
				)
		self.__device.write(cmd_page_read)
		page = self.__device.read(256)
		if len(page) != 256:
			raise FlasherException(
					'Unable to read page: Timeout or insufficient data (%d).' % len(page)
					)
		return page

	def page_write(self, addr, data):

		self.__sanity(id_validation=True, clock_validation=True)

		cmd_page_write = struct.pack(
				"BBB",
				0x41,
				(addr >> 8) & 0xff,
				(addr >> 16) & 0xff
				)
		self.__device.write(cmd_page_write)
		self.__device.write(data)

	def page_erase(self, addr):

		self.__sanity(id_validation=True, clock_validation=True)

		cmd_page_erase = struct.pack(
				"BBBB",
				0x20,
				(addr >> 8) & 0xff,
				(addr >> 16) & 0xff,
				0xd0
				)
		self.__device.write(cmd_page_erase)
