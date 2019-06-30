import datetime
from pyzabbix import ZabbixMetric, ZabbixSender

zabbix_server = 'zproxy1.zvez.ga'
zabbix_host = 'Apt-Meters'
metric_key = 'coldWater'
water_multiplicator = 10


def application(environ, start_response):
    # lines = []
    # for key, value in environ.items():
    #    lines.append("%s: %r" % (key, value))
    # output = b'hello world from wsgi!'
    # output = " ".join(lines).encode()

    # /metric/value/0
    uri = environ['REQUEST_URI']
    value = uri.split("/")[-1]

    status, output = meta(value)

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]


def make_metrics(value):

    value = str(int(value) * water_multiplicator)
    # ZabbixMetric('Zabbix server', 'WirkleistungP3[04690915]', 3, clock=1554851400))

    results = []
    dt = int(datetime.datetime.now().strftime("%s"))
    # print("Pushing %s %s %s %s" % (zabbix_host, metric_key, value, str(dt)))
    results.append(ZabbixMetric(zabbix_host, metric_key, value, clock=dt))
    return results


def send_metrics(metrics):
    sender = ZabbixSender(zabbix_server)
    zabbix_response = sender.send(metrics)
    if zabbix_response.failed > 0:
        print("Failure: Result %s, Server: %s Host: %s Metric: %s" % (
            zabbix_response, zabbix_server, zabbix_host, metric_key))
        return "500 Internal Server Error", "Processing error".encode()
    else:
        print("OK: Result %s" % zabbix_response)
        return "200 OK", "Success".encode()


def meta(value):
    metrics = make_metrics(value)
    return send_metrics(metrics)
