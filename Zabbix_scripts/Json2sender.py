from pyzabbix import ZabbixMetric, ZabbixSender
from datetime import datetime as dt
import requests
import argparse


try:
    from Zabbix_scripts.Helpers.create_logger import create_logger
except ImportError:
    from Helpers.create_logger import create_logger
try:
    from Zabbix_scripts.Helpers.helpers import make_dates, Numeric_Metrics, get_metric_time
except ImportError:
    from Helpers.helpers import make_dates, Numeric_Metrics, get_metric_time

# TODO: Empty response from API
# TODO: Multiple meters from
# TODO:  "StromNeutralleiter": null - removed from Numeric_Metrics


class Meters:

    def __init__(self, logfile, loglevel, api_user, api_pass, meter_id, date, zabbix_server_ip):

        self.logger = create_logger(logfile, __name__, loglevel)
        self.logger.warning("Initiated app")
        self.logger.info("Input: \n\tlogfile = %s\n\tloglevel = %s\n\tapi_user = %s\
\n\tapi_pass = %s\n\tmeter_id = %s\n\tdate = %s\n\tzabbix_server_ip = %s" % (logfile, loglevel, api_user,
                                                                            api_pass, meter_id, date, zabbix_server_ip)
                         )

        self.zabbix_server_ip = zabbix_server_ip
        if date is None:
            date = make_dates()
            self.logger.info("Date not provided, using %s" % date)

        try:
            dt.strptime(date, "%d.%m.%Y")
        except ValueError:
            self.logger.error("Incorrect date %s, use \"dd.mm.yyyy\"" % date)
            exit(1)

        self.api_url = "https://webhelper.acteno.de:4443/home/GetGridQualityData?\
User=%s\
&pass=%s\
&id=%s&\
datum=%s" % (api_user, api_pass, meter_id, date)

    def get_json(self):
        self.logger.info("Querying URL %s" % self.api_url)
        response = requests.get(self.api_url)
        assert response.status_code == 200, self.logger.error("API responded %s, expected 200" % response.status_code)
        assert response.text != "Authenticarion Error.", self.logger.error("API authenticarion error")  # Typo in text

        self.logger.info("Response code %s in %s ms" % (response.status_code,
                                                        str(response.elapsed.microseconds / 1000))
                         )
        self.logger.debug("Headers: %s" % response.headers)
        self.logger.debug("Text: %s" % response.text)
        return response.json()

    def process_metrics(self):
        # ZabbixMetric('Zabbix server', 'WirkleistungP3[04690915]', 3, clock=1554851400))

        json = self.get_json()
        self.logger.info("Found %s measurements" % len(json))
        results = []
        for measurement in json:
            IdentificationNumber = measurement["IdentificationNumber"]
            metric_time = get_metric_time(measurement)

            for metric in Numeric_Metrics:
                metric_value = measurement[metric]
                metric_key = metric + "[" + IdentificationNumber + "]"
                self.logger.debug("Metric %s %s %s" % (metric_key, metric_value, metric_time))
                results.append(ZabbixMetric("Zabbix server", metric_key, metric_value, clock=metric_time))

        self.logger.info("Prepared %s metrics for insertion" % len(results))
        return results

    def send_metrics(self, metrics):
        sender = ZabbixSender(self.zabbix_server_ip)
        zabbix_response = sender.send(metrics)
        if zabbix_response.failed > 0 and zabbix_response.processed == 0:
            self.logger.error("Something went totally wrong, terminating\n%s" % zabbix_response)
            exit(1)
        elif zabbix_response.failed > 0 and zabbix_response.failed > zabbix_response.processed:
            self.logger.warning("More failures that successes %s" % zabbix_response)
        else:
            self.logger.warning("Result %s" % zabbix_response)
        return

    def run(self):
        self.logger.warning("Starting")
        metrics = self.process_metrics()
        self.send_metrics(metrics)


if __name__ == "__main__":
    optparser = argparse.ArgumentParser(description="Get JSON data from API and push it to Zabbix server")
    requiredNamed = optparser.add_argument_group("Mandatory arguments")
    requiredNamed.add_argument("-u", "--user", type=str, help="API user", required=True)
    requiredNamed.add_argument("-p", "--password", type=str, help="API password", required=True)
    requiredNamed.add_argument("-m", "--meter_id", type=str, help="Meter id", required=True)
    optparser.add_argument("-l", "--log_file", type=str, help="Log filename. Default Json2sender.log")
    optparser.add_argument("--log_level", help="Default: INFO")
    optparser.add_argument("--date", help="Date as \"dd.mm.yyyy\"")
    optparser.add_argument("-z", "--zabbix_server", help="Server IP address")
    args = optparser.parse_args()

    api_user = args.user
    api_pass = args.password
    meter_id = args.meter_id

    if not args.log_file:
        log_file = "Json2sender.log"
    else:
        log_file = args.log_file
    if not args.log_level:
        log_level = "INFO"
    else:
        log_level = args.log_level
    if not args.date:
        date = None
    else:
        date = args.date
    if not args.zabbix_server:
        zabbix_server = "127.0.0.1"
    else:
        zabbix_server = args.zabbix_server

    app = Meters(logfile=log_file, loglevel=log_level,
                 api_user=api_user, meter_id=meter_id, api_pass=api_pass,
                 date=date, zabbix_server_ip=zabbix_server
                 )
    app.run()
