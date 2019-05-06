import serial
import time
import functools
import operator
import datetime
try:
    from Act_dlms.Helpers.create_logger import create_logger
except ImportError:
    from Helpers.create_logger import create_logger

# TODO: result[-2:-1] doesn\t match b'\n' ETX for no-data mode


class Meter:

    SOH = b'\x01'
    STX = b'\x02'
    ETX = b'\x03'
    ACK = b'\x06'
    EOT = b'\x04'
    LF = b'\n'

    CTLBYTES = SOH + STX + ETX
    LineEnd = [ETX, LF, EOT]

    # tables = {"1": b"/1!\r\n",
    #           "3": b"/0!\r\n",
    #          "4": b"/2!\r\n"
    #          }
    tables = {"1": b"/105296170!\r\n",       # 05296170 - meter address at 0.0.0
              "2": b"/205296170!\r\n",
              "3": b"/305296170!\r\n",
              "4": b"/405296170!\r\n"
    }

    def __init__(self, port, timeout, loglevel="DEBUG", get_id=True):
        self.port = port
        self.timeout = timeout
        self.loglevel = loglevel
        self.data = None
        self.get_id = get_id

    def __enter__(self):
        self.logger = create_logger("IEC.log", "Meter", self.loglevel)
        self.logger.debug(f"Opening connection to {self.port}")
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
        self.logger.debug("Closing connection")
        self.ser.close()

    def sendcmd(self, cmd, data=None, etx=ETX):
        assert etx in Meter.LineEnd, f"Proposed text end {etx} if not in {Meter.LineEnd}"

        if data:
            cmdwithdata = cmd + Meter.STX + data + Meter.ETX
            cmdwithdata = Meter.SOH + cmdwithdata + Meter.bcc(cmdwithdata)
        else:
            cmdwithdata = cmd

        while True:
            self.logger.debug(f"Sending {cmdwithdata}")
            self.ser.write(cmdwithdata)
            # If timeout is small (10 sec) - not enough time to read big (10KB) response.
            response = self.ser.read_until(etx)
            self.logger.debug(f"Received {len(response)} bytes: {response}")
            if response[-1:] == etx:
                if etx == Meter.ETX:
                    bccbyte = self.ser.read(1)
                    self.logger.debug(f"BCC: {bccbyte}")
                return response
            self.logger.debug("Retrying")
            time.sleep(1)

    def sendcmd_2(self, cmd, data=None, etx=ETX):
        timer = 5
        assert etx in Meter.LineEnd, f"Proposed text end {etx} if not in {Meter.LineEnd}"

        if data:
            cmdwithdata = cmd + Meter.STX + data + Meter.ETX
            cmdwithdata = Meter.SOH + cmdwithdata + Meter.bcc(cmdwithdata)
        else:
            cmdwithdata = cmd

        result = b""
        self.logger.debug(f"Sending {cmdwithdata}")
        self.ser.write(cmdwithdata)
        while True:
            time.sleep(timer)
            # If timeout is small (10 sec) - not enough time to read big (10KB) response.
            response = self.ser.read_all()
            if len(response) > 0:
                self.logger.debug(f"Received {len(response)} bytes: {response}")
                result += response
                self.logger.debug(f"Result {result}")
                continue
            elif len(response) == 0 and len(result) > 0:
                self.logger.debug(f"no response returned in {timer} seconds, assuming transmission ended")
                if etx == Meter.ETX:
                    bccbyte = result[-1]
                    self.logger.debug(f"BCC: {bccbyte}")
                return result
            elif len(response) == 0 and len(result) == 0:
                self.logger.debug(f"no response returned in {timer} seconds, retrying")
                self.logger.debug(f"Sending {cmdwithdata}")
                self.ser.write(cmdwithdata)

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

        self.logger.debug(f"Sending {cmdwithdata}")
        self.ser.write(cmdwithdata)
        time.sleep(timer)

        while True:
            # Read may be infinite
            # self.logger.debug(f"Bytes waiting in input: {self.ser.in_waiting}")

            if self.ser.in_waiting > 0:
                # If there is data to read - read it
                response = self.ser.read(self.ser.in_waiting)
                # self.logger.debug(f"Result {response}")
                result += response
                waited = 0
                continue
            elif self.ser.in_waiting == 0:
                # If no data to read:
                # self.logger.debug(f"{result}")
                if len(result) > 0 and result[-2:-1] == etx:
                    # Check if the second-last read byte is End-of-Text (or similar)
                    self.logger.debug(f"ETX {etx} found, assuming end of transmission")
                    if etx == Meter.ETX:
                        bccbyte = result[-1:]
                        self.logger.debug(f"BCC: {bccbyte}")
                    return result

                # If the last is read byte not ETX - wait for more data
                if waited < wait_limit:

                    self.logger.debug(f"No data, waiting for {timer} sec, {timer*wait_limit - timer*waited} sec left")
                    time.sleep(timer)
                    waited += 1
                    continue
                elif waited >= wait_limit:
                    self.logger.debug(f"No more data in last {timer} seconds")
                    self.logger.debug(f"Received {len(result)} bytes: {result}")
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

    def __init__(self, meter, timeout=10, loglevel="DEBUG"):
        self.logger = create_logger("IEC.log", "MeterRequests", loglevel)
        self.meter = meter
        self.timeout = timeout

    def get_latest_p02(self):
        self.logger.debug("Requesting latest P.02")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.02({MeterRequests.get_dt()};)".encode())

    def get_latest_p01(self):
        self.logger.debug("Requesting latest P.01")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.01({MeterRequests.get_dt()};)".encode())

    def get_p98logbook(self):
        self.logger.debug("Requesting latest P.98")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.98()".encode())

    def get_p99logbook(self):
        self.logger.debug("Requesting latest P.99")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.99()".encode())

    def get_p200logbook(self):
        # Query every X minutes. P.200(ERROR) - means no events
        self.logger.debug("Requesting latest P.200")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.200()".encode())

    def get_p210logbook(self):
        self.logger.debug("Requesting latest P.210")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.210()".encode())

    def get_p211logbook(self):
        self.logger.debug("Requesting latest P.210")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"P.211()".encode())

    def get_errors(self):
        # Should be F.F(00000000)
        self.logger.debug("Requesting errors F.F()")
        with Meter(self.meter, self.timeout) as m:
            m.sendcmd_and_decode_response(Meter.ACK + b'051\r\n')
            return m.sendcmd_and_decode_response("R5".encode(), f"F.F()".encode())

    # Tables
    def get_table(self, table_no):
        assert str(table_no) in Meter.tables.keys(), f"No such table, choose one of {[a for a in Meter.tables.keys()]}"
        self.logger.debug(f"Requesting table {table_no}")
        with Meter(self.meter, self.timeout, get_id=False) as m:        # Using shortcut, id not needed
            return m.sendcmd_and_decode_response(Meter.tables[str(table_no)])

    def get_data(self):
        self.logger.debug("Requesting data")
        result = []
        result.append(self.get_latest_p01())
        time.sleep(5)
        result.append(self.get_latest_p02())
        time.sleep(5)
        result.append(self.get_errors())
        return result

    @staticmethod
    def get_dt():
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


if __name__ == "__main__":
    m = MeterRequests("socket://10.124.2.120:8000", 300)
    print(m.get_table(2))
    # print(m.get_p200logbook())

    # Does TCP retransmission breaks the meter?
    # client -Push-> meter
    # client -Push-> meter (retransmit)
    # meter -ACK-> client
    # meter -ACK-> client (duplicated ACK)
    # Meter stops sending data


