import datetime
from pyzabbix import ZabbixMetric, ZabbixSender
import sqlite3
from datetime import datetime

zabbix_server = 'zabbix.zvez.ga'
zabbix_host = 'Gas'
metric_key = 'gas'
multiplicator = 1

db = "/var/www/api/hall.db"
table = "gas"


def application(environ, start_response):
    # lines = []
    # for key, value in environ.items():
    #    lines.append("%s: %r" % (key, value))
    # output = b'hello world from wsgi!'
    # output = " ".join(lines).encode()

    # /metric/value/0
    uri = environ['REQUEST_URI']
    value = uri.split("/")[-1]

    try:
        value = int(value)
    except ValueError:
        print('Received {}, expecting integer in the end of URL'.format(uri))
        raise ValueError

    status, output = meta(value)

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]


def make_metrics(value):
    value = str(int(value) * multiplicator)
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
    value = str(int(value) * multiplicator)
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    utc_dt = datetime.strftime(datetime.now(), "%d-%m-%y %H:%M:%S")
    table_q = "CREATE TABLE IF NOT EXISTS {} (dt_utc TEXT, value INT, PRIMARY KEY(dt_utc, value))".format(table)
    data_q = "INSERT INTO {} VALUES ('{}', '{}')".format(table, utc_dt, value)

    try:
        cursor.execute(table_q)
        cursor.execute(data_q)
        conn.commit()
    except Exception as e:
        print(e)
        raise e
    finally:
        conn.close()
    return


def meta(value):
    metrics = make_metrics(value)
    insert_to_db(value)
    return send_metrics(metrics)
