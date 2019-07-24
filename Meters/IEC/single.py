#!/usr/bin/env python3

import serial
import argparse
import time
import functools
import operator
import os


def bcc(data):
    """Computes the BCC (block  check character) value"""
    return bytes([functools.reduce(operator.xor, data, 0)])


def remove_parity_bits(data):
    """Removes the parity bits from the (response) data"""
    return bytes(b & 0x7f for b in data)


debug = False


def debuglog(*args):
    if debug:
        print("DEBUG:", *args)


SOH = b'\x01'
STX = b'\x02'
ETX = b'\x03'
AUX = b'\x06'
LF = b'\n'

CTLBYTES = SOH + STX + ETX


def drop_ctl_bytes(data):
    """Removes the standard delimiter bytes from the (response) data"""
    return bytes(filter(lambda b: b not in CTLBYTES, data))


class Meter:
    def __init__(self, port, timeout):
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        debuglog("Opening connection")
        self.ser = serial.serial_for_url(self.port,
                                         baudrate=300,
                                         bytesize=serial.SEVENBITS,
                                         parity=serial.PARITY_EVEN,
                                         timeout=self.timeout)
        time.sleep(3)
        self.id = self.sendcmd(b'/?!\r\n', etx=LF)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        debuglog("Closing connection")
        self.ser.close()

    def sendcmd(self, cmd, data=None, etx=ETX):
        if data:
            cmdwithdata = cmd + STX + data + ETX
            cmdwithdata = SOH + cmdwithdata + bcc(cmdwithdata)
        else:
            cmdwithdata = cmd
        while True:
            debuglog("Sending {}".format(cmdwithdata))
            self.ser.write(cmdwithdata)
            r = self.ser.read_until(etx)
            debuglog("Received {} bytes: {}".format(len(r), r))
            if len(etx) > 0 and r[-1:] == etx:
                if etx == ETX:
                    bcbyte = self.ser.read(1)
                    debuglog("Read BCC: {}".format(bcbyte))
                return r
            debuglog("Retrying...")
            time.sleep(2)

    def sendcmd_and_decode_response(self, cmd, data=None):
        response = self.sendcmd(cmd, data)
        debuglog('-' * 40)
        debuglog('Cmd:', cmd)
        if data:
            debuglog('Data:', data)
        debuglog('Response:', response)
        decoded_response = drop_ctl_bytes(remove_parity_bits(response)).decode()
        debuglog('Decoded response:', decoded_response)
        debuglog('-' * 40)
        return decoded_response


myname = os.path.basename(__file__)

description = """
Sends a single command to the EMH LZQJ-XC meter and prints the decoded response
"""

examples = """
Examples:

    # Read the date from the meter
    python3 {0} socket://10.124.2.120:8000 R5 "0.9.2()"

    # Read the clock from the meter
    python3 {0} socket://10.124.2.120:8000 R5 "0.9.1()"

    # Read the clock from the meter and see how it works
    python3 {0} --debug socket://10.124.2.120:8000 R5 "0.9.1()"

    # Read the load profile since 2019-04-30 00:00
    python3 {0} socket://10.124.2.120:8000 R5 "P.01(11904300000;)"

""".format(myname)

parser = argparse.ArgumentParser(
    description=description,
    epilog=examples,
    formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument('--debug', action='store_true',
                    help='Enable debugging output')
parser.add_argument('--timeout', default=None, type=float,
                    help='Data readout timeout value in seconds (default: disabled)')
parser.add_argument('device', help='Meter address in socket://host:port format')
parser.add_argument('command', help='Command to send to the meter')
parser.add_argument('data', help='Command data to send to the meter')
args = parser.parse_args()

debug = args.debug
cmd = args.command.encode()
data = args.data.encode()

with Meter(args.device, args.timeout) as meter:
    # meter.sendcmd_and_decode_response(AUX + b'041\r\n')
    meter.sendcmd_and_decode_response(AUX + b'051\r\n')
    meter.ser.baudrate = 4800
    print(meter.sendcmd_and_decode_response(cmd, data))

