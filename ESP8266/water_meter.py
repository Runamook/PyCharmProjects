import machine
import os
import utime as time
try:
    import urequests.urequests as ur
except:
    import urequests as ur

# TODO: Add wifi sleep
# TODO: Add file cache, in case ESP is shutdown before it sent the values


# Variables setup START
led_pin = machine.Pin(2, machine.Pin.OUT)
pulse_pin_1 = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_UP)
pulse_pin_2 = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)

http_server = "192.168.5.11"        # Server IP
http_port = 8080                    # Server port
interval = 900 * 1000               # How often to send data to server

cold_pulse_processed = False
hot_pulse_processed = False
cold_last_report = 0                     # Should be zero
hot_last_report = 0                     # Should be zero
cold_cache_file = "cold_cache.txt"
hot_cache_file = "warm_cache.txt"

# Variables setup END

# esp.sleep_type(2)

"""
def http_get(url):
    # url = "http://192.168.5.11:8080/var/metric"
    _, _, host, path = url.split('/', 3)
    host, port = host.split(':')
    addr = socket.getaddrinfo(host, int(port))[0][-1]
    s = socket.socket()
    s.connect(addr)
    s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n' % (path, host), 'utf8'))
    result = b""
    while True:
        data = s.recv(100)
        if data:
            result += data
        else:
            break
    s.close()
    result = str(result, 'utf8')
    result_code = result.split()[1]
    if result_code in (301, 302):
        # http_get(new_url)
        pass
    return result, result_code
"""


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


def send_http(value, temp):
    url = "http://{}:{}/metric/{}/value/{}".format(http_server, http_port, temp, value)
    response = ur.get(url)
    if response.status_code == 200:
        use_cache('w', cold_cache_file, 0)
        return True
    else:
        return False


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
        print('Wrong mode {}, use "r" or "w"'.format(mode))
        raise KeyError


cold_water_counter = use_cache('r', cold_cache_file)
hot_water_counter = use_cache('r', hot_cache_file)


while True:
    if time.time() - cold_last_report > interval:
        if send_http(cold_water_counter, 'cold'):
            # send_http() should return False if unable to send the value
            cold_water_counter = 0
            cold_last_report = time.time()

    if time.time() - hot_last_report > interval:
        if send_http(hot_water_counter, 'hot'):
            # send_http() should return False if unable to send the value
            hot_water_counter = 0
            hot_last_report = time.time()

    if debouncer(pulse_pin_1):
        # Pulse detected, pulse is LOW
        led_pin.on()
        if not cold_pulse_processed:
            cold_water_counter += 1
            use_cache('w', cold_cache_file, cold_water_counter)
            cold_pulse_processed = True
    else:
        led_pin.off()
        cold_pulse_processed = False

    if debouncer(pulse_pin_2):
        # Pulse detected, pulse is LOW
        led_pin.on()
        if not hot_pulse_processed:
            hot_water_counter += 1
            use_cache('w', hot_cache_file, hot_water_counter)
            hot_pulse_processed = True
    else:
        led_pin.off()
        hot_pulse_processed = False
