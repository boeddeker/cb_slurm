#!/usr/bin/env python

# From /home/cbj/python/cbj/cbj_smon/jobs/util.py
import time
import os


class c:
    purple = '\033[35m'
    Purple = '\033[95m'
    green = '\033[32m'
    red = '\033[31m'
    yellow = '\033[33m'
    cyan = '\033[36m'
    blue = '\033[34m'
    end = '\033[0m'
    invert = '\033[7m'



def slurm_nums_to_python(obj):
    """
    >>> slurm_nums_to_python({"set": True, "infinite": False, "number": 1720527843})
    1720527843
    >>> print(slurm_nums_to_python({"set": False, "infinite": False, "number": 0}))
    None
    """
    if isinstance(obj, dict):
        if obj.keys() == {'set', 'infinite', 'number'}:
            if obj['set']:
                assert not obj['infinite'], obj
                return obj['number']
            else:
                return None
        else:
            return {k: slurm_nums_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [slurm_nums_to_python(v) for v in obj]
    else:
        return obj


def human_readable_time(seconds, is_timestamp=None):
    """
    >>> human_readable_time(60)
    '0:1:0'
    >>> human_readable_time(3600)
    '1:0:0'
    >>> human_readable_time(86400)
    '24:0:0'
    >>> human_readable_time(86400 + 3600 + 60)
    '25:1:0'

    >>> human_readable_time(time.time())
    '16:07'
    >>> human_readable_time(time.time() - 60)
    '16:06'
    >>> human_readable_time(time.time() - 60*60*24)
    'Mon 16:07'
    >>> human_readable_time(time.time() - 60*60*24*7)
    '07-02 16:07'
    >>> human_readable_time(time.time() + 60)
    '\\x1b[31m16:14\\x1b[0m'
    """
    if is_timestamp is None:
        is_timestamp = seconds > 1_000_000_000
    elif is_timestamp is True:
        pass
    elif is_timestamp is False:
        pass
    else:
        raise ValueError(f'is_timestamp={is_timestamp!r}')

    if is_timestamp:  # assume seconds is a timestamp
        if seconds == 0:
            return '?'

        # 6 days in seconds = 6 * 24 * 60 * 60 = 518400
        # 7 days in seconds = 7 * 24 * 60 * 60 = 604800
        # 365 days in seconds = 365 * 24 * 60 * 60 = 31536000
        now = time.time()

        if (  # today
                abs(seconds - now) < 86400  # cheap test
                and time.strftime("%Y-%m-%d", time.localtime(seconds)) == time.strftime("%Y-%m-%d", time.localtime(now))  # actual test
        ):
            time_format = '%H:%M'
        elif abs(seconds - now) < 518400:  # less than 6 days
            time_format = '%a %H:%M'
        elif abs(seconds - now) < 31536000:  # less than 1 year
            time_format = '%m-%d %H:%M'
        else:
            time_format = '%Y-%m-%d %H:%M'

        if seconds < now:
            return f'{time.strftime(time_format, time.localtime(seconds))}'
        else:
            if seconds == 4294967294:  # dummy start value in slurm from sacct
                return '-'
            return f'\033[31m{time.strftime(time_format, time.localtime(seconds))}\033[0m'
    else:
        if seconds >= 4294967294:
            return '?'

        seconds = round(seconds)
        hours = seconds // 3600
        # days = hours // 24
        # hours = hours % 24
        seconds = seconds % 3600
        minutes = seconds // 60
        seconds = seconds % 60
        # if hours:
        # return f'{seconds / 36000:.1f}h'
        # if days:
        #     return f'{days}-{hours:02d}:{minutes:02d}'
        # else:
        return f'{hours:02d}:{minutes:02d}'
        # return f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        # else:
        #     return f'{minutes:02d}:{seconds:02d}'


def format_memory(mem_in_MB):
    """
    >>> format_memory(1024)
    '1024M'
    >>> format_memory(1024*1024)
    '1049G'
    >>> format_memory(1024*1024*1024)
    '1074T'
    >>> format_memory(1024*1024*1024*1024)
    '1100P'
    """
    try:
        factor = 1024
        margin = 8
        for suffix in ['M', 'G', 'T', 'P', 'E']:
            if mem_in_MB < factor * margin:
                return f'{mem_in_MB:.0f}{suffix}'
            mem_in_MB /= factor
    except Exception:
        raise ValueError(f'Error in format_memory({mem_in_MB!r})')


def highlight_progress_text(progress, text):
    """
    >>> highlight_progress_text(0.5, 'Some text')
    '\\x1b[7mSome\\x1b[0m text'
    >>> highlight_progress_text(0.5, 'Some')
    '\\x1b[7mSo\\x1b[0mme'
    """
    progress = int(round(progress * len(text)))
    return c.invert + text[:progress] + c.end + text[progress:]


def colorize_table(table):
    for line in table.values():
        for k in ['JobID']:
            line[k] = str(line[k])

        # user self should be purple
        if line['User'] == os.environ['USER']:
            # color user, jobid and name
            line['User'] = c.purple + line['User'] + c.end
            line['JobID'] = c.purple + line['JobID'] + c.end
            line['Name'] = c.purple + line['Name'] + c.end

        # colorize the state
        for state, color in [
            ('PENDING', c.cyan),
            ('RUNNING', c.green),
            ('COMPLETED', c.yellow),
            ('FAILED', c.red),
            ('TIMEOUT', c.red),
        ]:
            line['State'] = line['State'].replace(state, color + state + c.end)

        if line['Tool'] == 'sacct':
            line['State'] = line['State'].replace('RUNNING', 'RUNNING (outdated sacct?)').replace('PENDING', 'PENDING (outdated sacct?)')

        line['mem'] = format_memory(line['mem'])
        # line['Elapsed'] = human_readable_time(line['Elapsed'], is_timestamp=False)
        line['Submit'] = human_readable_time(line['Submit'], is_timestamp=True)
        line['Start'] = human_readable_time(line['Start'], is_timestamp=True)
        line['End'] = human_readable_time(line['End'], is_timestamp=True)

        if line['billing'] is not None:
            bil_eca, bil_tres = line['billing']
            bil_tres = round(bil_tres)
            bil_eca = round(bil_eca)
            color = ''
            if bil_eca > 30 * 24:  # over a month
                color = c.red
            elif bil_eca > 7 * 24:  # over a week
                color = c.yellow
            line['billing'] = f'{color}{bil_eca},{bil_tres: 3d}{c.end}'
        else:
            line['billing'] = '?,  ?'

    Elapsed_width_0 = 0
    Elapsed_width_1 = 0
    for line in table.values():
        line['Elapsed'] = [
            human_readable_time(line['Elapsed'][0], is_timestamp=False),
            human_readable_time(line['Elapsed'][1], is_timestamp=False),
            line['Elapsed'][0] / line['Elapsed'][1],
        ]
        Elapsed_width_0 = max(Elapsed_width_0, len(line['Elapsed'][0]))
        Elapsed_width_1 = max(Elapsed_width_1, len(line['Elapsed'][1]))

    for line in table.values():
        Elapsed = [
            line['Elapsed'][0].rjust(Elapsed_width_0),
            line['Elapsed'][1].rjust(Elapsed_width_1),
        ]
        Elapsed = ' / '.join(Elapsed)
        line['Elapsed'] = highlight_progress_text(line['Elapsed'][2], Elapsed)

    return table


# From /home/cbj/python/cbj/cbj_smon/jobs/seff.py
import os
import subprocess

# from cbj_smon.jobs.util import c


def seff_slow(job):
    env = dict(os.environ)

    seff = {}

    stdout = subprocess.run(
        f"seff {job['job_id']}",
        check=True, shell=True, stdout=subprocess.PIPE,
        universal_newlines=True, env=env).stdout

    for line in stdout.splitlines():
        if line.startswith('CPU Efficiency:'):
            seff['CEff'] = round(float(line.split()[2].replace('%', '')))
        if line.startswith('Memory Efficiency:'):
            # ToDo: Replace seff with output of sacct:
            # ['steps'][i]['tres']['requested']['max'][2]['count']

            seff['MEff'] = round(float(line.split()[2].replace('%', '')))

    return seff


def seff(job):
    # This code is a inspired by seff and checking json output,
    # to identify the values. The json output is strange:
    # several names don't match the meaning of the value,
    # e.g. requested mem mean used memory of the process.
    seff = {}

    cpu_time_used = 0
    for step in job['steps']:
        cpu_time_used += step['time']['total']['seconds'] * 1_000_000
        cpu_time_used += step['time']['total']['microseconds']

    elapsed_times_cpus = job['time']['elapsed'] * job['required']['CPUs']

    if elapsed_times_cpus > 0:
        seff['CEff'] = round(
            (cpu_time_used / 1_000_000) / elapsed_times_cpus * 100)

        if seff['CEff'] > 70:
            seff['CEff'] = f"{c.green}{seff['CEff']}{c.end}"
    else:
        seff['CEff'] = '??'

    mem_tres_requested = 0  # max/peak memory used.
    mem_tres_allocated = 0  # max memory that can be used, before OOM-Killer starts
    for step in job['steps']:
        for entry in step['tres']['requested']['max']:
            if entry['type'] == 'mem':
                mem_tres_requested = max(mem_tres_requested, entry['count']) * \
                                     step['tasks']['count']
        for entry in step['tres']['allocated']:
            if entry['type'] == 'mem':
                mem_tres_allocated = max(mem_tres_allocated, entry['count'])

    if mem_tres_allocated > 0:
        seff['MEff'] = round(
            mem_tres_requested / (mem_tres_allocated * 1024 ** 2) * 100)

        if seff['MEff'] > 95:
            seff['MEff'] = f"{c.red}{seff['MEff']}{c.end}"
        elif seff['MEff'] < 20:
            seff['MEff'] = f"{c.yellow}{seff['MEff']}{c.end}"
    else:
        seff['MEff'] = '??'

    return seff


# From /home/cbj/python/cbj/cbj_smon/__init__.py


# From /home/cbj/python/cbj/cbj_smon/jobs/create_bin.py
import sys
import os
from pathlib import Path
import inspect
import ast
import runpy


def is_package_module(module_name, package_dir):
    """Check if the module belongs to the package directory."""
    try:
        module = sys.modules[module_name]
        module_file = getattr(module, '__file__', None)
        if module_file:
            return os.path.abspath(module_file).startswith(
                os.path.abspath(package_dir))
    except KeyError:
        pass
    return False


def gather_used_files(package_dir, main_module):
    """Run the main module and gather all used files in the package."""
    used_files = set()

    # Backup original sys.modules
    original_modules = sys.modules.copy()

    # Run the main module
    # sys.path.insert(0, package_dir)
    try:
        runpy.run_module(main_module, run_name='__not_main__')
    except SystemExit:
        pass

    # Gather used files
    for module_name in sys.modules:
        if is_package_module(module_name, package_dir):
            module = sys.modules[module_name]
            module_file = getattr(module, '__file__', None)
            if module_file:
                used_files.add(module_file)

    # Restore original sys.modules
    sys.modules = original_modules
    return used_files


def adjust_imports(line, main=False, file=None, i=None):
    """
    >>> adjust_imports('from cbj_smon.table import print_table')
    >>> adjust_imports('from cbj_smon import table')  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    AssertionError: ('table', <module 'cbj_smon.table' from '.../cbj_smon/table.py'>)


    """
    assert not line.strip().startswith('from .'), (line, file)
    assert not line.strip().startswith('import .'), (line, file)
    assert not line.strip().startswith('import cbj_smon'), (line, file)

    if line.startswith('from cbj_smon'):
        g = {}
        l = {}
        exec('', g, l)
        copy = g.copy()
        exec(line, g, g)

        for k, v in g.items():
            if copy.get(k) != v:
                assert inspect.isfunction(v) or inspect.isclass(v), (type(v), k, v, f'{file}:{i+1}')  # module not allowed
        return f'# {line}'
    elif line.startswith('if __name__ == "__main__":') or line.startswith("if __name__ == '__main__':"):
        if not main:
            return f'if False:  # {line}'
    elif line.startswith('if'):
        raise NotImplementedError(f"Unexpected if statement: {line}", f'{file}:{i+1}')
    return line


def extract_definitions(file_content):
    tree = ast.parse(file_content)
    definitions = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Assign)):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        definitions.add(target.id)
            else:
                definitions.add(node.name)
    return definitions


def concatenate_files(py_files, main_file, output_file):
    all_definitions = set()

    with open(output_file, 'w') as outfile:
        outfile.write('#!/usr/bin/env python\n\n')

        for file in py_files:
            with open(file, 'r') as infile:
                content = infile.read()
                definitions = extract_definitions(content)

                # Check for conflicts
                conflict = all_definitions.intersection(definitions)
                if conflict:
                    raise ValueError(f"Conflict detected in file {file}: {conflict}")

                all_definitions.update(definitions)

                outfile.write(f'# From {file}\n')
                for i, line in enumerate(content.splitlines()):
                    outfile.write(adjust_imports(line, file=file, i=i) + '\n')
                outfile.write('\n\n')

        # Finally, add __main__.py content
        with open(main_file, 'r') as infile:
            content = infile.read()
            definitions = extract_definitions(content)

            # Check for conflicts
            conflict = all_definitions.intersection(definitions)
            if conflict:
                raise ValueError(
                    f"Conflict detected in file {main_file}: {conflict}")

            all_definitions.update(definitions)

            outfile.write(f'# From {main_file}\n')
            for i, line in enumerate(content.splitlines()):
                outfile.write(adjust_imports(line, file=file, main=True, i=i) + '\n')
            outfile.write('\n\n')

if False:  # if __name__ == "__main__":
    package_dir = Path(__file__).parent.parent
    output_file = Path(__file__).parent.parent.parent / 'bin' / 'smon_jobs.py'

    main_module = 'cbj_smon.jobs.__main__'
    main_file = package_dir / 'jobs/__main__.py'

    py_files = gather_used_files(package_dir, main_module)
    concatenate_files(py_files, main_file, output_file)

    os.chmod(output_file, 0o755)
    # print(f'Sorted imports in {output_file}')
    # os.system(f'autopep8 --in-place --aggressive --aggressive {output_file}')

    print(f'Created {output_file}')


# From /home/cbj/python/cbj/cbj_smon/jobs/__init__.py


# From /home/cbj/python/cbj/cbj_smon/table.py
import re


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
    >>> print_table([{'a': 1, 'b\\nf': 2}, {'a': 10, ('c', 'd'): 20}])
    =========
    a   b   c
        f   d
    =========
    1   2   -
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

    def str_width(s):
        if isinstance(s, str):
            if '\n' in s:
                return max(map(str_width, s.split('\n')))
            return len(strip_ANSI_escape_sequences(s))
        elif isinstance(s, tuple):
            return max([str_width(k) for k in s])
        else:
            raise TypeError(s)

    def str_height(s: str):
        if isinstance(s, str):
            return s.count('\n') + 1
        elif isinstance(s, tuple):
            return max([str_height(k) for k in s])
        else:
            raise TypeError(s)

    widths = {
        k: max([str_width(strip_ANSI_escape_sequences(d.get(k, '')))
                for d in data if isinstance(d, dict)] + [str_width(k)])
        for k in keys
    }
    header_lines = max([str_height(k) for k in keys])

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

    def get_line(s, n):
        if isinstance(s, str):
            s = s.split('\n')
        if len(s) <= n:
            return ''
        return s[n]

    # print(format_line(widths, '='))
    # print(format_line(widths))
    # print(format_line(widths, '='))
    for i, d in enumerate(data):
        if i % 40 == 0:
            print(format_line(widths, '='))
            for h in range(header_lines):
                print(format_line(widths, {
                    k: get_line(k, h)
                    for k, v in widths.items()
                }))
            # print(format_line(widths))
            print(format_line(widths, '='))
        print(format_line(widths, d))
    print(format_line(widths, '='))


# From /home/cbj/python/cbj/cbj_smon/jobs/gather_sacct.py
import os
import json
import subprocess
import time

# from cbj_smon.jobs.util import slurm_nums_to_python, human_readable_time, format_memory


def gather_sacct(start, mine=False):

    if start is None:
        # now[{+|-}count[seconds(default)|minutes|hours|days|weeks]]
        start = 'now-1days'

    env = dict(os.environ)

    if mine:
        cmd = f'sacct --json -S {start}'
    else:
        cmd = f"sacct --json -S {start}  --allusers"
    sacct_stdout = subprocess.run(
        cmd,
        check=True, shell=True, stdout=subprocess.PIPE,
        universal_newlines=True, env=env
    ).stdout
    return parse_sacct_stdout(sacct_stdout, time.time())


def parse_sacct_stdout(sacct_stdout, now):
    sacct_out = slurm_nums_to_python(json.loads(sacct_stdout))

    id_to_submit_time = {}
    table: 'dict[dict]' = {}
    for job in sacct_out['jobs']:
        allocated = {r['type']: r['count'] for r in job['tres']['allocated']}
        requested = {r['type']: r['count'] for r in job['tres']['requested']}
        tres = allocated if allocated else requested

        if job['required']['memory_per_node'] is not None:
            mem = job['required']['memory_per_node'] * job['allocation_nodes']
        elif job['required']['memory_per_cpu'] is not None:
            mem = job['required']['memory_per_cpu'] * job['required']['CPUs']
        else:
            raise ValueError(f'No memory information found for job {job["job_id"]} by sacct')

        id_to_submit_time[job['job_id']] = job['time']['submission']

        state = ','.join(job['state']['current'])

        if job['kill_request_user']:
            if state == 'CANCELLED':
                state += f' by {job["kill_request_user"]}'
            else:
                state += f' (Killed by {job["kill_request_user"]})'

        if job['state']['reason'] != 'None':
            state += f' ({job["state"]["reason"]})'

        tasks = max([s['tasks']['count'] for s in job['steps']], default='-')

        billing = tres.get('billing', '?')

        elapsed = job['time']['elapsed']

        if elapsed == 0 and job['time']['start'] < now:
            elapsed = job['time']['end'] - job['time']['start']

        billing = (billing * elapsed / 3600, billing)

        table[job['job_id']] = {
            'User': job['association']['user'],
            'JobID': job['job_id'],
            'Name': job['name'],
            'State': state,
            'Elapsed': (elapsed, job['time']['limit'] * 60),
            'Submit': job['time']['submission'],
            'Start': job['time']['start'],
            'End': job['time']['end'],
            'n': tasks,
            'cpu': job['required']['CPUs'],
            'gpu': tres.get('gres', 0),
            'mem': mem,
            'N': job['allocation_nodes'],
            'Partition': job['partition'],
            'billing': billing,
            'Acc': job['association']['account'].removeprefix('hpc-prf-'),
            'QoS': job['qos'],
            'Nodes': job['nodes'],
            'Priority': job['priority'],
            'Tool': 'sacct',
        }
    return table, id_to_submit_time, sacct_out['jobs']


# From /home/cbj/python/cbj/cbj_smon/jobs/gather_squeue.py
import os
import json
import time
import subprocess
# from cbj_smon.jobs.util import slurm_nums_to_python, human_readable_time, format_memory


def _get_gpu(job):
    """
    >>> job = {
    ...     'gres_detail': ["gpu:a40:1(IDX:1)"],
    ...     "tres_per_node": "gres/gpu:a40:1",
    ...     'tres_req_str': "cpu=2,mem=20G,node=1,billing=4,gres/gpu=1,gres/gpu:a40=1"
    ... }
    >>> _get_gpu(job)
    'a40:1'
    >>> job['gres_detail'] = []
    >>> _get_gpu({'gres_detail': None, 'tres_req_str': "cpu=2,mem=20G,node=1,billing=4,gres/gpu=1,gres/gpu:a40=1",})
    '1'
    """
    if job['gres_detail']:
        # Running job
        gpus = ','.join([
            d.removeprefix('gpu:').removesuffix('(IDX:0)').removesuffix('(IDX:1)').removesuffix('(IDX:2)').removesuffix('(IDX:3)')
            for d in job['gres_detail']
        ])
    elif 'gres/gpu=' in job['tres_req_str']:
        # Pending gpu job
        gpus = job['tres_req_str'].split(r'gres/gpu=')[-1].split(',')[0]
    else:
        # Pending cpu job
        gpus = '0'
    return gpus


def gather_squeue(mine=False):
    env = dict(os.environ)

    if mine:
        cmd = f'squeue --json --user $USER'
    else:
        cmd = f"squeue --json"

    squeue_stdout = subprocess.run(
        cmd,
        check=True, shell=True, stdout=subprocess.PIPE,
        universal_newlines=True, env=env).stdout
    return parse_squeue_stdout(squeue_stdout, time.time())


def parse_squeue_stdout(squeue_stdout, now):
    squeue_out = slurm_nums_to_python(json.loads(squeue_stdout))
    id_to_submit_time = {}
    table: 'dict[dict]' = {}
    for job in squeue_out['jobs']:
        # calculated elapsed from difference between now and start (time_limit is the total time limit, not the remaining time limit)
        if job['start_time'] == 0:
            elapsed = 0
        else:
            elapsed = max(0, now - job['start_time'])
        time_limit = job['time_limit'] * 60

        # sum from job resources
        if job['job_resources'] and 'allocated_nodes' in job['job_resources']:
            mem = sum(node['memory_allocated'] for node in job['job_resources']['allocated_nodes'])
        elif job['memory_per_node'] is not None:
            mem = job['memory_per_node'] * job['node_count']
        elif job['memory_per_cpu'] is not None:
            mem = job['memory_per_cpu'] * job['cpus']
        else:
            raise ValueError(f'No memory information found for job {job["job_id"]}')

        state = ','.join(job['job_state'])
        if job['state_reason'] != 'None':
            state += f' ({job["state_reason"]})'
        if job['state_description']:
            state += f' ({job["state_description"]})'
        # Add info from dependency field?
        # e.g. "dependency": "afternotok:5516697(unfulfilled)",

        billing = job['billable_tres']
        if billing is not None:
            billing = (billing * elapsed / 3600, billing)

        id_to_submit_time[job['job_id']] = job['submit_time']

        table[job['job_id']] = {
            'User': job['user_name'],
            'JobID': job['job_id'],
            'Name': job['name'],
            'State': state,
            'Elapsed': (elapsed, time_limit),
            'Submit': (job['submit_time']),
            'Start': (job['start_time']),
            'End': (job['end_time']),
            'n': job['tasks'],
            'cpu': job['cpus'],
            'gpu': _get_gpu(job),
            'mem': (mem),
            'billing': billing,
            'N': job['node_count'],
            'Partition': job['partition'],
            'Acc': job['account'].removeprefix('hpc-prf-'),
            'QoS': job['qos'],
            'Nodes': job['nodes'],
            'Priority': job['priority'],
            'Tool': 'squeue',
        }
    return table, id_to_submit_time, squeue_out['jobs']


# From /home/cbj/python/cbj/cbj_smon/jobs/__main__.py
import sys
# from cbj_smon.table import print_table
# from cbj_smon.jobs.gather_squeue import gather_squeue
# from cbj_smon.jobs.gather_sacct import gather_sacct
# from cbj_smon.jobs.util import human_readable_time, format_memory, colorize_table
# from cbj_smon.jobs.seff import seff


def main(start='now-12hours', *options):

    if len(options) == 1 and options[0] in ['mine', '--mine']:
        mine = True
    elif len(options) == 0:
        mine = False
    else:
        raise ValueError(options)

    table, id_to_submit_time, jobs = gather_squeue(mine=mine)
    table2, id_to_submit_time2, jobs2 = gather_sacct(start, mine=mine)

    for job in jobs2:
        table2[job['job_id']].update(seff(job))

    id_to_submit_time = {**id_to_submit_time2, **id_to_submit_time}
    table = {**table2, **table}
    assert table.keys() == id_to_submit_time.keys(), (table.keys(), id_to_submit_time.keys())
    table = {k: table[k] for k in sorted(table, key=lambda k: id_to_submit_time[k])}

    colorize_table(table)

    for v in table.values():
        v['Elapsed hh:mm'] = v.pop('Elapsed')

    print_table(list(table.values()),
                sep='  ',
                just={
                    'User': 'l',
                    'JobID': 'r',
                    'Name': 'l',
                    'State': 'l',
                    'Elapsed hh:mm': 'r',
                    'Submit': 'r',
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
                    'Priority': 'r',
                    'Tool': 'l',
                },)


if __name__ == '__main__':
    main(*sys.argv[1:])


