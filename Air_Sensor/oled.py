from machine import Pin, I2C
import ssd1306
from time import sleep

# ESP32 Pin assignment
i2c = I2C(-1, scl=Pin(22), sda=Pin(21))

# ESP8266 Pin assignment
# i2c = I2C(-1, scl=Pin(5), sda=Pin(4))

oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

oled.text('Hello, World 1!', 0, 0)
oled.text('Hello, World 2!', 0, 10)
oled.text('Hello, World 3!', 0, 20)

oled.show()

oled.pixel(0, 0, 1)         # X, Y, color: 1 = white, 0 = black
oled.show()

# White Blue color 0.96 inch 128X64 OLED Display Module Yellow Blue OLED Display Module For arduino 0.96'' IIC SPI Communicate
# https://www.aliexpress.com/snapshot/0.html?spm=a2g0s.buyer_waiting_review.0.0.38dc6c1b9wIAZ3&orderId=5000780885148272&productId=32233334632


import ssd1306
from machine import I2C, Pin
from dht import DHT22
import time


i2c = I2C(sda=Pin(4), scl=Pin(5))
display = ssd1306.SSD1306_I2C(128, 64, i2c)


def disp_t_h(t, h):
    display.fill(0)
    display.text("Temparature: {}".format(t),0,0,1)
    display.text("Humidity: {}".format(h),0,32,1)
    display.show()


def temp_humid():
    d = DHT22(Pin(16))
    d.measure()
    return d.temperature(), d.humidity()


def m():
    while True:
        time.sleep(2)
        t, h = temp_humid()
        disp_t_h(t, h)