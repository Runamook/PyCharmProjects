import machine
import os
import sys
import time
import utime
import gc
import onewire
import ds18x20
from boot import do_connect, do_disconnect


try:
    import urequests.urequests as ur
except ImportError:
    import urequests as ur


# TODO: make it async


class PulseDetector:
    disconnect = False              # Enable to periodically disconnect ESP from WiFi
    version = 0.6
    pulse_processed = False

    # LED logic is inverted - .on = LED off, .off = LED on
    led_pin = machine.Pin(2, machine.Pin.OUT)

    def __init__(self, pulse_pin, **kwargs):
        self.interval = kwargs.get('interval') or 300 * 1000  # How often to send data to server
        self.cache_file = kwargs.get('cache_file') or "default_cache.txt"
        self.reset_timer = kwargs.get('reset_timer') or 21600  # Timer to reset the board; 21600 = 6h
        self.pulse_pin = machine.Pin(pulse_pin, machine.Pin.IN, machine.Pin.PULL_UP)  # 5 = NodeMCU D1

        self.pulse_counter = self.use_cache('r', self.cache_file)
        self.report_status = "Never done"
        self.last_report = time.time()  # Time of the last report.

        # HTTP variables
        self.http_server, self.http_port, self.url_base = None, None, None

        # Temperature variables
        self.temp_adjustment = None
        self.ds_sensor = None
        self.ds_rom = None
        self.temp = None

    def set_temp_params(self, **kwargs):
        self.temp_adjustment = kwargs.get('temp_adjustment') or 0
        ds_pin = machine.Pin(kwargs.get('temp_sensor_pin'))
        self.ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
        ds_roms = self.ds_sensor.scan()
        if len(ds_roms) > 1:
            self.send_log('Error, more than one DS device found. I only can process one')
            raise
        elif len(ds_roms) < 1:
            self.send_log('Error, no DS devices found but temperature reading is enabled')
            raise
        self.ds_rom = ds_roms[0]
        print('Found DS device: ', self.ds_rom)

    def set_http_params(self, **kwargs):
        self.http_server = kwargs.get('http_server') or '192.168.5.11'  # Server IP
        self.http_port = kwargs.get('http_port') or 8080  # Server port
        self.url_base = kwargs.get('url_base') or 'http://{}:{}/metric'.format(self.http_server, self.http_port)

    def greeter(self):
        # Привет
        # self.blinker(".−−. .−. .. .−− . −")
        self.blinker("....")
        print('Starting pulse based monitoring v {}'.format(self.version))

        print("\nReporting every {} seconds\nCurrent counter: {}\nReload every {}\n".format(
            self.interval,
            self.pulse_counter,
            self.reset_timer
        ))

        if self.http_server:
            print("Report method: HTTP Server: {}:{}\n".format(
                self.http_server,
                self.http_port
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

    def get_temp(self):
        self.ds_sensor.convert_temp()
        time.sleep_ms(750)
        print(self.ds_sensor.read_temp(self.rom))


    def send_http(self, value):
        try:
            url = "{}/value/{}".format(self.url_base, value)
            self.send_log('Trying to send "{}" over HTTP to {}'.format(value, url))
            response = ur.get(url)
            if response.status_code == 200:

                # Reset cache and pending counter if data push was successful
                self.use_cache('w', self.cache_file, 0)
                self.pulse_counter = 0
                self.report_status = 'Success'
                return True
            else:
                self.report_status = 'Failure, status code {}'.format(response.status_code)
                return False
        except Exception as e:
            self.report_status = 'Failure, exception {}'.format(e)
            return False

    def get_temp(self):
        self.temp = self.ds_sensor.read_temp(self.ds_rom)
        self.ds_sensor.convert_temp()
        if self.temp_adjustment:
            self.temp += self.temp_adjustment

    def send_temp(self, value):
        try:
            url = "{}/temp/value/{}".format(self.url_base, value)
            self.send_log('Trying to send "{}" over HTTP to {}'.format(value, url))
            response = ur.get(url)
            if response.status_code != 200:
                self.report_status = 'Failure, status code {}'.format(response.status_code)
        except Exception as e:
            self.report_status = 'Failure, exception {}'.format(e)

    @staticmethod
    def send_log(log_string):
        gc.collect()
        mem_info = 'Free: {} Allocated: {}'.format(gc.mem_free(), gc.mem_alloc())
        (year, month, mday, hour, minute, second, weekday, yearday) = utime.localtime()
        _time = '[{}-{}-{} {}:{}:{} UTC-30min]'.format(mday, month, year, hour, minute, second)
        print('Version: {} {} {}: {}'.format(PulseDetector.version, mem_info, _time, log_string))

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

    @staticmethod
    def reset():
        # machine.reset()   # board crushes
        # sys.exit() # no code executed after by default
        pass

    def main(self):
        temp_timer = time.time()
        self.greeter()
        if PulseDetector.disconnect:
            do_disconnect()
        if not self.http_server:
            self.send_log('ERROR: No report method specified. Please select HTTP')
            return
        while True:
            if time.time() - temp_timer > 30:
                self.get_temp()
                temp_timer = time.time()
            if time.time() // self.reset_timer >= 1:
                self.reset()
            if time.time() - self.last_report > self.interval:
                try:
                    if PulseDetector.disconnect:
                        do_connect()
                    if self.http_server:
                        self.send_http(self.pulse_counter)
                    if self.temp:
                        self.send_temp(self.temp)
                    # Reset last report, so there is no blocking in case server is down
                    self.last_report = time.time()
                finally:
                    if PulseDetector.disconnect:
                        do_disconnect()
                    else:
                        pass

            if self.debouncer(self.pulse_pin):
                # Pulse detected, pulse is LOW
                self.led_pin.off()
                if not self.pulse_processed:
                    self.pulse_counter += 1
                    self.send_log(
                        'Current value: {}, Last Report: {}, Interval: {}, Last Report status: {}'.format(
                            self.pulse_counter, self.last_report, self.interval, self.report_status)
                    )
                    self.use_cache('w', self.cache_file, self.pulse_counter)
                    self.pulse_processed = True
            else:
                self.led_pin.on()
                self.pulse_processed = False
