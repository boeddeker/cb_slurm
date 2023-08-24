#!/usr/bin/python3

import sys
import os
import subprocess
import json
import getpass
import re
import collections
import math
import textwrap

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


def shorten(s, width, placeholder='[...]'):
    """
    shorten based on chars, not words (textwrap.shorten shotens only complete words)

    Comment of https://stackoverflow.com/a/39017530/5766934
    """
    return s[:width] if len(s) <= width else s[:width-len(placeholder)] + placeholder


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
        just: 'str | dict' ='lr',
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

    if isinstance(just, dict):
        assert header == (), header
        header = just.keys()
        just = ''.join(just.values())

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

    # print(format_line(widths, '='))
    # print(format_line(widths))
    # print(format_line(widths, '='))
    for i, d in enumerate(data):
        if i % 40 == 0:
            print(format_line(widths, '='))
            print(format_line(widths))
            print(format_line(widths, '='))
        print(format_line(widths, d))
    print(format_line(widths, '='))


sep = '|'

# cbj   1037549_22  mixlog.sh         COMPLETED      5G      00:01:42  02:00:00   1       1      n2cn1196  normal

from datetime import timedelta, datetime

now = datetime.now()
yesterday = now - timedelta(days=1)
tomorrow = now + timedelta(days=1)
lastweek = now - timedelta(days=7)
nextweek = now + timedelta(days=7)
hourago = now - timedelta(hours=1)

my_user = getpass.getuser()


def format_datetime(time, highlight_hourago=False):
    """
    >>> format_datetime(1662456138)
    '11:22:18'
    >>> format_datetime(1662356138)
    '2022-09-05 07:35:38'
    """
    if time == 0:
        return 'Running'
    time = datetime.fromtimestamp(time)
    if now > time:
        # Running or Stopped
        if time > yesterday and time.strftime('%a') == now.strftime('%a'):
            # return str(time.time())
            ret = str(time.strftime('%H:%M'))
            if highlight_hourago and time > hourago:
                ret = f'{c.Reverse}{ret}{c.Color_Off}'
            return ret
        elif time > lastweek:
            # return str(time.strftime('%a %X'))
            return str(time.strftime('%a %H:%M'))
        else:
            return str(time)
    else:
        # Pending
        if time < tomorrow and time.strftime('%a') == now.strftime('%a'):
            return f'{c.Red}{time.time()}{c.Color_Off}'
        elif time < nextweek:
            return f"{c.Red}{time.strftime('%a %X')}{c.Color_Off}"
        else:
            return f'{c.Red}{time}{c.Color_Off}'


def expand_nodes(nodes):
    """
    >>> expand_nodes('n2gpu1222')
    ['n2gpu1222']
    >>> expand_nodes('n2cn[1007-1011]')
    ['n2cn1007', 'n2cn1008', 'n2cn1009', 'n2cn1010', 'n2cn1011']
    >>> expand_nodes('n2cn[1037,1040,0106-0107]')
    ['n2cn1037', 'n2cn1040', 'n2cn0106', 'n2cn0107']

    """
    def do(s: str, prefix=''):
        if not s:
            yield prefix
        elif s[0] == '[':
            idx = s.rfind(']')
            yield from [
                prefix + e + postfix
                for e in do(s[1:idx])
                for postfix in do(s[idx+1:])
            ]
        elif s[0] in [',']:
            yield prefix
            yield from do(s[1:], '')
        elif s[0] in ['-']:
            start = prefix
            i = iter(do(s[1:], ''))
            stop = next(i)

            assert start.isdigit(), start
            assert stop.isdigit(), stop
            assert len(start) == len(stop), (start, stop)

            yield from [f'{val:0{len(start)}}' for val in range(int(start), int(stop)+1)]
            yield from i
        else:
            yield from do(s[1:], prefix + s[0])

    return list(do(nodes))


def main(start=None, *options):
    mine = False

    # for o in options:
    #     if o in ['mine', '--mine']:
    #         mine = True

    if len(options) == 1 and options[0] in ['mine', '--mine']:
        mine = True
    elif len(options) == 0:
        pass
    else:
        raise ValueError(options)

    if start is None:
        start = "$(date -d '4 hour ago' +%D-%R)"

    env = os.environ.copy()
    env.pop('SLURM_TIME_FORMAT', '')

    stdout = subprocess.run(
        f"sacct --json -S {start}",
        check=True, shell=True, stdout=subprocess.PIPE,
        universal_newlines=True, env=env).stdout
    data = json.loads(stdout)

    # sacct: Has information over finished jobs
    # squeue:
    #   Has correct start time for pending jobs, key "start_time"
    #   Has tasks information, key "tasks"
    squeue_stdout = subprocess.run(
        # f"squeue --json -S {start}",
        f"squeue --json",
        check=True, shell=True, stdout=subprocess.PIPE,
        universal_newlines=True, env=env).stdout
    datas_queue = json.loads(squeue_stdout)

    datas_queue = {
        e['job_id']: e
        for e in datas_queue['jobs']
    }

    lines = []
    lines2 = []
    lines.append(['User', 'JobID', 'Name', 'State', 'Elapsed', 'Start', 'End', 'Required', 'Partition', 'Nodes'])
    lines.append([])

    if 'jobs' not in data:
        raise ValueError('\n' + stdout)

    for job in data['jobs']:
        user = job['user']

        jobid = job['job_id']
        if job['array']['task_id'] is not None:
            jobid = f"{job['array']['job_id']}_{job['array']['task_id']}"

        name = job['name'][:40]

        if user != my_user:
            if mine:
                continue
        else:
            user = f'{c.Purple}{user}{c.Color_Off}'
            jobid = f'{c.Purple}{jobid}{c.Color_Off}'
            name = f'{c.Purple}{name}{c.Color_Off}'

        nodes = job['nodes']

        elapsed = timedelta(seconds=job['time']['elapsed'])
        limit = timedelta(seconds=job['time']['limit'] * 60)

        nodes = shorten(nodes, width=25, placeholder="...")

        if 'tres' in job and 'allocated' in job['tres']:

            def format_required(v):
                if v['type'] in ['cpu']:
                    return {v['type']: f"{v['count']:2}"}
                elif v['type'] in ['mem']:
                    # Slurm can only integer
                    return {f"{v['type']}": f"{int(v['count'])/1000:3.1f}G"}
                elif v['type'] in ['node']:
                    if v['count'] > 1:
                        # return {f"{v['type']}": f"{v['count']}"}
                        return {f"N": f"{v['count']}"}
                elif v['type'] in ['gres']:
                    if v['name'] != 'gpu':
                        name = 'gpu'
                        type_ = re.sub('gpu:', '', v['name'])
                        return {f"{name}": f"{type_}:{v['count']}"}
                    else:
                        return {f"{v['name']}": f"{v['count']}"}
                elif v['type'] in ['billing']:
                    billing = v['count'] * elapsed
                    billing_str = f"{round(billing.total_seconds() / 3600,):_}, {str(v['count']).rjust(3, ' ')}"
                    # billing_str = f"{round(billing.total_seconds() / 3600,):_} h"
                    # billing_str = f"{round(billing.total_seconds() / 3600 / 24, 1):_} d"}

                    if billing > timedelta(days=30):
                        billing_str = f"{c.Red}{billing_str}{c.Color_Off}"
                    elif billing > timedelta(days=7):
                        billing_str = f"{c.Yellow}{billing_str}{c.Color_Off}"

                    return {f"{v['type']}": billing_str}
                elif v['type'] in ['energy']:
                    pass
                else:
                    raise ValueError(v['type'])

            # requested = ','.join(filter(None, map(format_required, job['tres']['allocated'])))
            requested = {
                k: v
                for d in filter(None, map(format_required, job['tres']['allocated'] or job['tres']['requested']))
                for k, v in d.items()
            }
        else:
            requested = job['required']

            def format_required(k, v):
                if k == 'memory':
                    # Slurm can only integer
                    return f'{k}={int(v)/1000}G'
                else:
                    return f'{k}={v}'

            requested = {'Required': ','.join(
                [format_required(k, v) for k, v in requested.items()])}

        partition = job['association']['partition']
        account = {'hpc-prf-nt1': 'nt1', 'hpc-prf-nt2': 'nt2'}.get(job['association']['account'])
        qos = job['qos']
        # "qos": "lowcont"

        # start = format_datetime(job['time']['submission'])  # Submission time
        # start = format_datetime(job['time']['start'])  # Submission time
        # start = format_datetime(job['time']['eligible'])  # Usually Submission time

        start = [
            # ToDo: Why has every job multiple steps?
            step['time']['start']
            for step in job['steps']
        ]
        if start:
            start = format_datetime(min(start))
        elif job['job_id'] in datas_queue:
            # Start time of Pending Jobs is unknown to sacct
            tmp = datas_queue[job['job_id']]
            start = format_datetime(tmp['start_time'])
        else:
            start = f'Unknown'

        end = format_datetime(job['time']['end'], highlight_hourago=True)

        ratio_elapsed = elapsed / limit

        if end == 'Running':
            tmp = elapsed / limit
            pbar_length = 6
            pbar = "#" * (round(tmp * pbar_length))
            pbar = pbar.ljust(pbar_length)
            end = f'[{pbar}]'
            # end = f'[{pbar}] {tmp*100:.2f}%'
        # else:


        def format_timedelta(s):
            hours, remainder = divmod(s.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            hours, minutes, seconds = int(hours), int(minutes), int(seconds)
            return f'{hours:02}:{minutes:02}:{seconds:02}'
            if hours > 5:
                return f'{round(s.total_seconds() / 3600)} h'
            if minutes > 5:
                return f'{round(s.total_seconds() / 60)} m'
            return f'{s.total_seconds()} s'

        elapsed = f'{format_timedelta(elapsed)} / {format_timedelta(limit)}'

        def insert_str(string, str_to_insert, index):
            return string[:index] + str_to_insert + string[index:]

        elapsed = insert_str(elapsed, c.Color_Off, round(ratio_elapsed * len(elapsed)))
        elapsed = f'{c.Reverse}{elapsed}'

        state = job['state']['current']
        seff = True
        if state == 'RUNNING':
            state = f'{c.Green}{state}{c.Color_Off}'
            seff = False
        elif state in ['FAILED', 'TIMEOUT', 'OUT_OF_MEMORY']:
            state = f'{c.Red}{state}{c.Color_Off}'
            # seff = True
        elif state == 'COMPLETED':
            state = f'{c.Yellow}{state}{c.Color_Off}'
            # seff = True
        elif state == 'CANCELLED':
            pass
            # seff = True

        if job['kill_request_user'] is not None:
            if state == 'CANCELLED':
                state = f"{state} by {job['kill_request_user']}"
            else:
                # Can this happen?
                state = f"{state}(Killed by {job['kill_request_user']})"

        if job['state']['reason'] == 'None':
            state = f"{state}"
        else:
            state = f"{state}({job['state']['reason']})"

        if job['job_id'] in datas_queue:
            requested['n'] = datas_queue[job['job_id']]['tasks']
        else:
            tmp = [s['tasks']['count'] for s in job['steps']]
            if tmp:
                requested['n'] = max(tmp)

        if seff:
            # stdout = subprocess.run(
            #     f"seff {job['job_id']}",
            #     check=True, shell=True, stdout=subprocess.PIPE,
            #     universal_newlines=True, env=env).stdout
            seff = {}
            # for line in stdout.splitlines():
            #     if line.startswith('CPU Efficiency:'):
            #         seff['CEff'] = round(float(line.split()[2].replace('%', '')))
            #     if line.startswith('Memory Efficiency:'):
            #         # ToDo: Replace seff with output of sacct:
            #         # ['steps'][i]['tres']['requested']['max'][2]['count']
            #
            #         seff['MEff'] = round(float(line.split()[2].replace('%', '')))

            # This code is a inspired by seff and checking json output,
            # to identify the values. The json output is strange:
            # several names don't match the meaning of the value,
            # e.g. requested mem mean used memory of the process.

            cpu_time_used = 0
            for step in job['steps']:
                cpu_time_used += step['time']['total']['seconds'] * 1_000_000
                cpu_time_used += step['time']['total']['microseconds']

            elapsed_times_cpus = job['time']['elapsed'] * job['required']['CPUs']

            if elapsed_times_cpus > 0:
                seff['CEff'] = round((cpu_time_used / 1_000_000) / elapsed_times_cpus * 100)

                if seff['CEff'] > 70:
                    seff['CEff'] = f"{c.Green}{seff['CEff']}{c.Color_Off}"
            else:
                seff['CEff'] = '??'

            mem_tres_requested = 0  # max/peak memory used.
            mem_tres_allocated = 0  # max memory that can be used, before OOM-Killer starts
            for step in job['steps']:
                for entry in step['tres']['requested']['max']:
                    if entry['type'] == 'mem':
                        mem_tres_requested = max(mem_tres_requested, entry['count']) * step['tasks']['count']
                for entry in step['tres']['allocated']:
                    if entry['type'] == 'mem':
                        mem_tres_allocated = max(mem_tres_allocated, entry['count'])

            if mem_tres_allocated > 0:
                seff['MEff'] = round(mem_tres_requested / (mem_tres_allocated * 1024**2) * 100)

                if seff['MEff'] > 95:
                    seff['MEff'] = f"{c.Red}{seff['MEff']}{c.Color_Off}"
                elif seff['MEff'] < 20:
                    seff['MEff'] = f"{c.Yellow}{seff['MEff']}{c.Color_Off}"
            else:
                seff['MEff'] = '??'


        else:
            seff = {}

        lines.append([user, jobid, name, state, elapsed, start, end, requested, partition, nodes])
        lines2.append({
            'User': user,
            'JobID': jobid,
            'Name': name,
            'State': state,
            'Elapsed': elapsed,
            'Start': start,
            'End': end,
            'Acc': account,
            'QoS': qos,
            **requested,
            **seff,
            'Partition': partition,
            'Nodes': nodes,
        })

    print_table(lines2,
                # just='lrllrrlrrrrrllr',
                just={
                    'User': 'l',
                    'JobID': 'r',
                    'Name': 'l',
                    'State': 'l',
                    'Elapsed': 'r',
                    'Start': 'r',
                    'End': 'r',
                    'n': 'r',
                    'cpu': 'r',
                    'gpu': 'r',
                    'mem': 'r',
                    'CEff': 'r',
                    'MEff': 'r',
                    'billing': 'r',
                    'N': 'r',
                    'Partition': 'r',
                    'Acc': 'l',
                    'QoS': 'l',
                    'Nodes': 'l',
                },
                sep=' | ')

    summary = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))

    strip_ansi = StripANSIEscapeSequences()

    for line in lines2:
        if 'running' in strip_ansi(line['State']).lower():
            key = tuple(
                [('State', 'RUNNING')]
                + [(k, line[k]) for k in ['Partition', 'User']])
        else:
            continue
            key = tuple(
                [('State', 'NOT RUNNING')]
                + [(k, line[k]) for k in ['Partition', 'User']])

        mem = line['mem']
        if mem.endswith('G'):
            mem = float(mem.replace('G', ''))
        else:
            raise RuntimeError(mem)

        summary[key]['cpu'] += int(line['cpu'])
        summary[key]['gpu'] += int(line.get('gpu', '0').split(':')[-1])
        summary[key]['mem'] += mem

        total, per_h = map(int, strip_ansi(line['billing']).split(','))

        summary[key]['billing'] += total
        summary[key]['billing/h'] += per_h

        for k, _ in line.items():
            if k.startswith('gpu:'):
                summary[key][k] += int(line[k])

    summary_table = []

    for key, v in summary.items():
        key = dict(key)

        v['mem'] = f"{round(v['mem'])} GB"

        if key['State'] == 'RUNNING':
            def colorize_granted(value, granted_30d):
                granted_1h = granted_30d / 30 / 24
                if value >= granted_1h:
                    return f"{c.Red}{value}{c.Color_Off}"
                elif value >= granted_1h / 4:
                    return f"{c.Yellow}{value}{c.Color_Off}"
                return value

            v['gpu'] = colorize_granted(v['gpu'], granted_30d=8_196.72)
            v['cpu'] = colorize_granted(v['cpu'], granted_30d=327_868.85)
            v['billing/h'] = colorize_granted(v['billing/h'], granted_30d=327_868.85)
        else:
            ratio = v['billing'] / v['billing/h']
            v['avg time'] = f"{round(ratio, 1)} h"

        summary_table.append({
            **key,
            **v,
        })

    summary_table = sorted(summary_table, key=lambda e: list(e.values()))

    print_table(summary_table, just={
                    'State': 'l',
                    'Partition': 'l',
                    'User': 'l',
                    'cpu': 'r',
    })
    # lines = '\n'.join([sep.join([str(e)[:40] for e in line]) for line in lines])

    # subprocess.run(['column', '-t', '-s', sep], input=lines, universal_newlines=True)


if __name__ == '__main__':
    main(*sys.argv[1:])
