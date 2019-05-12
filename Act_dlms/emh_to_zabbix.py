from Act_dlms.emhmeter import get_data_15
from multiprocessing.dummy import Pool
import requests
from pyzabbix import ZabbixMetric, ZabbixSender


# TODO: Add transforms


def get_json():
    url = "http://10.11.30.97:5000/api/meterpinginfo"
    response = requests.get(url)
    assert response.status_code == 200, self.logger.error("API responded %s, expected 200" % response.status_code)

    return response.json()


def create_metrics(data, meter_data):
    """
    data = {
    'table4': {'1557693253': [('21.25', '0.004'), (), (), ...)]},
    'p01': {'1558989000': [('1.5.0', '0.017'), (), (), ...)]}
            }

    ZabbixMetric('Zabbix server', 'WirkleistungP3[04690915]', 3, clock=1554851400))
    """
    zabbix_metrics = []
    metric_host = f"Meter {meter_data['meterNumber']}"

    for data_set in data:
        for metric_time in data_set:
            for metric_tuple in data_set[dt]:
                metric_key = metric_tuple[0]
                metric_value = metric_tuple[1]

                zabbix_metrics.append(ZabbixMetric(metric_host, metric_key, metric_value, clock=metric_time))

    return zabbix_metrics


def push_data(meter_data):
    """
    :param meter_data: {
    'meterNumber': '04682656',
    'manufacturer': 'EMH',
    'ip': '10.124.0.62',
    'installationDate': '2014-12-16T10:55:00',
    'isActive': True,
    'voltageRatio': 200,
    'currentRatio': 10,
    'totalFactor': 210
    }
    """

    data = get_data_15(meter_data["ip"])
    metrics = create_metrics(data, meter_data)
    sender = ZabbixSender(zabbix_server_ip)
    zabbix_response = sender.send(metrics)

    if zabbix_response.failed > 0 and zabbix_response.processed == 0:
        self.logger.error("Something went totally wrong, terminating\n%s" % zabbix_response)
        exit(1)
    elif zabbix_response.failed > 0 and zabbix_response.failed > zabbix_response.processed:
        self.logger.warning("More failures that successes %s" % zabbix_response)
    else:
        self.logger.warning("Result %s" % zabbix_response)
    return


def meta_15():
    pool = Pool(32)
    list_of_meters = get_json()
    pool.map(push_data, list_of_meters)


if __name__ == "__main__":
    meta_15()
