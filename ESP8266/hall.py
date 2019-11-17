import machine
import os
import time
from umqtt.simple import MQTTClient
import network

try:
    import urequests.urequests as ur
except ImportError:
    import urequests as ur


# TODO: Add wifi sleep
# TODO: Threading support

class HallSensor:
    version = 0.2
    pulse_processed = False
    last_report = 0  # Time of the last report. Should be zero
    cache_file = "hall_cache.txt"
    gas_value_init = 10000

    # LED logic is inverted - .on = off, .off = on
    led_pin = machine.Pin(2, machine.Pin.OUT)
    pulse_pin = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_UP)  # NodeMCU D1

    def __init__(self, **kwargs):
        self.http_server = kwargs.get('http_server') or '192.168.5.11'  # Server IP
        self.http_port = kwargs.get('http_port') or 8080  # Server port
        self.interval = kwargs.get('http_interval') or 300 * 1000  # How often to send data to server

        self.mqtt_client = kwargs.get('mqtt_client') or 'nodemcu_home'
        self.mqtt_server = kwargs.get('mqtt_server') or 'soldier.cloudmqtt.com'
        self.mqtt_port = kwargs.get('mqtt_port') or 14585
        self.mqtt_username = kwargs.get('mqtt_username') or 'aaa'
        self.mqtt_password = kwargs.get('mqtt_password') or 'sss'

        self.hall_counter = self.use_cache('r', self.cache_file)
        self.report_status = "Never done"

        # Привет
        self.blinker(".−−. .−. .. .−− . −")
        print('Starting hall sensor-based monitoring v 0.1')
        print("\nServer {}:{}\nReporting every {} seconds\nCurrent counter: {}\n".format(
            self.http_server,
            self.http_port,
            self.interval,
            self.hall_counter
        ))

    def blinker(self, sequence):
        # Logic is inverted: on = LED off, off = LED on
        self.led_pin.on()  # OFF
        for i in sequence:
            self.led_pin.off()  # ON
            if i == '.':
                time.sleep(0.1)
            elif i == ' ':
                self.led_pin.on()  # OFF
                time.sleep(0.3)
            else:
                time.sleep(0.2)
            self.led_pin.on()  # OFF

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
        gas_value = int(value) + HallSensor.gas_value_init
        self.send_log('Trying to send "{}" over HTTP'.format(gas_value))
        try:
            url = "http://{}:{}/metric/{}/value/{}".format(self.http_server, self.http_port, temp, gas_value)
            response = ur.get(url)
            if response.status_code == 200:

                # Reset cache and pending counter if data push was successful
                self.use_cache('w', self.cache_file, 0)
                self.hall_counter = 0
                self.report_status = 'Success'
                return True
            else:
                self.report_status = 'Failure, status code {}'.format(response.status_code)
                return False
        except Exception as e:
            self.report_status = 'Failure, exception {}'.format(e)
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
    def send_log(log_string):
        print('Version: {} Time: {} {}'.format(HallSensor.version, time.time(), log_string))

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

                # Reset last report, so there is no blocking in case server is down
                self.last_report = time.time()

                """
                if http_success:
                    self.send_mqtt(self.hall_counter, 'hall')
                """

            if self.debouncer(self.pulse_pin):
                # Pulse detected, pulse is LOW
                self.led_pin.off()
                if not self.pulse_processed:
                    self.hall_counter += 1
                    self.send_log(
                        'Current value: {}, Last Report: {}, Interval: {}, Last Report status: {}'.format(
                            self.hall_counter, self.last_report, self.interval, self.report_status)
                    )
                    self.use_cache('w', self.cache_file, self.hall_counter)
                    self.pulse_processed = True
            else:
                self.led_pin.on()
                self.pulse_processed = False


my_agrs = {
    'http_interval': 120,
    'http_server': '192.168.1.79'
}

m = HallSensor(**my_agrs)
m.main()
