import datetime
from pyzabbix import ZabbixMetric, ZabbixSender
from sqlalchemy import create_engine
from datetime import datetime

# Use sudo pip3 install or pip3 install to install a package for apache


zabbix_server = 'zproxy1.zvez.ga'
zabbix_host = 'Apt-Meters'
metric_key = 'coldWater'
water_multiplicator = 10

db = "sqlite:////var/www/api/water.db"
table = "cold_water"


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
    dt = int(datetime.now().strftime("%s"))
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


def insert_to_db(value):
    value = str(int(value) * water_multiplicator)
    engine = create_engine(db)
    conn = engine.connect()
    inserts = []

    utc_dt = datetime.strftime(datetime.now(), "%d-%m-%y %H:%M:%S")

    if table not in engine.table_names():
        conn.execute("CREATE TABLE %s (dt_utc TEXT, value INT)" % table)

    inserts.append({
        "dt_utc": utc_dt,
        "value": value,
    })

    for insert in inserts:
        i_dt_utc = insert.get("dt_utc")
        i_value = insert.get("value")
        query = "INSERT INTO %s (dt_utc, value) values ('%s', '%s');" % (table, i_dt_utc, i_value)
        conn.execute(query)
    return


def meta(value):
    metrics = make_metrics(value)
    insert_to_db(value)
    return send_metrics(metrics)
