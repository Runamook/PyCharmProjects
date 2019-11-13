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
# PM2.5 rankings
aqi = dict()
aqi['good'] = (0, 50)
aqi['moderate'] = (51, 100)
aqi['unhealthy_for_sensetive'] = (101, 150)
aqi['unhealthy'] = (151, 200)
aqi['very_unhealthy'] = (201, 300)
aqi['hazardous'] = (301, 500)


def get_pm(hb, lb):
    # PM2.5 (mkg/m3) = pm25hb * 256 + pm25lb/10
    # PM10 (mkg/m3) = pm10hb * 256 + pm10lb/10

    return hb * 256 + lb / 10


def decoder(message):
    """
        :param message: b'\xaa\xc0Y\x00\x98\x00\xfb\x16\x02\xab'
        :return:
        """

    pm25lb = message[2]
    pm25hb = message[3]
    pm10lb = message[4]
    pm10hb = message[5]

    pm10 = get_pm(pm10hb, pm10lb)
    pm25 = get_pm(pm25hb, pm25lb)

    return f"PM10 = {pm10} mkg/m3, PM2.5 = {pm25} mkg/m3"


for i in range(1000):
    x = ser.read_all()
    if x != b'':
        print(decoder(x))
        time.sleep(1)
    else:
        time.sleep(1)
        pass

