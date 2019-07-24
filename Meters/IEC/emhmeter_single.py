#!/usr/bin/env python3

import serial
import argparse
import time
import functools
import operator
import os
import datetime
from time import sleep
import re
from serial.serialutil import SerialException

try:
    from .emhmeter import MeterBase, create_input_vars, logger
except ModuleNotFoundError:
    from emhmeter import MeterBase, create_input_vars, logger


"""
Set clock time to 10:23:50:

sent:         /?!<CR><LF>
received:     /EMH5\@01LZQJL0014E <CR><LF>
sent:         <ACK>051<CR><LF>
received:     <SOH>P0<STX>()<ETX><BCC>
sent:         <SOH>W5<STX>0.9.1(0102350)(00000000)<ETX><BCC>
received:     <ACK>
sent:         <SOH>B0<ETX><BCC>
/// Это вроде работает

Set date to 17.06.03:

sent:          /?!<CR><LF>
received:      /EMH5\@01LZQJC0014E <CR><LF>
sent:          <ACK>051<CR><LF>
received:      <SOH>P0<STX>()<ETX><BCC>
sent:          <SOH>W5<STX>0.9.2(1030617)(00000000)<ETX><BCC>
received:      <ACK>
sent:          <SOH>B0<ETX><BCC>

"""


def set(cmd, data, input_vars):
    with MeterBase(input_vars) as m:
        m.sendcmd_and_decode_response(MeterBase.ACK + b'051\r\n')
        result = m.sendcmd_and_decode_response(cmd.encode(), data.encode())
        cmd = MeterBase.SOH + b'B0' + MeterBase.ETX
        m.sendcmd_and_decode_response(cmd + MeterBase.bcc(cmd))
        return result


def make_pause():
    pause = 25
    logger.debug(f"Pausing for {pause} seconds")
    i = 0
    while i < pause:
        print(".", end=" ")
        i += 1
        sleep(1)
    print()
    return


def set_dt(input_vars):
    make_pause()
    # dt = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    dt = datetime.datetime.utcnow()
    date = dt.strftime("2" + "%y%m%d")
    time = dt.strftime("2" + "%H%M%S")
    logger.info(f"Setting dt to {date}, {time}")
    # Set time
    logger.debug(f"===================== Setting time ===================== ")
    set("W5", f"0.9.1({time})(00000000)", input_vars)
    make_pause()
    # Set date
    logger.debug(f"===================== Setting date ===================== ")
    set("W5", f"0.9.2({date})(00000000)", input_vars)


def get_dt(input_vars):
    # Get time
    results = dict()
    new_time, new_date = None, None
    logger.debug(f"===================== Getting time ===================== ")
    new_time = set("R5", f"0.9.1()", input_vars=input_vars)
    logger.debug(f"Time {new_time}")
    results["time"] = (datetime.datetime.now(), new_time)
    make_pause()
    # Get date
    logger.debug(f"===================== Getting date ===================== ")
    new_date = set("R5", f"0.9.2()", input_vars=input_vars)
    logger.debug(f"Date: {new_date}, Time: {new_time}")
    results["date"] = (datetime.datetime.now(), new_date)
    return results


def check_dt(dt):
    # 0.9.2(1190724), 0.9.1(1221856)
    re_in_parenthesis = re.compile('^0.9..[(](.+?)[)]')
    logger.debug(f"Checking meter date {dt}")

    local_time = 2                              # UTC +2

    reference_date = dt["date"][0]
    in_date = dt["date"][1]

    reference_time = dt["time"][0]
    in_time = dt["time"][1]

    date = re_in_parenthesis.search(in_date).groups()[0]
    time = re_in_parenthesis.search(in_time).groups()[0]

    if reference_date.strftime("%y%m%d") == date:
        logger.debug(f"Date is correct")
    else:
        logger.debug(f"Date is incorrect")

    dt_to_check = datetime.datetime.strptime(f"{date[1:]}{time[1:]}", "%y%m%d%H%M%S")
    if time[0] == "1":
        # Time in localtime should be increased
        dt_to_check = dt_to_check + datetime.timedelta(seconds=3600)

    delta = abs(int((reference_time - dt_to_check).total_seconds()))

    logger.debug(f"Delta = {delta} seconds")
    if delta > 6:
        return True
    else:
        return False


def meta(input_vars):
    dt = get_dt(input_vars)
    if check_dt(dt):
        set_dt(input_vars)
    else:
        logger.info(f"Meter {input_vars['meter']['meterNumber']} time is correct")


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

"""
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
"""

meter = {
        "meterNumber": "05939038",
        "Manufacturer": "EMH",
        "ip": "10.124.2.117",
        "InstallationDate": "2018-10-10T10:00:00",
        "IsActive": True,
        "voltageRatio": 1,
        "currentRatio": 200,
        "totalFactor": 201
    }

vars = {"port": MeterBase.get_port(meter["ip"]),
                      "timestamp": MeterBase.get_dt(),
                      "data_handler": "P.01",
                      "exporter": "Zabbix",
                      "server": "192.168.33.33",
                      "meter": meter
                      }

logger.setLevel("DEBUG")
logger.debug(f"Starting")

print(f"{vars}")
meta(vars)


# New date = , new time = 0.9.1(1033552)
# UTC time worked
# New date = , new time = 0.9.1(1003935)
# Time change worked
