import os
import datetime as dt
import sys
import json


def check_backup(backup_dir):
    network_elements = []
    backups = dict()

    now = dt.datetime.now()
    delta = dt.timedelta(hours=backup_age)

    for NE in os.listdir(backup_dir):
        network_elements.append({'NE': NE})
        mtime = os.stat('{}/{}'.format(backup_dir, NE)).st_mtime
        backup_time = dt.datetime.fromtimestamp(mtime)

        if backup_time + delta < now:
            backups[NE] = 0
        else:
            backups[NE] = 1

    return network_elements, backups


if __name__ == '__main__':

    backup_dir = '/home/core-bup/backup'
    backup_age = 1  # Hours

    network_elements, backups = check_backup(backup_dir)
    if sys.argv[1] == 'all':
        print(json.dumps(network_elements))
    else:
        print(json.dumps(backups))

