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

"""Serial line flasher application for m16c microcontrollers."""

import serial, m16c, struct, sys, srec
from optparse import OptionParser, SUPPRESS_HELP

class M16CFlashApp:
	"""Serial flasher for M16, application class."""

	def __init__(self):

		parser = OptionParser()

		# Options goes here
		parser.add_option(
				'-d', '--device',
				dest='device',
				type='string',
				help='The serial device.'
				)
		parser.add_option(
				'-b', '--baud-rate',
				dest='baud',
				type='int',
				default=9600,
				help='The baud rate (default: 9600).'
				)
		parser.add_option(
				'-t', '--timeout',
				dest='timeout',
				type='int',
				default=5,
				help='Timeout in seconds for serial communication (default: 5).'
				)
		parser.add_option(
				'--device-id',
				dest='device_id',
				type='string',
				default='0:0:0:0:0:0:0',
				help='The device id used to validate the device. ' +
				'Example: ae:23:3a:dd:ea:32:3f (default: 0:0:0:0:0:0:0).'
				)
		parser.add_option(
				'--device-id-addr',
				dest='device_id_addr',
				type='int',
				default=0x0fffdf,
				help=SUPPRESS_HELP
				#help='The address of the device id. Example: 0x0fffdf'
				)
		parser.add_option(
				'-n', '--no-clock-validation',
				dest='clock_validation',
				action='store_false',
				default=True,
				help=SUPPRESS_HELP
				#help='Disable clock validation when connecting.'
				)
		parser.add_option(
				'-a', '--address',
				dest='address',
				action='append',
				type='string',
				help=SUPPRESS_HELP
				#help='The address of the operation (except id-validate). Format: addr[:size], if addr or sizeis on the form 0xXXXXX hex is assumed, otherwise base 10. May be specified more than once accumulative.'
				)
		parser.add_option(
				'-i', '--input-file',
				dest='input_file',
				type='string',
				help='The input file for the operation.'
				)
		parser.add_option(
				'-o', '--output-file',
				dest='output_file',
				type='string',
				help=SUPPRESS_HELP
				#help='The output file for the operation.'
				)
		parser.add_option(
				'-u', '--unsafe',
				dest='safe',
				action='store_false',
				default=True,
				help='Enable unsafe assumptions (do not use unless you know what you are doing!!!).'
				)
		
		self.__action = None
		self.__action_map = [
			(
			 '--flash-program',
			 'Program the flash with the given file.',
			 self.__flash_program
			),
			(
			 '--status-read',
			 SUPPRESS_HELP,
			 #'Read the status register of the device.',
			 self.__status_read
			),
			(
			 '--status-clear',
			 SUPPRESS_HELP,
			 #'Clear the status register of the device.',
			 self.__status_clear
			),
			(
			 '--version-read',
			 SUPPRESS_HELP,
			 #'Read the version of the device.',
			 self.__version_read
			),
			(
			 '--flash-read',
			 SUPPRESS_HELP,
			 #'Read the specified address(es) range(s) from the device.',
			 self.__flash_read
			),
			(
			 '--flash-write',
			 SUPPRESS_HELP,
			 #'Write the give input file to the device flash.',
			 self.__flash_write
			),
			(
			 '--flash-erase',
			 SUPPRESS_HELP,
			 #'Erase the block(s) at the address(es) (broken).',
			 self.__flash_erase
			),
			(
			 '--flash-erase-all',
			 SUPPRESS_HELP,
			 #'Erase all blocks (that are unlocked).',
			 self.__flash_erase_all
			),
			(
			 '--id-validate',
			 SUPPRESS_HELP,
			 #'Perform an id validation, required for most actions.',
			 self.__id_validate
			)
			]

		# Add each of the actions from the action map.
		for i in self.__action_map:
			parser.add_option(
					i[0],
					help=i[1],
					action='callback',
					callback=self.__append_action,
					callback_args=(i[2],)
					)


		(options, args) = parser.parse_args()
		
		# Garbage is error(?)
		if len(args) != 0:
			raise Exception(
					'Unknown garbage on command line:' +
					' \'%s\'' * len(args) % (tuple(args))
					)

		# Check the device.
		if options.device == None:
			raise Exception('No device specified.')

		# Grab device id
		self.__device_id_addr = options.device_id_addr
		try:
			# Create a list of int instead
			self.__device_id = options.device_id.split(':')
			fields = len(self.__device_id)

			# Make sure no number are too large or too small
			self.__device_id = filter(
					lambda x: (x >= 0) and (x <= 255),
					map(lambda x: int(x, 16), self.__device_id)
					)
			if fields != len(self.__device_id):
				raise Exception('Device id field(s) out of range.')

		except TypeError:
			raise Exception('Device id contains invalid field(s).')
			
		# Grab any input/output files.
		self.__input_file = options.input_file
		self.__output_file = options.output_file

		# Grab any addresses
		self.__address = options.address
		if self.__address != None:
			tmp = []
			for i in self.__address:
				try:
					val = i.split(':')
					addr = val[0]
	
					if addr[:2] == '0x':
						addr = int(addr, 16)
					else:
						addr = int(addr)

					if len(val) != 1:
						rng = val[1]
						if rng[:2] == '0x':
							rng = int(rng[2:], 16)
						else:
							rng = int(rng)
					else:
						rng = 0
					
					tmp.append((addr, rng))

				except:
					raise Exception('Invalid address format.')

			self.__address = tmp

		# Propagate any unsafe behvaiour.
		self.__safe = options.safe

		# Create a serial device
		device = serial.Serial(
				port=options.device,
				timeout=options.timeout
				)

		# Make sure we managed to open the device succesfully
		if not device.isOpen():
			raise Exception('Unable to open the serial device.')

		# Create the flasher
		self.__flasher = m16c.Flasher(
				device,
				not options.clock_validation
				)
		if not self.__flasher.clock_validated():
			try:
				self.__flasher.clock_validate()
				self.__flasher.baud_set(options.baud)
			except m16c.FlasherException, (error):
				if self.__safe:
					raise
				else:
					print('Warning: Clock validation failed, assuming M16C.')
					self.__flasher.baud_set_force(options.baud)
					self.__flasher.status_clear()
		else:
			device.setBaudrate(options.baud)

		# Make sure an action was specified.
		if self.__action == None:
			raise Exception('No action was given, nothing is performed.')


	def __append_action(self, option, opt, value, parser, action):
		"""For internal use ONLY!"""

		if self.__action == None:
			self.__action = list()
		self.__action.append(action)

	def __device_id_set(self, option, opt, value, parser):
		"""For internal use ONLY!"""


	def __unimplemented(self):
		"""For internal use ONLY!"""

		raise Exception('Action is not implemented.')

	def __flash_program(self):
		"""For internal use ONLY!"""
		
		# Let's do this here as well, might be redundant but at least we don't
		# erase the flash each time we fail to give an input file.
		if self.__input_file == None:
			raise Exception('No input file was given.')

		# Validate.
		if not self.__flasher.id_validated():
			self.__flasher.id_validate(self.__device_id)

		# Erase the entire flash.
		self.__flash_erase_all()

		# And program the file.
		self.__flash_write()

	def __status_read(self):
		"""For internal use ONLY!"""

		status = self.__flasher.status_read()
		print('Status register: 0x%04x' % status)

	def __status_clear(self):
		"""For internal use ONLY!"""

		status = self.__flasher.status_clear()

	def __version_read(self):
		"""For internal use ONLY!"""

		print('Firmware version: %s' % self.__flasher.version_read())

	def __id_validate(self):
		"""For internal use ONLY!"""

		if self.__device_id == None:
			raise Exception('Device id not specified.')

		self.__flasher.id_validate(self.__device_id, self.__device_id_addr)

	def __flash_read(self):
		"""For internal use ONLY!"""

		if self.__address == None:
			raise Exception('No address specified.')
		
		# Simple sanity check, might still fawk up but...
		for i in self.__address:
			if i[0] > 0xffff00:
				raise Exception('Address out of range (beyond theorethical).')
			if i[1] == 0:
				raise Exception('Range 0 not allowed when reading flash.')

		# And start dumping the data.
		data = str()
		for i in self.__address:
			(addr, rng)= (i[0], i[1])
			while rng > 0:
				tmp = self.__flasher.page_read(addr)
				lower = addr%len(tmp)
				upper = min(lower+rng, len(tmp))
				data += tmp[lower:upper]
				addr += upper-lower
				rng  -= upper-lower

				sys.stderr.write('\rReading 0x%06x...' % (addr & 0xffff00))
		sys.stderr.write(' Done.\n')

		# Dump to file or stdout
		if self.__output_file != None:
			file = open(self.__output_file, 'wb')
			file.write(data)
			file.close()
		else:
			sys.stdout.write(data)


	def __flash_write(self):
		"""For internal use ONLY!"""

		if self.__input_file == None:
			raise Exception('No input file was given.')

		# Parse the file.
		file = open(self.__input_file)
		file = srec.SRecFile(file)

		# Write the segments of the file.
		for i in file.segments():
			self.__flasher.segment_write(i)

	
	def __flash_erase(self):
		"""For internal use ONLY!"""

		if self.__address == None:
			raise Exception('No address specified.')
		
		# Simple sanity check, might still fawk up but...
		for i in self.__address:
			if i[0] > 0xffff00:
				raise Exception('Address out of range (beyond theorethical).')

			# Erase the block.
			self.__flasher.block_erase(i[0])

	def __flash_erase_all(self):
		"""For internal use ONLY!"""
		
		# Erase all unlocked blocks.
		self.__flasher.block_erase_all()

	def __ram_program(self):
		"""For internal use ONLY!"""
		
		if self.__input_file == None:
			raise Exception('No input file was given.')

	def run(self):

		for i in self.__action:
			i()


