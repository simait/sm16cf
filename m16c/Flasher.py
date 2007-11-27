#!/usr/bin/env python
"""Serial line flasher for m16c microcontrollers."""

import time
import struct

class FlasherException(Exception):
	"""Base class for Flasher exceptions."""
class Flasher:
	def __init__(self, device, device_id=None, device_id_addr=None):
		self.device = device
		self.device_id = device_id
		self.device_id_addr = device_id_addr

	def validateClock(self):
		zero = struct.pack("B", 0x00)
		cmd_clock = struct.pack("B", 0xb0)
		self.device.write(cmd_clock)
		if self.device.read() != cmd_clock:
			raise FlasherException(
					'Could not connect: Clock valiadation failed.'
					)

		for i in range(16):
			self.device.write(zero)
			time.sleep(0.02)

		if self.device.read() != cmd_clock:
			raise FlasherException(
					'Could not connect: Clock valiadation failed.'
					)

	def idCheck(self):
		if self.device_id == None:
			raise FlasherException(
					'Unable to check id, none specified.'
					)
		if self.device_id_addr == None:
			raise FlasherException(
					'No device id address specified.'
					)
		cmd_id_check = struct.pack(
				"BBBBB",
				0xf5,
				self.device_id_addr & 0xff,
				(self.device_id_addr >> 8) & 0xff,
				(self.device_id_addr >> 16) & 0xff,
				len(self.device_id)
				)
		for i in range(len(self.device_id)):
			cmd_id_check += struct.pack("B", self.device_id[i])

		self.device.write(cmd_id_check)
		return
		
	def readStatus(self):
		cmd_read_status = struct.pack("B", 0x70)
		self.device.write(cmd_read_status)
		status = self.device.read(2)
		return status

	def readVersion(self):
		cmd_version = struct.pack("B", 0xfb)
		self.device.write(cmd_version)
		version = self.device.read(8)
		return version

	def readPage(self, addr):
		cmd_read_page = struct.pack(
				"BBB",
				0xff,
				(addr >> 8) & 0xff,
				(addr >> 16) & 0xff
				)
		self.device.write(cmd_read_page)
		page = self.device.read(256)
		if len(page) != 256:
			raise FlasherException(
					'Unable to read page: Timeout or insufficient data (%d).' % len(page)
					)
		for i in range(len(page)):
			print(hex(int(page[i])))
