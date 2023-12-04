#!/usr/bin/env python
"""
Like watch, but scrollable. Inspired by the idea of viddy.

Why not viddy?
 - With ssh and a jump host it froze sometimes.
 - Copy worked only with Shift.
 - viddy used several threads. This uses only one thread.
 - Only a subset of the features of viddy required.

"""

import sys
import os
import subprocess
import time
import shlex
import datetime
import socket

import curtsies.events
from curtsies import FullscreenWindow, Input, fsarray


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


def get_msg(cmd):
    msg = []
    cp = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, check=False,
                        universal_newlines=True)
    # watch ignores the return code, hence also do it here.
    # if cp.returncode != 0:
    #     raise Exception(
    #         '\n'
    #         f'$ {cmd}  # Return code: {cp.returncode}\n'
    #         f'{cp.stdout}\n'
    #         f'{cp.stderr}'
    #     )
    if cp.stdout:
        msg.append(cp.stdout)
    if cp.stderr:
        msg.append(cp.stderr)

    msg = '\n'.join(msg).split('\n')

    last_exec = datetime.datetime.now()
    last_exec = last_exec.strftime('%c')
    return msg, last_exec


class TimeEvent(curtsies.events.ScheduledEvent):
    def __repr__(self):
        return f'''{self.__class__.__name__}("{datetime.datetime.fromtimestamp(self.when).strftime('%c')}")'''


class Draw:
    def __init__(self):
        self.header_data = []
        self.data = []

        self.offset_x = 0
        self.offset_y = 0
        self.step_x = 4
        self.step_y = 1

    def to_curtsies(self, height, width):
        header_data = self.header_data
        header_data = [
            curtsies.FmtStr.from_str(line)[:width]
            for line in header_data
        ]

        data_height = height - len(header_data)
        data = self.data[self.offset_y:self.offset_y+data_height]
        data = [
            curtsies.FmtStr.from_str(line)[self.offset_x:self.offset_x+width]
            for line in data
        ]

        return fsarray(header_data + data)

    def move(self, c, height):
        if c in ['<UP>']:
            self.offset_y -= self.step_y
        elif c in ['<DOWN>']:
            self.offset_y += self.step_y
        elif c in ['<PAGEDOWN>']:
            self.offset_y += height - len(self.header_data)
        elif c in ['<PAGEUP>']:
            self.offset_y -= height + len(self.header_data)
        elif c in ['<HOME>']:
            self.offset_x = 0
        elif c in ['<LEFT>']:
            self.offset_x -= self.step_x
        elif c in ['<RIGHT>']:
            self.offset_x += self.step_x
        elif c in ['<TAB>']:
            self.offset_x += 8
        else:
            return False
        self.offset_x = max(0, self.offset_x)
        self.offset_y = min(max(0, self.offset_y), max(height, len(self.data) - height // 2))
        return True

    def header(self, lines):
        if isinstance(lines, str):
            self.header_data.append(lines)
        else:
            self.header_data.extend(lines)

    def __call__(self, lines):
        if isinstance(lines, str):
            self.data.append(lines)
        else:
            self.data.extend(lines)


def main(screen, cmd='ls --color ~/', interval=60, color=None):
    idle_thresh = 30 * 60  # 30 min

    # ToDo: implement color argument (At the moment always True)

    if not isinstance(interval, int):
        interval = int(interval)

    with Input(sigint_event=True) as input_generator:
        schedule_next_frame = input_generator.scheduled_event_trigger(TimeEvent)
        schedule_next_frame(when=time.time())

        draw = Draw()

        last_seen = time.time()
        idle = False

        for event in input_generator:
            height, width = screen.height, screen.width
            if str(event) in ['<ESC>', 'q', '<SigInt Event>']:
                # curtsies.events.SigIntEvent
                break
            elif draw.move(event, height=height):
                action = 'move'
                pass
            elif isinstance(event, curtsies.events.PasteEvent):
                action = 'move multi'
                for e in event.events:
                    draw.move(e, height=height)
            elif event in ['<Ctrl-j>', '<SPACE>'] or isinstance(event, TimeEvent):
                action = 'exec'
                msg, last_exec = get_msg(cmd)
                draw.data = []
                draw(msg)
                idle = False
            else:
                action = 'nothing'

            draw.header_data = []
            pre = f'Every {interval}s: {cmd}'
            post = f' {socket.gethostname()}: {last_exec}'
            fillerlen = width - len(pre) - len(post)
            draw.header(
                pre + ' ' * fillerlen + post
                if fillerlen >= 0
                else pre[:fillerlen] + post)

            if not isinstance(event, TimeEvent):
                last_seen = time.time()

            if time.time() - last_seen > idle_thresh:
                idle = True
            else:
                if len(input_generator.queued_scheduled_events) == 0:
                    schedule_next_frame(
                        when=time.time() + (0 if idle else interval))
                idle = False

            tmp = f"x,y={draw.offset_x},{draw.offset_y}; {event!r}; {action}"
            draw.header(f"{tmp}, {c.Red}idle: Press ENTER{c.Color_Off}" if idle else f"{tmp}")
            draw.header(f"")
            screen.render_to_terminal(draw.to_curtsies(height, width))


if __name__ == '__main__':
    import argparse
    # -n, --interval <secs>  seconds to wait between updates
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--color', action='store_true', help='interpret ANSI color and style sequences (Ignored, always active)')
    parser.add_argument('-n', '--interval', help='seconds to wait between updates', default=60)
    parser.add_argument('cmd')
    args = vars(parser.parse_args())
    print(args)

    terminal_title = f'{socket.gethostname()}: {os.path.basename(sys.argv[0])} {shlex.join(sys.argv[1:])}'
    print(f'\33]0;{terminal_title}\a', end='', flush=True)  # https://stackoverflow.com/a/47262154/5766934

    with FullscreenWindow() as screen:
        main(screen, **args)
