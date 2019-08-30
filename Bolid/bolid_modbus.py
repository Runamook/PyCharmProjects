# TODO: Контроль связи с С2000М 1.1.4.5 - события 250/251 в зоне опросчика
# TODO: Получение температуры от С2000-ИП
# TODO: Получение нарпяжения и тока от РИП
# TODO: Получение событий
# TODO: Зона опросника - пульт С2000М (в режиме Orion-slave)

# Регистр расшренного состояния зоны 46192, читается через 2 запроса. Первый запрос записывает номер зоны.
# Функция 6 регистр 46176 № зоны
# Функция 3 регистр 46192 Количество регистров = количество байт состояния / 2
#
# Регистр расшренного состояния раздела 46200, читается через 2 запроса. Первый запрос записывает номер раздела.
# 46177 -> 46200 Количество регистров = количество байт состояния / 2
#
# Регистр события по установленному номеру 46296, читается через 2 запроса. Первый запрос записывает номер события.

from pymodbus.client.sync import ModbusSerialClient
from decoder import *

"""
Запросить сразу несколько полей - зон (если больше 8 - ответит ошибкой, так как сейчас всего 8 зон)
1:28:30 -> 02 03 9C 40 00 07 2B BF 
1:28:30 <- 02 03 0E 18 BC 18 BC C7 2F FA BB FB 00 6D BC 6D BC EC B7  [CRC OK]
"""


class S2000pp:

    def __init__(self):

        self.zone_count = 7
        self.address = 0x2
        self.port = "/dev/ttyUSB1"

        self.cl = ModbusSerialClient(port=self.port, method="rtu", stopbits=1, bytesize=8, parity='N', baudrate=9600)
        self.cl.connect()

    def get_initial_zone_state(self):
        # Запрос первой зоны Modbus = 40000 = 9c40
        zones = self.send_request(40000, self.zone_count)
        decoded_response = self.decode_response(zones)
        for zone_number in zone_descriptions.keys():
            print(f"{zone_descriptions[zone_number]}, {decoded_response[zone_number - 1][0]['short']}, {decoded_response[zone_number - 1][1]['short']}")

        return zones

    def send_request(self, register, count):
        # Starting add, num of reg to read, slave unit.
        # print(start, count, self.address)
        result = self.cl.read_holding_registers(register, count, unit=self.address)
        return result.registers

    def decode_response(self, data):
        results = []
        for element in data:
            hbyte = hex(element)[2:4]
            lbyte = hex(element)[4:]
            # print(element, hbyte, lbyte)
            results.append((result_codes[hbyte], result_codes[lbyte]))
        return results

    def parse_response(self):

        pass

    def get_log(self):
        # Самое новое событие
        print("Самое новое событие", end=" ")
        print(self.send_request(46160, 1))
        # Самое старое событие
        print("Самое старое событие", end=" ")
        print(self.send_request(46161, 1))
        # Количество событий
        print("Всего событий", end=" ")
        print(self.send_request(46162, 1))

        # Установка номера события
        print(self.send_request(46178, 11))
        # Запрос события
        print(self.send_request(46296, 11))
        return


if __name__ == "__main__":
    device = S2000pp()
    device.get_initial_zone_state()
    device.get_log()
