import sys
import subprocess
import logging
import paramiko
# try:
#    import paramiko
# except ImportError:
#    print("\033[1;31;40m \n\nInstall paramiko module:\n$ pip install paramiko\n\n \033[0;37;40m \n")
import argparse


def create_logger(log_filename, instance_name, loglevel="INFO"):
    if loglevel == "ERROR":
        log_level = logging.ERROR
    elif loglevel == "WARNING":
        log_level = logging.WARNING
    elif loglevel == "INFO":
        log_level = logging.INFO
    elif loglevel == "DEBUG":
        log_level = logging.DEBUG
    else:
        log_level = "INFO"

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


class Ngfw:

    filter = ['-->', 'Total Sessions', '2019-09-26 ']
    def __init__(self, logfile=None, loglevel="DEBUG", command=None):

        log_file = logfile or "/dev/null"
        self.logger = create_logger(log_file, "NGFW", loglevel)
        pre_command = command
        self.command = pre_command.split()

        self._use_ssh = False
        self.fw_host = None
        self.fw_user = None
        self.fw_password = None
        self.fw_ssh_key = None

    def set_ssh_params(self, user=None, password=None, host=None, keyfile=None):
        self.fw_host = host
        self.fw_user = user
        self.fw_password = password
        self.fw_ssh_key = keyfile
        self._use_ssh = True

    def line_cleaner(self, line):
        line = line.strip("\r\n").rstrip(" ")
        self.logger.debug("Parsing line \"%s\"" % line)
        return line

    def line_filter(self, lines):
        self.logger.debug("Filters: \"%s\"" % Ngfw.filter)
        line_result = []
        for line in lines:
            for filter_str in Ngfw.filter:
                if filter_str in line:
                    self.logger.debug("Line match: \"%s\"" % line)
                    line_result.append(line)
        return line_result

    def get_data(self):

        if not self._use_ssh:
            data_result = subprocess.run(self.command, stdout=subprocess.PIPE).stdout.decode().split('\r\n')
        else:
            data_result = self.get_data_over_ssh()

        return data_result

    def fw_get_data(self):
        command_output = self.get_data()
        data_result = self.line_filter(command_output)
        return data_result

    def get_data_over_ssh(self):
        ssh = paramiko.SSHClient()
        policy = paramiko.AutoAddPolicy
        ssh.set_missing_host_key_policy(policy)
        if self.fw_ssh_key:
            ssh.connect(self.fw_host, username=self.fw_user, key_filename=self.fw_ssh_key)
        elif self.fw_password:
            ssh.connect(self.fw_host, username=self.fw_user, password=self.fw_password)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(" ".join(self.command))
        data_result = [x.strip("\n") for x in ssh_stdout.readlines()]
        return data_result


def test():
    cmd = "display firewall session table source inside 10.193.0.16"
    llevel = "INFO"
    lfile = "/dev/null"
    fw = Ngfw(loglevel=llevel, logfile=lfile, command=cmd)
    fw.set_ssh_params(host="10.96.19.251", user="sshadmin", password="Huawei12#$")
    print('\n'.join(fw.fw_get_data()))


if __name__ == "__main__":
    test()
"""

if __name__ == "__main__":
    optparser = argparse.ArgumentParser(description="Executes a command, parses response \
    and returns JSON data. Can be used in Zabbix")
    requiredNamed = optparser.add_argument_group('Required arguments')
    optparser.add_argument("--fw_host", type=str, help="Host IP address, used only if data gathered over SSH")
    optparser.add_argument("--fw_user", type=str, help="username, used only if data gathered over SSH")
    optparser.add_argument("--fw_ssh_key", type=str, help="SSH key for auth, used only if data gathered over SSH")
    optparser.add_argument("--fw_password", type=str, help="Password, used only if data gathered over SSH")
    optparser.add_argument("--llevel", type=str, help="Log level, DEBUG/INFO/WARN/ERROR, Default: INFO")
    optparser.add_argument("--lfile", type=str, help="Log file, Default: /dev/null")

    fw_host, fw_user, fw_password, fw_ssh_key = None, None, None, None
    args = optparser.parse_args()

    # cmd = args.command
    if not args.lfile:
        # lfile = "/var/log/zabbix/fw_stats_parser.log"
        lfile = "/dev/null"
    else:
        lfile = args.lfile

    if not args.llevel:
        llevel = "INFO"
    else:
        llevel = args.llevel

    if args.fw_host:
        fw_host = args.fw_host
        use_ssh = True
    else:
        use_ssh = False

    if args.fw_ssh_key:
        fw_ssh_key = args.fw_ssh_key
    if args.fw_user:
        fw_user = args.fw_user
    if args.fw_password:
        fw_password = args.fw_password

    cmd = "cat log.txt"

    fw = Ngfw(loglevel=llevel, logfile=lfile, command=cmd)

    if use_ssh:
        fw.set_ssh_params(host=fw_host, user=fw_user, password=fw_password, keyfile=fw_ssh_key)

    result = fw.fw_get_data()

    print(result)
"""
