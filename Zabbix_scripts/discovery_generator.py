import csv


infile = "/home/egk/Work/Misc/Zabbix_net_srv/Devices.csv"

header = '{"data":['
footer = ']}'
separator = ' , '


def record_maker(name, address, customer, location):
    result = '{"{#VPNNAME}":"%s", "{#VPNADDR}":"%s", "{#VPNCUSTOMER}":"%s", "{#VPNLOCATION}":"%s"}' % (name, address, customer, location)
    return result


total_result = header

with open(infile, "r") as file:
    # reader = csv.reader(file, delimiter=';', quoting=csv.QUOTE_ALL)
    reader = csv.reader(file)
    i = 0
    for row in reader:
        if i < 1:
            i += 1
            continue
        customer = row[0]
        location = row[1]
        name = row[2]
        address = row[3]

        record = record_maker(name, address, customer, location)

        total_result += record
        total_result += separator

total_result += footer

print(total_result)
