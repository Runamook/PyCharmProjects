# uos.dupterm(None, 1) # disable REPL on UART(0)
import gc
import webrepl


def do_connect():
    import network
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect('sasa', 'pass')
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())


# with open('webrepl_cfg.py', 'r') as f:
#     print(f.read())

do_connect()
webrepl.start()
gc.collect()

