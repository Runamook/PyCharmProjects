import machine
import os
import time
from umqtt.simple import MQTTClient

try:
    import urequests.urequests as ur
except ImportError:
    import urequests as ur


# TODO: Add wifi sleep
# TODO: Threading support

class HallSensor:
    pulse_processed = False
    last_report = 0  # Time of the last report. Should be zero
    cache_file = "hall_cache.txt"

    # LED logic is inverted - .on = off, .off = on
    led_pin = machine.Pin(2, machine.Pin.OUT)
    pulse_pin = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_UP)

    def __init__(self, **kwargs):
        self.http_server = kwargs.get('http_server') or '192.168.5.11'  # Server IP
        self.http_port = kwargs.get('http_port') or 8080  # Server port
        self.interval = kwargs.get('http_interval') or 300 * 1000  # How often to send data to server

        self.mqtt_client = kwargs.get('mqtt_client') or 'nodemcu_home'
        self.mqtt_server = kwargs.get('mqtt_server') or 'soldier.cloudmqtt.com'
        self.mqtt_port = kwargs.get('mqtt_port') or 14585
        self.mqtt_username = kwargs.get('mqtt_username') or 'fiwibpzw'
        self.mqtt_password = kwargs.get('mqtt_password') or '1JkIxUsIMZsA'

        self.hall_counter = self.use_cache('r', self.cache_file)

        # Привет
        self.blinker(".−−. .−. .. .−− . −")
        print('Starting hall sensor-based monitoring v 0.1')
        print("\n\nServer {}:{}\nInterval {}\nCurrent counter: {}".format(
            self.http_server,
            self.http_port,
            self.interval,
            self.hall_counter
        ))

    def blinker(self, sequence):
        # Logic is inverted: on = LED off, off = LED on
        self.led_pin.on()
        for i in sequence:
            self.led_pin.off()
            if i == '.':
                time.sleep(0.2)
            elif i == ' ':
                self.led_pin.on()
                time.sleep(0.3)
            else:
                time.sleep(0.1)
            self.led_pin.on()

    @staticmethod
    def debouncer(pin):
        if pin.value() == 1:
            return False
        else:
            time.sleep(0.02)
            result = 0
            for i in range(3):
                result += pin.value()
                time.sleep(0.01)
            return result == 0

    def send_http(self, value, temp):
        print('Trying to send "{}" over HTTP'.format(value))
        try:
            url = "http://{}:{}/metric/{}/value/{}".format(self.http_server, self.http_port, temp, value)
            response = ur.get(url)
            if response.status_code == 200:
                self.use_cache('w', self.cache_file, 0)
                return True
            else:
                return False
        except:
            return False

    def send_mqtt(self, value, temp):
        try:
            client = MQTTClient(
                client_id=self.mqtt_client,
                server=self.mqtt_server,
                port=self.mqtt_port,
                user=self.mqtt_username,
                password=self.mqtt_password)
            client.connect()
            client.publish('micropython/hall/{}'.format(temp), str(value))
            return True
        except:
            return False

    @staticmethod
    def use_cache(mode, filename, value=None):

        if mode == 'r':
            if filename not in os.listdir():
                return 0
            with open(filename, mode) as f:
                cached_val = f.read()
                if cached_val == '':
                    return 0
                else:
                    return int(cached_val)
        elif mode == 'w':
            with open(filename, mode) as f:
                f.write(str(value))
            return
        else:
            print('Wrong mode "{}", use "r" or "w"'.format(mode))
            raise KeyError

    def main(self):
        while True:
            if time.time() - self.last_report > self.interval:
                http_success = self.send_http(self.hall_counter, 'hall')

                if http_success:
                    self.hall_counter = 0
                    self.last_report = time.time()
                    # self.send_mqtt(self.hall_counter, 'hall')

            if self.debouncer(self.pulse_pin):
                # Pulse detected, pulse is LOW
                self.led_pin.off()
                if not self.pulse_processed:
                    self.hall_counter += 1
                    print('Current value: {}, Current time: {}, Last Report: {}, Interval: {}'.format(
                        self.hall_counter, time.time(), self.last_report, self.interval)
                    )
                    self.use_cache('w', self.cache_file, self.hall_counter)
                    self.pulse_processed = True
            else:
                self.led_pin.on()
                self.pulse_processed = False


my_agrs = {
    'http_interval': 120
}
m = HallSensor(**my_agrs)
m.main()
