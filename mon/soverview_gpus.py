#!/usr/bin/python3

import json
import subprocess
import sys
import re

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


class StripANSIEscapeSequences:
    """
    https://stackoverflow.com/a/2188410/5766934

    >>> StripANSIEscapeSequences()('\x1b[1m0.0\x1b[0m')
    '0.0'

    """
    def __init__(self):
        self.r = re.compile(r"""
            \x1b     # literal ESC
            \[       # literal [
            [;\d]*   # zero or more digits or semicolons
            [A-Za-z] # a letter
            """, re.VERBOSE).sub

    def __call__(self, s):
        return self.r("", s)


def print_table(
        data: 'list[dict, str]',
        header=(),
        just='lr',
        sep='  ',
        missing='-',
):
    """

    Args:
        data: list of dict or str
            dict: Keys indicate the column, values the values in the table
            str:
                char (i.e. length 1): row separator
                str (i.e. length != 1): printed as is, might break table layout
        header:
            Optional keys for the header. Will be filled with the keys from the dicts.
            Usecase: Enforce an ordering.
        just:
            Left or right just of the columns.
            Last one will be repeated.
        sep:
            Separator for the columns.
        missing:
            Placeholder for missing values.

    Returns:

    >>> print_table([{'a': 1, 'b': 2}, {'a': 10, 'c': 20}])
    =========
    a   b   c
    =========
    1   2   -
    10  -  20
    =========
    >>> print_table([{'a': 1, 'b': 2}, 'd', 'ef', {'a': 10, 'c': 20}])
    =========
    a   b   c
    =========
    1   2   -
    ddddddddd
    ef
    10  -  20
    =========
    """
    # Take header as suggestion for ordering, fill with remaining keys.
    keys = list(dict.fromkeys(list(header) + [
        k for d in data if isinstance(d, dict) for k in d.keys()]))

    data = [{k: str(v) for k, v in d.items()} if isinstance(d, dict) else d
            for d in data]

    strip_ANSI_escape_sequences = StripANSIEscapeSequences()

    widths = {
        k: max([len(strip_ANSI_escape_sequences(d.get(k, '')))
                for d in data if isinstance(d, dict)] + [len(k)])
        for k in keys
    }

    def just_fn(position, value, width):
        invisible_width = len(value) - len(strip_ANSI_escape_sequences(value))

        if just[min(position, len(just)-1)] == 'l':
            return value.ljust(width + invisible_width, ' ')
        else:
            return value.rjust(width + invisible_width, ' ')

    def format_line(widths, d: '[dict, str]' = None):
        if d is None:
            d = dict(zip(widths.keys(), widths.keys()))
        if isinstance(d, str):
            if len(d) == 1:
                return d * (
                        sum(widths.values()) + len(sep)
                        * (len(widths.values()) - 1)
                )
            else:
                return d
        return sep.join([just_fn(pos, d.get(k, missing), w)
                         for pos, (k, w) in enumerate(widths.items())])

    print(format_line(widths, '='))
    print(format_line(widths))
    print(format_line(widths, '='))
    for i, d in enumerate(data):
        print(format_line(widths, d))
    print(format_line(widths, '='))


def get_color(num_str, den_str):
    """
    >>> get_color('1', '2')
    '\\x1b[0;32m'
    >>> get_color('1M', '2M')
    '\\x1b[0;32m'
    """
    def to_int(s):
        try:
            return int(s)
        except ValueError:
            if s[-1] == 'M':
                return int(s[:-1]) * 1_000_000
            elif s[-1] == 'G':
                return int(float(s[:-1]) * 1_000_000_000)
            else:
                raise

    num = to_int(num_str)
    den = to_int(den_str)

    ratio = num / den

    if ratio <= 0.7:
        return c.Green
    elif ratio <= 0.9:
        return c.Yellow
    else:
        return c.Red


def merge_tres_tres_used(tres, tres_used):
    """
    >>> merge_tres_tres_used('cpu=128,mem=485000M,billing=128,gres/gpu=4,gres/gpu:a100=4', 'cpu=4,mem=485000M,gres/gpu=4,gres/gpu:a100=4')
    'cpu:4/128,mem:485000M/485000M,billing:?/128,gres/gpu:4/4,gres/gpu:a100:4/4'
    """
    def to_dict(s):
        if s:
            return dict([i.split('=', maxsplit=1)for i in s.split(',')])
        else:
            return {}

    tres = to_dict(tres)
    tres_used = to_dict(tres_used)

    new = []
    for k in [*tres.keys()] + [k for k in tres_used.keys() if k not in tres.keys()]:
        total = tres.get(k, "?")
        used = tres_used.get(k, "?")
        color = get_color(used, total) if '?' not in used + total else ''
        s = f'{k}:{color}{used}/{total}{c.Color_Off}'
        new.append(s)

    new = ','.join(new)
    return new




def main(filter='gpu'):
    stdout = subprocess.run(
        f"sinfo --json",
        check=True, shell=True, stdout=subprocess.PIPE,
        universal_newlines=True).stdout
    data = json.loads(stdout)

    delete = {
        'architecture': 'x86_64',
        'burstbuffer_network_address': '',
        'boards': 1,
        'boot_time': 1667924581,
        # 'comment': '',
        'cores': 64,
        'cpu_binding': 0,
        # 'cpu_load': 410,
        # 'extra': '',
        # 'free_memory': 409476,
        'cpus': 128,
        'last_busy': 1667924988,
        'features': '',
        'active_features': '',
        'gres': 'gpu:a100:4(S:0-1)',
        # 'gres_drained': 'N/A',
        'gres_used': 'gpu:a100:4(IDX:0-3),fpga:0',
        'mcs_label': '',
        # 'name': 'n2gpu1201',
        'next_state_after_reboot': 'invalid',
        'address': 'n2gpu1201',
        # 'hostname': 'n2gpu1201',
        # 'state': 'mixed',
        # 'state_flags': [],
        'next_state_after_reboot_flags': [],
        'operating_system': 'Linux 4.18.0-348.20.1.el8_5.x86_64 #1 SMP Tue Mar 8 12:56:54 EST 2022',
        'owner': None,
        'partitions': ['all', 'gpu'],
        'port': 6818,
        'real_memory': 485000,
        # 'reason': '',
        'reason_changed_at': 0,
        'reason_set_by_user': None,
        'slurmd_start_time': 1667924685,
        'sockets': 2,
        'threads': 1,
        'temporary_disk': 0,
        'weight': 1,
        # 'tres': 'cpu=128,mem=485000M,billing=128,gres/gpu=4,gres/gpu:a100=4',
        'slurmd_version': '21.08.6',
        'alloc_memory': 131072,
        'alloc_cpus': 16,
        'idle_cpus': 112,
        # 'tres_used': 'cpu=16,mem=128G,gres/gpu=4,gres/gpu:a100=4',
        'tres_weighted': 16.0,
    }.keys()

    table = []
    table2 = []

    state_keys = [
        'name',
        'comment',
        'extra',
        # 'free_memory',
        # 'cpus',
        # 'gres',
        # 'gres_drained',
        # 'gres_used',
        'state',
        'state_flags',
        # 'real_memory',
        'reason',
        # 'tres',
        # 'alloc_memory',
        # 'alloc_cpus',
        # 'idle_cpus',
        # 'tres_used,
    ]

    for node in data['nodes']:
        if filter in node['hostname']:
            for k in delete:
                del node[k]

            node['tres_used/tres'] = merge_tres_tres_used(node['tres'], node['tres_used'])
            del node['tres_used']
            del node['tres']

            # print(node)
            table.append({k: node[k] for k in state_keys if k in node})
            table2.append({
                k: v for k, v in node.items() if k not in state_keys
            })
            # break

    print_table(table)
    print_table(table2)


if __name__ == '__main__':
    main(*sys.argv[1:])
