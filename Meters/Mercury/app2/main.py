import serial
import time

try:
    import Mercury.app2.mercury as mercury
except ImportError:
    import mercury as mercury

serialPort = serial.Serial(port='/dev/ttyUSB0',
                           baudrate=9600,
                           timeout=1,
                           parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE,
                           bytesize=serial.EIGHTBITS
                           )
x = 1
serialPort.flushInput()
serialPort.flush()

netAdr = '174'
while x != 0:
    print(mercury.getDataFromCounter(netAdr, serialPort))
    time.sleep(2)

serialPort.close()
