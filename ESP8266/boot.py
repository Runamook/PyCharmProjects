# uos.dupterm(None, 1) # disable REPL on UART(0)
import gc
import webrepl
import time
import machine
import socket
import ntptime


# TODO: add ping/TCP check


def check_connection():
    """
    Check if network connectivity is working by sending DNS request
    :return: boolean
    """
    try:
        socket.getaddrinfo('google.com', 80)
        # DNS is working
        return True
    except OSError:
        # DNS not working
        return False


def do_connect():
    """
    Connect to WiFi.
    Reset the board until DNS is responding
    """
    connect_timeout = 5000
    start = time.ticks_ms()
    import network
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.ifconfig(('192.168.1.33', '255.255.255.0', '192.168.1.1', '1.1.1.1'))
        sta_if.connect('Home', 'niggagetyourownwifi')
        while not sta_if.isconnected():
            # If not connected in connect_timeout - hard reset board
            if time.ticks_ms() - start > connect_timeout:
                machine.reset()
            time.sleep(0.2)
            pass
    # Reset board if network connection is not working
    if not check_connection():
        machine.reset()
    ntptime.settime()
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
