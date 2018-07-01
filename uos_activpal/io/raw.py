# -*- coding: utf-8 -*-
"""
This module does blah blah.
"""


from collections import namedtuple
from datetime import datetime
import os
import errno
import numpy as np
import pandas as pd
from numba import jit


meta = namedtuple('metadata', [
    'firmware', 'bitdepth', 'resolution', 'hz', 'axes',
    'start_datetime', 'stop_datetime', 'duration',
    'start_condition', 'stop_condition', 'file_code', 'device_id'
    ])


def change_file_code(file_path, new_code):
    # file_code = ''.join([(chr(x) if not x == 0 else '') for x in header[512:520]])
    # Check csv_file exists and is a file
    if not os.path.isfile(file_path):
        raise FileNotFoundError(errno.ENOENT,
                                os.strerror(errno.ENOENT), file_path)
    # Chech new code is str or convertable to str
    if not isinstance(new_code, str):
        str(new_code)
    # Check the str is 8 chars or less
    assert (len(new_code) <= 8), 'New file code longer than 8 characters'
    # Format bytes to write to file
    new_bytes = bytes(new_code, 'ascii').ljust(8, b'\x00')
    # Write to file
    with open(file_path, 'r+b') as f:
        f.seek(512, 0)
        f.write(new_bytes)


def extract_metadata_from_file(file_path):
    header = np.fromfile(file_path, dtype=np.uint8, count=1024, sep='')
    return extract_metadata(header)


def extract_metadata(header):
    firmware = header[39] * 255 + header[17]  # Should it be 256?

    if header[38] < 128:
        bitDepth = 8
        resolution_byte = header[38]
    else:
        bitDepth = 10
        resolution_byte = header[38] - 128

    resolution_map = {0: 2, 1: 4, 2: 8}
    resolution = resolution_map.get(resolution_byte)

    hz = header[35]

    axes_map = {0: 3, 1: 1}
    axes = axes_map.get(header[280])

    start_datetime = datetime(header[261] + 2000, header[260], header[259],
                              header[256], header[257], header[258])

    stop_datetime = datetime(header[267] + 2000, header[266], header[265],
                             header[262], header[263], header[264])

    duration = stop_datetime - start_datetime
    # duration = '{:.3f} days'.format(duration.days + duration.seconds / 86400)

    start_condition_map = {0: 'Trigger', 1: 'Immediately', 2: 'Set Time'}
    start_condition = start_condition_map.get(header[268])

    stop_condition_map = {0: 'Memory Full', 3: 'Low Battery', 64: 'USB',
                          128: 'Programmed Time'}
    stop_condition = stop_condition_map.get(header[275])

    file_code = ''.join([(chr(x) if not x == 0 else '') for x in header[512:520]])
    # Header 10 is the year code, old device use 12 for 2012 newer ones use 4
    # for 2014. Device ID needs first digit to be the last digit of the year
    # % means mod, anything mod 10 returns the last digit
    device_id = ((header[10] % 10) * 100000 + header[14] * 10000 +
                 header[40] * 4096 + header[11] * 256 + header[12] * 16 +
                 header[13])

    return meta(firmware, bitDepth, resolution, hz, axes,
                start_datetime, stop_datetime, duration,
                start_condition, stop_condition, file_code, device_id)


@jit
def old_tail_check(x):
    return (x[0] == 0 and x[1] == 0 and x[2] > 0 and x[3] == 0 and
            x[4] == 0 and x[5] > 0 and x[6] > 0 and x[7] == 0)


@jit
def extract_accelerometer_data(f_body, firmware, datx):
    length = len(f_body)
    max_rows = int(np.floor(length / 3) * 255)
    xyz = np.zeros([max_rows, 3], dtype=np.uint8, order='C')

    adjust_nduplicates = firmware < 218

    row = 0
    for i in range(0, length, 3):
        x = f_body[i]
        y = f_body[i + 1]
        z = f_body[i + 2]

        if datx:
            tail = (x == 116 and y == 97 and z == 105 and f_body[i + 3] == 108)
        else:
            tail = (x == 0 and y == 0 and z > 0 and
                    f_body[i+3] == 0 and f_body[i+4] == 0 and
                    f_body[i+5] > 0 and f_body[i+6] > 0 and f_body[i+7] == 0)

        two54 = (x == 255 and y == 255 and z == 255)
        two55 = (x == 255 and y == 255 and z == 255)
        invalid = two54 or two55

        compressed = (x == 0 and y == 0)

        if tail:
            xyz = xyz[:row]
            break
        elif invalid:
            xyz_prev = xyz[row - 1]
            xyz[row] = xyz_prev
            row += 1
        elif compressed:
            xyz_prev = xyz[row - 1]
            if adjust_nduplicates:
                nduplicates = z + 1
            else:
                nduplicates = z
            for r in range(nduplicates):
                xyz[row] = xyz_prev
                row += 1
        else:
            xyz[row, 0] = x
            xyz[row, 1] = y
            xyz[row, 2] = z
            row += 1
    return xyz


def load_activpal_data(file_path):
    file_ext = os.path.splitext(file_path)[1]
    if file_ext == '.datx':
        header_end = 1024
    elif file_ext == '.dat':
        header_end = 1023
    else:
        raise ValueError(''.join(('Unknown file extension "', file_ext,
                                  '" for file "', file_path, '"')))

    file_content = np.fromfile(file_path, dtype=np.uint8, count=-1, sep='')

    # compression = file_content[36]  # True(1) / False(0)

    metadata = extract_metadata(file_content[:header_end])
    xyz = extract_accelerometer_data(file_content[header_end:],
                                     metadata.firmware, file_ext == '.datx')
    return (metadata, xyz)


class activpal_data(object):
    def __init__(self, file_path):
        data = load_activpal_data(file_path)
        self.metadata = data[0]
        data_g = (np.array(data[1], dtype=np.float64, order='F') - 127) / 63
        interval = pd.tseries.offsets.Milli() * (1000 / data[0].hz)
        ind = pd.date_range(data[0].start_datetime, periods=len(data[1]),
                            freq=interval)
        self.signals = pd.DataFrame(data_g, columns=['x', 'y', 'z'], index=ind)

    @property
    def data(self):
        # For backwards compatibility
        warning('activpal_data.data is depricated use activpal_data.signals')
        return self.signals

    @property
    def timestamps(self):
        return self.signals.index

    @property
    def x(self):
        if 'x' not in self.signals.columns:
            raise AttributeError('activpal_data property X no longer exists.\
                                 The signals must have been interfered with.')
        return self.signals['x']

    @property
    def y(self):
        if 'y' not in self.signals.columns:
            raise AttributeError('activpal_data property Y no longer exists.\
                                 The signals must have been interfered with.')
        return self.signals['y']

    @property
    def z(self):
        if 'z' not in self.signals.columns:
            raise AttributeError('activpal_data property Z no longer exists.\
                                 The signals must have been interfered with.')
        return self.signals['z']

    @property
    def rss(self):
        if 'rss' not in self.signals.columns:
            sqr = np.square(self.signals[['x', 'y', 'z']])
            sumsqr = np.sum(sqr, axis=1)
            self.signals['rss'] = np.sqrt(sumsqr)
        return self.signals['rss']
