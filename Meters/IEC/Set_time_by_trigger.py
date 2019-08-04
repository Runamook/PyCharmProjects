from pyzabbix.api import ZabbixAPI
from datetime import datetime as dt
from time import sleep
try:
    from .emhmeter import MeterBase, create_input_vars, logger, GetTime
except ModuleNotFoundError:
    from emhmeter import MeterBase, create_input_vars, logger, GetTime
try:
    from .Helpers.list_of_meters import list_of_meters_2 as list_of_meters
except ModuleNotFoundError:
    from Helpers.list_of_meters import list_of_meters_2 as list_of_meters

# Create ZabbixAPI class instance
zapi = ZabbixAPI(url='https://10.11.30.123/zabbix/', user='Admin', password='zabbix')

# Get all monitored hosts
result1 = zapi.host.get(monitored_hosts=1, output='extend')
result3 = zapi.application.get()
time_apps = []
for app in result3:
    if app['name'] == "Time":
        time_apps.append(app['applicationid'])

output = ["triggerid", "description", "lastchange"]
# Filter results
meters = list(filter(lambda x: "Meter" in x, [host['host'] for host in result1]))
meters_to_fix = dict()

for meter in meters:
    triggers = zapi.trigger.get(host=meter, only_true=1, applicationids=time_apps, output=output, expandDescription=1)
    if triggers:
        for trigger in triggers:
            epoch = dt.fromtimestamp(int(trigger['lastchange']))
            trigger['timestamp'] = epoch.strftime('%y-%m-%d %H:%M:%S')
            print(trigger)
            if "time is incorrect" in trigger["description"]:
                what = "time"
            elif "date is incorrect" in trigger["description"]:
                what = "date"
            else:
                print(f"Expecting 'time is incorrect' or 'date is incorrect'")
                raise ValueError
            meters_to_fix[meter.split()[1]]= what
            # {'triggerid': '20747', 'description': 'Meter 07777737 time is incorrect',
            # 'lastchange': '1564238630', 'timestamp': '19-07-27 17:43:50'}

# Logout from Zabbix
zapi.user.logout()


def fix_time(meter_data, what):
    logger.info(f"{meter_data}, fixing {what}")
    input_vars = create_input_vars(meter_data)["Time"]
    logger.info(f"{input_vars}")
    m = GetTime(input_vars)
    m.new_set(what)


for meter in list_of_meters:
    if meter.get("meterNumber") in meters_to_fix.keys():
        what = meters_to_fix[meter.get("meterNumber")]
        fix_time(meter, what)


# Meter 07777737
# API returns
# [{'triggerid': '20747', 'expression': '{24535}<>0', 'description': '{HOST.HOST} time is incorrect', 'url': '',
# 'status': '0', 'value': '1', 'priority': '3', 'lastchange': '1564238630', 'comments': '', 'error': '',
# 'templateid': '20713', 'type': '0', 'state': '0', 'flags': '0', 'recovery_mode': '0', 'recovery_expression': '',
# 'correlation_mode': '0', 'correlation_tag': '', 'manual_close': '1', 'details': ''}]
