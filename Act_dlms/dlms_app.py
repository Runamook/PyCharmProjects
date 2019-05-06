import socket
import time
import functools
import operator

try:
    from Act_dlms.Helpers.create_logger import create_logger
except ImportError:
    from Helpers.create_logger import create_logger

# TODO: Response length check

SOH = b'\x01'
STX = b'\x02'
ETX = b'\x03'
AUX = b'\x06'
CTLBYTES = SOH + STX + ETX


def drop_ctl_bytes(data):
    """Removes the standard delimiter bytes from the (response) data"""
    return bytes(filter(lambda b: b not in CTLBYTES, data))


def remove_parity_bits(data):
    """Removes the parity bits from the (response) data"""
    return bytes(b & 0x7f for b in data)


def bcc(data):
    """Computes the BCC (block  check character) value"""
    return bytes([functools.reduce(operator.xor, data, 0)])


class Client:

    def __init__(self, host="localhost", port=8000, protocol_mode='C'):
        self.host = host
        self.port = port
        self.protocol_mode = protocol_mode

        self.s = None

        self.data = []
        self.identifier = b""

        self.logger = create_logger("iec_app.log", "IEC_APP", "DEBUG")

    def read(self, table="1"):
        if table == "3":        # EMH Internal
            query = b'/0!\r\n'
        elif table == "1":      # Billing data
            query = b'/1!\r\n'
        elif table == "4":      # Service table - instant values
            query = b'/2!\r\n'
        elif table == "2":      # Load profile
            query = b'/3!\r\n'
        else:
            self.logger.info("Incorrect table")
            exit(1)

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.host, self.port))
        self.logger.debug(f"Connected to {self.host}:{self.port}")
        self.s.settimeout(15)

        # self.read_id()
        self.read_data(query)

        self.s.close()

    def read_data(self, query):

        self.logger.debug(f"Sending data query {query}")
        self.s.send(query)
        query_result = b""
        while True:
            try:
                reply = self.s.recv(4096)
                query_result += reply
                time.sleep(1)
                # if reply == b'' or reply is None:
                #    self.logger.info("Empty response on data")
                #    break
            except socket.timeout:
                self.logger.info("Timeout reading data, assuming meter ended transmission")
                break
        self.data = remove_parity_bits(query_result)
        self.data = drop_ctl_bytes(self.data).decode("ascii").split("\r\n")
        return



