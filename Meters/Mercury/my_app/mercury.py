import binascii
try:
    from Mercury.my_app.crc16_calc import *
except ModuleNotFoundError:
    from crc16_calc import *
import serial
import logging
import sys
import time
import json
from pyzabbix import ZabbixMetric, ZabbixSender


errors = {
    "08": {"code": "Е-08", "name": "Пусто"},
    "07": {"code": "Е-07", "name": "Нарушено функционирование памяти #3"},
    "06": {"code": "Е-06", "name": "Нарушено функционирование RTC"},
    "05": {"code": "Е-05", "name": "Нарушено функционирование памяти #1"},
    "04": {"code": "Е-04", "name": "Нарушено функционирование ADC"},
    "03": {"code": "Е-03", "name": "Нарушено функционирование UART1"},
    "02": {"code": "Е-02", "name": "Нарушено функционирование памяти #2"},
    "01": {"code": "Е-01", "name": "Напряжение батареи менее 2,2 В"},
    "16": {"code": "Е-16", "name": "Ошибка КС байта тарификатора"},
    "15": {"code": "Е-15", "name": "Ошибка КС массива варианта исполнения счетчика"},
    "14": {"code": "Е-14", "name": "Ошибка КС пароля"},
    "13": {"code": "Е-13", "name": "Ошибка КС серийного номера"},
    "12": {"code": "Е-12", "name": "Ошибка КС адреса прибора"},
    "11": {"code": "Е-11", "name": "Ошибка КС массива регистров накопленной энергии"},
    "10": {"code": "Е-10", "name": "Ошибка КС массива калибровочных коэфициентов в Flash MSP430"},
    "09": {"code": "Е-09", "name": "Ошибка КС программы"},
    "32": {"code": "Е-32", "name": "Ошибка КС параметров среза"},
    "31": {"code": "Е-31", "name": "Ошибка КС массива регистров накопления по периодамвремени"},
    "30": {"code": "Е-30", "name": "Ошибка КС массива коэффициентов трансформации"},
    "29": {"code": "Е-29", "name": "Ошибка КС массива местоположения прибора"},
    "28": {"code": "Е-28", "name": "Ошибка КС массива сезонных переходов"},
    "27": {"code": "Е-27", "name": "Ошибка КС массива таймера"},
    "26": {"code": "Е-26", "name": "Ошибка КС массива тарифного расписания"},
    "25": {"code": "Е-25", "name": "Ошибка КС массива праздничных дней"},
    "48": {"code": "Е-48", "name": "Напряжение батареи менее 2,65 В"}
}

commands = {
    "channel_test": {"cmd": b'\x00', "response_size": 4, "name": "Тест канала", "decoder": "Initial"},
    # Теоретически, 111111 = 0x313131313131, запрос b'\x01\x01\x31\x31\x31\x31\x31\x31', но работает так
    "channel_open": {"cmd": b'\x01\x01\x01\x01\x01\x01\x01\x01', "response_size": 4, "name": "Открытие канала",
                     "decoder": "Initial"},
    # 2.5.16  ЗАПРОСЫ НА ЧТЕНИЕ МАССИВОВ РЕГИСТРОВ НАКОПЛЕННОЙ ЭНЕРГИИ
    # \x00 в середине - от сброса \x40 - за сутки
    "get_power": {"cmd": b'\x05\x00\x00', "response_size": 19, "name": "Мощность", "decoder": "P"},  # За все время
    # Пример ответа: aea4006282ffffffff00006107ffffffff258b
    # "get_power_this_year": {"cmd": b'\x05\x01\x00', "response_size": 19, "name": "Мощность за год", "decoder": "P"},
    # "get_power_prev_year": {"cmd": b'\x05\x02\x00', "response_size": 19, "name": "Мощность за прошлый год", "decoder": "P"},
    # "get_power_this_month": {"cmd": b'\x05\x0c\x00', "response_size": 19, "name": "Мощность за месяц", "decoder": "P"},
    # Запросы - 2.5.32
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
    "get_u1": {"cmd": b'\x08\x11\x11', "response_size": 6, "name": "Напряжение Ф1", "decoder": "U"},
    "get_u2": {"cmd": b'\x08\x11\x12', "response_size": 6, "name": "Напряжение Ф2", "decoder": "U"},
    "get_u3": {"cmd": b'\x08\x11\x13', "response_size": 6, "name": "Напряжение Ф3", "decoder": "U"},
    "get_i1": {"cmd": b'\x08\x11\x21', "response_size": 6, "name": "Ток Ф1", "decoder": "I"},
    "get_i2": {"cmd": b'\x08\x11\x22', "response_size": 6, "name": "Ток Ф2", "decoder": "I"},
    "get_i3": {"cmd": b'\x08\x11\x23', "response_size": 6, "name": "Ток Ф3", "decoder": "I"},
    "get_summ_p": {"cmd": b'\x08\x11\x00', "response_size": 6, "name": "Мощность по сумме фаз", "decoder": "P_inst"},
    "get_angle_12": {"cmd": b'\x08\x11\x51', "response_size": 6, "name": "Угол между Ф1 и Ф2", "decoder": "sin"},
    "get_angle_13": {"cmd": b'\x08\x11\x52', "response_size": 6, "name": "Угол между Ф1 и Ф3", "decoder": "sin"},
    "get_angle_23": {"cmd": b'\x08\x11\x53', "response_size": 6, "name": "Угол между Ф2 и Ф3", "decoder": "sin"},
    # 2.5.32.5 Ответ прибора на запрос чтения коэффициентов искажения синусоидальности фазных напряжений.
    "get_sin_koeff_1": {"cmd": b'\x08\x11\x61', "response_size": 6, "name": "Коэффициент искажения Ф1",
                        "decoder": "koeff"},
    "get_sin_koeff_2": {"cmd": b'\x08\x11\x62', "response_size": 6, "name": "Коэффициент искажения Ф2",
                        "decoder": "koeff"},
    "get_sin_koeff_3": {"cmd": b'\x08\x11\x63', "response_size": 6, "name": "Коэффициент искажения Ф3",
                        "decoder": "koeff"},
    "get_freq": {"cmd": b'\x08\x11\x40', "response_size": 6, "name": "Частота", "decoder": "F"},
    # "get_temp": {"cmd": b'\x08\x11\x70', "response_size": 6, "name": "Температура в корпусе"},
    # 2.5.12  ЧТЕНИЕ ВРЕМЕНИ И КОДА СЛОВОСОСТОЯНИЯ ПРИБОРА.
    # "get_state": {"cmd": b'\x04\x14\x00', "response_size": 15, "name": "Состояние", "decoder": "None"}
}


commands2 = {
    "channel_test": {"cmd": b'\x00', "response_size": 4, "name": "Тест канала", "decoder": "Initial"},
    # Теоретически, 111111 = 0x313131313131, запрос b'\x01\x01\x31\x31\x31\x31\x31\x31', но работает так
    "channel_open": {"cmd": b'\x01\x01\x01\x01\x01\x01\x01\x01', "response_size": 4, "name": "Открытие канала",
                     "decoder": "Initial"},
    "get_summ_p": {"cmd": b'\x08\x11\x00', "response_size": 6, "name": "P по сумме фаз", "decoder": "P_inst"},
    "get_summ_q": {"cmd": b'\x08\x11\x10', "response_size": 6, "name": "Q по сумме фаз", "decoder": "P_inst"},
    "get_summ_s": {"cmd": b'\x08\x11\x20', "response_size": 6, "name": "S по сумме фаз", "decoder": "P_inst"},
    "get_angle_12": {"cmd": b'\x08\x11\x51', "response_size": 6, "name": "Угол между Ф1 и Ф2", "decoder": "sin"},
    "get_angle_13": {"cmd": b'\x08\x11\x52', "response_size": 6, "name": "Угол между Ф1 и Ф3", "decoder": "sin"},
    "get_angle_23": {"cmd": b'\x08\x11\x53', "response_size": 6, "name": "Угол между Ф2 и Ф3", "decoder": "sin"},
    # "get_temp": {"cmd": b'\x08\x11\x70', "response_size": 6, "name": "Температура в корпусе", "decoder": "None"},
    # 2.5.12  ЧТЕНИЕ ВРЕМЕНИ И КОДА СЛОВОСОСТОЯНИЯ ПРИБОРА.
    # "get_state": {"cmd": b'\x04\x14\x00', "response_size": 15, "name": "Состояние", "decoder": "None"}
}

commands3 = {
    "channel_test": {"cmd": b'\x00', "response_size": 4, "name": "Тест канала", "decoder": "Initial"},
    "channel_open": {"cmd": b'\x01\x01\x01\x01\x01\x01\x01\x01', "response_size": 4, "name": "Открытие канала",
                     "decoder": "Initial"},
    "get_power": {"cmd": b'\x05\x00\x00', "response_size": 19, "name": "Мощность", "decoder": "P"},
    "get_u1": {"cmd": b'\x08\x11\x11', "response_size": 6, "name": "Напряжение Ф1", "decoder": "U"},
    "get_u2": {"cmd": b'\x08\x11\x12', "response_size": 6, "name": "Напряжение Ф2", "decoder": "U"},
    "get_u3": {"cmd": b'\x08\x11\x13', "response_size": 6, "name": "Напряжение Ф3", "decoder": "U"},
    "get_i1": {"cmd": b'\x08\x11\x21', "response_size": 6, "name": "Ток Ф1", "decoder": "I"},
    "get_i2": {"cmd": b'\x08\x11\x22', "response_size": 6, "name": "Ток Ф2", "decoder": "I"},
    "get_i3": {"cmd": b'\x08\x11\x23', "response_size": 6, "name": "Ток Ф3", "decoder": "I"},
    "get_p1": {"cmd": b'\x08\x11\x01', "response_size": 6, "name": "Мощность P1", "decoder": "P_inst"},
    "get_p2": {"cmd": b'\x08\x11\x02', "response_size": 6, "name": "Мощность P2", "decoder": "P_inst"},
    "get_p3": {"cmd": b'\x08\x11\x03', "response_size": 6, "name": "Мощность P3", "decoder": "P_inst"},
    "get_angle_12": {"cmd": b'\x08\x11\x51', "response_size": 6, "name": "Угол между Ф1 и Ф2", "decoder": "sin"},
    "get_angle_13": {"cmd": b'\x08\x11\x52', "response_size": 6, "name": "Угол между Ф1 и Ф3", "decoder": "sin"},
    "get_angle_23": {"cmd": b'\x08\x11\x53', "response_size": 6, "name": "Угол между Ф2 и Ф3", "decoder": "sin"},
    "get_freq": {"cmd": b'\x08\x11\x40', "response_size": 6, "name": "Частота", "decoder": "F"},
}

violations = {
    "channel_test": {"cmd": b'\x00', "response_size": 4, "name": "Тест канала", "decoder": "Initial"},
    # Теоретически, 111111 = 0x313131313131, запрос b'\x01\x01\x31\x31\x31\x31\x31\x31', но работает так
    "channel_open": {"cmd": b'\x01\x01\x01\x01\x01\x01\x01\x01', "response_size": 4, "name": "Открытие канала",
                     "decoder": "Initial"},
    # 2.5.14  ЧТЕНИЕ ВРЕМЕНИ ВЫХОДА/ВОЗВРАТА ЗА ДОПУСТИМЫЕ ПАРАМЕТРОВ СЧЁТЧИКА.
    "u1_min_limit": {"cmd": b'\x04\x20\x00', "response_size": 15,
                     "name": "Выход/возврат за минимальное предельно допустимое значение напряжения в фазе 1", "decoder": "None"},
    "u1_min_normal": {"cmd": b'\x04\x21\x00', "response_size": 15,
                      "name": "Выход/возврат за минимальное нормально допустимое значение напряжения в фазе 1", "decoder": "None"},
    "u1_max_normal": {"cmd": b'\x04\x22\x00', "response_size": 15,
                      "name": "Выход/возврат за максимальное нормально допустимое значение напряжения в фазе 1", "decoder": "None"},
    "u1_max_limit": {"cmd": b'\x04\x23\x00', "response_size": 15,
                     "name": "Выход/возврат за максимальное предельно допустимое значение напряжения в фазе 1", "decoder": "None"},
    "u2_min_limit": {"cmd": b'\x04\x24\x00', "response_size": 15,
                     "name": "Выход/возврат за минимальное предельно допустимое значение напряжения в фазе 2", "decoder": "None"},
    "u2_min_normal": {"cmd": b'\x04\x25\x00', "response_size": 15,
                      "name": "Выход/возврат за минимальное нормально допустимое значение напряжения в фазе 2", "decoder": "None"},
    "u2_max_normal": {"cmd": b'\x04\x26\x00', "response_size": 15,
                      "name": "Выход/возврат за максимальное нормально допустимое значение напряжения в фазе 2"},
    "u2_max_limit": {"cmd": b'\x04\x27\x00', "response_size": 15,
                     "name": "Выход/возврат за максимальное предельно допустимое значение напряжения в фазе 2"},
    "u3_min_limit": {"cmd": b'\x04\x28\x00', "response_size": 15,
                     "name": "Выход/возврат за минимальное предельно допустимое значение напряжения в фазе 3"},
    "u3_min_normal": {"cmd": b'\x04\x29\x00', "response_size": 15,
                      "name": "Выход/возврат за минимальное нормально допустимое значение напряжения в фазе 3"},
    "u3_max_normal": {"cmd": b'\x04\x2a\x00', "response_size": 15,
                      "name": "Выход/возврат за максимальное нормально допустимое значение напряжения в фазе 3"},
    "u3_max_limit": {"cmd": b'\x04\x2b\x00', "response_size": 15,
                     "name": "Выход/возврат за максимальное предельно допустимое значение напряжения в фазе 3"},
    "freq_min_limit": {"cmd": b'\x04\x2c\x00', "response_size": 15,
                       "name": "Выход/возврат за минимальное предельно допустимое значение частоты"},
    "freq_min_normal": {"cmd": b'\x04\x2d\x00', "response_size": 15,
                        "name": "Выход/возврат за минимальное нормально допустимое значение частоты"},
    "freq_max_normal": {"cmd": b'\x04\x2e\x00', "response_size": 15,
                        "name": "Выход/возврат за максимальное нормально допустимое значение частоты"},
    "freq_max_limit": {"cmd": b'\x04\x2f\x00', "response_size": 15,
                       "name": "Выход/возврат за максимальное предельноо допустимое значение частоты"},
}


def create_logger(log_filename, instance_name, loglevel="INFO"):
    if loglevel == "ERROR":
        log_level = logging.ERROR
    elif loglevel == "WARNING":
        log_level = logging.WARNING
    elif loglevel == "INFO":
        log_level = logging.INFO
    else:
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


class Decoders:

    def __init__(self, addr, decoded):
        self.decoded = decoded
        self.addr = addr
        self.value = None

    def decode(self, value):
        self.value = value
        self.strip_crc_id()

        if self.decoded == "Initial":
            value = self.decode_generic()
        elif self.decoded in ["U", "F", "sin"]:
            value = self.decode_hex_to_dec_by_100()
        elif self.decoded in ["I"]:
            value = self.decode_hex_to_dec_by_1000()
        elif self.decoded in ["P_inst"]:
            value = self.decode_hex_to_dec_by_100_strip_byte()
        elif self.decoded in ["Temp"]:
            value = self.decode_hex_to_dec()
        elif self.decoded in ["P"]:
            value = self.decode_energy()
        elif self.decoded in ["koeff"]:
            value = self.decode_sin_koeff()
        elif self.decoded in ["None"]:
            pass

        return value

    def decode_generic(self):
        # Decode generic comnand, check if the response is 0
        if int(self.value, base=16) == 0:
            return "OK"
        else:
            return "Something went wrong"

    def decode_hex_to_dec_by_100(self):
        value = self.normalize_3b(self.value.decode())
        value = "0x" + value
        return int(value, base=16) / 100

    def decode_hex_to_dec_by_1000(self):
        value = self.normalize_3b(self.value.decode())
        value = "0x" + value
        return int(value, base=16) / 1000

    def decode_hex_to_dec(self):
        value = "0x" + self.value.decode()
        return int(value, base=16)

    def decode_hex_to_dec_by_100_strip_byte(self):
        value = self.normalize_3b(self.value.decode())
        if len(value) == 5:
            value = value[1:]
        elif len(value) == 6:
            value = value[2:]
        value = "0x" + value
        return int(value, base=16) / 100

    def decode_sin_koeff(self):
        value = self.normalize_2b(self.value.decode())
        value = "0x" + self.value.decode()
        return int(value, base=16) / 100

    # Байты нужно менять местами в соответствии с документацией
    @staticmethod
    def normalize_4b(value):
        result = value[2:4] + value[:2] + value[6:] + value[4:6]
        return result

    @staticmethod
    def normalize_3b(value):
        result = value[:2] + value[4:] + value[2:4]
        return result

    @staticmethod
    def normalize_2b(value):
        result = value[2:] + value[:2]
        return result

    def decode_energy(self):
        self.value = self.value.decode()
        # ffffffff = нет

        result = dict()
        # active_plus = "A+ " + str(int("0x" + self.normalize_4b(self.value[:8]), base=16)) + " Вт*ч"
        # active_minus = "A- " + str(int("0x" + self.normalize_4b(self.value[8:16]), base=16)) + " Вт*ч"
        # reactive_plus = "R+ " + str(int("0x" + self.normalize_4b(self.value[16:24]), base=16)) + " вар*ч"
        # reactive_minus = "R- " + str(int("0x" + self.normalize_4b(self.value[24:]), base=16)) + " вар*ч"
        active_plus = str(int("0x" + self.normalize_4b(self.value[:8]), base=16))
        active_minus = str(int("0x" + self.normalize_4b(self.value[8:16]), base=16))
        reactive_plus = str(int("0x" + self.normalize_4b(self.value[16:24]), base=16))
        reactive_minus = str(int("0x" + self.normalize_4b(self.value[24:]), base=16))

        result['active_plus'] = active_plus
        result['active_minus'] = active_minus
        result['reactive_plus'] = reactive_plus
        result['reactive_minus'] = reactive_minus

        if "4294967295" in result['active_plus']:
            # active_plus = "A+ нет"
            result['active_plus'] = "0"
        if "4294967295" in result['active_minus']:
            # active_minus = "A- нет"
            result['active_minus'] = "0"
        if "4294967295" in result['reactive_plus']:
            # reactive_plus = "R+ нет"
            result['reactive_plus'] = "0"
        if "4294967295" in result['reactive_minus']:
            # reactive_minus = "R- нет"
            result['reactive_minus'] = "0"

        return result

    def strip_crc_id(self):
        # If first byte matches the address - strip it, it's an address
        if int(self.value[:2], base=16) == self.addr:
            self.value = self.value[2:-4]
        else:
            self.value = self.value[:-4]


class Mercury:
    timeout = 1

    def __init__(self, addr, lfile, commands, llevel="INFO", meter_type="230", port="/dev/ttyUSB0", mode="normal"):
        self.type = meter_type
        self.addr = int(addr)
        self.addr_byte = bytes([self.addr])
        self.port = port
        self.logger = create_logger(lfile, f"Mercury{self.type}", llevel)
        self.commands = commands
        self.mode = mode
        self.export_data = []

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
        time.sleep(0.1)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.flush()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.debug(f"{self.addr} Closing connection")
        self.ser.close()

    def send_cmd(self, cmd):
        if cmd not in self.commands.keys():
            self.logger.error(f"Wrong command {cmd}, choose one of {list(self.commands)}")
            raise KeyError
        req = self.addr_byte + self.commands[cmd]["cmd"]
        # req = b'\xae\x00'
        crc = crc16(req, CRC16_MODBUS)
        # crc = b'\x7d\xd0'
        req += crc
        # self.logger.debug(f"Request {req} {binascii.hexlify(req)}")
        self.logger.debug(f"Request {req}")
        self.ser.write(req)

        resp = b""
        received_bytes = 0
        while received_bytes != self.commands[cmd]["response_size"]:
            resp += self.ser.read(1)
            received_bytes += 1
        self.logger.debug(f"Command {cmd}, request {req}, response {resp}")
        return resp

    def decoder(self, in_bytes, cmd):
        new_decoder = Decoders(self.addr, self.commands[cmd]["decoder"])
        decoded_result = new_decoder.decode(in_bytes)
        return decoded_result

    def crc_check(self, in_bytes):
        bytes_no_crc = in_bytes[:-2]
        bytes_crc = in_bytes[-2:]
        bytes_crc_check = crc16(bytes_no_crc, CRC16_MODBUS)
        self.logger.debug(f"{in_bytes}, CRC: {bytes_crc}, Calculated CRC: {bytes_crc_check}")
        return bytes_crc == bytes_crc_check

    def run(self):
        for cmd in self.commands:
            response = self.send_cmd(cmd)
            if not self.crc_check(response):
                self.logger.error(f"CRC error, CMD: {cmd}, response: {response}")
            decoded_resp = self.decoder(binascii.hexlify(response), cmd)
            if self.mode == "normal":
                print(f"{self.commands[cmd]['name']}: {decoded_resp}")
            elif self.mode == "export":
                self.export_data.append(json.loads(f'{{"{cmd}": "{decoded_resp}"}}'))
        self.export()

    def export(self):
        # [{'channel_test': 'OK'},
        # {'get_power': "{'active_plus': '59598256', 'active_minus': '0', 'reactive_plus': '2758489', 'reactive_minus': '0'}"},
        # {'get_u1': '238.83'}, {'get_u2': '230.23'}, {'get_u3': '235.48'}, {'get_i1': '0.184'}, {'get_i2': '8.565'},
        # {'get_i3': '2.086'}, {'get_p1': '36.57'}, {'get_p2': '647.95'}]
        # ZabbixMetric('Zabbix server', 'WirkleistungP3[04690915]', 3, clock=1554851400))

        host = "ZV-Electricity"
        zserver = '127.0.0.1'

        zsender = ZabbixSender(zserver)
        zmetrics = []

        banned = ['channel_test', 'channel_open']
        for metric in self.export_data:
            k = list(metric.keys())[0]
            if k in banned:
                continue
            if k == 'get_power':
                powers = json.loads(metric[k].replace("'", '"'))
                for power in powers:
                    zmetrics.append(ZabbixMetric(host, k + '_' + power, powers[power]))
                    if power == 'active_plus':
                        # For usage calculation
                        zmetrics.append(ZabbixMetric(host, 'get_power_active_plus_consumption', powers[power]))
                continue
            zmetrics.append(ZabbixMetric(host, k, metric[k]))
        # print(zmetrics)
        zresponse = zsender.send(zmetrics)
        print(zresponse)


if __name__ == "__main__":
    # meter_addr = 174
    meter_addr = 88
    # llevel = "DEBUG"
    llevel = "INFO"

    with Mercury(addr=meter_addr, commands=commands3, lfile="/dev/null", llevel=llevel, mode="export") as m:
        m.run()
