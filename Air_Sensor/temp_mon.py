import machine
from dht import DHT22
from dht import DHT11
from time import sleep


def check(in_pin, dht_type):
    pin = machine.Pin(in_pin)
    if dht_type == 'dht22':
        d = DHT22(pin)
    else:
        d = DHT11(pin)
    d.measure()
    print("Temperature " + str(d.temperature()) + " C*")
    print("Humidity " + str(d.humidity()))


while True:
    check(16, 'dht22')
    sleep(5)
