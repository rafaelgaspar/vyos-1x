#!/usr/bin/env python3
#
# Copyright (C) 2017 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import os
import re
import sys

from vyos.config import Config
from vyos import ConfigError

from vyos import airbag
airbag.enable()

crontab_file = "/etc/cron.d/vyos-crontab"


def format_task(minute="*", hour="*", day="*", dayofweek="*", month="*", user="root", rawspec=None, command=""):
    fmt_full = "{minute} {hour} {day} {month} {dayofweek} {user} {command}\n"
    fmt_raw = "{spec} {user} {command}\n"

    if rawspec is None:
        s = fmt_full.format(minute=minute, hour=hour, day=day,
                            dayofweek=dayofweek, month=month, command=command, user=user)
    else:
        s = fmt_raw.format(spec=rawspec, user=user, command=command)

    return s

def split_interval(s):
    result = re.search(r"(\d+)([mdh]?)", s)
    value = int(result.group(1))
    suffix = result.group(2)
    return( (value, suffix) )

def make_command(executable, arguments):
    if arguments:
        return("sg vyattacfg \"{0} {1}\"".format(executable, arguments))
    else:
        return("sg vyattacfg \"{0}\"".format(executable))

def get_config():
    conf = Config()
    conf.set_level("system task-scheduler task")
    task_names = conf.list_nodes("")
    tasks = []

    for name in task_names:
        interval = conf.return_value("{0} interval".format(name))
        spec = conf.return_value("{0} crontab-spec".format(name))
        executable = conf.return_value("{0} executable path".format(name))
        args = conf.return_value("{0} executable arguments".format(name))
        task = {
                "name": name,
                "interval": interval,
                "spec": spec,
                "executable": executable,
                "args": args
              }
        tasks.append(task)

    return tasks

def verify(tasks):
    for task in tasks:
        if not task["interval"] and not task["spec"]:
            raise ConfigError("Invalid task {0}: must define either interval or crontab-spec".format(task["name"]))

        if task["interval"]:
            if task["spec"]:
                raise ConfigError("Invalid task {0}: cannot use interval and crontab-spec at the same time".format(task["name"]))
 
            if not re.match(r"^\d+[mdh]?$", task["interval"]):
                raise(ConfigError("Invalid interval {0} in task {1}: interval should be a number optionally followed by m, h, or d".format(task["name"], task["interval"])))
            else:
                # Check if values are within allowed range
                value, suffix = split_interval(task["interval"])

                if not suffix or suffix == "m":
                    if value > 60:
                        raise ConfigError("Invalid task {0}: interval in minutes must not exceed 60".format(task["name"]))
                elif suffix == "h":
                    if value > 24:
                        raise ConfigError("Invalid task {0}: interval in hours must not exceed 24".format(task["name"]))
                elif suffix == "d":
                    if value > 31:
                        raise ConfigError("Invalid task {0}: interval in days must not exceed 31".format(task["name"]))

        if not task["executable"]:
            raise ConfigError("Invalid task {0}: executable is not defined".format(task["name"]))
        else:
            # Check if executable exists and is executable
            if not (os.path.isfile(task["executable"]) and os.access(task["executable"], os.X_OK)):
                raise ConfigError("Invalid task {0}: file {1} does not exist or is not executable".format(task["name"], task["executable"]))

def generate(tasks):
    crontab_header = "### Generated by vyos-update-crontab.py ###\n"
    if len(tasks) == 0:
        if os.path.exists(crontab_file):
            os.remove(crontab_file)
        else:
            pass
    else:
        crontab_lines = []
        for task in tasks:
            command = make_command(task["executable"], task["args"])
            if task["spec"]:
                line = format_task(command=command, rawspec=task["spec"])
            else:
                value, suffix = split_interval(task["interval"])
                if not suffix or suffix == "m":
                    line = format_task(command=command, minute="*/{0}".format(value))
                elif suffix == "h":
                    line = format_task(command=command, minute="0", hour="*/{0}".format(value))
                elif suffix == "d":
                    line = format_task(command=command, minute="0", hour="0", day="*/{0}".format(value))
            crontab_lines.append(line)

        with open(crontab_file, 'w') as f:
            f.write(crontab_header)
            f.writelines(crontab_lines)

def apply(config):
    # No daemon restarts etc. needed for cron
    pass


if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        sys.exit(1)
