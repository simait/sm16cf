#!/usr/bin/env python
"""Serial line flasher for m16c microcontrollers."""

import time
import struct

class FlasherException(Exception):
	"""Base class for Flasher exceptions."""
class Flasher:
	def __init__(self, device, device_id=None):
		self.device = device
		self.device_id = device_id

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

	def readStatus(self):
		cmd_read_status = struct.pack("B", 0x70)
		self.device.write(cmd_read_status)
		status = self.device.read(2)
		return int(struct.unpack("H", status)[0])

	def readVersion(self):
		cmd_version = struct.pack("B", 0xfb)
		self.device.write(cmd_version)
		version = self.device.read(8)
		return version
