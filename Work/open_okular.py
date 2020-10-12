#!/usr/bin/python3

import subprocess as sp

okular = '/usr/bin/okular'
data_dir = '/home/egk/.local/share/okular/docdata'


def find_files():
    file_list = []
    files_to_open = []
    today = f" {sp.check_output(['/bin/date', '+%b %d']).decode().strip()} "
    command = f'/bin/ls -ltr {data_dir}'.split()
    all_files = sp.check_output(command, stderr=sp.STDOUT, shell=False).decode().split('\n')
    for pdf_filename in all_files:
        if today in pdf_filename:
            file_list.append(' '.join(pdf_filename.split()[8:]))

    for pdf_filename in file_list:
        with open(f'{data_dir}/{pdf_filename}', 'r') as f:
            file_data = f.read().split('\n')
            for line in file_data:
                if 'documentInfo url' in line:
                    files_to_open.append(line[19:-2])

    return files_to_open


def open_files(file_list):
    for file_name in file_list:
        command = [okular, file_name]
        # print(f'Command: {command}')
        sp.check_output(command, stderr=sp.STDOUT, shell=False)


if __name__ == '__main__':
    open_files(find_files())
