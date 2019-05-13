from Act_dlms.emhmeter import get_data_15
from multiprocessing.dummy import Pool
import requests
from pyzabbix import ZabbixMetric, ZabbixSender
from Act_dlms.Helpers.create_logger import create_logger

# TODO: Add transforms


logger = create_logger("/var/log/emh_to_zabbix.log", "MainApp", loglevel="INFO")


def get_json():
    url = "http://10.11.30.97:5000/api/meterpinginfo"
    logger.debug(f"Connecting to {url}")
    response = requests.get(url)
    assert response.status_code == 200, logger.error("API responded %s, expected 200" % response.status_code)
    # assert response.status_code == 200, f"API responded {response.status_code}, expected 200"
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
            for metric_tuple in data_set[metric_time]:
                metric_key = metric_tuple[0]
                metric_value = metric_tuple[1]

                zabbix_metrics.append(ZabbixMetric(metric_host, metric_key, metric_value, clock=metric_time))

    return zabbix_metrics


def push_data(meter_data):
    """
    meter_data: {
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
    # sender = ZabbixSender(zabbix_server_ip)
    sender = ZabbixSender("127.0.0.1")
    zabbix_response = sender.send(metrics)

    if zabbix_response.failed > 0 and zabbix_response.processed == 0:
        # self.logger.error("Something went totally wrong, terminating\n%s" % zabbix_response)
        print(f"Something went totally wrong, terminating\n{zabbix_response}")
        exit(1)
    elif zabbix_response.failed > 0 and zabbix_response.failed > zabbix_response.processed:
        # self.logger.warning("More failures that successes %s" % zabbix_response)
        print(f"More failures that successes {zabbix_response}")
    else:
        # self.logger.warning("Result %s" % zabbix_response)
        print(f"Result {zabbix_response}")
    return


def meta_15():
    logger.info(f"Starting app")
    pool = Pool(16)
    # list_of_meters = get_json()
    list_of_meters = {
        "meterNumber":"05296170",
        "manufacturer":"EMH",
        "ip":"10.124.2.120",
        "installationDate":"2019-02-20T09:00:00",
        "isActive":True,
        "voltageRatio":200,
        "currentRatio":15,
        "totalFactor":215
    }
    logger.debug(f"Found {len(list_of_meters)} meters")
    pool.map(push_data, list_of_meters)


if __name__ == "__main__":
    meta_15()
