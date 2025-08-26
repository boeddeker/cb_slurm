#!/usr/bin/python3

import sys
import os
import subprocess
import json
import re
import collections
import math


class c:  # noqa
    Color_Off = '\033[0m'  # Text Reset
    Black = '\033[30m'  # Black
    Red = '\033[31m'  # Red
    Green = '\033[32m'  # Green
    Yellow = '\033[33m'  # Yellow
    Blue = '\033[34m'  # Blue
    Purple = '\033[35m'  # Purple
    Cyan = '\033[36m'  # Cyan
    White = '\033[37m'  # White
    BG_Black = '\033[40m'  # Background Black
    BG_White = '\033[47m'  # Background Black

    # Reset_Reverse = '\033[0;07m'  # First reset, then Switch FG and BG
    Reverse = '\033[7m'  # Switch FG and BG
    Reverse_Reset = '\033[27m'  # Disable switch FG and BG

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


def parse_res(res, raw=False):
    """
    >>> tres_used = "cpu=16,mem=367188M,gres\/gpu=4,gres\/gpu:a100=4"
    >>> tres = "cpu=128,mem=485000M,billing=128,gres\/gpu=4,gres\/gpu:a100=4"
    >>> parse_res(tres_used)
    {'cpu': 16, 'mem': 367188, 'gres_gpu': 4, 'gres_gpu:a100': 4}
    >>> parse_res(tres)
    {'cpu': 128, 'mem': 485000, 'billing': 128, 'gres_gpu': 4, 'gres_gpu:a100': 4}
    """
    # pre 23: None
    # since 23: ''
    if res is None or res == '':
        return {}

    orig = res

    res = [
        r.split('=')
        for r in res.strip().split(',')
    ]
    try:
        res = {
            re.sub('[\\\\/]+', '_', k): v
            for k, v in res
        }
    except Exception:
        raise Exception(res, orig)
    # for k in [
    #         'cpu',
    #         r'gres_gpu:a100',
    #         'gres_gpu:rtx2080ti',
    #         'billing',
    #         'gres_gpu',
    #         'gres_fpga',
    #         'gres_fpga:u280',
    #         'gres_fpga:520n',
    # ]:
    #     if k in res:
    #         res[k] = int(res[k])
    for k in res:
        try:
            res[k] = int(res[k])
        except ValueError:  # e.g. ValueError: invalid literal for int() with base 10: '187.50G'
    # for k in ['mem']:
    #     if k in res:
            if res[k][-1] == 'M':
                res[k] = int(res[k].replace('M', ''))
            elif res[k][-1] == 'G':
                res[k] = int(float(res[k].replace('G', '')) * 1000)
            elif res[k][-1] == 'T':
                res[k] = int(float(res[k].replace('T', '')) * 1000 * 1000)
            else:
                raise NotImplementedError(k, res)

    # for old, new in [
    #     ('gres_gpu:a100', 'gpu'),
    #     ('gres_gpu', 'gpu'),
    # ]:
    #     if old in res:
    #         assert new not in res, res
    #         res[new] = res[old]
    return res


class _RatioFracEntry:
    def __init__(self, reduction):
        self._value = []
        self.reduction = reduction

    def __iadd__(self, other):
        self._value.append(other)
        return self

    def __str__(self):
        return str(self._numeric)

    def __truediv__(self, other):
        if isinstance(other, _RatioFracEntry):
            return self._numeric / other._numeric
        else:
            raise NotImplementedError

    # @property
    # def value(self):
    #     return sum(self._value)

    @property
    def _numeric(self):
        return self.reduction(self._value)


class RatioField:
    _shared = collections.defaultdict(list)

    @classmethod
    def reset(cls, key=None):
        if key is None:
            cls._shared = collections.defaultdict(list)
        else:
            cls._shared[key] = []

    def __init__(
            self,
            key,
            rjust=True,
            highlight: [None, 'pbar', 'color', 'invcolor'] = None,
            format: str = '{}/{}',
            nom_format='{x:_}',
            den_format='{x:_}',
            reduction=sum
    ):
        self._shared[key].append(self)
        self.key = key
        self.nom = _RatioFracEntry(reduction=reduction)
        self.den = _RatioFracEntry(reduction=reduction)
        self.format = format
        self.rjust = rjust
        self.highlight = highlight
        self.reduction = reduction
        self.nom_format = nom_format
        self.den_format = den_format

    @property
    def ratio(self):
        return self.nom / self.den

    @property
    def nom_str(self):
        return self.nom_format.format(x=self.nom._numeric)

    @property
    def den_str(self):
        return self.den_format.format(x=self.den._numeric)

    def __repr__(self):
        """
        >>> f = RatioField('abc')
        >>> f.nom += 10
        >>> f.den += 20
        >>> print(f)
        10/20
        >>> f2 = RatioField('abc')
        >>> f2.nom += 1
        >>> f2.den += 2
        >>> print(f2)
         1/ 2
        >>> f3 = RatioField('abc', highlight='pbar')
        >>> f3.nom += 1
        >>> f3.den += 2
        >>> print(repr(str(f3)))
        '\\x1b[0;07m 1\\x1b[0m/ 2'
        """

        if self.rjust:
            len_nom = max([len(e.nom_str) for e in self._shared[self.key]])
            len_den = max([len(e.den_str) for e in self._shared[self.key]])
            nom_str = self.nom_str.rjust(len_nom)
            den_str = self.den_str.rjust(len_den)
            s = self.format.format(nom_str, den_str)
        else:
            s = self.format.format(self.nom_str, self.den_str)

        if self.highlight is None:
            pass
        elif self.highlight == 'pbar':
            s = pbarstring(s, self.ratio)
        elif self.highlight == 'color':
            ratio = self.ratio
            if ratio <= 0.7:
                color = c.Green
            elif ratio <= 0.9:
                color = c.Yellow
            else:
                color = c.Red
            s = f'{color}{s}{c.Color_Off}'
        else:
            raise NotImplementedError(self.highlight)

        return s


def pbarstring(string, ratio):
    index = round(ratio * len(string))
    string = string[:index] + c.Color_Off + string[index:]
    # string = string[:index] + c.Reverse_Reset + string[index:]
    string = f'{c.Reverse}{string}'
    return string


dummy_nodes_data = [{
       "architecture": "x86_64",
       "burstbuffer_network_address": "",
       "boards": 1,
       "boot_time": 1668149071,
       "comment": "",
       "cores": 64,
       "cpu_binding": 0,
       "cpu_load": 12831,
       "extra": "",
       "free_memory": 105139,
       "cpus": 128,
       "last_busy": 1668376998,
       "features": "",
       "active_features": "",
       "gres": "",
       "gres_drained": "N\/A",
       "gres_used": "gpu:0,fpga:0",
       "mcs_label": "",
       "name": "n2cn0167",
       "next_state_after_reboot": "invalid",
       "address": "n2cn0167",
       "hostname": "n2cn0167",
       "state": "allocated",
       "state_flags": [
       ],
       "next_state_after_reboot_flags": [
       ],
       "operating_system": "Linux 4.18.0-348.20.1.el8_5.x86_64 #1 SMP Tue Mar 8 12:56:54 EST 2022",
       "owner": None,
       "partitions": [
         "all",
         "normal"
       ],
       "port": 6818,
       "real_memory": 240000,
       "reason": "",
       "reason_changed_at": 0,
       "reason_set_by_user": None,
       "slurmd_start_time": 1668149154,
       "sockets": 2,
       "threads": 1,
       "temporary_disk": 0,
       "weight": 1,
       "tres": "cpu=128,mem=240000M,billing=128",
       "slurmd_version": "21.08.6",
       "alloc_memory": 240000,
       "alloc_cpus": 128,
       "idle_cpus": 0,
       "tres_used": "cpu=128,mem=240000M",
       "tres_weighted": 128.0
},     {
       "architecture": "x86_64",
       "burstbuffer_network_address": "",
       "boards": 1,
       "boot_time": 1666156440,
       "comment": "",
       "cores": 64,
       "cpu_binding": 0,
       "cpu_load": 13503,
       "extra": "",
       "free_memory": 710207,
       "cpus": 128,
       "last_busy": 1668028735,
       "features": "",
       "active_features": "",
       "gres": "",
       "gres_drained": "N\/A",
       "gres_used": "gpu:0,fpga:0",
       "mcs_label": "",
       "name": "n2lcn0165",
       "next_state_after_reboot": "invalid",
       "address": "n2lcn0165",
       "hostname": "n2lcn0165",
       "state": "mixed",
       "state_flags": [
       ],
       "next_state_after_reboot_flags": [
       ],
       "operating_system": "Linux 4.18.0-348.20.1.el8_5.x86_64 #1 SMP Tue Mar 8 12:56:54 EST 2022",
       "owner": None,
       "partitions": [
         "all",
         "largemem"
       ],
       "port": 6818,
       "real_memory": 950000,
       "reason": "",
       "reason_changed_at": 0,
       "reason_set_by_user": None,
       "slurmd_start_time": 1666156520,
       "sockets": 2,
       "threads": 1,
       "temporary_disk": 0,
       "weight": 1,
       "tres": "cpu=128,mem=950000M,billing=128",
       "slurmd_version": "21.08.6",
       "alloc_memory": 911360,
       "alloc_cpus": 114,
       "idle_cpus": 14,
       "tres_used": "cpu=114,mem=890G",
       "tres_weighted": 114.0
     },
     {
       "architecture": "x86_64",
       "burstbuffer_network_address": "",
       "boards": 1,
       "boot_time": 1667204324,
       "comment": "",
       "cores": 64,
       "cpu_binding": 0,
       "cpu_load": 12787,
       "extra": "",
       "free_memory": 946103,
       "cpus": 128,
       "last_busy": 1668008206,
       "features": "",
       "active_features": "",
       "gres": "",
       "gres_drained": "N\/A",
       "gres_used": "gpu:0,fpga:0",
       "mcs_label": "",
       "name": "n2lcn0166",
       "next_state_after_reboot": "invalid",
       "address": "n2lcn0166",
       "hostname": "n2lcn0166",
       "state": "allocated",
       "state_flags": [
       ],
       "next_state_after_reboot_flags": [
       ],
       "operating_system": "Linux 4.18.0-348.20.1.el8_5.x86_64 #1 SMP Tue Mar 8 12:56:54 EST 2022",
       "owner": None,
       "partitions": [
         "all",
         "largemem"
       ],
       "port": 6818,
       "real_memory": 950000,
       "reason": "",
       "reason_changed_at": 0,
       "reason_set_by_user": None,
       "slurmd_start_time": 1667204401,
       "sockets": 2,
       "threads": 1,
       "temporary_disk": 0,
       "weight": 1,
       "tres": "cpu=128,mem=950000M,billing=128",
       "slurmd_version": "21.08.6",
       "alloc_memory": 949888,
       "alloc_cpus": 128,
       "idle_cpus": 0,
       "tres_used": "cpu=128,mem=949888M",
       "tres_weighted": 128.0
     }
]


def workload(
    nodes=dummy_nodes_data
):
    """
    >>> from pprint import pprint
    >>> pprint(workload())
    {'all,largemem': {'Partition': 'all,largemem (2)',
                      'cpu': 242 / 256,
                      'mem': 1_839_888M / 1_900_000M},
     'all,normal': {'Partition': 'all,normal (1)',
                    'cpu': 128 / 128,
                    'mem':   240_000M /   240_000M}}
    >>> print_table(workload().values())
    ====================================================
    Partition               cpu                      mem
    ====================================================
    all,normal (1)    128 / 128    240_000M /   240_000M
    all,largemem (2)  242 / 256  1_839_888M / 1_900_000M
    ====================================================
    """
    data = {}

    for node in nodes:
        partitions = ','.join(node['partitions'])
        tres = parse_res(node['tres'])
        tres_used = parse_res(node['tres_used'])
        # key = (partitions, tuple(tres.items()))

        ignore = ['billing', 'gres_gpu', 'gres_fpga']

        if partitions not in data:
            data[partitions] = {
                'Partition': [partitions, 0],
                **{
                    k: RatioField(
                        key=f'{k}',
                        format=(
                            '{} / {}'
                            if k != 'mem' else
                            '{}M / {}M'
                        ),
                    )
                    for k, v in tres.items()
                    if k not in ignore
                }
            }

        data[partitions]['Partition'][1] += 1

        for k, v in tres.items():
            if k not in ignore:
                data[partitions][k].den += v
        for k, v in tres_used.items():
            if k not in ignore:
                data[partitions][k].nom += v

    for v in data.values():
        v['Partition'] = f'{v["Partition"][0]} ({v["Partition"][1]})'
    return data


def ld_to_dl(ld):
    """

    Assumes each dict has the same keys.
    Here not an issue.

    >>> ld_to_dl([{'a':0, 'b':2, 'c':4}, {'a':1, 'b':3, 'c':5}])
    {'a': [0, 1], 'b': [2, 3], 'c': [4, 5]}
    """
    # Code: https://stackoverflow.com/a/5559178/5766934
    dl = collections.defaultdict(list)
    for d in ld:
        for key, val in d.items():
            dl[key].append(val)
    return dict(dl)


def ldd_to_ddl(ldd):
    """
    Outer list to inner list.

    >>> ldd_to_ddl([{'a': {'A': 1}}, {'b': {'B': 2}}])
    {'a': {'A': [1]}, 'b': {'B': [2]}}
    """
    return {k: ld_to_dl(v) for k, v in ld_to_dl(ldd).items()}



def transpose_dict_of_dict(dct):
    """
    >>> transpose_dict_of_dict({'A': {'1': 1, '2': 2}, 'B': {'1': 101, '2': 102}})
    {'1': {'A': 1, 'B': 101}, '2': {'A': 2, 'B': 102}}
    """
    # https://stackoverflow.com/a/21977805/5766934
    d = collections.defaultdict(dict)
    for key1, inner in dct.items():
        for key2, value in inner.items():
            d[key2][key1] = value
    return dict(d)


def main_v2():
    stdout = subprocess.run(
        # f"sinfo --json",  # pre 23.11 (maybe 22?)
        f"scontrol show node --json",
        check=True, shell=True, stdout=subprocess.PIPE,
        universal_newlines=True).stdout
    sinfo = json.loads(stdout)

    data = collections.defaultdict(list)

    # try:
    nodes = sinfo['nodes'] # pre 23.11 (maybe 22?)

    for node in nodes:
        partitions = {'Partition': ','.join(node['partitions'])}
        tres = parse_res(node['tres'])
        tres_used = parse_res(node['tres_used'])

        non_printed_group_key = tuple(tres.items())

        if 'state_flags' not in node:
            # pre 23: state_flags is a list and state a string
            # since 23: state is a list and state_flags doesn't exits
            node['state_flags'] = node['state']

        if node['state_flags'] in [
                [],
                # ['COMPLETING'],
          #      ['PLANNED']
        ]:
            partitions['state_flags'] = ''
        elif 'DRAIN' in node['state_flags']:
            partitions['state_flags'] = 'DRAIN'
            partitions['Partition'] = '*'
            non_printed_group_key = ''
        else:
            partitions['state_flags'] = ', '.join(node['state_flags'])

        data[tuple(partitions.items()), non_printed_group_key].append(transpose_dict_of_dict({
            'tres': tres,
            'tres_used': tres_used,
        }))

    def reduce_sum(tres_used, tres):
        return sum(tres_used), sum(tres)

    def reduce_mean(tres_used, tres):
        if len(set(tres)) == 1:
            return sum(tres_used) / len(tres), tres[0]
        else:
            return sum(tres_used) / len(tres), sum(tres) / len(tres)

    meta_keys = set()

    for reduce in [
            # reduce_mean,
            reduce_sum,
    ]:
        print_data = []

        for (partitions, _), d in data.items():
            # new = {}
            # new['Partition'] = f'{partitions} ({len(d)})'
            # new['co']
            new = {'N': len(d), **dict(partitions)}
            meta_keys |= set(new.keys())

            d = ldd_to_ddl(d)

            tres = d['cpu']['tres']
            if len(set(tres)) == 1:
                new['cpu/N'] = tres[0]
                meta_keys |= {'cpu/N'}

            tres = d['mem']['tres']
            if len(set(tres)) == 1:
                new['mem/N'] = f'{round(tres[0] / 1000)} GB'
                meta_keys |= {'mem/N'}

            for k, v in d.items():
                if k in ['billing',
                         # 'gres_gpu',
                         'gres_fpga',
                         ]:
                    continue
                try:
                    tres_used, tres = reduce(v.get('tres_used', [0]), v['tres'])
                except Exception:
                    raise Exception(v, k)

                tres_used, tres = reduce(v.get('tres_used', [0]), v['tres'])
                # tres = reduce()

                new[k] = (tres_used, tres)


            print_data.append(new)

        columns = list(dict.fromkeys([k for d in print_data for k in d]).keys())

        def to_string(number, c, width=None):
            try:
                if c in ['mem']:
                    if width is None:
                        return f'{round(number / 1000):_}'
                    else:
                        return f'{round(number / 1000):{width}_}'
                else:
                    if isinstance(number, float):
                        number = round(number, 2)
                        spec = '.2f'
                    else:
                        spec = ''
                    if width is None:
                        return f'{number:_{spec}}'
                    else:
                        return f'{number:{width}_{spec}}'
            except Exception:
                raise ValueError(type(number), number, c, width)

        format_spec = {}
        for c in columns:
            if c not in meta_keys:
                format_spec[c] = [
                    max([len(to_string(e.get(c, [0, 0])[0], c)) for e in print_data]),
                    max([len(to_string(e.get(c, [0, 0])[1], c)) for e in print_data]),
                ]

        final_print_data = []
        for d in print_data:
            new = {}
            full = False
            for c, v in d.items():
                if c in meta_keys:
                    new[c] = v
                else:
                    tres_used, tres = v
                    ratio = tres_used / tres
                    if ratio >= 0.98:
                        full = True
                    new[{'mem': 'mem / GB'}.get(c, c)] = pbarstring(
                        f'{to_string(tres_used, c, format_spec[c][0])} / {to_string(tres, c, format_spec[c][1])}',
                        ratio
                    )
            color = None
            if 'DRAIN' in new['state_flags'] or 'RESERVED' in new['state_flags']:
                red = '\033[31m'
                color = red
            if full:
                yellow = '\033[33m'
                color = yellow
            if color:
                reset = '\033[0m'
                # The replace is nessesary, because I use curtsies.FmtStr.from_str
                # in vatch, that lacks support for the reset code 27
                new = {k: color + str(v).replace("\033[0m", "\033[0m" + color) + reset for k, v in new.items()}
            # print(new)
            final_print_data.append(new)

        # final_print_data = sorted(final_print_data, key=lambda x: [x['state_flags'], x['Partition']])

        print_table(final_print_data, just='rllrrrrr')



def main():
    stdout = subprocess.run(
        f"sinfo --json",
        check=True, shell=True, stdout=subprocess.PIPE,
        universal_newlines=True).stdout
    data = json.loads(stdout)

    p_tres = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
    p_tres_used = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))

    summary = collections.defaultdict(lambda: collections.defaultdict(lambda: []))

    for node in data['nodes']:

        partitions = ','.join(node['partitions'])

        tres = parse_res(node['tres'])
        tres_used = parse_res(node['tres_used'])

        key = (partitions, tuple(tres.items()))

        for k in tres.keys():
            # if k in summary[key]:
            summary[key][k].append(tres_used.get(k, 0))

        for k, v in tres.items():
            try:
                p_tres[key][k] += v
            except Exception:
                raise Exception(k, v, tres)
        for k, v in tres_used.items():
            try:
                p_tres_used[key][k] += v
            except Exception:
                raise Exception(k, v, tres_used)

    def format_(k, used, total, avg=True):
        if avg:
            used = sum(used) / len(used)
        else:
            total = total * len(used)
            used = sum(used)

        if k != 'mem':
            total = f'{total:_}'
            if avg:
                used = f'{used:{len(total) + 3}_.2f}'
            else:
                used = f'{used:{len(total) + 3}_}'
            return f'{k}:{sep}{used}{sep}/{sep}{total}'
        else:
            total = f'{total // 1000:_}'
            used = f'{used / 1000:{len(total) + 3}_.2f}'
            return f'{k}:{sep}{used}G{sep}/{sep}{total}G'

    def format_2(k, used, total, avg=True, sep='|'):
        if avg:
            used = sum(used) / len(used)
        else:
            total = total * len(used)
            used = sum(used)

        ratio = used / total

        if avg:
            # key: (used, total)
            width = {
                'cpu': (6, 3),
                'mem': (6, 5),
            }
        else:
            width = {
                'cpu': (7, 7),
                'mem': (10, 9),
            }

        if k != 'mem':
            total = f'{total:{width.get(k, ["", ""])[1]}_}'
            if avg:
                # used = f'{used:{len(total) + 3}_.2f}'
                used = f'{used:{width.get(k, [""])[0]}_.2f}'
            else:
                # used = f'{used:{len(total) + 3}_}'
                used = f'{used:{width.get(k, [""])[0]}_}'
            r = f'{used}{sep}/{sep}{total}'
        else:
            total = f'{total // 1000:{width.get(k, ["", ""])[1]}_}'
            used = f'{used / 1000:{width.get(k, [""])[0]}_.2f}'
            r = f'{used}G{sep}/{sep}{total}G'


        # if k in width:
        #     r = r.rjust(width[k])

        return pbarstring(r, ratio)

    sep = '|'

    print(summary)

    for avg in [True, False]:
        tbl = []
        msg = []
        for key, tres_used in summary.items():
            # print(key)
            partitions, tres = key
            tres = dict(tres)

            num_nodes = len(list(tres_used.values())[0])

            line = [
                format_(k, tres_used[k], tres[k], avg)
                # f'{k}:{sep}{sum(tres_used[k]) / len(tres_used[k]):_{len(str(tres[k]))}.2f}{sep}/{sep}{tres[k]:_}'
                for k in tres
                if k not in ['billing',
                             # 'gres_gpu',
                             'gres_fpga']
            ]
            msg.append(sep.join([f'{partitions} ({num_nodes})', *line]))

            tbl.append({
                'Partition': f'{partitions} ({num_nodes})',
                **{
                    k: format_2(k, tres_used[k], tres[k], avg, sep=' ')
                    for k in tres
                    if k not in ['billing',
                                 # 'gres_gpu',
                                 'gres_fpga']
                }
            })

        # tbl_3 = [
        #     {
        #         'Partition': f'{partitions} ({len(list(tres_used.values())[0])})',
        #         **{
        #             k: RatioField(k, tres_used[k], v, highlight='pbar')
        #             for k, v in tres
        #             if k not in ['billing', 'gres_gpu', 'gres_fpga']
        #         }
        #     }
        #     for (partitions, tres), tres_used in summary.items()
        # ]

        # msg = '\n'.join(msg)
        # subprocess.run(['column', '-e', '-t', '-s', sep], input=msg, universal_newlines=True)
        # print('')

        print_table(tbl, just='rllrrrrr')
        # print_table(tbl_3, just='lrrrrr')


if __name__ == '__main__':
    main_v2(*sys.argv[1:])
    # main(*sys.argv[1:])
