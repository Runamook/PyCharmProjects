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
    from Act_dlms.Helpers.list_of_meters import list_of_meters
except ImportError:
    from Helpers.list_of_meters import list_of_meters
from pyzabbix import ZabbixMetric, ZabbixSender
import logging
import sys
from redis import Redis
from rq import Queue

# Version with redis queue
# TODO: Incorrect date in header ['P.0', 'ERROR'], lines: ['P.01(ERROR)', '']


def create_logger(log_filename, instance_name, loglevel="INFO"):
    if loglevel == "ERROR":
        log_level = logging.ERROR
    elif loglevel == "WARNING":
        log_level = logging.WARNING
    elif loglevel == "INFO":
        log_level = logging.INFO
    elif loglevel == "DEBUG":
        log_level = logging.DEBUG

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


logger = create_logger("/var/log/emh_to_zabbix.log", "Meter", loglevel="DEBUG")


class Meter:

    SOH = b'\x01'
    STX = b'\x02'
    ETX = b'\x03'
    ACK = b'\x06'
    EOT = b'\x04'
    LF = b'\n'
    CRLF = b'\r\n'

    CTLBYTES = SOH + STX + ETX
    LineEnd = [ETX, LF, EOT]

    def __init__(self, port, timeout, get_id=True):
        self.port = port
        self.timeout = timeout
        self.data = None
        self.get_id = get_id

    def __enter__(self):
        logger.debug(f"Opening connection to {self.port}")
        self.ser = serial.serial_for_url(self.port,
                                         baudrate=300,
                                         bytesize=serial.SEVENBITS,
                                         parity=serial.PARITY_EVEN,
                                         timeout=self.timeout)
        time.sleep(1)
        if self.get_id:
            self.id = Meter.remove_parity_bits(Meter.drop_ctl_bytes(self.sendcmd_3(b"/?!\r\n", etx=Meter.LF))).decode("ascii")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug("Closing connection")
        self.ser.close()

    def sendcmd_3(self, cmd, data=None, etx=ETX):
        # Remember IEC 62056-21 timers:
        #       tr <= 1500 ms       The time between the reception of a message and the transmission of an answer
        #       ta <= 1500 ms       The time between two characters in a character sequence
        timer = 1.5      # Timer 10 seconds is too big - meter doesn't respond
        result = b""
        waited = 0
        wait_limit = 4

        assert etx in Meter.LineEnd, f"Proposed text end {etx} if not in {Meter.LineEnd}"

        if data:
            cmdwithdata = cmd + Meter.STX + data + Meter.ETX
            cmdwithdata = Meter.SOH + cmdwithdata + Meter.bcc(cmdwithdata)
        else:
            cmdwithdata = cmd

        logger.debug(f"Sending {cmdwithdata}, expecting {etx}")
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
                    logger.debug(f"ETX {etx} found, assuming end of transmission")
                    if etx == Meter.ETX:
                        bccbyte = result[-1:]
                        logger.debug(f"BCC: {bccbyte}")
                        result = result[:-1]            # Remove BCC from result
                    return result

                # If the last is read byte not ETX - wait for more data
                if waited < wait_limit:

                    logger.debug(f"No data, waiting for {timer} sec, {timer*wait_limit - timer*waited} sec left")
                    time.sleep(timer)
                    waited += 1
                    continue
                elif waited >= wait_limit:
                    logger.debug(f"No more data in last {timer} seconds")
                    logger.debug(f"Received {len(result)} bytes: {result}")
                    return result

    def sendcmd_and_decode_response(self, cmd, data=None):
        # response = self.sendcmd(cmd, data)
        response = self.sendcmd_3(cmd, data)
        self.data = Meter.drop_ctl_bytes(Meter.remove_parity_bits(response)).decode("ascii")
        return self.data

    @staticmethod
    def drop_ctl_bytes(data):
        """Removes the standard delimiter bytes from the (response) data"""
        return bytes(filter(lambda b: b not in Meter.CTLBYTES, data))

    @staticmethod
    def remove_parity_bits(data):
        """Removes the parity bits from the (response) data"""
        return bytes(b & 0x7f for b in data)

    @staticmethod
    def bcc(data):
        """Computes the BCC (block  check character) value"""
        return bytes([functools.reduce(operator.xor, data, 0)])


class MeterRequests:

    def __init__(self, meter, timeout=10):
        self.meter = meter
        self.timeout = timeout

    def get_latest_p02(self):
        logger.debug("Requesting latest P.02")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.02({MeterRequests.get_dt()};)".encode())

    def get_latest_p01(self):
        logger.debug("Requesting latest P.01")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.01({MeterRequests.get_dt()};)".encode())

    def get_p01(self, timestamp):
        logger.debug(f"Requesting P.01 from {timestamp}")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.01({timestamp};)".encode())

    def get_p98logbook(self):
        logger.debug("Requesting latest P.98")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.98()".encode())

    def get_p99logbook(self):
        logger.debug("Requesting latest P.99")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.99()".encode())

    def get_p200logbook(self):
        # Query every X minutes. P.200(ERROR) - means no events
        logger.debug("Requesting latest P.200")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.200()".encode())

    def get_p210logbook(self):
        logger.debug("Requesting latest P.210")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.210()".encode())

    def get_p211logbook(self):
        logger.debug("Requesting latest P.210")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.211()".encode())

    def get_errors(self):
        # Should be F.F(00000000)
        logger.debug("Requesting errors F.F()")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"F.F()".encode())

    # Tables
    def get_table(self, table_no, meter_number):
        tables = {"1": b"/105296170!\r\n",  # 05296170 - meter address at 0.0.0
                  "2": b"/205296170!\r\n",
                  "3": b"/305296170!\r\n",
                  "4": b"/405296170!\r\n"
                  }
        assert str(table_no) in tables.keys(), f"No such table, choose one of {[a for a in tables.keys()]}"
        # Substitute meter number
        query = tables[str(table_no)][:2] + meter_number.encode() + tables[str(table_no)][10:]
        logger.debug(f"Requesting table {table_no}, {query}")
        with Meter(self.meter, self.timeout, get_id=False) as m:        # Using shortcut, id not needed
            return m.sendcmd_and_decode_response(query)

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
        re_value = re.compile('[(]([0-9]+\\.[0-9]+)')
        pre_results = []
        results = {}

        lines = data.split('\r\n')[1:]            # Remove header (meter id)
        for line in lines:
            if len(line) < 5:
                continue
            if not re_key.search(line):
                logger.debug(f"no key in line {line}")
                continue
            else:
                key = re_key.search(line).group()[:-1]

            if key == "0.9.1":
                cur_time = re_dt.search(line).group()[2:-1]        # Strip first digit
            elif key == "0.9.2":
                cur_date = re_dt.search(line).group()[2:-1]        # Strip first digit
            else:
                if not re_value.search(line):
                    logger.debug(f"Not found value X.X in line {line}")
                    continue
                else:
                    # value = re_value.search(line).group()[1:-1]
                    value = re_value.search(line).group()[1:]
                    pre_results.append((key, value))

        epoch = datetime.datetime.strptime(cur_date + cur_time, "%y%m%d%H%M%S").strftime("%s")
        results[epoch] = pre_results        # {epoch: [(obis_code:val), (), (), ...]}
        # logger.debug(f"Results: {results}")
        logger.debug("Finished parsing table 4 output")
        return results

    def parse_p01(self, data):
        # P.01(1190417001500)(00000000)(15)(6)(1.5)(kW)(2.5)(kW)(5.5)(kvar)(6.5)(kvar)(7.5)(kvar)(8.5)(kvar)
        # (0.014)(0.000)(0.013)(0.000)(0.000)(0.000)
        # (0.014)(0.000)(0.013)(0.000)(0.000)(0.000)

        logger.debug("Parsing P.01 output")
        # logger.debug(data)
        keys = ["1.5.0", "2.5.0", "5.5.0", "6.5.0", "7.5.0", "8.5.0"]

        lines = data.split('\r\n')
        pre_header = lines[0].split("(")                                    # Strip closing parenthesis
        header = [elem[:-1] for elem in pre_header]                         # Strip opening parenthesis
        try:
            base_dt = datetime.datetime.strptime(header[1][1:], "%y%m%d%H%M%S")
        except ValueError:
            logger.error(f"Incorrect date in header {header}, lines: {lines}")
            raise
        lines = lines[1:]
        pre_obis_codes = operator.itemgetter(5, 7, 9, 11, 13, 15)(header)           # Not used
        results = {}
        counter = 0
        for line in lines:
            if len(line) > 5:
                result = []
                values = line.split("(")[1:]            # First value is an empty string
                value_counter = 0
                for value in values:
                    result.append((keys[value_counter], value[:-1]))
                    value_counter += 1
                counter += 1
            results[(base_dt + datetime.timedelta(counter*15)).strftime("%s")] = result

        # Results = { epoch : [(obis_code, value), (), ...], epoch + 15m, [(), (), ...]}
        # logger.debug(f"Results: {results}")
        logger.debug("Finished parsing P.01 output")
        return results

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

# Get functions, that return meter data in dict format

'''
def get_data_15(meter_address):
    m = MeterRequests(f"socket://{meter_address}:8000", 300)
    table4_data = m.get_table(4)
    assert len(table4_data) > 0, "No data returned for Table4"
    p01_data = m.get_latest_p01()
    assert len(p01_data) > 0, "No data returned for P.01"
    table4_res = m.parse_table4(table4_data)
    p01_res = m.parse_p01(p01_data)
    return {"table4": table4_res, "p01": p01_res}
'''


def get_p01_parsed(meter_address, timestamp):
    m = MeterRequests(f"socket://{meter_address}:8000", 300)
    # p01_data = m.get_latest_p01()
    p01_data = m.get_p01(timestamp)
    assert len(p01_data) > 0, "No data returned for P.01"
    p01_res = m.parse_p01(p01_data)
    return {"p01": p01_res}


def get_table4_parsed(meter_address, meter_number):
    m = MeterRequests(f"socket://{meter_address}:8000", 300)
    table4_data = m.get_table(4, meter_number)
    assert len(table4_data) > 0, "No data returned for Table4"
    table4_res = m.parse_table4(table4_data)
    return {"table4": table4_res}

# Get functions, that return meter data in dict format, END


def get_json():
    url = "http://10.11.30.97:5000/api/meterpinginfo"
    logger.debug(f"Connecting to {url}")
    response = requests.get(url)
    assert response.status_code == 200, logger.error("API responded %s, expected 200" % response.status_code)
    # assert response.status_code == 200, f"API responded {response.status_code}, expected 200"
    return response.json()


def transform_metrics(meter_data, metric_key, metric_value):

    assert metric_key in transform_set, logger.error(f"Metric {metric_key} not in transform set {transform_set}")
    voltageRatio = float(meter_data["VoltageRatio"])
    currentRatio = float(meter_data["CurrentRatio"])
    totalFactor = float(meter_data["TotalFactor"])

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


def create_metrics(data, meter_data):
    """
    data = {
    'table4': {'1557693253': [('21.25', '0.004'), (), (), ...)]},
    'p01': {'1558989000': [('1.5.0', '0.017'), (), (), ...)]}
            }

    ZabbixMetric('Zabbix server', 'WirkleistungP3[04690915]', 3, clock=1554851400))
    """
    logger.debug(f"{data}, {meter_data}")
    zabbix_metrics = []
    metric_host = f"Meter {meter_data['MeterNumber']}"

    for data_set_name in data:                                      # Parse each table/logbook
        for metric_time in data[data_set_name]:                     # Parse each timestamp dataset
            for metric_tuple in data[data_set_name][metric_time]:   # Parse each key-value pair
                # logger.debug(f"Host: {metric_host}, Tuple: {metric_tuple}, Time: {metric_time}")
                metric_key = zabbix_obis_codes[metric_tuple[0]]
                metric_value = transform_metrics(meter_data, metric_key, metric_tuple[1])   # Apply transform
                logger.debug(f"{metric_host}, {metric_key}, {metric_value}, {metric_time}")
                zabbix_metrics.append(ZabbixMetric(metric_host, metric_key, metric_value, clock=int(metric_time)))

    return zabbix_metrics


'''
def push_data(meter_data):
    """
    meter_data: {
    "MeterNumber":"05296170",
    "manufacturer":"EMH",
    "ip":"10.124.2.120",
    "installationDate":"2019-02-20T09:00:00",
    "isActive":true,
    "voltageRatio":200,
    "currentRatio":15,
    "totalFactor":215
    }
    """
    data = get_data_15(meter_data["ip"])
    metrics = create_metrics(data, meter_data)
    # sender = ZabbixSender(zabbix_server_ip)
    sender = ZabbixSender("127.0.0.1")
    logger.debug(f"{metrics}")
    zabbix_response = sender.send(metrics)

    if zabbix_response.failed > 0 and zabbix_response.processed == 0:
        logger.error(f"Something went totally wrong {zabbix_response}")
        # exit(1)
    elif zabbix_response.failed > 0 and zabbix_response.failed > zabbix_response.processed:
        logger.warning(f"More failures that successes {zabbix_response}")
    else:
        logger.warning(f"Result {zabbix_response}")
    return


def meta_15():
    logger.info(f"Starting app")
    pool = Pool(16)
    # list_of_meters = get_json()
    list_of_meters = [{
        "MeterNumber": "05296170",
        "manufacturer": "EMH",
        "ip": "10.124.2.120",
        "installationDate": "2019-02-20T09:00:00",
        "isActive": True,
        "voltageRatio": 200,
        "currentRatio": 15,
        "totalFactor": 215
    }]
    logger.debug(f"Found {len(list_of_meters)} meters")
    pool.map(push_data, list_of_meters)
'''


def send_metrics(metrics):
    sender = ZabbixSender("127.0.0.1")
    logger.debug(f"{metrics}")
    zabbix_response = sender.send(metrics)

    if zabbix_response.failed > 0 and zabbix_response.processed == 0:
        logger.error(f"Something went wrong, {zabbix_response}")
        # exit(1)
    elif zabbix_response.failed > 0 and zabbix_response.failed > zabbix_response.processed:
        logger.warning(f"More failures that successes {zabbix_response}")
    else:
        logger.info(f"Result {zabbix_response}")
    return

# RQ mod

'''
def rq_create_metrics(data, meter_data):
    """
    data = {
    'table4': {'1557693253': [('21.25', '0.004'), (), (), ...)]},
    'p01': {'1558989000': [('1.5.0', '0.017'), (), (), ...)]}
            }
    """
    logger.debug(f"{data}, {meter_data}")
    metrics = []
    metric_host = f"Meter {meter_data['MeterNumber']}"

    for data_set_name in data:                                      # Parse each table/logbook
        for metric_time in data[data_set_name]:                     # Parse each timestamp dataset
            for metric_tuple in data[data_set_name][metric_time]:   # Parse each key-value pair
                metric_obis_code = metric_tuple[0]
                metric_key = zabbix_obis_codes[metric_obis_code]
                metric_value = transform_metrics(meter_data, metric_key, metric_tuple[1])   # Apply transform
                logger.debug(f"{metric_host}, {metric_key}, {metric_value}, {metric_time}")
                metrics.append([metric_host, metric_key, metric_value, metric_time])

    return metrics
'''


def rq_push_p01(meter, timestamp):
    data = get_p01_parsed(meter["ip"], timestamp)
    logger.debug(f"Creating metrics for Zabbix")
    metrics = create_metrics(data, meter)
    logger.debug(f"Sending metrics to Zabbix")
    send_metrics(metrics)
    return


def rq_push_table4(meter):
    data = get_table4_parsed(meter["ip"], meter["MeterNumber"])
    # metrics = rq_create_metrics(data, meter)
    metrics = create_metrics(data, meter)
    send_metrics(metrics)
    return


def get_job_meta(queue):

    running_jobs = {}
    for job_id in queue.job_ids:                          # job_id - '52ad7ebf-f8f1-4ac2-9cc8-c1a165b6675b'
        if queue.fetch_job(job_id) is None:
            logger.debug(f"Skipping None type job {job_id}")
            pass
        meta = queue.fetch_job(job_id).meta
        meta['job_id'] = job_id                           # Add job_id key to meta dictionary
        logger.debug(f"found meta: {meta}")
        running_jobs[meta["MeterNumber"]] = meta          # running_jobs = {MeterNumber1 : {meta}, MeterNumber2: {} ...}

    failed_jobs = {}
    for job_id in queue.failed_job_registry.get_job_ids():
        if queue.fetch_job(job_id) is None:
            logger.debug(f"Skipping None type job {job_id}")
            pass
        meta = queue.fetch_job(job_id).meta
        meta["job_id"] = job_id
        logger.debug(f"found meta: {meta}")
        failed_jobs[meta["MeterNumber"]] = meta

    return running_jobs, failed_jobs


def rq_create_jobs():
    """
    Receives list of meter dictionaries
    Places jobs to queues for python RQ
    """
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
        timestamp = MeterRequests.get_dt()                                              # This is used for P01 query
        current_timestamp = datetime.datetime.strptime(timestamp[1:], '%y%m%d%H%M')     # This is used for comparing

        new_job = {"MeterNumber": meter["MeterNumber"], "timestamp": timestamp}
        if new_job["MeterNumber"] in p01_failed_jobs.keys():
            # If job is found in "failed" queue
            existing_job = p01_failed_jobs[meter["MeterNumber"]]
            job_start_time = existing_job["timestamp"]
            existing_timestamp = datetime.datetime.strptime(job_start_time[1:], '%y%m%d%H%M')
            # If the job was started less than 24 hours ago - requeue
            delta = (current_timestamp - existing_timestamp).total_seconds()
            if delta < 86400:                                                             # Compare timestamps
                logger.debug(f"Requeueing failed P.01 job {existing_job['MeterNumber']}, start time: {job_start_time[1:]} UTC")
                p01_q.failed_job_registry.requeue(existing_job["job_id"])
            elif delta > 86400:
                logger.debug(f"Removing failed P.01 job {existing_job['MeterNumber']} after 24h, start time: {job_start_time[1:]} UTC")
                p01_q.failed_job_registry.remove(p01_q.fetch_job(existing_job["job_id"]))
        elif new_job["MeterNumber"] in p01_running_jobs.keys():
            # If job is found in "running/waiting" queue
            existing_job = p01_running_jobs[meter["MeterNumber"]]
            job_start_time = existing_job["timestamp"]

            logger.debug(f"Pending P.01 job {existing_job['MeterNumber']}, start time: {job_start_time[1:]} UTC")
            pass
        else:
            # New job, not found anywhere
            logger.debug(f"New P.01 job {new_job['MeterNumber']}")
            p01_q.enqueue(rq_push_p01, meter, timestamp, meta=new_job, result_ttl=10, ttl=900, failure_ttl=600)
        logger.debug(f"enqueueing rq_push_table4 for {meter['ip']}")
        table4_q.enqueue(rq_push_table4, meter, result_ttl=10, ttl=300, failure_ttl=600)

# RQ mod

'''
def requeue():
    p01_q = Queue(name="p01", connection=Redis())
    table4_q = Queue(name="table4", connection=Redis())
    for i in p01_q.failed_job_registry.get_job_ids():
        p01_q.failed_job_registry.requeue(i)
    for i in table4_q.failed_job_registry.get_job_ids():
        table4_q.failed_job_registry.requeue(i)
'''

if __name__ == "__main__":
    # To run create script.py with:
    # from emhmeter_rq import rq_create_jobs, logger
    #
    # logger.setLevel("DEBUG")
    # rq_create_jobs()

    # (venv) [root@vsrvenomos00123 app]# rq worker p01 table4
    logger.setLevel("DEBUG")
    rq_create_jobs()
