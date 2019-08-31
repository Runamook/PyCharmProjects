"""

import network

sta_if = network.WLAN(network.STA_IF); sta_if.active(True)
sta_if.scan()                             # Scan for available access points
sta_if.connect("<AP_name>", "<password>") # Connect to an AP
sta_if.isconnected()                      # Check for successful connection
# Change name/password of ESP8266's AP:
ap_if = network.WLAN(network.AP_IF)
ap_if.config(essid="<AP_NAME>", authmode=network.AUTH_WPA_WPA2_PSK, password="<password>")

"""
import machine
import time

pin = machine.Pin(2, machine.Pin.OUT)


def dot_show():
    pin.off()
    time.sleep(1)
    pin.on()


def dash_show():
    pin.off()
    time.sleep(2)
    pin.on()


Hello_world = '**** * *-** *-** ---    *-- --- *-* *-** -**'

for i in Hello_world:
    if i == "*":
        dot_show()
    elif i == '-':
        dash_show()
    else:
        time.sleep(3)
    time.sleep(0.5)


