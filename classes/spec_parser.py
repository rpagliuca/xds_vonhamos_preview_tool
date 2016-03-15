# -*- coding: utf-8 -*-

# Von Hamos Preview Tool for XDS Beamline
# Author: Rafael Pagliuca <rafael.pagliuca@lnls.br>
# Date created: 2015-12-02
# Date modified: 2015-12-11

import re
import os
from collections import OrderedDict

# Custom classes
from profiler import *

class SpecParser:

    def __init__(self, specfile):

        # Variable initialization
        self.scans = OrderedDict()

        # Set file path
        self.specfile = specfile

        self.profiler = Profiler()

        self.parse()

    def get_scans(self):
        return self.scans

    def parse(self):

        last_line = None

        values_regex = re.compile('(?:\s|^)([a-zA-Z0-9\._\+-]+)')
        data_line_regex = re.compile('^[^#]')
        data_line_regex_other =  re.compile('^\s*$')

        last_scan_id = 0
        scan_prefix = 0

        with open(self.specfile) as fp:
            # Motors names should be initialized before reading each line, because it is an ocasional header that is not guarenteed to exist, and, when it does, it is not attached to a specific scan
            motors_names = []

            for line in fp:


                # Lines not starting with comment (#) and
                # which are not empty are treated as column values (actual data / measurements)
                if re.search(data_line_regex, line) and not re.search(data_line_regex_other, line):
                    # Headers for the current scans are over, so now we can store them
                    if last_line != 'DATA':
                        self.scans[scan_id_prefix] = {
                            'id': scan_id_prefix,
                            'command': scan_command,
                            'motors_names': motors_names,
                            'motors_positions': motors_positions,
                            'columns_names': ['row_number', ] + columns_names, # append row_number column
                            'exposure_time': exposure_time,
                            'date': scan_date,
                            'data_dict': list(),
                            'data_dict_indexed': OrderedDict(),
                            'data_lines': list(),
                            'data_values': list(),
                            'data_values_indexed': OrderedDict(),
                        }
                        row_number = 0
                    last_line = 'DATA' 
                    # Following regex starts with '?:', which is a non-capturing regex group
                    matches = re.findall(values_regex, line)
                    if matches:
                        columns_values = matches

                        #Ordered dict is too slow!!!!!!

                        #data_dict = OrderedDict(zip(columns_names, columns_values))
                        #self.scans[scan_id_prefix]['data_dict'].append(data_dict)
                        #self.scans[scan_id_prefix]['data_dict_indexed'][row_number] = data_dict
                        self.scans[scan_id_prefix]['data_values'].append([row_number+1, ] + columns_values)
                        self.scans[scan_id_prefix]['data_values_indexed'][row_number] = [row_number+1, ] + columns_values
                        self.scans[scan_id_prefix]['data_lines'].append(line.replace('\n', '').replace('\s', ''))
                        row_number += 1

                # Lines starting with #O are motor names
                elif line.startswith("#O"): #re.search('^#O', line):
                    # Reset motors names if the header is placed multiple times in the file
                    if last_line != '#O':
                        motors_names = []
                    last_line = '#O'
                    matches = re.findall('\s([a-zA-Z0-9\._-]+)', line)
                    if matches:
                        motors_names.extend(matches)

                # Lines starting with #P are motor positions
                elif re.search('^#P', line):
                    last_line = '#P'
                    matches = re.findall('\s([a-zA-Z0-9\._-]+)', line)
                    if matches:
                        motors_positions.extend(matches)

                # Lines starting with #S are beggining of scans (scan header)
                elif re.search('^#S', line):
                    last_line = '#S'
                    matches = re.findall('^#S\s([0-9]+)', line)
                    scan_id = int(matches[0])
                    if scan_id <= last_scan_id:
                        scan_prefix += 1
                    last_scan_id = scan_id
                    scan_id_prefix = str(scan_prefix) + '.' + str(scan_id)
                    scan_command = line.replace('\n', '').replace('\s', '')
                    # Reset some values
                    motors_positions = []
                    columns_names = []
                    columns_values = []
                    row_number = 0
                    exposure_time = None
                    scan_date = None
                    header = True

                # Lines starting with #T are exposure time
                elif re.search('^#T', line):
                    last_line = '#T'
                    matches = re.findall('\s([0-9]+)\s', line)
                    if matches:
                        exposure_time = matches[0]

                # Lines starting with #L are column names
                elif re.search('^#L', line):
                    last_line = '#L'
                    matches = re.findall('\s([a-zA-Z0-9\._-]+)', line)
                    if matches:
                        columns_names.extend(matches)

                # Lines starting with #D are date
                elif re.search('^#D', line):
                    last_line = '#D'
                    matches = re.findall('^#D (.*)$', line)
                    if matches:
                        scan_date = matches[0]

                else:
                    last_line = 'OTHER'
