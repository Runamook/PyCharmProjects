import machine
import os
import utime as time
from umqtt.simple import MQTTClient
try:
    import urequests.urequests as ur
except:
    import urequests as ur


# TODO: Add wifi sleep
# TODO: Threading support

class WaterMeter:
    cold_pulse_processed = False
    hot_pulse_processed = False
    cold_last_report = 0  # Should be zero
    hot_last_report = 0  # Should be zero
    cold_cache_file = "cold_cache.txt"
    hot_cache_file = "warm_cache.txt"

    led_pin = machine.Pin(2, machine.Pin.OUT)
    pulse_pin_cold = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_UP)
    pulse_pin_hot = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)

    def __init__(self, **kwargs):
        self.http_server = kwargs.get('http_server') or '192.168.5.11'  # Server IP
        self.http_port = kwargs.get('http_port') or 8080  # Server port
        self.interval = kwargs.get('http_interval') or 900  # How often to send data to server

        self.mqtt_client = kwargs.get('mqtt_client') or 'nodemcu_home'
        self.mqtt_server = kwargs.get('mqtt_server') or 'soldier.cloudmqtt.com'
        self.mqtt_port = kwargs.get('mqtt_port') or 14585
        self.mqtt_username = kwargs.get('mqtt_username') or 'fiwibpzw'
        self.mqtt_password = kwargs.get('mqtt_password') or '1JkIxUsIMZsA'

        self.cold_water_counter = self.use_cache('r', WaterMeter.cold_cache_file)
        self.hot_water_counter = self.use_cache('r', WaterMeter.hot_cache_file)

        # esp.sleep_type(2)

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
            url = "http://{}:{}/metric/{}/value/{}".format(self.http_server, self.http_port, temp, value)
            response = ur.get(url)
            print("HTTP response {}".format(response.status_code))
            if int(response.status_code) == 200:
                if temp == 'cold':
                    WaterMeter.use_cache('w', WaterMeter.cold_cache_file, 0)
                if temp == 'hot':
                    WaterMeter.use_cache('w', WaterMeter.hot_cache_file, 0)
                return True
            else:
                return False
        except Exception as e:
            print(e)
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
            client.publish('micropython/water/{}'.format(temp), str(value))
            print("Successfully sent MQTT report")
            return True
        except:
            print("Error while sending {} over MQTT".format(value))
            return False

    @staticmethod
    def use_cache(mode, filename, value=None):

        if mode == 'r':
            if filename not in os.listdir():
                return 0
            with open(filename, mode) as f:
                result = f.read()
                if result == '':
                    return 0
                else:
                    return int(result)
        elif mode == 'w':
            with open(filename, mode) as f:
                f.write('{}'.format(value))
            return
        else:
            print('Wrong mode {}, use "r" or "w"'.format(mode))
            raise KeyError

    def main(self):
        print("Starting app")
        while True:
            try:
                if time.time() - WaterMeter.cold_last_report > self.interval:
                    print("Sending cold report")
                    if self.send_http(self.cold_water_counter, 'cold'):
                        # send_http() should return False if unable to send the value
                        self.send_mqtt(self.cold_water_counter, 'cold')
                        self.cold_water_counter = 0
                        WaterMeter.cold_last_report = time.time()

                """
                if time.time() - WaterMeter.hot_last_report > self.interval:
                    if self.send_http(self.hot_water_counter, 'hot'):
                        # send_http() should return False if unable to send the value
                        self.hot_water_counter = 0
                        self.send_mqtt(self.hot_water_counter, 'hot')
                        WaterMeter.hot_last_report = time.time()
                """

                if WaterMeter.debouncer(self.pulse_pin_cold):
                    # Pulse detected, pulse is LOW
                    self.led_pin.on()
                    if not self.cold_pulse_processed:
                        self.cold_water_counter += 1
                        self.use_cache('w', WaterMeter.cold_cache_file, self.cold_water_counter)
                        self.cold_pulse_processed = True
                else:
                    self.led_pin.off()
                    self.cold_pulse_processed = False
            except KeyboardInterrupt:
                print("Interrupted by keyboard")
                break


kwargs = {'http_interval': 100}

m = WaterMeter(**kwargs)
m.main()
