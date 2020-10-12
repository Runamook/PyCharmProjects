import xml.etree.ElementTree as ET
from xml.dom import minidom
import json

"""
{
"Default": {
"Origin-Host": "oh.com",
"Origin-Realm": "com",
"Host-IP-Address": "10.2.3.4"
},
"CE":
{ "Product-Name": "Gull" },
"Traffic": {}
}

"""


class SeagullConfig:

    default_commands = dict()
    default_commands['CER'] = {
      "Vendor-Id": "9",
      "Product-Name": "Seagull",
      "Origin-State-Id": "1094807040",
      "Supported-Vendor-Id": "10415",
      "Auth-Application-Id": "16777238",
      "Acct-Application-Id": "0",
      "Vendor-Specific-Application-Id": {
        "Vendor-Id": "10415",
        "Auth-Application-Id": "16777238",
        "Acct-Application-Id": "0"
        },
      "Firmware-Revision": "182"
      }

    def __init__(self, config_file):
        self.cfg = json.load(config_file)
        self.scenario = None

    def build_scenario(self):
        self.scenario = ET.Element('scenario')
        self.add_counters()
        self.build_init()

    def build_init(self):
        init = ET.SubElement(self.scenario, 'init')
        init_send = ET.SubElement(init, 'send', attrib={'channel': 'channel-1'})
        self.add_command(init_send, 'CER')

        return init

    def add_command(self, parent, command):
        pre_command = ET.SubElement(parent, 'command', attrib={'name': command})
        self.add_default_avps(pre_command, command)

    def add_counters(self):
        counter = ET.SubElement(self.scenario, 'counter')
        hbh_counter = ET.SubElement(counter, 'counterdef', attrib={'name': 'HbH-counter', 'init': '0'})
        ete_counter = ET.SubElement(counter, 'counterdef', attrib={'name': 'EtE-counter', 'init': '0'})
        session_counter = ET.SubElement(counter, 'counterdef', attrib={'name': 'session-counter', 'init': '0'})

    def add_avp(self, parent, name, value):
        return ET.SubElement(parent, 'avp', attrib={'name': name, 'value': value})

    def add_default_avps(self, parent, command):
        for avp_name in SeagullConfig.default_commands[command].keys():
            avp_value = SeagullConfig.default_commands[command][avp_name]
            if type(avp_value) == str:
                parent = self.add_avp(parent, avp_name, avp_value)





traffic = ET.SubElement(scenario, 'traffic')
default = ET.SubElement(scenario, 'default')



xmlstr = minidom.parseString(ET.tostring(scenario)).toprettyxml(indent="   ")
print(xmlstr)
