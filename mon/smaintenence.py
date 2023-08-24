#!/usr/bin/python3

import sys
import os
import subprocess
import json
import re
import collections
import math
import pprint


class c:  # noqa
    Color_Off = '\033[0m'  # Text Reset
    Black = '\033[0;30m'  # Black
    Red = '\033[0;31m'  # Red
    Green = '\033[0;32m'  # Green
    Yellow = '\033[0;33m'  # Yellow
    Blue = '\033[0;34m'  # Blue
    Purple = '\033[0;35m'  # Purple
    Cyan = '\033[0;36m'  # Cyan
    White = '\033[0;37m'  # White

    BG_Black = '\033[0;40m'  # Background Black
    BG_Red = '\033[0;41m'  # Background Red
    BG_Green = '\033[0;42m'  # Background Green
    BG_Yellow = '\033[0;43m'  # Background Yellow
    BG_Blue = '\033[0;44m'  # Background Blue
    BG_Purple = '\033[0;45m'  # Background Purple
    BG_Cyan = '\033[0;46m'  # Background Cyan
    BG_White = '\033[0;47m'  # Background Black

    Reverse = '\033[0;07m'  # Switch FG and BG

    # 00 none
    # 01 bold
    # 04 underscore
    # 05 blink
    # 07 reverse
    # 08 concealed

    @classmethod
    def print_info(cls, *args):
        args = ' '.join([str(a) for a in args])
        print(c.Blue + args + c.Color_Off)

def parse(
    lines
):
    """
    >>> from paderbox.utils.pretty import pprint
    >>> s = 'ReservationName=hsmptest StartTime=1671442626 EndTime=1685397600 Duration=161-12:22:54 Nodes=n2cn1136 NodeCnt=1 CoreCnt=128 Features=(null) PartitionName=normal Flags=SPEC_NODES TRES=cpu=128 Users=(null) Groups=(null) Accounts=hpc-prf-ekiapp,pc2-mitarbeiter Licenses=(null) State=ACTIVE BurstBuffer=(null) Watts=n/a MaxStartDelay=(null)'
    >>> pprint(parse(s))
    [{'ReservationName': 'hsmptest',
      'StartTime': '1671442626',
      'EndTime': '1685397600',
      'Duration': '161-12:22:54',
      'Nodes': 'n2cn1136',
      'NodeCnt': '1',
      'CoreCnt': '128',
      'Features': '(null)',
      'PartitionName': 'normal',
      'Flags': 'SPEC_NODES',
      'TRES': 'cpu=128',
      'Users': '(null)',
      'Groups': '(null)',
      'Accounts': 'hpc-prf-ekiapp,pc2-mitarbeiter',
      'Licenses': '(null)',
      'State': 'ACTIVE',
      'BurstBuffer': '(null)',
      'Watts': 'n/a',
      'MaxStartDelay': '(null)'}]
    """
    data = []
    for line in lines.strip().split('\n\n'):
        line_data = {}
        data.append([line, line_data])
        for kv in line.split():
            try:
                k, v = kv.split('=', maxsplit=1)
                assert k not in line_data, (kv, line)
            except ValueError:
                pass
            else:
                line_data[k] = v

    return data


if __name__ == '__main__':


    env = os.environ.copy()
    env.pop('SLURM_TIME_FORMAT', '%s')

    stdout = subprocess.run(
        f"scontrol show reservation",
        check=True, shell=True, stdout=subprocess.PIPE,
        universal_newlines=True, env=env).stdout

    data = parse(stdout)

    p = []
    for l, d in data:
        # StartTime = int(d['StartTime'])
        # EndTime = int(d['EndTime'])
        # hours = (EndTime - StartTime) / 3600
        # if hours >

        # s = pprint.pformat(d)
        if int(d['NodeCnt']) >= 10:
            l = l.replace('NodeCnt', f'{c.Red}NodeCnt{c.Color_Off}')
        else:
            l = l.replace('NodeCnt', f'{c.Green}NodeCnt{c.Color_Off}')

        l = l.replace('n2gpu', f'{c.Black}{c.BG_Red}n2gpu{c.Color_Off}')
        p.append(l)

    print('\n\n'.join(p))


# scontrol show reservation --oneline | grep NodeCnt
