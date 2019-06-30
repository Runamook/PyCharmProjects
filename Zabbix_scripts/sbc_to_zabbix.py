import sys
import re
import subprocess
import logging
import json
try:
    import paramiko
except ImportError:
    print("\033[1;31;40m \n\nInstall paramiko module:\n$ pip install paramiko\n\n \033[0;37;40m \n")
import argparse

# TODO: Match metric lines with text in the end:
"""
   - signaling_type                        SIP
   - reset_stats                           : No             (No,Yes)
   - call_congestion                       false
"""


def create_logger(log_filename, instance_name, loglevel="INFO"):
    if loglevel == "ERROR":
        log_level = logging.ERROR
    elif loglevel == "WARNING":
        log_level = logging.WARNING
    elif loglevel == "INFO":
        log_level = logging.INFO
    elif loglevel == "DEBUG":
        log_level = logging.DEBUG

    logger = logging.getLogger(instance_name)
    logger.setLevel(log_level)
    fmt = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

    fh = logging.FileHandler(filename=log_filename)
    fh.setFormatter(fmt)
    fh.setLevel(log_level)
    fh.setFormatter(fmt)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(log_level)

    logger.addHandler(fh)
    logger.addHandler(sh)

    return logger


class Sbc:
    # Not matching strings like:
    #    - reset_stats                           : No             (No,Yes)
    #
    # Test data:
    # m = re.compile("^\s+- (\S+).*")
    # s = re.compile("^\s+\|-\s+(\S+)")
    # a1 = "   - sip_shared_usage_percent              0"
    # a2 = "   - asr_stats_incoming_struct"
    # a3 = "     |- global_asr_percent                 0"

    entities = {
        "value": re.compile(".* (\S+)$"),
        # "metric": re.compile("^\s+- (\S+)\s+\S$"),
        "metric": re.compile("^\s+- (\S+)\s+\S+$"),
        "metric_group": re.compile("^\s+- (\S+)$"),
        "submetric": re.compile("^\s+\|-\s+(\S+)")
    }

    sep = "--"

    """
    To add data to ignore_list
    
    "Simple" metric: 
   - reset_nap_drop_stats                  : No             (No,Yes)
   add "metric name" to the ignore_list variable.
   
   "Complex" metric:
   - local_drop_stats                                      
     |- TOTAL                              1309
    add "metric group" + sep + "metric name" to the ignore_list variable
        
    
    """
    ignore_list = ["unique_id", "signaling_type", "reset_stats", "firewall_blocked_cnt", "inst_incoming_file_playbacks",
                   "inst_incoming_file_recordings", "total_incoming_file_playbacks", "total_incoming_file_recordings",
                   "inst_outgoing_file_playbacks", "inst_outgoing_file_recordings", "total_outgoing_file_playbacks",
                   "total_outgoing_file_recordings", "mips_shared_usage_percent", "port_range_shared_usage_percent",
                   "sip_shared_usage_percent", "reset_asr_stats", "reset_rtp_stats",
                   # "rtp_statistics_struct" + sep + "from_net_nb_packets",
                   # "rtp_statistics_struct" + sep + "from_net_nb_out_of_seq_packets",
                   # "rtp_statistics_struct" + sep + "from_net_nb_lost_packets",
                   # "rtp_statistics_struct" + sep + "from_net_nb_duplicate_packets",
                   # "rtp_statistics_struct" + sep + "from_net_nb_early_late_packets",
                   # "rtp_statistics_struct" + sep + "from_net_nb_bad_protocol_headers",
                   # "rtp_statistics_struct" + sep + "from_net_nb_buffer_overflows",
                   # "rtp_statistics_struct" + sep + "from_net_nb_other_errors",
                   # "rtp_statistics_struct" + sep + "to_net_nb_packets",
                   # "rtp_statistics_struct" + sep + "to_net_nb_arp_failures",
                   # "rtp_statistics_struct" + sep + "t38_nb_pages_to_tdm",
                   # "rtp_statistics_struct" + sep + "t38_nb_pages_from_tdm",
                   # "local_drop_stats" + sep + "TOTAL",
                   # "system_drop_stats" + sep + "TOTAL",
                   "reset_nap_drop_stats", "remote_drop_stats"]

    positives = ["yes", "true"]             # Transformed to 1
    negatives = ["no", "false"]             # Transformed to 0

    def __init__(self, logfile=None, loglevel="DEBUG", command=None):

        log_file = logfile or "sbc_to_zabbix.log"
        self.logger = create_logger(log_file, "SBC", loglevel)
        pre_command = command or "/bin/cat /home/egk/PycharmProjects/Zabbix_scripts/tb.txt"
        self.command = pre_command.split()

        self._use_ssh = False
        self.sbc_host = None
        self.sbc_user = None
        self.sbc_password = None
        self.sbc_ssh_key = None

    def set_ssh_params(self, user=None, password=None, host=None, keyfile=None):
        self.sbc_host = host
        self.sbc_user = user
        self.sbc_password = password
        self.sbc_ssh_key = keyfile
        self._use_ssh = True

    def parser(self, in_data):
        # Parses input list of strings with tb SBC stats
        # Returns list of dicts {metric: value}

        metrics = []
        sep = Sbc.sep
        provider = None
        metric = None
        metric_group = None
        submetric = None
        value = None

        for line in in_data:
            line = self.line_cleaner(line)
            if len(line) < 15:
                # Skip the line
                continue

            if ":/nap:" in line:
                # Provider line
                provider = line.split(":")[-1].strip()                  # ":" is fixed here
                self.logger.debug("Found provider: %s" % provider)
                continue

            elif Sbc.entities["metric_group"].match(line):
                # self.logger.debug("Parsing for SG \"%s\"" % line)
                # Metric group line
                pre_metric = Sbc.entities["metric_group"].match(line).groups()[0]
                if not provider:
                    self.logger.error("Provider is unknown when metric_group line % is parsed: %s" % (line, in_data))
                metric_group = provider + sep + pre_metric
                self.logger.debug("Found metric group: %s" % metric_group)
                continue

            elif Sbc.entities["metric"].match(line):
                # self.logger.debug("Parsing for M \"%s\"" % line)
                # Metric line
                pre_metric = Sbc.entities["metric"].match(line).groups()[0]
                if pre_metric in Sbc.ignore_list:
                    continue
                if not provider:
                    self.logger.error("Provider is unknown when metric line % is parsed: %s" % (line, in_data))
                metric = provider + sep + pre_metric
                self.logger.debug("Found metric: %s" % metric)

            elif Sbc.entities["submetric"].match(line):
                # Submetric line
                # self.logger.debug("Parsing for SM \"%s\"" % line)
                submetric = Sbc.entities["submetric"].match(line).groups()[0]
                check_metric = metric_group.split(sep)[1] + sep + submetric         # local_drop_stats:TOTAL
                if check_metric in Sbc.ignore_list:
                    submetric = None
                    continue

                if not metric_group or not provider:
                    self.logger.error("Provider or metric group is unknown when submetric line %s is parsed: %s" % (line, in_data))
                # assert not submetric, "No submetric in line" + line
                metric = metric_group + sep + submetric

            if metric:     # remove submetric
                value = Sbc.entities["value"].match(line).groups()[0]
                if value.lower() in Sbc.positives:
                    value = "1"
                elif value.lower() in Sbc.negatives:
                    value = "0"

            if metric:
                metrics.append({metric: value})
                metric = None
                submetric = None

        return metrics

    def line_cleaner(self, line):
        line = line.strip("\r\n").rstrip(" ")
        self.logger.debug("Parsing line \"%s\"" % line)
        return line

    def get_data(self):

        if not self._use_ssh:
            result = subprocess.run(self.command, stdout=subprocess.PIPE).stdout.decode().split('\r\n')
        else:
            result = self.get_data_over_ssh()

        return result

    def sbc_items_lld(self):
        command_output = self.get_data()
        metrics = self.parser(command_output)

        metric_names = [{"Metric": list(metric)[0]} for metric in metrics]

        return metric_names

    def sbc_get_items(self):
        command_output = self.get_data()
        items = self.parser(command_output)
        result = dict()
        for item in items:
            result[list(item.items())[0][0]] = list(item.items())[0][1]

        return result

    def sbc_get_items_text(self):
        command_output = self.get_data()
        items = self.parser(command_output)             # [{key: value}, {key: value}]
        result = ""
        for item in items:
            key = list(item.items())[0][0]
            value = list(item.items())[0][1]
            result += "%s = %s\n" % (key, value)

        return result

    def get_sbc_data(self):
        raise NotImplementedError
        pass

    def get_data_over_ssh(self):
        ssh = paramiko.SSHClient()
        policy = paramiko.AutoAddPolicy
        ssh.set_missing_host_key_policy(policy)
        if self.sbc_ssh_key:
            ssh.connect(self.sbc_host, username=self.sbc_user, key_filename=self.sbc_ssh_key)
        elif self.sbc_password:
            ssh.connect(self.sbc_host, username=self.sbc_user, password=self.sbc_password)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(" ".join(self.command))
        result = [x.strip("\n") for x in ssh_stdout.readlines()]
        return result


"""
def test():
    cmd = "cat log.txt"
    llevel = "INFO"
    lfile = "./sbc_to_zabbix.log"
    sbc = Sbc(loglevel=llevel, logfile=lfile, command=cmd)
    sbc.set_ssh_params(host="127.0.0.1", user="adm", password="pass")
    print(sbc.sbc_get_items_text())
    

if __name__ == "__main__":
    test()
"""

if __name__ == "__main__":
    optparser = argparse.ArgumentParser(description="TelcoBriges SBC stats parser. Executes a command, parses response \
    and returns JSON data. Can be used in Zabbix")
    requiredNamed = optparser.add_argument_group('Required arguments')
    optparser.add_argument("--sbc_host", type=str, help="SBC Host IP address, used only if data gathered over SSH")
    optparser.add_argument("--sbc_user", type=str, help="SBC username, used only if data gathered over SSH")
    optparser.add_argument("--sbc_ssh_key", type=str, help="SSH key for SBC auth, used only if data gathered over SSH")
    optparser.add_argument("--sbc_password", type=str, help="SBC password, used only if data gathered over SSH")
    optparser.add_argument("--llevel", type=str, help="Log level, DEBUG/INFO/WARN/ERROR, Default: INFO")
    optparser.add_argument("--lfile", type=str, help="Log file, Default: /var/log/zabbix/sbc_stats_parser.log")

    # requiredNamed.add_argument("--command", type=str, help="Command to execute to get data from host. \
    # Something like \"/bin/cat tb.txt\" or \"/usr/local/bin/tbstatus /nap\".")
    requiredNamed.add_argument("--operation", type=str, help="Can be LLD or Data, Default: LLD", required=True)

    sbc_ssh_key = None
    sbc_password = None
    args = optparser.parse_args()

    if args.operation == "LLD" or args.operation == "Data":
        operation = args.operation
    else:
        print("Unknown operation %s" % args.operation)
        sys.exit(1)
    # cmd = args.command
    if not args.lfile:
        lfile = "/var/log/zabbix/sbc_stats_parser.log"
    else:
        lfile = args.lfile

    if not args.llevel:
        llevel = "INFO"
    else:
        llevel = args.llevel

    if args.sbc_host:
        sbc_host = args.sbc_host
        use_ssh = True
    else:
        use_ssh = False

    if args.sbc_ssh_key:
        sbc_ssh_key = args.sbc_ssh_key
    if args.sbc_user:
        sbc_user = args.sbc_user
    if args.sbc_password:
        sbc_password = args.sbc_password

    cmd = "cat log.txt"

    sbc = Sbc(loglevel=llevel, logfile=lfile, command=cmd)

    if use_ssh:
        sbc.set_ssh_params(host=sbc_host, user=sbc_user, password=sbc_password, keyfile=sbc_ssh_key)

    if operation == "LLD":
        result = json.dumps(sbc.sbc_items_lld())
    elif operation == "Data":
        # result = json.dumps(sbc.sbc_get_items_text())
        result = sbc.sbc_get_items_text()

    print(result)

