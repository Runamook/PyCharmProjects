#!/usr/bin/python2
import commands
import json
from sys import argv


gsns = {'RND': ['185.77.18.2', '185.77.18.66'],
        'MSK': ['185.77.17.17', '185.77.17.145', '185.77.17.25', '185.77.17.153'],
        'EKT': ['185.77.16.145', '185.77.16.209'],
        'NIN': ['185.77.18.130', '185.77.18.194'],
        'SPB': ['217.169.81.73', '217.169.81.105'],
        'NSK': ['185.77.16.17', '185.77.16.81'],
        'SGSN-SPB': ['217.169.80.161'],
        'SGSN-NSK': ['185.77.16.1'],
        'SGSN-EKT': ['185.77.16.128'],
        'SGSN-MSK': ['185.77.17.1'],
        'SGSN-RND': ['185.77.18.1'],
        'SGSN-NIN': ['185.77.18.132'],
        'Full_EKB': ['185.174.131.209', '185.174.131.210']
        }

#_gsn_list = gsns['RND'] + gsns['MSK'] + gsns['EKT'] + gsns['NIN'] + gsns['SPB'] + gsns['NSK'] + gsns['Full_EKB']
_gsn_list = []
for region in gsns:
    for gsn in gsns[region]:
        _gsn_list.append(gsn)
gsn_list = ' '.join(_gsn_list)
fping = '/usr/bin/fping -q -c 10 -p 500 -'
command = '{} {}'.format(fping, gsn_list)


def get_gsn_data():
    response = commands.getstatusoutput(command)[1].split('\n')
    result = dict()
    for gsn_line in response:
        l = gsn_line.split()
        gsn_addr = l[0]
        gsn_loss_rate = l[4].split('/')[-1].strip(',%')
        if gsn_loss_rate != '100':
            min_rtt, max_rtt, avg_rtt = l[7].split('/')
        else:
            min_rtt, max_rtt, avg_rtt = '9999', '9999', '9999'
        result[gsn_addr] = {'LOSS': gsn_loss_rate, 'RTT': avg_rtt}

    return json.dumps(result)


def get_gsns():
    result = []
    for i in gsns.keys():
        for j in gsns[i]:
            result.append({'ip': j, 'region': i})
    return json.dumps(result)


if __name__ == '__main__':
    if argv[0] == 'all':
        print(get_gsns())
    else:
        print(get_gsn_data())
