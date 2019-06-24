import sys
import re
import subprocess
import logging
import json


"""
sudo chown zabbix:zabbix /usr/lib/zabbix/externalscripts/Sensors.py

/etc/zabbix/zabbix_agentd.d/userparameter_temperature.conf
# UserParameter=temperature.hdd[*],/usr/bin/python3 /usr/lib/zabbix/externalscripts/Sensors.py --hdd $1
UserParameter=temperature.hdd[*],sudo hddtemp $1 | grep -Eo "...C$" | grep -Eo "^.."
UserParameter=temperature.sensor[*],/usr/bin/python3 /usr/lib/zabbix/externalscripts/Sensors.py --sensor $1
UserParameter=temperature.sensors.discovery,/usr/bin/python3 /usr/lib/zabbix/externalscripts/Sensors.py sensor_discovery
UserParameter=temperature.hdd.discovery,/usr/bin/python3 /usr/lib/zabbix/externalscripts/Sensors.py hdd_discovery


/etc/sudoers
zabbix  ALL=(ALL) NOPASSWD: /usr/sbin/hddtemp

"""


logger = logging.getLogger()
logger.setLevel(logging.ERROR)
fmt = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(fmt)
sh.setLevel(logging.ERROR)
logger.addHandler(sh)


entities = {
        # Core 0:       +51.0°C  (high = +80.0°C, crit = +100.0°C) = 51.0
        'temperature': re.compile('^.*\\+(.+)°C .*'),
        # Core 0:       +51.0°C  (high = +80.0°C, crit = +100.0°C) = Core 0
        'device': re.compile('^(.+): .+'),
        # Adapter: ACPI interface = ACPI Interface
        'adapter': re.compile('^Adapter: (.*)'),
        # '+12 Voltage:       +12.26 V  (min = +10.20 V, max = +13.80 V)' = +10.20 V
        # 'min': re.compile('.*min = (.+ .+), .*'),
        # '+12 Voltage:       +12.26 V  (min = +10.20 V, max = +13.80 V)' = +13.80 V
        # 'max': re.compile('.* max = (.+).$'),
        'high': re.compile('.*high = (.+).0°C, .*'),
        'crit': re.compile('.*crit = (.+).0.*$'),
    }


def get_data_all_sensors():
    """
    """
    in_data = subprocess.run("/usr/bin/sensors", stdout=subprocess.PIPE).stdout.decode().split("\n")
    results = []
    for line in in_data:
        if ":" not in line and len(line) > 1:
            hw_device = line
        # if "Adapter" in line:
        #     adapter = _get("adapter", line)

        if "°C" in line:
            device = _get("device", line)
            temperature = _get("temperature", line)

            results.append({f"{hw_device}:{device}": temperature})

            """
            if "high =" in line:
                high = _get("high", line)
                data[sensor]["high"] = high

            if "crit =" in line:
                crit = _get("crit", line)
                data[sensor]["crit"] = crit
            """

    return results


def get_data_one_sensor(sensor):
    """
    """
    logger.debug(sensor)
    in_data = subprocess.run('/usr/bin/sensors', stdout=subprocess.PIPE).stdout.decode().split('\n')
    results = dict()
    for line in in_data:
        if ":" not in line and len(line) > 1:
            hw_device = line
        # if "Adapter" in line:
        #     adapter = _get("adapter", line)

        if "°C" in line:
            device = _get("device", line)
            results[f"{hw_device}:{device}"] = int(float(_get("temperature", line)))

            """
            if "high =" in line:
                high = _get("high", line)
                data[sensor]["high"] = high

            if "crit =" in line:
                crit = _get("crit", line)
                data[sensor]["crit"] = crit
            """
    logger.debug(results)
    return results[sensor]


def _get(entity_name, line):
    if entities[entity_name].search(line):
        return entities[entity_name].search(line).groups()[0].strip().strip("+").replace(" ", "_")
    else:
        return None


def get_data_all_hdds(disks):
    results = dict()

    for disk in disks:
        cmd_output = subprocess.run(["/usr/sbin/hddtemp", disk], stdout=subprocess.PIPE).stdout
        temperature = cmd_output.split()[-1][:2].decode()                # "/dev/sdb: WDC WD1600JS-22MHB1: 52°C" = 52
        results[disk] = temperature

    return results


def get_data_one_hdd(disk):

    cmd_output = subprocess.run(["/usr/sbin/hddtemp", disk], stdout=subprocess.PIPE).stdout
    if b'\xc2\xb0C' not in cmd_output:
        print(f"No temperature in output: {cmd_output}")
        raise ValueError
    return cmd_output.split()[-1][:2].decode()                          # "/dev/sdb: WDC WD1600JS-22MHB1: 52°C" = 52


def to_json(func):

    def wrapper(*args, **kwargs):
        return json.dumps(func(*args, **kwargs))
    return wrapper()


@to_json
def sensors_discovery():
    """
    """
    logger.debug(f"sensors_discovery called")
    in_data = subprocess.run('/usr/bin/sensors', stdout=subprocess.PIPE).stdout.decode().split('\n')
    sensors = []
    for line in in_data:
        if ":" not in line and len(line) > 1:
            hw_device = line
        if "°C" in line:
            device = _get("device", line)

            sensors.append({"sensor": f"{hw_device}:{device}"})

    return sensors


@to_json
def hdd_discovery():
    cmd_output = subprocess.run('/sbin/blkid', stdout=subprocess.PIPE).stdout.decode().split('\n')
    pre_disks = set([x[:8] for x in cmd_output])                    # Only /dev/sdX
    disks = list(filter(lambda x: len(x) > 1, pre_disks))           # Filter out empty strings
    result = [{"disk": disk} for disk in disks]
    return result


def main():
    logger.debug(f"Input: {sys.argv}")
    if sys.argv[1] == "sensor_discovery":
        logger.debug(f"Sensor discovery")
        result = sensors_discovery
    elif sys.argv[1] == "hdd_discovery":
        logger.debug(f"HDD discovery")
        result = hdd_discovery
    elif sys.argv[1] == "--sensor":
        logger.debug(f"Sensor {sys.argv[1]} data query")
        result = get_data_one_sensor(sys.argv[2])
    elif sys.argv[1] == "--hdd":
        logger.debug(f"HDD {sys.argv[1]} data query")
        result = get_data_one_hdd(sys.argv[2])
    elif sys.argv[1] == "-h" or sys.argv[1] == "--help":
        result = f"Usage: {sys.argv[0]} [sensor_discovery | hdd_discovery | --sensor {{sensor}} | --hdd {{hdd}}]"
    print(result)
    return result


if __name__ == "__main__":
    main()


