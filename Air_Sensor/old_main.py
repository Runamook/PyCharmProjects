# This works with PC based UART and regular python

import time
import serial

ser = serial.Serial(
    port='/dev/ttyUSB0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=None
)

# https://www.airnow.gov/index.cfm?action=aqibasics.aqi
# https://en.wikipedia.org/wiki/Air_quality_index
# PM2.5 rankings
caqi = dict()
caqi['Very low'] = (0, 15)
caqi['Low'] = (15, 30)
caqi['Medium'] = (30, 55)
caqi['Hugh'] = (55, 110)
caqi['Very high'] = (110, 1000)


def get_pm(hb, lb):
    # PM2.5 (mkg/m3) = pm25hb * 256 + pm25lb/10
    # PM10 (mkg/m3) = pm10hb * 256 + pm10lb/10

    return hb * 256 + lb / 10


def decoder(message):
    """
        :param message: b'\xaa\xc0Y\x00\x98\x00\xfb\x16\x02\xab'
        :return:
        """

    header = message[0]
    commander_no = message[1]
    pm25lb = message[2]
    pm25hb = message[3]
    pm10lb = message[4]
    pm10hb = message[5]
    id1 = message[6]
    id2 = message[7]
    checksum = message[8]               # message[2] + ... + message[7]
    tail = message[9]

    pm10 = float(get_pm(pm10hb, pm10lb))
    pm25 = float(get_pm(pm25hb, pm25lb))

    # return f"PM10 = {pm10} mkg/m3, PM2.5 = {pm25} mkg/m3"
    return pm10, pm25


for i in range(1000):
    time.sleep(1)               # First measurement is always b''
    x = ser.read_all()
    if x != b'':
        pm10, pm25 = decoder(x)
        if pm10 > 999 or pm25 > 999:                  # 999 is sensor limit
            print(f'Value to high, must be an error. Raw value {x}, decoded PM10 {pm10}, PM2.5 {pm25}')
        print(f"PM10 = {pm10} mkg/m3, PM2.5 = {pm25} mkg/m3")
    else:
        print('No data returned')
        pass

