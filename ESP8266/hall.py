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
    last_report = 0  # Should be zero
    cache_file = "hall_cache.txt"

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
        try:
            url = "http://{}:{}/metric/{}/value/{}".format(self.http_server, self.http_port, hall, value)
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
                return int(f.read(value))
        elif mode == 'w':
            with open(filename, mode) as f:
                f.write(value)
            return
        else:
            print('Wrong mode "{}", use "r" or "w"'.format(mode))
            raise KeyError

    def main(self):
        while True:
            if time.time() - self.last_report > self.interval:
                http_success = self.send_http(self.hall_counter, 'hall')
                # send_http() should return False if unable to send the value

                if http_success:
                    self.hall_counter = 0
                    self.last_report = time.time()
                    # self.send_mqtt(self.hall_counter, 'hall')

            if self.debouncer(self.pulse_pin):
                # Pulse detected, pulse is LOW
                self.led_pin.on()
                if not self.pulse_processed:
                    self.hall_counter += 1
                    self.use_cache('w', self.cache_file, self.hall_counter)
                    self.pulse_processed = True
            else:
                self.led_pin.off()
                self.pulse_processed = False


m = HallSensor()
m.main()
