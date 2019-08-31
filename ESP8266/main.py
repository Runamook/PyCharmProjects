import socket
import machine

html = """<!DOCTYPE html>
<html>
<head> <title> ESP8266 Controller </title> </head>
<form>
<H1>ESP8266 Controller</H1>
<button name="LED" value="ON" type="submit">ON</button><br>
<button name="LED" value="OFF" type="submit">OFF</button>
</form>
</html>
"""

pin = machine.Pin(2, machine.Pin.OUT)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)
while True:

    conn, addr = s.accept()
    print("Connected with " + str(addr))
    request = conn.recv(1024)
    request = str(request)
    print(request)
    LEDON = request.find('/?LED=ON')
    LEDOFF = request.find('/?LED=OFF')

    if LEDON == 6:
        print('TURN LED0 ON')
        pin.off()
    if LEDOFF == 6:
        print('TURN LED0 OFF')
        pin.on()
    response = html
    conn.send(response)
    conn.close()
