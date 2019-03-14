import re
import sys
import csv
import time
import mysql.connector
from mysql.connector import errorcode

# TODO: prometheus exporter


def time_converter(epoch):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(epoch)))


def parse_rndc_stats(filename):
    type_dict = {
        'DumpStart': re.compile('^\\+\\+\\+ Sta.*Dump \\+\\+\\+ \\((\d+)\\)\n'),  # +++ Statistics Dump +++ (1551367104)
        'DumpEnd': re.compile('--- Statistics Dump --- \\((\d+)\\)\n'),  # --- Statistics Dump --- (1551367104)
        'MetricGroup': re.compile('^\\+\\+ (.*) \\+\\+\n'),  # ++ Incoming Requests ++
        'Metric': re.compile(' +(\d+ .+)\n'),  # 5 QUERY
        'View': re.compile('^\\[View: (.+)\\]\n'),  # [View: default]
        'Other': re.compile('^\\[([A-Z][a-z]+)\\]\n')  # [Common]
    }

    view = 'NA'
    other_var = 'NA'

    with open(filename, 'r') as f:
        file = f.readlines()

        dataset = []

        for line in file:
            if type_dict['DumpStart'].match(line):
                dt_epoch = time_converter(type_dict['DumpStart'].match(line).group(1))
                printable = False

            elif type_dict['DumpEnd'].match(line):
                dt_epoch = time_converter(type_dict['DumpEnd'].match(line).group(1))
                printable = False

            elif type_dict['MetricGroup'].match(line):
                metric_group = type_dict['MetricGroup'].match(line).group(1)
                printable = False

            elif type_dict['Metric'].match(line):
                metric_value = type_dict['Metric'].match(line).group(1).split(' ', maxsplit=1)
                value = metric_value[0]
                metric = metric_value[1]
                # Prettify
                metric = metric[0].capitalize() + metric[1:]
                printable = True

            elif type_dict['View'].match(line):
                view = type_dict['View'].match(line).group(1)
                printable = False

            elif type_dict['Other'].match(line):
                other_var = type_dict['Other'].match(line).group(1)
                printable = False

            # other_var not used
            if printable:
                result = (dt_epoch, metric_group, metric, value, view)
                dataset.append(result)

    return dataset


def write_csv(results_list, results_csv):
    with open('results_csv', 'w') as ff:
        writer = csv.writer(ff)
        for row in results:
            writer.writerow(row)


def db_connect(db_config):
    try:
        cnx = mysql.connector.connect(**db_config)

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
            sys.exit(1)
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
            sys.exit(1)
        else:
            print(err)
            sys.exit(1)
    else:
        return (cnx)


def write_db(cnx, dataset):
    insert_metric = 'INSERT INTO stats (dt, metricgroup, metric, value, view) VALUES (%s, %s, %s, %s, %s)'

    # https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlconnection-cursor.html
    cursor = cnx.cursor()
    for metric in dataset:
        try:
            cursor.execute(insert_metric, metric)
        except Exception as e:
            print(e)

    cnx.commit()
    cursor.close()
    cnx.close()


def send_to_zabbix(zabbix, dataset):
    # Function is not finished
    # Switched to Zabbix ODBC

    # zabbix_sender -z zabbix -s "Linux DB3" -k db.connections -o 43
    for line in dataset:
        stats_line = ["zabbix_sender", "-z", "asus.zvez.ga", "-s", "MetricName", "-k", "test", "-o", "43"]
        try:
            subprocess.run(stats_line).check_returncode()
        except subprocess.CalledProcessError:
            raise Exception("Unable to send data")


def meta(fl, db_config):

    # fl = '/home/egk/PycharmProjects/bind-stats/named_stats.txt'
    # results_csv = '/home/egk/PycharmProjects/bind-stats/output.csv'

    # Parse stats file and return a list of sets
    dataset = parse_rndc_stats(fl)

    # Connect to the MySQL database
    cnx = db_connect(db_config)

    # Write dataset into DB
    write_db(cnx, dataset)


if __name__ == "__main__":
    fl = sys.argv[1]
    db_config = {
        'host': '127.0.0.1',
        'port': '13306',
        'user': 'stats',
        'password': 'statspass',
        'database': 'bind_stats'
    }

    meta(fl)
