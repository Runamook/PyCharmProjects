from lxml import etree
import json
from sys import argv


class SeagullConfig:

    def __init__(self, config_file):
        # Читаем протокол, режим работы и значащие AVP
        self.cfg = json.load(config_file)
        self.scenario = None
        self.config = None


    def make_scen(self):
        # По протоколу и режиму работы определяем имя шаблона
        self.read_scen()
        # Дополняем шаблон нужными AVP
        self.add_avps()
        # Пишем новый сценарий в файл
        self.write_template()

    def make_config(self):
        # По протоколу и режиму работы определяем имя шаблона
        self.read_config()
        # Дополняем шаблон нужными AVP
        self.add_config_data()
        # Пишем новый сценарий в файл
        self.write_config()

    def make_ids(self, filename):
        """
        Шапка
        "string";"string";"string";"string";
        # "framed-ip","imsi";"msisdn";"imei"
        "aa100101";"250999000000001";"79990000001";"3548170784554801";
        "aa100102";"250999000000002";"79990000002";"3548170784554802";
        """
        user_count = int(self.cfg['config']['user_count'])
        msisdn_start = int(self.cfg['config']['msisdn_start'])
        imsi_start = int(self.cfg['config']['imsi_start'])
        ip_start = self.cfg['config']['ip_start'].split('.')
        hex_ip_start = int('{:02X}{:02X}{:02X}{:02X}'.format(*map(int, ip_start)), base=16)
        imeisv = '3548170784554801'
        with open(filename, 'w') as f:
            f.write(f'"string";"string";"string";"string";\n')
            f.write(f'# "framed-ip","imsi";"msisdn";"imei";\n')
            for i in range(user_count):
                hex_ip = f'{hex_ip_start+i:x}'
                if len(hex_ip) != 8:
                    hex_ip = f'0{hex_ip}'
                line = f'"0x{hex_ip}";"{imsi_start+i}";"{msisdn_start+i}";"{imeisv}";\n'
                f.write(line)

    def read_config(self):
        template_name = f'{self.cfg["Protocol"]}_{self.cfg["Mode"]}_template.xml'
        self.config = etree.parse(f'templates/{template_name}').getroot()

    def read_scen(self):
        template_name = f'{self.cfg["Protocol"]}_{self.cfg["Mode"]}_scenario_template.xml'
        self.scenario = etree.parse(f'templates/{template_name}').getroot()

    def add_avps(self):
        # Найти все AVP в конфиге
        avps = self.cfg['avps']
        for avp_name in avps.keys():
            if avp_name == 'Host-IP-Address':
                octets = avps[avp_name].split('.')
                avp_value = '0x0001{:02X}{:02X}{:02X}{:02X}'.format(int(octets[0]), int(octets[1]), int(octets[2]), int(octets[3]))
            else:
                avp_value = avps[avp_name]
            # Найти все элементы для дополнения
            avps_to_change = self.scenario.xpath(f"//avp[@name='{avp_name}']")
            for avp_to_change in avps_to_change:
                # В каждый элемент добавить аттрибут
                avp_to_change.set('value', avp_value)

    def add_config_data(self):
        conf = self.cfg['config']
        params = conf['params']
        channels = self.config.xpath(f"//define[@entity='channel']")
        if len(channels) != 1:
            input(f'Количество каналов != 1: {channels}\nPress Enter to continue')
        else:
            channels[0].set('open-args', f'mode=client;dest={conf["ServerIP"]}:{conf["ServerPort"]}')

        for param_name in params.keys():
            if param_name == 'external-data-file':
                self.make_ids(params[param_name])
            param = self.config.xpath(f"//define[@name='{param_name}']")
            if len(param) != 1:
                input(f'Количество {param_name} != 1: {param}\nPress Enter to continue')
            else:
                param[0].set('value', params[param_name])


    def write_template(self):
        etree.dump(self.scenario)
        with open(self.cfg['config']['scen_file'], 'wb') as f:
            f.write(etree.tostring(self.scenario))

    def write_config(self):
        etree.dump(self.config)
        with open(self.cfg['config']['conf_file'], 'wb') as f:
            f.write(etree.tostring(self.config))


if __name__ == '__main__':
    if len(argv) > 1:
        cfg_file = argv[1]
    else:
        cfg_file = 'cfg.json'
    try:
        f = open(cfg_file, 'r')
        gull = SeagullConfig(f)
        gull.make_config()
        gull.make_scen()
    finally:
        f.close()



