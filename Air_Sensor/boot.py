# uos.dupterm(None, 1) # disable REPL on UART(0)
import gc
import webrepl
import time


def do_connect():
    start = time.ticks_ms()
    import network
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.ifconfig(('192.168.5.244', '255.255.255.0', '192.168.5.1', '1.1.1.1'))
        sta_if.connect('Azaza', 'razdvapoltora1215rrr33')
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())
    print('Connected to WiFi in {} ms'.format(time.ticks_ms() - start))


def do_disconnect():
    print('Disconnecting from the network')
    import network
    sta_if = network.WLAN(network.STA_IF)
    sta_if.disconnect()
    sta_if.active(False)


# with open('webrepl_cfg.py', 'r') as f:
#     print(f.read())

if __name__ == '__main__':
    do_connect()
    webrepl.start()
    gc.collect()
