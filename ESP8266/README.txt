### AP

>>> import network
>>> ap_if = network.WLAN(network.AP_IF)
>>> ap_if.isconnected
<bound_method>
>>> ap_if.isconnected()
False
>>> ap_if.active()
True
>>> dir(ap_if)
['__class__', 'active', 'config', 'connect', 'disconnect', 'ifconfig', 'isconnected', 'scan', 'status']
>>> ap_if.status()
-1
>>> ap_if.ifconfig()
('192.168.4.1', '255.255.255.0', '192.168.4.1', '208.67.222.222')



### Station


>>> sta_if = network.WLAN(network.STA_IF)
>>> sta_if.active()
False
>>> sta_if.active(True)
#5 ets_task(4020f4d8, 28, 3fff95d0, 10)
>>> sta_if.connect('Azaza','niggagetyourown')
>>> sta_if.isconnected()
True
>>> dir(sta_if)
['__class__', 'active', 'config', 'connect', 'disconnect', 'ifconfig', 'isconnected', 'scan', 'status']
>>> sta_if.status()
5
>>> sta_if.ifconfig()
('192.168.5.35', '255.255.255.0', '192.168.5.1', '192.168.5.11')
>>>


"""
webrepl_cfg/py

"PASS = 'p01emhpas'\n"
"""

"""
improt os
os.listdir()
"""