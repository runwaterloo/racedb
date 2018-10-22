#!/usr/bin/env python
""" Upgrade packages listed in requirements.txt

Needs to be run as the application user, in the
correct venv
"""

import os
import subprocess


def main():
    os.system('pip install --upgrade pip')
    with open('requirements.txt', 'r') as f:
        lines = f.readlines()
        packages = [x.split('==')[0] for x in lines]
    for p in packages:
        os.system('pip install --upgrade {}'.format(p))
    freeze_dict = get_freeze_dict()
    new_freeze = ''
    for p in packages:
        newline = '{}=={}\n'.format(p, freeze_dict[p])
        new_freeze += newline
    with open('requirements.txt', 'w') as f:
        f.write(new_freeze)


def get_freeze_dict():
    freeze_dict = {}
    pip_freeze = subprocess.check_output(['pip', 'freeze'])
    for line in pip_freeze.splitlines():
        parts = line.decode('utf-8').split('==')
        freeze_dict[parts[0]] = parts[1]
    return freeze_dict


if __name__ == '__main__':
    main()
