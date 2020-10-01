#!/usr/bin/env python3
# -*-

'''
------------------------------------------------------------------------------
Copyright (c) 2019 SUSE LLC

This program is free software; you can redistribute it and/or modify it under
the terms of version 3 of the GNU General Public License as published by the
Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program; if not, contact SUSE Linux GmbH.

------------------------------------------------------------------------------
Author: Sören Schmidt <soeren.schmidt@suse.com>

This tool checks if WMP is set up correctly. 

Exit codes:        0   No problems.
                   1   Error in arguments.
                   2   No WMP log data found. 

Changelog:

30.09.2020  v1.0    First release.
01.10.2020  v1.0.1  Exit codes corrected
'''

import argparse
import collections
import glob
import lzma
import os
import re
import signal
import sys
    
__version__ = '1.0'


def signal_handler(signal, frame):
    """ Terminate with exit code 1. """
    sys.exit(1)


def print_err(text):
    """ Prints text on stderr. """
    sys.stderr.write("%s\n" % text)


def exit_on_error(text, exitcode=1):
    """ Prints text on stderr and terminates with exitcode. """
    sys.stderr.write(text)
    sys.exit(exitcode)


def parse_arguments():
    """ Evaluate commandline arguments. """

    program_description = 'Extracts WMP cgroup memory data from system log and prints it as CSV or as a human-readable table.'

    parser = argparse.ArgumentParser(description=program_description)
    parser.add_argument('--timestamp', action='store', dest='timestamp_pattern', metavar='PATTERN', help='regular expression used to filter timestamps', default=False)
    parser.add_argument('--unit', action='store', dest='unit', choices=['B', 'kB', 'kiB', 'MB', 'MiB', 'GB', 'GiB'],help='unit for memory values', default='B')
    parser.add_argument('--cgroup', action='store', dest='cgroups_wanted', metavar='CGROUP,...', help='extract only these cgroups', default=None)
    parser.add_argument('--param', action='store', dest='params_wanted', metavar='PARAM,...', help='extract only these controller parameters', default=None)
    parser.add_argument('--sort', action='store_true', dest='sorting', help='sort timestamps', default=False)
    parser.add_argument('--csv', action='store_true', dest='csv', help='print data as CSV with delimiter character (default is comma)', default=False)
    parser.add_argument('--delim', action='store', dest='delim', help='delimiter character for CSV output', default=',')
    parser.add_argument('logfile', metavar ='LOGFILE', type = str, nargs ='*', help ='(xz compressed) system log file (default is /var/log/messages*)') 
    arguments = parser.parse_args()
    
    # If no logfiles have been provided we take a sorted list of all messages in /var/log/.
    if len(arguments.logfile) == 0:
        arguments.logfile = sorted(glob.glob('/var/log/messages-*'))
        if os.path.exists('/var/log/messages'):
            arguments.logfile.append('/var/log/messages')

    # Convert cgroups_wanted and params_wanted into lists, if they have been used.
    if arguments.cgroups_wanted:
        arguments.cgroups_wanted = arguments.cgroups_wanted.split(',')
    if arguments.params_wanted:
        arguments.params_wanted = arguments.params_wanted.split(',')

    # Transform unit in factor.
    arguments.factor = {'B': 1, 'kB': 1024, 'kiB': 1024, 'MB':1024*1024, 'MiB':1024*1024, 'GB':1024*1024*1024, 'GiB':1024*1024*1024}[arguments.unit]

    # Convert from/to timestamps into datetime objects.
    try:
        if arguments.timestamp_pattern:
            arguments.timestamp_pattern = re.compile(arguments.timestamp_pattern)
    except Exception as err:
        exit_on_error('Timestamp pattern is invalid: %s\n' % err, 2) 

    return arguments


def read_logs(filenames, cgroups_wanted, params_wanted, timestamp_pattern, factor=1):
    """ Reads logfiles and returns an ordered dictionary. """

    cgroup_data = collections.OrderedDict()
    column_width = {}
    found_cgroup_params = []
    filter = re.compile(' wmp_memory_current: ')

    for filename in filenames:

        # Open the (compressed) file.
        try:
            if filename.endswith('.xz'):
                fh = lzma.open(filename, mode='rt')
            else:
                fh = open(filename, mode='r')     
        except Exception as err:
            print_err('Could not read %s: %s' % (filename, err))
            continue
            
        # Read in each line that matches the filter.
        for line in fh.readlines():
            if not filter.search(line):
                continue
            if 'Exiting.' in line:
                continue

            # Extract the data and build up the dictionary.
            try:
                timestamp, _, _, data = line.strip().split(maxsplit=3)
                if timestamp_pattern:  # except entries that does not match the timestamp pattern
                    if not timestamp_pattern.match(timestamp):
                        continue
                        print('%s matches!' % timestamp)
                for section in data.split(','):
                    cgroup, dataset = section.split(':')
                    cgroup = cgroup.strip()
                    if cgroups_wanted and cgroup not in cgroups_wanted:
                        continue
                    for pair in  dataset.split():
                        param, value = pair.split('=')
                        if params_wanted and param not in params_wanted:
                            continue
                        if value == '-':
                            continue
                        if factor != 1:
                            value = '{:.1f}'.format(int(value)/factor)
                        key = '{}/{}'.format(cgroup, param)
                        cgroup_data.setdefault(timestamp, {})[key] = value
                        if key not in found_cgroup_params:
                            found_cgroup_params.append(key)
                        column_width['timestamp'] = max(len(timestamp), column_width.get('timestamp', 9))
                        column_width[key] = max(len(cgroup), len(param), len(value), column_width.get(key, 0))
                    
            except Exception as err:
                print_err('Error \"%s\" parsing line: %s' % (err, line.strip()))
                continue
                
        # Close file.
        fh.close()

    return cgroup_data, found_cgroup_params, column_width


def print_csv(cgroup_data, found_cgroup_params, separator = ',', sorting=False):
    """ Prints log data as csv. """

    if sorting:
        timestamps = sorted(cgroup_data.keys())
    else:
        timestamps = list(cgroup_data.keys())

    # Print header.
    header_string = 'timestamp%s%s' % (separator, separator.join(found_cgroup_params))
    print(header_string)

    # Print data.
    for timestamp in timestamps:
        data = cgroup_data[timestamp]
        line = []
        for name in found_cgroup_params: # we don't go through keys of column_with because we need a reproducable order of the columns
            if name in data:
                value = data[name]
            else:
                value = '-'
            line.append(value)    
        print("%s%s%s" % (timestamp, separator, separator.join(line)))


def print_humanreadable(cgroup_data, found_cgroup_params, column_width, sorting=False):
    """ Prints log data as a nice human-readable table. """

    max_val, min_val = {}, {}

    if sorting:
        timestamps = sorted(cgroup_data.keys())
    else:
        timestamps = list(cgroup_data.keys())

    # Prepare headers.
    field_format = '{text:^{width}s}'
    header_string_1a = [field_format.format(text='timestamp', width=column_width['timestamp'])]
    header_string_1b = [field_format.format(text=' '*column_width['timestamp'], width=column_width['timestamp'])]
    header_string_2 = [field_format.format(text=' '*column_width['timestamp'], width=column_width['timestamp'])]
    ruler = [field_format.format(text='='*column_width['timestamp'], width=column_width['timestamp'])]
    for col in found_cgroup_params:  # we don't go through keys of column_with because we need a reproducable order of the columns
        width = column_width[col]
        cgroup, param = col.split('/')
        header_string_1a.append(field_format.format(text=cgroup, width=width))
        header_string_1b.append(field_format.format(text=cgroup, width=width)) 
        header_string_2.append(field_format.format(text=param, width=width))
        ruler.append(field_format.format(text='='*width, width=width))

    # Print data and calculate maximum and minimum.
    print('\n%s\n%s\n%s' % (' '.join(header_string_1a), ' '.join(header_string_2), ' '.join(ruler)))
    field_format = '{text:>{width}s}'
    pattern_int = re.compile('[0-9]+')
    pattern_float  = re.compile('[0-9]+\.[0-9]+')
    for timestamp in timestamps:
        data = cgroup_data[timestamp]
        line = []
        for name in found_cgroup_params: # we don't go through keys of column_with because we need a reproducable order of the columns
            if name in data:
                value = data[name]
                if pattern_int.fullmatch(value):  # we have an integer
                    value = int(value)
                elif pattern_float.fullmatch(value):  # we have a float
                    value = float(value)
                try:
                    max_val[name] = max(max_val.setdefault(name, value) , value)
                    min_val[name] = min(min_val.setdefault(name, value) , value)
                except:
                    pass           
            else:
                value = '-'
            line.append(field_format.format(text=str(value), width=column_width[name]))
        print("%s %s" % (timestamp, ' '.join(line)))

    # Print naximum and minimum.
    print('\n%s\n%s\n%s' % (' '.join(header_string_1b), ' '.join(header_string_2), ' '.join(ruler)))
    line_max, line_min = [], []
    for name in found_cgroup_params:
        if name in max_val:
            value_max = max_val[name]
        else:
            value_max = '-'
        if name in min_val:
            value_min = min_val[name]
        else:
            value_min = '-'
        line_max.append(field_format.format(text=str(value_max), width=column_width[name]))
        line_min.append(field_format.format(text=str(value_min), width=column_width[name]))    
    print('%s %s' % (field_format.format(text='minimum', width=column_width['timestamp']), ' '.join(line_min)))
    print('%s %s' % (field_format.format(text='maximum', width=column_width['timestamp']), ' '.join(line_max)))


def main():

    # Avoid "IOError: [Errno 32] Broken pipe" when pipe ootput to other programs.
    # http://coding.derkeiler.com/Archive/Python/comp.lang.python/2004-06/3823.html
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    # Terminate nicely at ^C.
    signal.signal(signal.SIGINT, signal_handler)

    # Get arguments.
    arguments = parse_arguments()

    # Read log files.
    cgroup_data, found_cgroup_params, column_width = read_logs(arguments.logfile, arguments.cgroups_wanted, arguments.params_wanted, arguments.timestamp_pattern, arguments.factor)

    # Exit if we don't have any data collected.
    if len(cgroup_data) == 0:
        exit_on_error('No WMP data found! Exiting.\n', 1)

    # Print data as CSV or human-readable .
    if arguments.csv:
        print_csv(cgroup_data, found_cgroup_params, arguments.delim, arguments.sorting)
    else:
        print_humanreadable(cgroup_data, found_cgroup_params, column_width, arguments.sorting)

    # Bye.
    sys.exit(0)


if __name__ == '__main__':
    main()