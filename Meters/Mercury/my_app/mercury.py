import binascii
from Mercury.my_app.crc16_calc import *
import serial
import logging
import sys


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


class Mercury:

    timeout = 1
    commands = {
        # "channel_test": {"cmd": b'\x00', "response_size": 4, "name": "Тест канала"},
        # Теоретически, 111111 = 0x313131313131, запрос b'\x01\x01\x31\x31\x31\x31\x31\x31', но работает так
        "channel_open": {"cmd": b'\x01\x01\x01\x01\x01\x01\x01\x01', "response_size": 4, "name": "Открытие канала"},
        # \x00 в середине - от сброса \x40 - за сутки
        "get_active_power": {"cmd": b'\x05\x00\x00', "response_size": 19, "name": "Активная мощность"},
        # Чтение параметров - чтение вспомогательных параметров \x08
        # \x11 - мгновенные значения тока, мощности, напряжения и т.д.
        # +
        # \x0[1-3] - мощн 2 бита P/Q/S + 2 бита фазы; \x0A=S по ф2 (2 и 2 = 10 и 10 - b1010 = \xА); \x00 - P по сумм фаз
        # \x1[1-3] - напряжение по фазе 1-3
        # \x2[1-3] - ток по фазе 1-3
        # \x40 - частота
        # \x5[1-3] - угол между фазами 1-2/1-3/2-3
        # \x6[1-3] - коэфициент искажения синусоидальности фазных напряжений по фазе 1/2/3
        # \x70 - температура в корпусе
        "get_u1": {"cmd": b'\x08\x11\x11', "response_size": 6, "name": "Напряжение Ф1"},
        "get_u2": {"cmd": b'\x08\x11\x12', "response_size": 6, "name": "Напряжение Ф2"},
        "get_u3": {"cmd": b'\x08\x11\x13', "response_size": 6, "name": "Напряжение Ф3"},
        "get_i1": {"cmd": b'\x08\x12\x13', "response_size": 6, "name": "Ток Ф1"},
        "get_i2": {"cmd": b'\x08\x12\x13', "response_size": 6, "name": "Ток Ф2"},
        "get_i3": {"cmd": b'\x08\x12\x13', "response_size": 6, "name": "Ток Ф3"},
        "get_summ_p": {"cmd": b'\x08\x11\x00', "response_size": 6, "name": "Мощность по сумме фаз"},
        "get_angle_12": {"cmd": b'\x08\x11\x51', "response_size": 6, "name": "Угол между Ф1 и Ф2"},
        "get_angle_13": {"cmd": b'\x08\x11\x52', "response_size": 6, "name": "Угол между Ф1 и Ф3"},
        "get_angle_23": {"cmd": b'\x08\x11\x53', "response_size": 6, "name": "Угол между Ф2 и Ф3"},
        "get_freq": {"cmd": b'\x08\x11\x40', "response_size": 6, "name": "Частота"}
    }

    def __init__(self, addr, lfile, llevel="INFO", type="230", port="/dev/ttyUSB0"):
        self.type = type
        self.addr = int(addr)
        self.addr_byte = chr(self.addr).encode()
        self.port = port
        self.logger = create_logger(lfile, f"Mercury{self.type}", llevel)

    def __enter__(self):
        self.logger.debug(f"{self.addr} Opening connection to {self.port}")

        try:
            self.ser = serial.serial_for_url(self.port,
                                             baudrate=9600,
                                             bytesize=serial.EIGHTBITS,
                                             parity=serial.PARITY_NONE,
                                             stopbits=serial.STOPBITS_ONE,
                                             timeout=Mercury.timeout)
        except serial.SerialException:
            self.logger.error(f"{self.addr} Timeout when connecting to {self.port}")
            raise serial.SerialException
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.flush()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.debug(f"{self.addr} Closing connection")
        self.ser.close()

    def send_cmd(self, cmd):
        if cmd not in Mercury.commands.keys():
            self.logger.error(f"Wrong command {cmd}, choose one of {list(Mercury.commands)}")
            raise KeyError
        req = self.addr_byte + Mercury.commands[cmd]["cmd"]
        crc = hex(crc16(req, CRC16_MODBUS)).encode()
        self.logger.debug(f"Request {req} CRC {crc}")
        req += crc
        self.ser.write(req)

        resp = b""
        received_bytes = 0
        while received_bytes != Mercury.commands[cmd]["response_size"]:
            resp += self.ser.read(1)
            received_bytes += 1
        self.logger.debug(f"Command {cmd}, request {req}, response {resp}")
        return binascii.hexlify(resp)

    def run(self):
        for cmd in Mercury.commands:
            print(f"{Mercury.commands[cmd]['name']}: {self.send_cmd(cmd)}")


if __name__ == "__main__":
    with Mercury(addr=174, lfile="/dev/null", llevel="DEBUG") as m:
        m.run()
