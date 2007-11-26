#!/usr/bin/env python

import serial, m16c, sys
from optparse import OptionParser

def read_status(device):
	print('Status register: 0x%4x' % device.readStatus())

def read_version(device):
	print('Firmware version: %s' % device.readVersion())

if __name__ == "__main__":

	parser = OptionParser()
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
			'-i', '--device-id',
			dest='device_id',
			type='string',
			help='The device id used for mutable operations. ' +
			'Example: ae:23:3a:dd:ea:32'
			)
	parser.add_option(
			'-n', '--no-validation',
			dest='clock_validation',
			action='store_false',
			help='Disable clock validation when connecting.',
			default=True
			)
	parser.add_option(
			'--read-status',
			dest='action',
			action='store_const',
			const=read_status,
			help='Read the status register of the device.'
			)
	parser.add_option(
			'--read-version',
			dest='action',
			action='store_const',
			const=read_version,
			help='Read the firmware version of the device.'
			)
	(options, args) = parser.parse_args()

	try:
		if options.device == None:
			print('You must specify the device to use.')
			parser.print_help()
			sys.exit()

		if options.action == None:
			print('No action specified.')
			parser.print_help()
			sys.exit()

		#if options.device_id == None:
		#	print('You must specify the device id to use.')
		#	parser.print_help()
		#	sys.exit()

		device_id = options.device_id
		if device_id != None:
			try:
				device_id = device_id.strip().split(':')
				fields = len(device_id)
				if fields != 6:
					print('Invalid number of fields in device id.')
					parser.print_help()
					sys.exit()

				device_id = filter(
						lambda x: (x >= 0) and (x <= 255),
						map(lambda x: int(x, 16), device_id)
						)

				if fields != len(device_id):
					print('Device id field(s) out of range.')
					parser.print_help()
					sys.exit()

			except TypeError:
				print('Device id contains invalid field(s).')
				parser.print_help()
				sys.exit()

		device = serial.Serial(
				port=options.device,
				baudrate=options.baud,
				timeout=options.timeout
				)

		flasher = m16c.Flasher(device, device_id)
		if options.clock_validation:
			flasher.validateClock()
		options.action(flasher)

	except serial.SerialException, (error):
		print(error)

	except m16c.FlasherException, (error):
		print(error)
