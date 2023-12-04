#!/usr/bin/env python3

import sys
import os
import glob
import subprocess
import re
import functools
import shlex
from pathlib import Path
import time


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

    @classmethod
    def print_info(cls, *args):
        args = ' '.join([str(a) for a in args])
        print(c.Blue + args + c.Color_Off)


@functools.lru_cache()
def squeue():
    # %i %j %T == JobId JobName State
    cmd = '''squeue -u $USER --format='%i %j %T' --noheader'''
    squeue_lines = sorted(subprocess.check_output(cmd, shell=True, universal_newlines=True).splitlines())
    return squeue_lines


def jobid_to_workdir():
    """
    >>> jobid_to_workdir()
    {'2662929': '/scratch/hpc-prf-nt1/ebbers/exp',
     '2662930': '/scratch/hpc-prf-nt1/ebbers/exp',
     '2662937': '/scratch/hpc-prf-nt1/ebbers/exp',
     '2667238': '/scratch/hpc-prf-nt1/awerning/deploy/msm-mae',
     '2667250': '/scratch/hpc-prf-nt1/cord/models/dvectors/silver_desirable_puma',
     '2667253': '/scratch/hpc-prf-nt1/cord/models/multispeaker_dvectors_VoxCelebMix/aqua_mutual_hummingbird',
     '2667254': '/scratch/hpc-prf-nt1/cord/models/multispeaker_dvectors_VoxCelebMix/black_progressive_loon',
     '2667256': '/scratch/hpc-prf-nt1/cord/models/multispeaker_dvectors_VoxCelebMix/green_vicarious_heron',
     '2667258': '/scratch/hpc-prf-nt1/cord/models/multispeaker_dvectors_VoxCelebMix/green_entire_felidae',
     '2667260': '/scratch/hpc-prf-nt1/cord/models/multispeaker_dvectors_VoxCelebMix/rose_voluntary_opossum_finetuning',
     '2669263': '/scratch/hpc-prf-nt1/cord/models/dvectors/silver_desirable_puma/evaluation/3',
     '2669296': '/scratch/hpc-prf-nt2/cbj/deploy/css/egs/extract/77/eval/62000/76'}
    """
    # %i %Z == JobId WorkDir
    cmd = 'squeue --format "%i %Z" --noheader'
    output = subprocess.check_output(
        cmd, shell=True, universal_newlines=True)
    return dict(sorted([line.split(maxsplit=1) for line in output.splitlines()]))


def find_workdir_from_SubmitLine(jobid, workdir='.'):
    """
    >>> find_workdir_from_SubmitLine('3103666_24')


    # python -m fire /scratch/hpc-prf-nt2/cbj/deploy/cbj/bin/stail.py find_workdir_from_SubmitLine '"3103666_24"'
    """
    cmd = ['sacct', '--noheader', '-j', jobid, '-o', 'SubmitLine%-10000']
    stdout = subprocess.check_output(cmd, universal_newlines=True)
    stdout = stdout.splitlines()

    output = list({o.strip(): None for o in stdout if o.strip()}.keys())

    if len(output) != 1:
        if output[0].startswith('salloc'):
            print(
                f'{c.Red}{jobid} is an interactive job, hence it has no stdout files.{c.Color_Off}\n',
                *output, sep='\n'
            )
            exit(1)
        raise Exception(shlex.join(cmd) + '\n\n' + str(output))
    if len(stdout) > 1:
        print(f'{jobid} is a jobarray and each arrayjob has the same commandline.')

    output, = output
    # print(output)
    # -o, --output
    # -e, --error

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output')
    parser.add_argument('-e', '--error')
    args = vars(parser.parse_known_args(shlex.split(output))[0])
    # print(args, workdir)

    add_workdir = lambda x: os.path.join(workdir, x)

    output = args['output']
    error = args['error'] or output

    if output:
        if output != error:
            c.print_info(f'Found {output} and {error} (in SubmitLine of sacct) in workdir ({workdir})')
            output = add_workdir(output)
            error = add_workdir(error)
            return output + ' ' + error
        else:
            c.print_info(f'Found {output} (in SubmitLine of sacct) in {workdir}')
            output = add_workdir(output)
            return output
    else:
        raise ValueError(f'Could not find workdir from submitline via {shlex.join(cmd)}')


def file_from_job_id(jobid):
    """
    # >>> file_from_job_id('1109571')
    """
    cmd = f'scontrol show job {jobid}'
    try:
        stdout = subprocess.check_output(cmd, shell=True, universal_newlines=True)
    except subprocess.CalledProcessError:
        c.print_info(f'Could not find stdout file with "{cmd}"')
        c.print_info(f'Try to find the workdir with sacct.')
        output = subprocess.check_output(
            f'sacct -j {jobid} --format workdir%1000 --noheader -X'.split(),
            universal_newlines=True)
        dest = {l.strip() for l in output.splitlines() if l.strip()}
        assert len(dest) == 1, dest
        dest, = dest

        pattern = dest + '/' + f'*{jobid}*'
        files = list(glob.glob(pattern))
        if len(files) == 0:
            # raise RuntimeError(f'Could not find {pattern}. Was {jobid} an interactive job?') from None
            c.print_info(f'Could not find {pattern}. Was {jobid} an interactive job?')

            return find_workdir_from_SubmitLine(jobid, workdir=dest)
        elif len(files) > 1:
            # When can this happen?
            raise RuntimeError(pattern, files)
        file = files[0]

        # files = [file]
    else:
        r = re.search(f'StdOut=(.*)', stdout)
        if r:
            c.print_info(f'Found stdout file via {cmd!r}')
            file = r.group(1)
            # files = [file]
        else:
            r = re.search(f'WorkDir=(.*)', stdout)
            WorkDir = r.group(1) if r else '???'
            raise NotImplementedError(f'Could not find StdOut with {cmd!r} with WorkDir \n    {WorkDir}\n. Is it an interactive job?')

        r = re.search(f'StdErr=(.*)', stdout)
        if r:
            file_stderr = r.group(1)
            if file_stderr != file:
                c.print_info(f'Found stderr file via {cmd!r}')
                file += f' {file_stderr}'
        else:
            raise NotImplementedError(f'Could not find StdErr with {cmd!r}')
    return file


def main(argv, _interactive=None):
    if len(argv) == 1 and len(argv[0]) > 3:
        lines = squeue()
        id_jobname = {
            line.split()[0]: line.split()[1].rsplit(maxsplit=1)[0]
            for line in lines
        }
        if argv[0] in id_jobname:
            pass
        else:
            for k, v in id_jobname.items():
                if argv[0] in v:
                    print(f'{c.Blue}Identified {argv[0]!r} as jobname via squeue. Continue with {k!r}.{c.Color_Off}')
                    argv = [k]
                    break

    if len(argv) == 1 and (argv[0].isdigit() or all([part.isdigit() for part in argv[0].split('_')])):
        file = file_from_job_id(argv[0])
    elif len(argv) > 1 and all(
            a.isdigit() or all([part.isdigit() for part in a.split('_')])
            for a in argv
    ):
        file = ' '.join([file_from_job_id(a) for a in argv])
    elif len(argv) == 1 and argv[0] == 'i':
        lines = squeue()
        import questionary
        text = questionary.select(
            'Select JobID: (Only running Jobs listed)',
            choices=lines,
            default=lines[-1],
        ).ask()
        if text is None:
            # print('Received Ctrl+C -> Exit')  # questionary prints something for the user.
            return
        text = text.split()[0]
        assert text.isdigit(), text
        return main([text])
    elif len(argv) == 2 and argv[0] == 'i':
        return main([argv[1]], _interactive=True)
    elif len(argv) == 2 and argv[1] == 'i':
        return main([argv[0]], _interactive=True)
    elif len(argv) > 1:
        raise Exception('Only up to one argument supported', argv)
    else:
        if len(argv) == 0:
            argv = ['.']
        else:
            if _interactive is None:
                _interactive = True

        folder, = argv
        files = list(glob.glob(folder + '/' + 'slurm-*.out'))
        # print('files', files)

        # What was the idea of this code?
        # folder_absolute = Path(folder).absolute()
        # files += [
        #     # folder + '/' + Path(v).relative_to(folder)  # Why used I such an code?
        #     for k, v in jobid_to_workdir().items()
        #     if folder_absolute.samefile(Path(v))
        # ]
        # print('files', files)

        files = sorted(
            set(files),
            key=lambda f: [re.findall('\d+', f)[-1], f],  # Assume last number to be the job id
        )
        # print('#' * 80)
        # print(jobid_to_workdir())
        # print('#' * 80)
        if len(files) == 0:
            print(f'{c.Red}Warning: Found no slurm file in current folder.{c.Color_Off}')

            squeue_lines = squeue()
            matchs = [
                line.split(' ', maxsplit=1)[0]
                for line in squeue_lines
                if folder in line.split(' ', maxsplit=1)[1].rsplit(' ', maxsplit=1)[0]
            ]
            if len(matchs) == 1:
                print(f'{c.Yellow}Identified arguments as JobName {matchs}{c.Color_Off}')
                return main(matchs)
            elif len(matchs) > 1:
                print(f'{c.Red}Warning: Identified arguments as non unique JobName, ignore it.{c.Color_Off}')
            print(f'{c.Yellow}Switch to interactive.{c.Color_Off}')
            return main(['i'])

        if len(files) == 1:
            _interactive = False

        if _interactive:
            squeue_lines = squeue()
            squeue_lines = dict([line.split(maxsplit=1) for line in squeue_lines])

            def get_info(file):
                for k, v in squeue_lines.items():
                    if k in file:
                        return f'{file} {v}'
                return file

            choices = {
                get_info(file): file
                for file in files
            }

            # lines = sorted(glob.glob(argv[1] + '/' + 'slurm-*.out'))
            import questionary
            choice = questionary.select(
                f'Select JobID: (Only jobs with stdout in {folder} listed)',
                choices=list(choices.keys()),
                default=list(choices.keys())[-1],
            ).ask()
            if choice is None:
                # print('Received Ctrl+C -> Exit')  # questionary prints something for the user.
                return
            file = choices[choice]
        else:
            print(f'Watch recent job in {folder}', files)
            file = files[-1]

    cmd = 'tail -F ' + file

    print(c.Yellow + '$ ' + cmd + c.Color_Off)
    os.system(cmd)


if __name__ == '__main__':
    main(sys.argv[1:])
