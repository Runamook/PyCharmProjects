from breezart import Vent
from pyzabbix import ZabbixMetric, ZabbixSender
import argparse
import time


def parser(in_data, host):
    # ZabbixMetric(host, key, value, time)
    # ZabbixMetric('Zabbix server', 'WirkleistungP3[04690915]', 3, clock=1554851400))

    zmetrics = []
    vent_data = in_data
    zmetrics.append(ZabbixMetric(host, 'Temperature.Current', vent_data['Temperature']['Current']))
    zmetrics.append(ZabbixMetric(host, 'Temperature.Target', vent_data['Temperature']['Target']))
    zmetrics.append(ZabbixMetric(host, 'Temperature.Minimum', vent_data['Temperature']['Minimum']))
    zmetrics.append(ZabbixMetric(host, 'Humidity.Mode', vent_data['Humidity']['Mode']))
    zmetrics.append(ZabbixMetric(host, 'Humidity.Auto', vent_data['Humidity']['Auto']))
    zmetrics.append(ZabbixMetric(host, 'Humidity.Current', vent_data['Humidity']['Current']))
    zmetrics.append(ZabbixMetric(host, 'Humidity.Target', vent_data['Humidity']['Target']))
    zmetrics.append(ZabbixMetric(host, 'Speed.SpeedIsDown', vent_data['Speed']['SpeedIsDown']))
    zmetrics.append(ZabbixMetric(host, 'Speed.Current', vent_data['Speed']['Current']))
    zmetrics.append(ZabbixMetric(host, 'Speed.Target', vent_data['Speed']['Target']))
    zmetrics.append(ZabbixMetric(host, 'Speed.Actual', vent_data['Speed']['Actual']))
    zmetrics.append(ZabbixMetric(host, 'Scene.Block', vent_data['Scene']['Block']))
    zmetrics.append(ZabbixMetric(host, 'Scene.SceneState', vent_data['Scene']['SceneState']))
    zmetrics.append(ZabbixMetric(host, 'Scene.Number', vent_data['Scene']['Number']))
    zmetrics.append(ZabbixMetric(host, 'Scene.WhoActivate', vent_data['Scene']['WhoActivate']))
    zmetrics.append(ZabbixMetric(host, 'Settings.Mode', vent_data['Settings']['Mode']))
    zmetrics.append(ZabbixMetric(host, 'State.Power', vent_data['State']['Power']))
    zmetrics.append(ZabbixMetric(host, 'State.Warning', vent_data['State']['Warning']))
    zmetrics.append(ZabbixMetric(host, 'State.Critical', vent_data['State']['Critical']))
    zmetrics.append(ZabbixMetric(host, 'State.Overheat', vent_data['State']['Overheat']))
    zmetrics.append(ZabbixMetric(host, 'State.AutoOff', vent_data['State']['AutoOff']))
    zmetrics.append(ZabbixMetric(host, 'State.ChangeFilter', vent_data['State']['ChangeFilter']))
    zmetrics.append(ZabbixMetric(host, 'State.AutoRestart', vent_data['State']['AutoRestart']))
    zmetrics.append(ZabbixMetric(host, 'State.Comfort', vent_data['State']['Comfort']))
    zmetrics.append(ZabbixMetric(host, 'State.PowerBlock', vent_data['State']['PowerBlock']))
    zmetrics.append(ZabbixMetric(host, 'State.Unit', vent_data['State']['Unit']))
    zmetrics.append(ZabbixMetric(host, 'State.Mode', vent_data['State']['Mode']))
    zmetrics.append(ZabbixMetric(host, 'State.IconHF', vent_data['State']['IconHF']))
    zmetrics.append(ZabbixMetric(host, 'State.ColorMsg', vent_data['State']['ColorMsg']))
    zmetrics.append(ZabbixMetric(host, 'State.ColorInd', vent_data['State']['ColorInd']))
    zmetrics.append(ZabbixMetric(host, 'State.FilterDust', vent_data['State']['FilterDust']))
    zmetrics.append(ZabbixMetric(host, 'Msg', vent_data['Msg']))

    return zmetrics


def main(vent_machine, zabbix_ip, zabbix_host, interval):

    zsender = ZabbixSender(zabbix_ip)

    while True:
        vent_machine.get_vent_status()
        zmetrics = parser(vent_machine.status, zabbix_host)
        print(zmetrics)
        zresponse = zsender.send(zmetrics)
        print(zresponse)
        time.sleep(interval)


if __name__ == '__main__':
    optparser = argparse.ArgumentParser(description="Breezart vent machine integration to Zabbix")
    requiredNamed = optparser.add_argument_group('Required arguments')
    optparser.add_argument("--debug", type=str, help="Debug mode True/False")
    optparser.add_argument("--query_interval", type=int, help="How often to send queries")
    optparser.add_argument("--port", type=int, help="TPD283 TCP port")
    requiredNamed.add_argument("--ip", type=str, help="TPD283 IP address", required=True)
    requiredNamed.add_argument("--password", type=int, help="TPD283 password", required=True)
    requiredNamed.add_argument("--zabbix_ip", type=str, help="Zabbix server IP", required=True)
    requiredNamed.add_argument("--zabbix_host", type=str, help="Vent host name in Zabbix configuration", required=True)

    args = optparser.parse_args()
    data = dict()

    if not args.debug:
        debug = False
    elif args.debug == 'False':
        debug = False
    elif args.debug == 'True':
        data['debug'] = True
    else:
        print(f'Wrong debug key {args.debug}, please select True/False')

    if not args.query_interval:
        query_interval = 5
    else:
        query_interval = args.query_interval

    if not args.port:
        port = None
    else:
        data['port'] = args.port

    data['ip'] = args.ip
    data['password'] = args.password
    my_vent = Vent(**data)

    main(my_vent, args.zabbix_ip, args.zabbix_host, query_interval)
