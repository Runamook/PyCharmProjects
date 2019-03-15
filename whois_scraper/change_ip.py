from .scraper import Scrapper
from subprocess import run, PIPE
import datetime

class IPChanger(Scrapper):
    def __init__(self):
        pass

    def change_ip(self):

        dt_start = datetime.datetime.now()
        ip_old = run(["/usr/bin/curl", "-s", "https://ipinfo.io/ip"], stdout=PIPE).stdout.strip().decode("utf-8")
        run(["/usr/bin/sakis3g", "reconnect"])
        ip_new = run(["/usr/bin/curl", "-s", "https://ipinfo.io/ip"], stdout=PIPE).stdout.strip().decode("utf-8")

        dt_stop = datetime.datetime.now()
        delta = dt_stop - dt_start

        if ip_old == ip_new:
            self.logger.error("Unable to change IP")
            raise Exception("IPChangeError")
        else:
            self.logger.info("Changed IP from %s to %s in %s" % (ip_old, ip_new, delta.seconds))

            return


