import ssd1306
from machine import I2C, Pin
from dht import DHT22
import time


i2c = I2C(sda=Pin(4), scl=Pin(5))       # SDA - D2, SCL - D1, 3.3v + G
display = ssd1306.SSD1306_I2C(128, 64, i2c)


def disp_t_h(t, h):
    display.fill(0)
    # display.text("Temp. : {} °C".format(t),0,0,1)
    display.text("Temp. : {} C".format(t), 0, 16, 1)
    display.text("Humid. : {} %".format(h), 0, 25, 1)
    display.text("Humid. : {} %".format(h), 0, 33, 1)
    display.show()


def oled_msg(msg):
    display.fill(0)
    if msg != '':
        display.text(msg,0,32,1)
    display.show()


def temp_humid():
    d = DHT22(Pin(16))
    d.measure()
    return d.temperature(), d.humidity()


def m():
    while True:
        try:
            time.sleep(2)
            t, h = temp_humid()
            disp_t_h(t, h)
        except KeyboardInterrupt:
            oled_msg('Power off in 3')
            time.sleep(1)
            oled_msg('Power off in 2')
            time.sleep(1)
            oled_msg('Power off in 1')
            time.sleep(1)
            oled_msg('')
            break
