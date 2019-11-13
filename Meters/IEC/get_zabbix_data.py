from pyzabbix.api import ZabbixAPI
import sys
import time


username = sys.argv[1]
password = sys.argv[2]

# Create ZabbixAPI class instance
zapi = ZabbixAPI(url='https://10.11.30.123/zabbix/', user=username, password=password)

# Get all monitored hosts
result1 = zapi.host.get(output='extend')

for meter in result1:
    result2 = zapi.item.get(hostids=meter['hostid'], application='Table4')
    # items = [meter['itemid'] for meter in result2]
    for item in result2:
        hist = zapi.history.get(output='extend',
                                itemids=item['itemid'],
                                history=0,
                                limit=1,
                                sortfield='clock',
                                sortorder='DESC')
        if hist != []:
            ts = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime(int(hist[0]['clock'])))
            print(meter['name'], item['name'], ts, '       ', hist[0]['value'])
