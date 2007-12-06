#!/usr/bin/env python

import serial, m16c, struct, sys, srec
from optparse import OptionParser

class M16CFlash:
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
				help='The baud rate.'
				)
		parser.add_option(
				'-t', '--timeout',
				dest='timeout',
				type='int',
				default=5,
				help='Timeout in seconds for serial communication.'
				)
		parser.add_option(
				'--device-id',
				dest='device_id',
				type='string',
				help='The device id used for mutable operations. ' +
				'Example: ae:23:3a:dd:ea:32'
				)
		parser.add_option(
				'--device-id-addr',
				dest='device_id_addr',
				type='int',
				default=0x0fffdf,
				help='The address of the device id. Example: 0x0fffdf'
				)
		parser.add_option(
				'-n', '--no-clock-validation',
				dest='clock_validation',
				action='store_false',
				help='Disable clock validation when connecting.',
				default=True
				)
		parser.add_option(
				'-a', '--address',
				dest='address',
				action='append',
				type='string',
				help='The address of the operation (except id-validate). Format: addr[:range], if addr or range is on the form 0xXXX hex is assumed, otherwise base 10. May be specified more than once accumulative.'
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
				help='The output file for the operation.'
				)
		
		# Actions goes here.
		parser.add_option(
				'--status-read',
				dest='action',
				action='append_const',
				const=self.__status_read,
				help='Read the status register of the device.'
				)
		parser.add_option(
				'--status-clear',
				dest='action',
				action='append_const',
				const=self.__status_clear,
				help='Clear the status register of the device.'
				)
		parser.add_option(
				'--version-read',
				dest='action',
				action='append_const',
				const=self.__version_read,
				help='Read the firmware version of the device.'
				)
		parser.add_option(
				'--flash-read',
				dest='action',
				action='append_const',
				const=self.__flash_read,
				help='Read the specified address(es) range(s) from the device.'
				)
		parser.add_option(
				'--flash-write',
				dest='action',
				action='append_const',
				const=self.__flash_write,
				help='Write the input file to the device flash.'
				)
		parser.add_option(
				'--id-validate',
				dest='action',
				action='append_const',
				const=self.__id_validate,
				help='Perform id check on the device.'
				)

		(options, args) = parser.parse_args()
		
		# Garbage is error(?)
		if len(args) != 0:
			raise Exception(
					'Unknown garbage on command line:' +
					' \'%s\'' * len(args) % (tuple(args))
					)

		if options.device == None:
			raise Exception('You must specify the device to use.')
			

		if options.action == None:
			raise Exception('No action specified')

		# Grad any input/output files.
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

		# Grab device id
		self.__device_id = options.device_id
		if self.__device_id != None:
			try:
				# Create a list of int instead
				self.__device_id = self.__device_id.strip().split(':')
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

		self.__device_id_addr = options.device_id_addr

		# Create a serial device
		device = serial.Serial(
				port=options.device,
				timeout=options.timeout
				)

		# Create the flasher
		self.__flasher = m16c.Flasher(
				device,
				not options.clock_validation
				)
		if not self.__flasher.clock_validated():
			self.__flasher.clock_validate()
			self.__flasher.baud_set(options.baud)
		else:
			device.setBaudrate(options.baud)

		# Last but not least grab what we are supposed to do.
		self.__action = options.action

	def __unimplemented(self):
		raise Exception('Action is not implemented.')

	def __status_read(self):
		status = self.__flasher.status_read()
		print('Status register: 0x%04x' % status)

	def __status_clear(self):
		status = self.__flasher.status_clear()

	def __version_read(self):
		print('Firmware version: %s' % self.__flasher.version_read())

	def __id_validate(self):
		if self.__device_id == None:
			raise Exception('Device id not specified.')

		self.__flasher.id_validate(self.__device_id, self.__device_id_addr)

	def __flash_read(self):
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

		# Dump to file or stdout
		if self.__output_file != None:
			file = open(self.__output_file, 'wb')
			file.write(data)
			file.close()
		else:
			sys.stdout.write(data)


	def __flash_write(self):
		if self.__input_file == None:
			raise Exception('No input file was given.')

		# Parse the file.
		file = open(self.__input_file)
		file = srec.SRecFile(file)

		# Write the segments of the file.
		for i in file.segments():
			self.__flasher.segment_write(i)

	def run(self):

		for i in self.__action:
			i()

if __name__ == "__main__":

	#try:
	flash = M16CFlash()
	flash.run()
	#except Exception, (error):
	#	sys.exit(error)
