from machine import UART, Pin
import time
import sds011
import uos
from dht import DHT22


class Meters:

    warmup_time = 30
    pause_time = 300
    cycle = 10

    def __init__(self, dht_pin, uart_no, **kwargs):
        self._dht_sensor = DHT22(Pin(dht_pin))
        self._temperature = None
        self._humidity = None
        self._p25 = 0
        self._p10 = 0
        self.warm_up_started = False
        self.warm_up_start_time = 0
        self.pause_started = False
        self.pause_start_time = 0

        if uart_no == 0:
            # disable REPL on UART(0)
            uos.dupterm(None, 1)
        uart = UART(uart_no, baudrate=9600)
        uart.init(timeout=1, baudrate=9600)
        self._dust_sensor = sds011.SDS011(uart)

        self.screen_present = kwargs.get('screen_present') or False
        if self.screen_present:
            self.oled = None
            self.init_oled(128, 64)

    def report_http(self):
        pass

    @property
    def temperature(self):
        return self._temperature

    @property
    def humidity(self):
        return self._humidity

    @property
    def p10(self):
        return self._p10

    @property
    def p25(self):
        return self._p25

    def init_oled(self, oled_w, oled_h):
        import ssd1306
        from machine import I2C
        i2c = I2C(sda=Pin(4), scl=Pin(5))              # SDA - D2, SCL - D1, 3.3v + G
        self.oled = ssd1306.SSD1306_I2C(oled_w, oled_h, i2c)

    def write_oled(self):
        self.oled.fill(0)
        self.oled.text("P10 {}  P25 {}".format(self._p10, self._p25), 0, 0, 1)
        self.oled.text("Humid. : {} %".format(self._humidity), 0, 24, 1)
        self.oled.text("Temp. : {} C".format(self._temperature), 0, 40, 1)
        self.oled.show()

    def update_temp_humid(self):
        self._dht_sensor.measure()
        self._temperature = self._dht_sensor.temperature()
        self._humidity = self._dht_sensor.humidity()

    def represent(self):
        print('{} {} {}'.format('=' * 30, time.time(), '=' * 30))
        print('T: {}C, H: {}%'.format(self._temperature, self._humidity))
        print('PM25: {}, PM10: {}'.format(self._p25, self._p10))
        if self.screen_present:
            self.write_oled()

    def init(self):
        # time.sleep(1)
        # self._dust_sensor.wake()
        time.sleep(self.cycle)
        self._dust_sensor.sleep()
        # time.sleep(self.cycle)
        # self._dust_sensor.sleep()

    def main_loop(self):
        self._dust_sensor.sleep()
        time.sleep(self.cycle)
        self._dust_sensor.sleep()
        while True:
            self.represent()

            # DHT22 позволяет считывать показания раз в 2 секунды
            time.sleep(self.cycle)
            self.update_temp_humid()
            print('DEBUG: Now = {}, pause ends at {}, warmup start time = {}, warmup = {}'
                  .format(time.time(), (self.pause_start_time + self.pause_time), self.warm_up_start_time, self.warm_up_started))

            if self.pause_start_time + Meters.pause_time > time.time():
                print('DEBUG: Pause loop')
                # Идет перерыв, не взаимодействуем с сенсором
                continue
            else:
                print('DEBUG: Warmup loop')
                # Перерыв закончился
                if not self.warm_up_started:
                    # Прогрев не начинался, стартуем
                    self._dust_sensor.wake()
                    self.warm_up_started = True
                    self.warm_up_start_time = time.time()
                    continue
                if time.time() > self.warm_up_start_time + Meters.warmup_time:
                    # Сенсор достаточно прогрет, можно читать
                    status = self._dust_sensor.read()
                    # time.sleep(0.5)
                    pkt_status = self._dust_sensor.packet_status
                    time.sleep(0.5)

                    self._dust_sensor.sleep()
                    if status is False:
                        print('ERROR: {}: Measurement failed'.format(time.time()))
                    elif pkt_status is False:
                        print('ERROR: {}: Received corrupted data'.format(time.time()))
                    else:
                        self._p10 = self._dust_sensor.pm10
                        self._p25 = self._dust_sensor.pm25
                    self.warm_up_started = False
                    self.pause_start_time = time.time()


if __name__ == '__main__':
    # measure()
    extra_args = {
        'screen_present': True
    }
    meters = Meters(16, 0, **extra_args)
    meters.main_loop()

