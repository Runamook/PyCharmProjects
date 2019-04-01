import Zabbix_scripts.templates as zt

dir = "/home/egk/Work/Misc/Zabbix_net_srv"
datafile = "data.txt"       # strings like: "Juniper SRX Router 10.11.0.1 - ACFRA0020001|10.11.0.1"
result = "generated_tpl.xml"
tpl_name = "VPNCheck"


data_file = dir + "/" + datafile
result_file = dir + "/" + result

# print(zt.item_header(tpl_name), end="")

result = zt.item_header(tpl_name)

with open(data_file, 'r') as inf:
    data = inf.readlines()
    for string in data:
        line = string.split(sep='|')
        item_name = line[0]
        item_addr = line[1].strip('\n')
        # print(zt.item1(item_name, item_addr), end="")
        # print(zt.item2(item_name, item_addr), end="")
        result += zt.item1(item_name, item_addr)
        result += zt.item2(item_name, item_addr)


# print(zt.item_trailer(), end="")
result += zt.item_trailer()


with open(data_file, 'r') as inf:
    data = inf.readlines()
    for string in data:
        line = string.split(sep='|')
        item_name = line[0]
        item_addr = line[1].strip('\n')
        # print(zt.trigger1(tpl_name, item_addr, item_name), end="")
        # print(zt.trigger2(tpl_name, item_addr, item_name), end="")
        result += zt.trigger1(tpl_name, item_addr, item_name)
        result += zt.trigger2(tpl_name, item_addr, item_name)


# print(zt.trigger_trailer(), end="")
result += zt.trigger_trailer()

with open(result_file, 'w') as ofl:
    ofl.write(result)
