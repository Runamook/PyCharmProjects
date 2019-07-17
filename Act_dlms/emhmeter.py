import serial
import time
import functools
import operator
import datetime
import re
import requests
try:
    from Act_dlms.Helpers.obis_codes import zabbix_obis_codes, transform_set
except ImportError:
    from Helpers.obis_codes import zabbix_obis_codes, transform_set
try:
    from Act_dlms.Helpers.list_of_meters import list_of_meters as list_of_meters
except ImportError:
    from Helpers.list_of_meters import list_of_meters as list_of_meters
from pyzabbix import ZabbixMetric, ZabbixSender
import logging
import sys
from redis import Redis
from rq import Queue
from serial.serialutil import SerialException

# Version with redis queue
# TODO: Incorrect date in header ['P.0', 'ERROR'], lines: ['P.01(ERROR)', '']
# TODO line 540 unknown OBIS codes are skipped
# TODO: Separate queues: frequent queries, slow queries


def create_logger(log_filename, instance_name, loglevel="INFO"):
    if loglevel == "ERROR":
        log_level = logging.ERROR
    elif loglevel == "WARNING":
        log_level = logging.WARNING
    elif loglevel == "INFO":
        log_level = logging.INFO
    elif loglevel == "DEBUG":
        log_level = logging.DEBUG
    else:
        raise ValueError

    logger = logging.getLogger(instance_name)
    logger.setLevel(log_level)
    fmt = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

    fh = logging.FileHandler(filename=log_filename)
    fh.setFormatter(fmt)
    fh.setLevel(log_level)
    fh.setFormatter(fmt)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(log_level)

    logger.addHandler(fh)
    logger.addHandler(sh)

    return logger


logger = create_logger("emh_to_zabbix.log", "Meter", loglevel="DEBUG")


class Meter:

    def __init__(self, data_handler, exporter):
        self.data_handler = data_handler        # Get table/p.xx something else, parse them
        self.exporter = exporter                # Export to Zabbix or somewhere else

        self.data = None
        self.parsed_data = None
        self.export_result = None

    def get_data(self):

        self.data = self.data_handler.get()
        return

    def parse_data(self):

        self.parsed_data = self.data_handler.parse(self.data)
        return

    def data_export(self):

        self.export_result = self.exporter.export(self.parsed_data)
        return


class MeterBase:

    SOH = b'\x01'
    STX = b'\x02'
    ETX = b'\x03'
    ACK = b'\x06'
    EOT = b'\x04'
    LF = b'\n'
    CRLF = b'\r\n'

    CTLBYTES = SOH + STX + ETX
    LineEnd = [ETX, LF, EOT]

    def __init__(self, input_vars):
        self.port = input_vars["port"]
        self.meter_number = input_vars["meter"]["meterNumber"]
        self.timeout = input_vars.get("timeout") or 300
        if input_vars.get("get_id") is None:
            self.get_id = True
        elif input_vars.get("get_id") is not None:
            self.get_id = input_vars["get_id"]

        self.data = None

    def __enter__(self):
        logger.debug(f"{self.meter_number} Opening connection to {self.port}")
        try:
            self.ser = serial.serial_for_url(self.port,
                                             baudrate=300,
                                             bytesize=serial.SEVENBITS,
                                             parity=serial.PARITY_EVEN,
                                             timeout=self.timeout)
        except SerialException:
            logger.error(f"{self.meter_number} Timeout when connecting to {self.port}")
            raise SerialException
        time.sleep(1)
        if self.get_id:
            self.id = MeterBase.remove_parity_bits(
                MeterBase.drop_ctl_bytes(
                    self.sendcmd(b"/?!\r\n", etx=MeterBase.LF))).decode("ascii")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug(f"{self.meter_number} Closing connection")
        self.ser.close()

    def sendcmd(self, cmd, data=None, etx=ETX):
        # Remember IEC 62056-21 timers:
        #       tr <= 1500 ms       The time between the reception of a message and the transmission of an answer
        #       ta <= 1500 ms       The time between two characters in a character sequence
        timer = 1.5      # Timer 10 seconds is too big - meter doesn't respond
        result = b""
        waited = 0
        wait_limit = 4

        if etx not in MeterBase.LineEnd:
            logger.error(f"{self.meter_number} Proposed text end {etx} if not in {MeterBase.LineEnd}")
            raise ValueError

        if data:
            cmdwithdata = cmd + MeterBase.STX + data + MeterBase.ETX
            cmdwithdata = MeterBase.SOH + cmdwithdata + MeterBase.bcc(cmdwithdata)
        else:
            cmdwithdata = cmd

        logger.debug(f"{self.meter_number} Sending {cmdwithdata}, expecting {etx}")
        self.ser.write(cmdwithdata)
        time.sleep(timer)

        while True:
            # Read may be infinite
            # logger.debug(f"Bytes waiting in input: {self.ser.in_waiting}")

            if self.ser.in_waiting > 0:
                # If there is data to read - read it
                response = self.ser.read(self.ser.in_waiting)
                # logger.debug(f"Result {response}")
                result += response
                waited = 0
                continue
            elif self.ser.in_waiting == 0:
                # If no data to read:
                # logger.debug(f"{result}")
                if len(result) > 0 and (result[-2:-1] == etx or result[-1:] == etx):
                    # Check if the second-last read byte is End-of-Text (or similar)
                    logger.debug(f"{self.meter_number} ETX {etx} found, assuming end of transmission")
                    if etx == MeterBase.ETX:
                        bccbyte = result[-1:]
                        logger.debug(f"{self.meter_number} BCC: {bccbyte}")
                        result = result[:-1]            # Remove BCC from result
                    return result

                # If the last is read byte not ETX - wait for more data
                if waited < wait_limit:

                    logger.debug(f"{self.meter_number} No data, waiting for {timer} sec, {timer*wait_limit - timer*waited} sec left")
                    time.sleep(timer)
                    waited += 1
                    continue
                elif waited >= wait_limit:
                    logger.debug(f"{self.meter_number} No more data in last {timer} seconds")
                    logger.debug(f"{self.meter_number} Received {len(result)} bytes: {result}")
                    return result

    def sendcmd_and_decode_response(self, cmd, data=None):
        # response = self.sendcmd(cmd, data)
        response = self.sendcmd(cmd, data)
        self.data = MeterBase.drop_ctl_bytes(MeterBase.remove_parity_bits(response)).decode("ascii")
        return self.data

    @staticmethod
    def drop_ctl_bytes(data):
        """Removes the standard delimiter bytes from the (response) data"""
        return bytes(filter(lambda b: b not in MeterBase.CTLBYTES, data))

    @staticmethod
    def remove_parity_bits(data):
        """Removes the parity bits from the (response) data"""
        return bytes(b & 0x7f for b in data)

    @staticmethod
    def bcc(data):
        """Computes the BCC (block  check character) value"""
        return bytes([functools.reduce(operator.xor, data, 0)])

    @staticmethod
    def get_dt():
        # P.01 will always return the last complete 15-minutes segment
        # "21905171700"
        now = datetime.datetime.utcnow()
        delta = datetime.timedelta(minutes=15)

        hour = now.hour
        day = now.day
        month = now.month
        year = str(now.year)[2:]

        if 0 <= now.minute < 15:
            minute = "45"
            hour = (now - delta).hour
            day = (now - delta).day
            month = (now - delta).month
            year = str((now - delta).year)[2:]
        elif 15 <= now.minute < 30:
            minute = "00"
        elif 30 <= now.minute < 45:
            minute = "15"
        elif now.minute >= 45:
            minute = "30"

        if month < 10:
            month = "0" + str(month)
        if day < 10:
            day = "0" + str(day)
        if hour < 10:
            hour = "0" + str(hour)

        return f"2{year}{month}{day}{hour}{minute}"     # 0 - normal time, 1 - summer time, 2 - UTC

    @staticmethod
    def get_port(ip_address):
        if len(ip_address.split(":")) == 1:
            port = f"socket://{ip_address}:8000"
        elif len(ip_address.split(":")) == 2:
            port = f"socket://{ip_address}"
        else:
            logger.error(f"Can't determine port {ip_address}")
            raise ValueError

        return port


# Handlers START


class GetP02:

    @staticmethod
    def get(input_vars):
        logger.debug("Requesting latest P.02")
        with MeterBase(input_vars) as m:
            m.sendcmd_and_decode_response(MeterBase.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.02({MeterBase.get_dt()};)".encode())

    @staticmethod
    def parse(input_vars, data):
        pass


class GetP01:

    def __init__(self, input_vars):
        self.input_vars = input_vars
        self.meter_number = input_vars["meter"]["meterNumber"]

    def get(self):
        timestamp = self.input_vars['timestamp']
        logger.debug(f"{self.meter_number} Requesting P.01 from {timestamp}")
        with MeterBase(self.input_vars) as m:
            m.sendcmd_and_decode_response(MeterBase.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.01({timestamp};)".encode())

    def parse(self, data):
        # Input
        # P.01(1190417001500)(00000000)(15)(6)(1.5)(kW)(2.5)(kW)(5.5)(kvar)(6.5)(kvar)(7.5)(kvar)(8.5)(kvar)
        # (0.014)(0.000)(0.013)(0.000)(0.000)(0.000)
        # (0.014)(0.000)(0.013)(0.000)(0.000)(0.000)

        logger.debug(f"{self.meter_number} Parsing P.01 output")
        # logger.debug(f"{self.meter_number} {data}")
        keys = [
            "bill-1.5.0", "bill-2.5.0", "bill-5.5.0", "bill-6.5.0", "bill-7.5.0", "bill-8.5.0"
        ]
        keys_raw = [
            "bill-raw-1.5.0", "bill-raw-2.5.0", "bill-raw-5.5.0", "bill-raw-6.5.0", "bill-raw-7.5.0", "bill-raw-8.5.0"
        ]

        lines = data.split('\r\n')
        pre_header = lines[0].split("(")                                    # Strip closing parenthesis
        header = [elem[:-1] for elem in pre_header]                         # Strip opening parenthesis
        try:
            base_dt = datetime.datetime.strptime(header[1][1:], "%y%m%d%H%M%S")
        except ValueError:
            logger.error(f"{self.meter_number} Incorrect date in header {header}, lines: {lines}")
            raise
        # Strip header line and all short lines
        # Reorder a list, cause newest values are the last by default
        log = header[2]
        # logger.debug(f"Log = {log}")
        lines = list(filter(lambda x: len(x) > 6, lines[1:]))[::-1]
        # logger.debug(f"Header {header}, time {base_dt}, lines {lines}")
        results = {}
        counter = 0
        for line in lines:
            if len(line) > 5:
                result = []
                values = line.split("(")[1:]            # First value is an empty string
                value_counter = 0
                for value in values:
                    result.append((keys[value_counter], value[:-1]))
                    result.append((keys_raw[value_counter], value[:-1]))
                    value_counter += 1
            result.append(("bill-Log", log))
            results[(base_dt + datetime.timedelta(minutes=counter*15)).strftime("%s")] = result
            logger.debug(f"{self.meter_number} Intermediate result {results}")
            counter += 1

        # Results = { epoch : [(obis_code, value), (), ...], epoch + 15m, [(), (), ...]}
        # logger.debug(f"Results: {results}")
        final_result = {"p01": results}
        logger.debug(f"{self.meter_number} Finished parsing P.01 output, result {final_result}")
        return final_result


class GetTable:

    def __init__(self, input_vars):
        self.input_vars = input_vars
        self.meter_number = input_vars["meter"]["meterNumber"]

    def get(self):
        table_no = str(self.input_vars.get("table_no")) or "4"
        meter_number = self.input_vars.get("meterNumber")
        if self.input_vars.get("get_id") is not False:
            self.input_vars["get_id"] = False

        if str(table_no) not in ["1", "2", "3", "4"]:
            logger.error(f"No such table {table_no}, choose table 1, 2, 3 or 4")
            raise ValueError
        query = b"/" + table_no.encode() + meter_number.encode() + b"!\r\n"
        logger.debug(f"{meter_number} :: Requesting table {table_no}, {query}")
        with MeterBase(self.input_vars) as m:
            return m.sendcmd_and_decode_response(query)

    def parse(self, data):

        if str(self.input_vars.get("table_no")) == "4":
            return self.parse_table4(data)
        elif str(self.input_vars.get("table_no")) == "1":
            return self.parse_table1(data)

    def parse_table4(self, data):
        # /EMH4\@01LZQJL0014F
        # 0.0.0(05296170)
        # 43.25(0.006*kvar)
        # 0.9.1(1185411)            # 18:54:11 localtime
        # 13.25(0.83*P/S)
        # C.7.2(0003)
        logger.debug("Parsing table4 output")
        # logger.debug(data)

        re_key = re.compile('^(.+)[(]')
        re_dt = re.compile('([(].+[)])')
        re_value = re.compile('[(](-?[0-9]+\\.[0-9]+)')
        pre_results = []
        results = {}

        lines = data.split('\r\n')[1:]  # Remove header (meter id)
        logger.debug(f"{self.meter_number}, {data}")
        for line in lines:
            # Attention: XC meter not found/available!
            if len(line) < 5:
                continue
            if not re_key.search(line):
                logger.debug(f"no key in line {line}")
                continue
            else:
                key = re_key.search(line).group()[:-1]

            if key == "0.9.1":
                cur_time = re_dt.search(line).group()[2:-1]  # Strip first digit
            elif key == "0.9.2":
                cur_date = re_dt.search(line).group()[2:-1]  # Strip first digit
            else:
                if not re_value.search(line):
                    logger.debug(f"Not found value X.X in line {line}")
                    continue
                else:
                    # value = re_value.search(line).group()[1:-1]
                    value = re_value.search(line).group()[1:]
                    pre_results.append((key, value))

        pre_results = self.enrich_data(pre_results)                 # Cos phi
        epoch = datetime.datetime.strptime(cur_date + cur_time, "%y%m%d%H%M%S").strftime("%s")
        results[epoch] = pre_results  # {epoch: [(obis_code:val), (), (), ...]}
        # logger.debug(f"Results: {results}")
        logger.debug("Finished parsing table 4 output")
        final_result = {"table4": results}
        return final_result

    def parse_table1(self, data):
        table_no = "1"
        logger.debug(f"Parsing table{table_no} output")

        pre_results = []
        results = {}

        keys = [
            '0.1.2', '1.2.1', '1.2.2', '1.6.1', '1.6.2', '1.8.0', '1.8.1', '1.8.2', '2.2.1', '2.2.2', '2.6.1',
            '2.6.2', '2.8.0', '2.8.1', '2.8.2', '5.8.0', '5.8.1', '5.8.2', '6.8.0', '6.8.1', '6.8.2', '7.8.0',
            '7.8.1', '7.8.2', '8.8.0', '8.8.1', '8.8.2'
            ]
        keys_with_interval = [
            '1.6.1', '1.6.2', '1.8.0', '1.8.1', '1.8.2', '2.6.1', '2.6.2', '2.8.0', '2.8.1',
            '2.8.2', '5.8.0', '5.8.1', '5.8.2', '6.8.0', '6.8.1', '6.8.2', '7.8.0', '7.8.1', '7.8.2', '8.8.0',
            '8.8.1', '8.8.2'
            ]

        lines = data.split('\r\n')[1:]  # Remove header /EMH4\@01LZQJL0014F
        logger.debug(f"{self.meter_number}, {data}")
        for line in lines:
            # Attention: XC meter not found/available!
            if len(line) < 5:
                continue

            parsed_line = self.parse_line(line)
            if not parsed_line:                     # Skip if None returned
                continue

            key = parsed_line.get("key")
            value = parsed_line.get("value")
            interval = parsed_line.get("interval")
            value_dt = parsed_line.get("value_dt")

            if key == "0.9.1":
                cur_time = value[1:]  # Strip first timezone digit
            elif key == "0.9.2":
                cur_date = value[1:]  # Strip first timezone digit
            elif key == "0.1.0":
                cur_interval = value  # Strip first timezone digit

            logger.debug(f"{line}, key = {key}, value = {value}, interval = {interval}, value_dt = {value_dt}")
            # If there is interval in key and the interval is not equal to current interval

            if key in keys_with_interval and interval is None:
                continue

            if interval:
                if cur_interval == interval:
                    if value_dt:
                        # key = f"{key}_{value_dt}"
                        pre_results.append((f"{key}-time", value_dt))
                    # else:
                    #     key = f"{key}_NoTimeInterval"
                    pass
                else:
                    continue          # Older intervals are not required

            if key in keys:
                pre_results.append((key, value))
                if key != '0.1.2':
                    pre_results.append((f"raw-{key}", value))

        # pre_results = self.enrich_data(pre_results)               # Cos phi
        epoch = datetime.datetime.strptime(cur_date + cur_time, "%y%m%d%H%M%S").strftime("%s")
        results[epoch] = pre_results  # {epoch: [(obis_code:val), (), (), ...]}
        # logger.debug(f"Results: {results}")
        logger.debug(f"Finished parsing table {table_no} output")
        final_result = {f"table{table_no}": results}
        return final_result

    def parse_line(self, line):
        # Table1
        # F.F(00000000)
        # 0.0.0(05939068)
        # 0.0.9(1EMH0005939068)
        # 0.1.0(26)
        # 0.1.2*26(1190701000000)
        # 0.1.2*25(1190601000000)
        # 0.9.2(1190714)
        # 1.2.1(011.387*kW)
        # 1.2.2(000.000*kW)
        # 1.6.1(0.482*kW)(1190711111500)
        # 1.6.1*26(0.473*kW)(1190625140000)
        # 1.6.1*25(0.476*kW)(1190514080000)
        re_key = re.compile('^(.+?)[(]')                 # ? for non-greedy match
        re_value = re.compile('^.*[(](.*)[)]')
        re_multi_value_1 = re.compile('^.*[(](.*)[)][(]')
        re_multi_value_2 = re.compile('^.*[)][(](.*)[)]')

        key, value, interval, value_dt = None, None, None, None
        if not re_key.search(line):
            logger.debug(f"no key in line {line}")
            return None
        else:
            key = re_key.search(line).groups()[0]        # Key - everything before opened parenthesis

        if not re_value.search(line) and not re_multi_value_1.search(line):
            logger.debug(f"No value found in {line}")
            return None

        if ")(" in line:                                 # Multi value
            value = re_multi_value_1.search(line).groups()[0]
            value_dt = re_multi_value_2.search(line).groups()[0][1:]
        else:                                            # Single value
            value = re_value.search(line).groups()[0]

        if "*" in key:
            old_key = key.split("*")
            key = old_key[0]
            interval = old_key[1]

        if "*" in value:
            value = value.split("*")[0]                   # Strip kW, kvar etc.

        return {"key": key, "value": value, "value_dt": value_dt, "interval": interval}

    def enrich_data(self, tuple_list):
        """
        [(k,v),(k,v),(k,v)]
        adds cos_phi and tan_phi metrics to the list
        Calculations are based on active and reactive power.

        """
        active_power = None
        reactive_power = None

        for tup in tuple_list:
            if tup[0] == "1.25":
                active_power = float(tup[1])
            if tup[0] == "3.25":
                reactive_power = float(tup[1])
        if active_power and reactive_power:
            tan_phi = reactive_power / active_power
            cos_phi = 1/((1 + tan_phi ** 2) ** 0.5)

            tuple_list.append(("tan_phi", str(tan_phi)))
            tuple_list.append(("cos_phi", str(cos_phi)))
            logger.debug(f"Meter {self.meter_number} Active power = {active_power}, Reactive power = {reactive_power}, Cos phi = {cos_phi}")
        else:
            logger.debug(f"Meter {self.meter_number} cos phi not found - not enough data")

        return tuple_list


class GetErrors:

    @staticmethod
    def get(input_vars):
        # Should be F.F(00000000)
        logger.debug("Requesting errors F.F()")
        with MeterBase(input_vars) as m:
            m.sendcmd_and_decode_response(MeterBase.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"F.F()".encode())

    @staticmethod
    def parse(selfinput_vars, data):

        pass


class GetP98:

    @staticmethod
    def get(input_vars):
        logger.debug("Requesting latest P.98")
        with MeterBase(input_vars) as m:
            m.sendcmd_and_decode_response(MeterBase.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.98()".encode())

    @staticmethod
    def parse(selfinput_vars, data):
        pass

    '''

    def get_p99logbook(self):
        logger.debug("Requesting latest P.99")
        with MeterBase(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(MeterBase.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.99()".encode())

    def get_p200logbook(self):
        # Query every X minutes. P.200(ERROR) - means no events
        logger.debug("Requesting latest P.200")
        with MeterBase(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(MeterBase.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.200()".encode())

    def get_p210logbook(self):
        logger.debug("Requesting latest P.210")
        with MeterBase(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(MeterBase.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.210()".encode())

    def get_p211logbook(self):
        logger.debug("Requesting latest P.210")
        with MeterBase(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(MeterBase.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.211()".encode())

    '''
# Handlers END

# Exporters START


class ExportToZabbix:

    def __init__(self, input_vars):
        """
        input_vars["meter_data"] = {
        "meterNumber": "05939068",
        "Manufacturer": "EMH",
        "ip": "10.124.1.12",
        "InstallationDate": "2017-06-27T08:00:00",
        "IsActive": True,
        "voltageRatio": 200,
        "currentRatio": 10,
        "totalFactor": 210
          }
        """

        self.server = input_vars.get("server") or "127.0.0.1"
        self.meter_data = input_vars["meter"]
        self.meter_number = input_vars["meter"]["meterNumber"]
        logger.info(f"Zabbix server {self.server}, input {input_vars}")

    def export(self, data):
        metrics = self.create_metrics(data)
        self.send_metrics(metrics, self.meter_number)
        return

    @staticmethod
    def transform_metrics(meter_data, metric_key, metric_value):

        if metric_key not in transform_set:
            logger.error(f"Metric {metric_key} not in transform set {transform_set}")
            raise AttributeError

        voltageRatio = float(meter_data["voltageRatio"])
        currentRatio = float(meter_data["currentRatio"])
        # totalFactor = float(meter_data["totalFactor"])
        totalFactor = currentRatio * voltageRatio

        if transform_set[metric_key] == "None":
            # logger.debug(f"Not transforming {metric_value}")
            return metric_value
        elif transform_set[metric_key] == "voltageRatio":
            # logger.debug(f"Transforming {metric_value} as voltage")
            return float(metric_value) * voltageRatio
        elif transform_set[metric_key] == "currentRatio":
            # logger.debug(f"Transforming {metric_value} as current")
            return float(metric_value) * currentRatio
        elif transform_set[metric_key] == "totalFactor":
            # logger.debug(f"Transforming {metric_value} as total")
            return float(metric_value) * totalFactor
        else:
            logger.error(f"No valid transform factor for {metric_key} in {transform_set}")
            return None

    def create_metrics(self, data):
        """
        data = {
        'table4': {'1557693253': [('21.25', '0.004'), (), (), ...)]},
        'p01': {'1558989000': [('1.5.0', '0.017'), (), (), ...)]}
                }

        ZabbixMetric('Zabbix server', 'WirkleistungP3[04690915]', 3, clock=1554851400))
        """
        logger.debug(f"{self.meter_number} creating metrics for Zabbix")
        logger.debug(f"{data}, {self.meter_data}")
        zabbix_metrics = []
        metric_host = f"Meter {self.meter_data['meterNumber']}"

        for data_set_name in data:  # Parse each table/logbook
            for metric_time in data[data_set_name]:  # Parse each timestamp dataset
                for metric_tuple in data[data_set_name][metric_time]:  # Parse each key-value pair
                    # logger.debug(f"Host: {metric_host}, Tuple: {metric_tuple}, Time: {metric_time}")
                    # metric_key = zabbix_obis_codes[metric_tuple[0]]
                    metric_key = zabbix_obis_codes.get(metric_tuple[0])
                    if not metric_key:
                        continue
                    metric_value = ExportToZabbix.transform_metrics(self.meter_data, metric_key, metric_tuple[1])  # Apply transform
                    logger.debug(f"{metric_host}, {metric_key}, {metric_value}, {metric_time}")
                    zabbix_metrics.append(ZabbixMetric(metric_host, metric_key, metric_value, clock=int(metric_time)))

        return zabbix_metrics

    def send_metrics(self, metrics, meter_number):
        sender = ZabbixSender(self.server)
        logger.debug(f"{meter_number} :: {metrics}")
        zabbix_response = sender.send(metrics)

        if zabbix_response.failed > 0 and zabbix_response.processed == 0:
            logger.error(f"{meter_number} :: Something went wrong, {zabbix_response}")
        elif zabbix_response.failed > 0 and zabbix_response.failed > zabbix_response.processed:
            logger.warning(f"{meter_number} :: More failures that successes {zabbix_response}")
        else:
            logger.info(f"{meter_number} :: Result {zabbix_response}")
        return


# Exporters END


# New Mod

def get_json():
    url = "http://10.11.30.97:5000/api/meterpinginfo"
    logger.debug(f"Connecting to {url}")
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"API responded {response.status_code}, expected 200")
        raise ValueError(f"No data returned from API result: {response.status_code}")
    return response.json()


def meta(input_vars):
    logger.debug(f"Input vars {input_vars['meter']['meterNumber']} - {input_vars}")
    if input_vars["data_handler"] == "P.01":
        data_handler = GetP01(input_vars)
    elif input_vars["data_handler"] == "Table":
        data_handler = GetTable(input_vars)

    if input_vars["exporter"] == "Zabbix":
        exporter = ExportToZabbix(input_vars)

    m = Meter(data_handler=data_handler, exporter=exporter)

    m.get_data()
    if len(m.data) <= 0:
        logger.error(f"No data returned for {input_vars['data_handler']} at {input_vars['port']}")
        raise ValueError(f"No data returned for {input_vars['data_handler']} at {input_vars['port']}")
    if m.data is None:
        raise ValueError(f"No data returned")
    m.parse_data()
    if m.parsed_data is None:
        raise ValueError(f"No data returned")
    m.data_export()
    return


def create_input_vars(meter):

    # P.01
    input_vars_p01 = {"port": MeterBase.get_port(meter["ip"]),
                      "timestamp": MeterBase.get_dt(),
                      "data_handler": "P.01",
                      "exporter": "Zabbix",
                      "server": "192.168.33.33",
                      "meter": meter
                      }

    # Table 4
    input_vars_table4 = {"port": MeterBase.get_port(meter["ip"]),
                         "get_id": False,
                         "table_no": "4",
                         "meterNumber": meter["meterNumber"],
                         "data_handler": "Table",
                         "exporter": "Zabbix",
                         "server": "192.168.33.33",
                         "meter": meter
                         }

    # Table 1
    input_vars_table1 = {"port": MeterBase.get_port(meter["ip"]),
                         "get_id": False,
                         "table_no": "1",
                         "meterNumber": meter["meterNumber"],
                         "data_handler": "Table",
                         "exporter": "Zabbix",
                         "server": "192.168.33.33",
                         "meter": meter
                         }

    return {"P01": input_vars_p01, "Table4": input_vars_table4, "Table1": input_vars_table1}
# RQ mod


def get_job_meta(queue):

    running_jobs = {}
    for job_id in queue.job_ids:                          # job_id - '52ad7ebf-f8f1-4ac2-9cc8-c1a165b6675b'
        if queue.fetch_job(job_id) is None:
            logger.debug(f"Jobs :: Skipping None type job {job_id}")
            continue
        meta = queue.fetch_job(job_id).meta
        meta['job_id'] = job_id                           # Add job_id key to meta dictionary
        logger.debug(f"Jobs :: found meta: {meta}")
        running_jobs[meta["meterNumber"]] = meta          # running_jobs = {meterNumber : {meta}, meterNumber: {} ...}

    failed_jobs = {}
    for job_id in queue.failed_job_registry.get_job_ids():
        if queue.fetch_job(job_id) is None:
            logger.debug(f"Jobs :: Skipping None type job {job_id}")
            continue
        meta = queue.fetch_job(job_id).meta
        meta["job_id"] = job_id
        logger.debug(f"Jobs :: found meta: {meta}")
        failed_jobs[meta["meterNumber"]] = meta

    return running_jobs, failed_jobs


"""
def rq_create_jobs():
    
    # Receives list of meter dictionaries
    # Places jobs to queues for python RQ
    
    p01_q = Queue(name="p01", connection=Redis())
    table4_q = Queue(name="table4", connection=Redis())
    logger.info("Connected to redis")

    # list_of_meters = get_json()

    logger.info(f"{len(list_of_meters)} meters to be processed")
    p01_running_jobs, p01_failed_jobs = get_job_meta(p01_q)
    for meter in list_of_meters:
        # ttl - job ttl, won't be executed on expiry
        # default_timeout - job shall be executed in default_timeout or marked as failed
        # result_ttl - store successful result
        # failure_ttl - store failed job

        # Before putting a job into a queue check if there is a failed
        # or pending job for that meter already in queue
        # Find a job by meterId - only one job for a meter id can exist in a queue at a time
        timestamp = MeterBase.get_dt()                                              # This is used for P01 query
        input_vars_dict = create_input_vars(meter)
        current_timestamp = datetime.datetime.strptime(timestamp[1:], '%y%m%d%H%M')     # This is used for comparing
        meter_number = meter["meterNumber"]

        new_job = {"meterNumber": meter_number, "timestamp": timestamp}
        if new_job["meterNumber"] in p01_failed_jobs.keys():
            # If job is found in "failed" queue
            existing_job = p01_failed_jobs[meter_number]
            job_start_time = existing_job["timestamp"]
            existing_timestamp = datetime.datetime.strptime(job_start_time[1:], '%y%m%d%H%M')
            # If the job was started less than 24 hours ago - requeue
            delta = (current_timestamp - existing_timestamp).total_seconds()
            if delta < 86400:                                                             # Compare timestamps
                logger.debug(f"Meter {meter_number} :: Requeueing failed P.01 job {existing_job['meterNumber']}, start time: {job_start_time[1:]} UTC")
                p01_q.failed_job_registry.requeue(existing_job["job_id"])
            elif delta > 86400:
                logger.debug(f"Meter {meter_number} :: Removing failed P.01 job {existing_job['meterNumber']} after 24h, start time: {job_start_time[1:]} UTC")
                p01_q.failed_job_registry.remove(p01_q.fetch_job(existing_job["job_id"]))
        elif new_job["meterNumber"] in p01_running_jobs.keys():
            # If job is found in "running/waiting" queue
            existing_job = p01_running_jobs[meter_number]
            job_start_time = existing_job["timestamp"]

            logger.debug(f"Meter {meter_number} :: Pending P.01 job {existing_job['meterNumber']}, start time: {job_start_time[1:]} UTC")
            pass
        else:
            # New job, not found anywhere
            logger.debug(f"Meter {meter_number} :: New P.01 job {new_job['meterNumber']}")
            # p01_q.enqueue(rq_push_p01, meter, timestamp, meta=new_job, result_ttl=10, ttl=900, failure_ttl=600)
            p01_q.enqueue(meta, input_vars_dict["P01"], meta=new_job, result_ttl=10, ttl=900, failure_ttl=600)
        logger.debug(f"Meter {meter_number} :: enqueueing rq_push_table4 for {meter['ip']}")
        # table4_q.enqueue(rq_push_table4, meter, result_ttl=10, ttl=300, failure_ttl=600)
        table4_q.enqueue(meta, input_vars_dict["Table4"], result_ttl=10, ttl=300, failure_ttl=600)
"""


def rq_create_table1_jobs(meter_list, test):
    table_no = "1"
    if test:
        q = Queue(name=f"test-table{table_no}", connection=Redis())
    else:
        q = Queue(name=f"table{table_no}", connection=Redis())
    logger.info("Connected to redis")

    logger.info(f"{len(meter_list)} meters to be processed")
    for meter in meter_list:
        input_vars_dict = create_input_vars(meter)
        meter_number = meter["meterNumber"]

        logger.debug(f"Meter {meter_number} :: enqueueing rq_push_table{table_no} for {meter['ip']}")
        q.enqueue(meta, input_vars_dict[f"Table{table_no}"], result_ttl=10, ttl=300, failure_ttl=600)


def rq_create_table4_jobs(meter_list, test):
    """
    Receives list of meter dictionaries
    Places jobs to queues for python RQ
    test = boolean, changes queue name to test-tale4
    """
    table_no = "4"
    if test:
        q = Queue(name=f"test-table{table_no}", connection=Redis())
    else:
        q = Queue(name=f"table{table_no}", connection=Redis())
    logger.info("Connected to redis")

    logger.info(f"{len(meter_list)} meters to be processed")
    for meter in meter_list:
        input_vars_dict = create_input_vars(meter)
        meter_number = meter["meterNumber"]

        logger.debug(f"Meter {meter_number} :: enqueueing rq_push_table{table_no} for {meter['ip']}")
        q.enqueue(meta, input_vars_dict[f"Table{table_no}"], result_ttl=10, ttl=300, failure_ttl=600)


def rq_create_p01_jobs(meter_list, test):
    """
    Receives list of meter dictionaries
    Places jobs to queues for python RQ
    test = boolean, changes queue name to test-p01
    """
    if test:
        p01_q = Queue(name="test-p01", connection=Redis())
    else:
        p01_q = Queue(name="p01", connection=Redis())
    logger.info("Connected to redis")

    # list_of_meters = get_json()

    logger.info(f"{len(meter_list)} meters to be processed")
    p01_running_jobs, p01_failed_jobs = get_job_meta(p01_q)
    for meter in meter_list:
        # ttl - job ttl, won't be executed on expiry
        # default_timeout - job shall be executed in default_timeout or marked as failed
        # result_ttl - store successful result
        # failure_ttl - store failed job

        # Before putting a job into a queue check if there is a failed
        # or pending job for that meter already in queue
        # Find a job by meterId - only one job for a meter id can exist in a queue at a time
        timestamp = MeterBase.get_dt()                                              # This is used for P01 query
        input_vars_dict = create_input_vars(meter)
        current_timestamp = datetime.datetime.strptime(timestamp[1:], '%y%m%d%H%M')     # This is used for comparing
        meter_number = meter["meterNumber"]

        new_job = {"meterNumber": meter_number, "timestamp": timestamp}
        if new_job["meterNumber"] in p01_failed_jobs.keys():
            # If job is found in "failed" queue
            existing_job = p01_failed_jobs[meter_number]
            job_start_time = existing_job["timestamp"]
            existing_timestamp = datetime.datetime.strptime(job_start_time[1:], '%y%m%d%H%M')
            # If the job was started less than 24 hours ago - requeue
            delta = (current_timestamp - existing_timestamp).total_seconds()
            if delta < 86400:                                                             # Compare timestamps
                logger.debug(f"Meter {meter_number} :: Requeueing failed P.01 job {existing_job['meterNumber']}, start time: {job_start_time[1:]} UTC")
                p01_q.failed_job_registry.requeue(existing_job["job_id"])
            elif delta > 86400:
                logger.debug(f"Meter {meter_number} :: Removing failed P.01 job {existing_job['meterNumber']} after 24h, start time: {job_start_time[1:]} UTC")
                p01_q.failed_job_registry.remove(p01_q.fetch_job(existing_job["job_id"]))
        elif new_job["meterNumber"] in p01_running_jobs.keys():
            # If job is found in "running/waiting" queue
            existing_job = p01_running_jobs[meter_number]
            job_start_time = existing_job["timestamp"]

            logger.debug(f"Meter {meter_number} :: Pending P.01 job {existing_job['meterNumber']}, start time: {job_start_time[1:]} UTC")
            pass
        else:
            # New job, not found anywhere
            logger.debug(f"Meter {meter_number} :: New P.01 job {new_job['meterNumber']}")
            # p01_q.enqueue(rq_push_p01, meter, timestamp, meta=new_job, result_ttl=10, ttl=900, failure_ttl=600)
            p01_q.enqueue(meta, input_vars_dict["P01"], meta=new_job, result_ttl=10, ttl=900, failure_ttl=600)

# RQ mod


if __name__ == "__main__":
    # To run create script.py with:
    # from emhmeter_rq import rq_create_jobs, logger
    #
    # logger.setLevel("INFO")
    # rq_create_jobs()

    # (venv) [root@vsrvenomos00123 app]# rq worker p01 table4
    logger.setLevel("DEBUG")
    rq_create_jobs()
