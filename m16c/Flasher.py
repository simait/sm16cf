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

"""Serial line flasher for m16c microcontrollers."""

import time
import struct

class FlasherException(Exception):
	"""Base class for Flasher exceptions."""

class Flasher:
	def __init__(self, device, clock_validated=False):
		self.__device = device
		self.__clock_validated = clock_validated
		self.__STATUS_OK            = 'Ok'
		self.__STATUS_WRITE_FAILED  = 'Write failed'
		self.__STATUS_PAGE_LOCKED   = 'Page locked'
		self.__STATUS_INVALID_BLOCK = 'Invalid block'
		self.__STATUS_INVALID_CMD   = 'Invalid command'


	def __sanity(self, id_validation=True, clock_validation=True):
		"""For internal use ONLY!"""

		if clock_validation:
			if not self.__clock_validated:
				raise FlasherException('Clock validation required.')
		if id_validation:
			if not self.id_validated():
				raise FlasherException('Device id validation required.')


	def __status_ready(self, status):
		"""For internal use ONLY!"""

		return (status & 0x80) == 0x80

	def __status_flash_ok(self, status):
		"""For internal use ONLY!"""

		return (status & 0x38) == 0

	def __status_check_ok(self, status):
		"""For internal use ONLY!"""

		return (status & 0x2000) == 0x2000

	def __status_id_ok(self, status):
		"""For internal use ONLY!"""

		return (status & 0xc00) == 0xc00

	def __status_ready_wait(self):
		"""For internal use ONLY!"""

		while True:
			status = self.status_read()
			if not self.__status_ready(status):
				time.sleep(0.1) # Sleep for 100ms
			else:
				break

	def __status_flash_error(self, status):
		"""For internal use ONLY!"""

		if (status & 0x38) == 0:
			return self.__STATUS_OK

		if (status & 0x18) == 0x18:
			return self.__STATUS_INVALID_CMD

		if (status & 0x10) == 0x10:
			return self.__STATUS_INVALID_BLOCK

		if (status & 0x08) == 0x08:
			return self.__STATUS_PAGE_LOCKED

		if (status & 0x04) == 0x04:
			return self.__STATUS_WRITE_FAILED
	
	def clock_validate(self):

		# Note, __sanity does not work here...
		if self.__clock_validated:
			raise FlasherException('Clock already validated.')

		zero = struct.pack("B", 0x00)
		cmd_clock = struct.pack("B", 0xb0)
		self.__device.write(cmd_clock)
		if self.__device.read() != cmd_clock:
			raise FlasherException(
					'Could not connect: Clock validation failed.'
					)

		for i in range(16):
			self.__device.write(zero)
			time.sleep(0.02)

		if self.__device.read() != cmd_clock:
			raise FlasherException(
					'Could not connect: Clock validation failed.'
					)

		self.__clock_validated = True

	def clock_validated(self):

		return self.__clock_validated

	def baud_set_force(self, baud):

		# Force clock validation and baud-rate.

		self.__clock_validated = True

		if self.__device.getBaudrate() == baud:
			return

		if not baud in [9600, 19200, 38400, 57600]:
			raise FlasherException('Invalid baud rate.')

		self.__device.setBaudrate(baud)

	def baud_set(self, baud):
		
		self.__sanity(id_validation=False, clock_validation=True)

		if self.__device.getBaudrate() == baud:
			return

		try:
			baud_rates = [9600, 19200, 38400, 57600]
			cmd_baud_set = struct.pack("B", 0xb0+baud_rates.index(baud))
		except:
			raise FlasherException('Invalid baudrate specified.')

		self.__device.write(cmd_baud_set)
		if self.__device.read() != cmd_baud_set:
			raise FlasherException('Set baudrate failed.')
		self.__device.setBaudrate(baud)

	def baud_get(self, baud):
		
		return self.__device.getBaudrate()

	def id_validate(self, device_id, device_id_addr=0x0fffdf):

		self.__sanity(id_validation=False, clock_validation=True)

		#if self.id_validated():
		#	raise FlasherException('Trying to validate when already validated.')

		if len(device_id) > 7:
			raise FlasherException('Device id too long (%d).' % len(device_id))

		cmd_id_check = struct.pack(
				"BBBBB"+"B"*len(device_id),
				0xf5,
				device_id_addr & 0xff,
				(device_id_addr >> 8) & 0xff,
				(device_id_addr >> 16) & 0xff,
				len(device_id),
				*device_id
				)
		self.__device.write(cmd_id_check)

		if not self.id_validated():
			raise FlasherException('Failed to validate id.')

	def id_validated(self):
		
		return (self.status_read() & 0xc00) == 0xc00

	def status_read(self):

		self.__sanity(id_validation=False, clock_validation=True)

		cmd_status_read = struct.pack("B", 0x70)
		self.__device.write(cmd_status_read)
		status = self.__device.read(2)
		return struct.unpack("<H", status)[0]

	def status_clear(self):

		self.__sanity(id_validation=True, clock_validation=True)

		cmd_status_read = struct.pack("B", 0x50)
		self.__device.write(cmd_status_read)

		# TODO: Check result of command

	def version_read(self):

		self.__sanity(id_validation=False, clock_validation=True)

		cmd_version_read = struct.pack("B", 0xfb)
		self.__device.write(cmd_version_read)
		version = self.__device.read(8)
		return version

	def lock_enable(self):

		self.__sanity(id_validation=True, clock_validation=True)

		cmd_lock_enable = struct.pack("B", 0x7a)
		self.__device.write(cmd_lock_enable)

		# TODO: Check result of command

	def lock_disable(self):

		self.__sanity(id_validation=True, clock_validation=True)

		cmd_lock_disable = struct.pack("B", 0x75)
		self.__device.write(cmd_lock_disable)

		# TODO: Check result of command

	def program_run(self, data):

		self.__sanity(id_validation=True, clock_validation=True)

		raise FlasherException('Loading program to RAM not yet supported.')

		#if len(data) > 0xffff:
		#	raise FlasherException('Program too large (>0xffff).')

		#checksum = 0
		#cmd_program_run = struct.pack(
		#		"BBBB",
		#		0xfa,
		#		len(data) & 0xff,
		#		(len(data) >> 8) & 0xff,
		#		checksum
		#		)
		#self.__device.write(cmd_program_run)
		#self.__device.write(data)

		# TODO: Check result of command

	def boot_read(self, addr):

		self.__sanity(id_validation=True, clock_validation=True)
		
		cmd_boot_read = struct.pack(
				"BBB",
				0xfc,
				(addr >> 8) & 0xff,
				(addr >> 16) & 0xff
				)
		self.__device.write(cmd_page_read)
		page = self.__device.read(256)
		if len(page) != 256:
			raise FlasherException(
					'Unable to read boot page: Timeout or insufficient data (%d).' % len(page)
					)

		if not self.__status_flash_ok(self.status_read()):
			raise FlasherException(
					'Failed to read page at address: 0x%60x' % address & 0xffff00
					)

		return page

	def page_read(self, addr):

		self.__sanity(id_validation=True, clock_validation=True)

		self.__status_ready_wait()

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

		status = self.status_read()
		if not self.__status_flash_ok(status):
			raise FlasherException(
					'Reading page 0x%06x failed: \'%s\'.' % (addr & 0xffff00, self.__status_flash_error(status))
					)

		return page

	def page_write(self, addr, data):

		self.__sanity(id_validation=True, clock_validation=True)

		self.__status_ready_wait()

		if len(data) > 256:
			raise FlasherException('Invalid page size (%d != 256).' % len(data))

		cmd_page_write = struct.pack(
				"BBB",
				0x41,
				(addr >> 8) & 0xff,
				(addr >> 16) & 0xff
				)
		self.__device.write(cmd_page_write)
		self.__device.write(data)

		status = self.status_read()
		if not self.__status_flash_ok(status):
			raise FlasherException(
					'Write to page 0x%06x failed: \'%s\'.' % (addr & 0xffff00, self.__status_flash_error(status))
					)

	def block_erase(self, addr):

		self.__sanity(id_validation=True, clock_validation=True)

		self.__status_ready_wait()

		cmd_block_erase = struct.pack(
				"BBBB",
				0x20,
				(addr >> 8) & 0xff,
				(addr >> 16) & 0xff,
				0xd0
				)
		self.__device.write(cmd_block_erase)

		status = self.status_read()
		if not self.__status_flash_ok(self.status_read()):
			raise FlasherException(
					'Block erase failed: \'%s\'.' % self.__status_flash_error(status)
					)

	def block_erase_all(self):

		self.__sanity(id_validation=True, clock_validation=True)

		self.__status_ready_wait()

		cmd_block_erase = struct.pack(
				"BB",
				0xa7,
				0xd0
				)
		self.__device.write(cmd_block_erase)

		status = self.status_read()
		if not self.__status_flash_ok(self.status_read()):
			raise FlasherException(
					'Erase all blocks failed: \'%s\'.' % self.__status_flash_error(status)
					)

	def segment_write(self, segment):
		"""Write a segment (address+data) to the device."""

		# Check the address sanity.
		if segment[0] < 0 or segment[0] > 0xffffffff:
			raise FlasherException('Invalid segment address.')

		# Make sure the segment does not go beyond the theorethical limit
		if (segment[0] + len(segment[1])) > 0xffffff:
			raise FlasherException(
					'Segment size beyond end of theorethical flash.'
					)

		page = segment[0] & 0xffff00
		last = (segment[0] + len(segment[1]) + 0xff) & 0xffff00
		sent = 0
		lower = segment[0]
		upper = segment[0] + len(segment[1])

		while page < last:

			start = max(0, lower-page)
			end   = min(256, start+upper-lower)
			size  = end - start

			if (start, end) != (0, 256):
				tmp = self.page_read(page)
				data = tmp[:start] + segment[1][sent:sent+size] + tmp[end:]
			else:
				data = segment[1][sent:sent+size]
			
			if len(data) != 256:
				raise FlasherException('Invalid length: %d (BUG!)' % len(data))

			self.page_write(page, data)

			page += 0x100
			sent += size
			lower += size

		if sent != len(segment[1]):
			raise FlasherException('Failed to write all data? (BUG!)')
