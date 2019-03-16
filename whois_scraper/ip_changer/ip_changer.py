from subprocess import run, PIPE
import datetime
from time import sleep

# TODO: May be enhance check_if_started with "ps aux | grep -v grep | grep sakis3g | wc -l"
# TODO: Reliably reset reset_file upon start


class IPChanger:
    lock_file = "/run/scrapper/lockfile"
    reset_file = "/run/scrapper/resetfile"

    @staticmethod
    def ip_change(logger):

        dt_start = datetime.datetime.now()
        ip_old = run(["/usr/bin/curl", "-s", "https://ipinfo.io/ip"], stdout=PIPE).stdout.strip().decode("utf-8")
        run(["/usr/bin/sakis3g",
             "reconnect",
             "CUSTOM_APN=internet.tele2.ru",
             "--sudo",
             "APN=CUSTOM_APN",
             "APN_USER=tele2",
             "APN_PASS=tele2"])
        ip_new = run(["/usr/bin/curl", "-s", "https://ipinfo.io/ip"], stdout=PIPE).stdout.strip().decode("utf-8")

        dt_stop = datetime.datetime.now()
        delta = dt_stop - dt_start

        if ip_old == ip_new:
            logger.error("Unable to change IP")
            raise Exception("IPChangeError")
        else:
            logger.info("Changed IP from %s to %s in %s seconds" % (ip_old, ip_new, delta.seconds))

            return

    @staticmethod
    def create_file(filename, content):
        """Create file if not exist
        """
        if run(["ls", filename]).returncode != 0:
            run(["touch", filename])
            with open(filename, 'w') as f:
                f.write(str(content))
        return

    @staticmethod
    def increment_lock(float_num):

        # Create file if not exist
        IPChanger.create_file(IPChanger.lock_file, "1")

        # Increment value
        with open(IPChanger.lock_file, 'r') as f:
            ip_change_counter = float(f.read())
            result = str(ip_change_counter + float(float_num))
        with open(IPChanger.lock_file, 'w') as f:
            f.write(result)
        return result

    @staticmethod
    def time_to_change_ip(change_ip_limit):
        """
        Reads IPChanger.lock_file and checks if it's time to change IP
        """
        with open(IPChanger.lock_file, 'r') as f:
            ip_change_counter = f.read()
        if float(ip_change_counter) > float(change_ip_limit):
            return True
        else:
            return False

    @staticmethod
    def reset_counter():
        with open(IPChanger.lock_file, 'w') as f:
            f.write("0")
        return

    @staticmethod
    def start_ip_change(start, logger):
        with open(IPChanger.reset_file, 'w') as f:
            if start == "start":
                f.write("start")
                logger.debug("start_ip_change - writing \"start\"")
            elif start == "stop":
                f.write("stop")
                logger.debug("start_ip_change - writing \"stop\"")
        return

    @staticmethod
    def check_if_started(logger):
        # Create file if not exist
        IPChanger.create_file(IPChanger.reset_file, "stop")

        with open(IPChanger.reset_file, 'r') as f:
            start = f.read()
            if start == "start":
                logger.debug("Check_if_started - \"start\"")
                return True
            elif start == "stop":
                logger.debug("Check_if_started - \"stop\"")
                return False

    @staticmethod
    def meta(change_ip_limit, logger):
        logger.debug("Starting IPChanger.meta()")
        result = "unchanged"
        if IPChanger.time_to_change_ip(change_ip_limit):
            logger.debug("Time to change IP")
            if IPChanger.check_if_started(logger):
                # If IP change is running, continuously check file
                while IPChanger.check_if_started(logger):
                    logger.debug("Paused because IP change is running")
                    sleep(10)
            elif not IPChanger.check_if_started(logger):
                logger.debug("I will change IP")
                try:
                    IPChanger.start_ip_change("start", logger)
                    logger.warning("Changing IP started, waiting for all to pause")
                    sleep(20)
                    logger.warning("Changing IP started, pause finished, changing")
                    IPChanger.ip_change(logger)
                    result = "changed"

                    # Reset IP changer counter
                    with open(IPChanger.lock_file, 'w') as f:
                        f.write(str(0))
                finally:
                    IPChanger.start_ip_change("stop", logger)
                    logger.warning("Changing IP finished")
        return result
