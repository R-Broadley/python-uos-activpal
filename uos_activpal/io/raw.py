# -*- coding: utf-8 -*-
"""
This module contains tools for working with activPAL raw data files.
"""

# Created on 06 Dec 2016
# @author: R-Broadley

from collections import namedtuple
from datetime import datetime
import os
import errno
import numpy as np
import pandas as pd
from numba import jit


_Meta = namedtuple('Meta', [
    'firmware', 'bitdepth', 'resolution', 'hz', 'axes',
    'start_datetime', 'stop_datetime', 'duration',
    'start_condition', 'stop_condition', 'file_code', 'device_id'
    ])


class Meta(_Meta):
    """
    A namedtuple with fields for the activPAL raw data's metadata.

    Parameters
    ----------
    firmware : int
    bitdepth : int
    resolution : int
    hz : int
    axes : int
    start_datetime : datetime.datetime
    stop_datetime : datetime.datetime
    duration : datetime.timedelta
    start_condition : str
    stop_condition : str
    file_code : str
    device_id : int

    """
    __slots__ = ()


def change_file_code(file_path, new_code):
    """
    Modifies the file code in the header of an activPAL raw data file.

    Parameters
    ----------
    file_path : str
        The path to an activPAL raw data file.
    new_code : str
        The upto 8 char string which the file code should be changed to.

    """
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
    """
    Returns a Meta object with the metadata from the given activPAL data file.

    Parameters
    ----------
    file_path : str
        The path to an activPAL raw data file.

    Returns
    -------
    meta : uos_activpal.io.raw.Meta
        The information extracted from the files header.

    See Also
    --------
    ActivpalData : An object to wrap activPAL data.
    load_activpal_data : Returns the data from an activPAL data file.
    change_file_code : Modifies the file code of an activPAL raw data file.
    extract_accelerometer_data : Extracts the signals from an activPAL raw data
        file body.

    """
    header = np.fromfile(file_path, dtype=np.uint8, count=1024, sep='')
    return extract_metadata(header)


def extract_metadata(header):
    """
    Returns a Meta object with the metadata from the given uint8 array.

    Parameters
    ----------
    header : numpy.uint8
        The header section of an activPAL raw data file.

    Returns
    -------
    meta : uos_activpal.io.raw.Meta
        The information extracted from the files header in a structured format.

    See Also
    --------
    extract_metadata_from_file : Returns a Meta object with the metadata from
        the given activPAL data file.
    ActivpalData : An object to wrap activPAL data.
    load_activpal_data : Returns the data from an activPAL data file.
    change_file_code : Modifies the file code of an activPAL raw data file.
    extract_accelerometer_data : Extracts the signals from an activPAL raw data
        file body.

    """
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

    return Meta(firmware, bitDepth, resolution, hz, axes,
                start_datetime, stop_datetime, duration,
                start_condition, stop_condition, file_code, device_id)


@jit
def _old_tail_check(x):
    return (x[0] == 0 and x[1] == 0 and x[2] > 0 and x[3] == 0 and
            x[4] == 0 and x[5] > 0 and x[6] > 0 and x[7] == 0)


@jit
def extract_accelerometer_data(body, firmware, datx):
    """
    Returns a numpyndarray with the signals from the given uint8 array.

    Parameters
    ----------
    body : numpy.ndarray, dype=numpy.uint8
        The body section of an activPAL raw data file.
    firmware : int
        The firmware version used to create the file from which body came.
    datx : bool
        Whether the source file had extension .datx (True) or .dat (False).

    Returns
    -------
    signals : numpy.ndarray
        The signals extracted from body in a column array.

    See Also
    --------
    extract_metadata_from_file : Returns a Meta object with the metadata from
        the given activPAL data file.
    ActivpalData : An object to wrap activPAL data.
    load_activpal_data : Returns the data from an activPAL data file.

    """
    length = len(body)
    max_rows = int(np.floor(length / 3) * 255)
    signals = np.zeros([max_rows, 3], dtype=np.uint8, order='C')

    adjust_nduplicates = firmware < 218

    row = 0
    for i in range(0, length, 3):
        x = body[i]
        y = body[i + 1]
        z = body[i + 2]

        if datx:
            tail = (x == 116 and y == 97 and z == 105 and body[i + 3] == 108)
        else:
            # TODO change thos to use _old_tail_check?
            # Would ^ slow it down - how would numba handle it?
            tail = (x == 0 and y == 0 and z > 0 and
                    body[i+3] == 0 and body[i+4] == 0 and
                    body[i+5] > 0 and body[i+6] > 0 and body[i+7] == 0)

        two54 = (x == 255 and y == 255 and z == 255)
        two55 = (x == 255 and y == 255 and z == 255)
        invalid = two54 or two55

        compressed = (x == 0 and y == 0)

        if tail:
            signals = signals[:row]
            break
        elif invalid:
            signals_prev = signals[row - 1]
            signals[row] = signals_prev
            row += 1
        elif compressed:
            signals_prev = signals[row - 1]
            if adjust_nduplicates:
                nduplicates = z + 1
            else:
                nduplicates = z
            for r in range(nduplicates):
                signals[row] = signals_prev
                row += 1
        else:
            signals[row, 0] = x
            signals[row, 1] = y
            signals[row, 2] = z
            row += 1
    return signals


def load_activpal_data(file_path):
    """
    Returns the data from an activPAL data file as (metadata, signals).

    Parameters
    ----------
    file_path : str
        The path to an activPAL raw data file.

    Returns
    -------
    metadata : uos_activpal.io.raw.Meta
        A namedtuple containing information extracted from the files header.
    signals : numpy.ndarray
        An array with a column for each axis of the device.

    See Also
    --------
    ActivpalData : An object to wrap activPAL data.

    """
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
    signals = extract_accelerometer_data(file_content[header_end:],
                                         metadata.firmware, file_ext == '.datx')
    return (metadata, signals)


class ActivpalData(object):
    """
    An object to wrap activPAL data.

    Methods
    -------
    TODO

    See Also
    --------
    load_activpal_data : Returns the data from an activPAL data file as a
        tuple (metadata, signals).

    """

    def __init__(self, file_path):
        """
        Create an instance of an activpal_data object.

        Parameters
        ----------
        file_path : str
            The path to an activPAL raw data file.

        """
        data = load_activpal_data(file_path)
        self._metadata = data[0]
        data_g = (np.array(data[1], dtype=np.float64, order='F') - 127) / 63
        interval = pd.tseries.offsets.Milli() * (1000 / data[0].hz)
        ind = pd.date_range(data[0].start_datetime, periods=len(data[1]),
                            freq=interval)
        self._signals = pd.DataFrame(data_g, columns=['x', 'y', 'z'], index=ind)

    @property
    def metadata(self):
        """namedtuple : The information extracted from the files header."""
        return self._metadata

    @property
    def signals(self):
        """pandas.DataFrame : The sensor signals."""
        return self._signals.copy()

    @property
    def data(self):
        """pandas.DataFrame : Depricated - use signals."""
        warning('activpal_data.data is depricated use activpal_data.signals')
        return self.signals

    @property
    def timestamps(self):
        """pandas.DatetimeIndex : The timestams of the signals."""
        return self.signals.index

    @property
    def x(self):
        """pandas.Series : The signal from the x axis."""
        if 'x' not in self._signals.columns:
            raise AttributeError('activpal_data property X no longer exists.\
                                 The signals must have been interfered with.')
        return self._signals['x'].copy()

    @property
    def y(self):
        """pandas.Series : The signal from the y axis."""
        if 'y' not in self._signals.columns:
            raise AttributeError('activpal_data property Y no longer exists.\
                                 The signals must have been interfered with.')
        return self._signals['y'].copy()

    @property
    def z(self):
        """pandas.Series : The signal from the z axis."""
        if 'z' not in self._signals.columns:
            raise AttributeError('activpal_data property Z no longer exists.\
                                 The signals must have been interfered with.')
        return self._signals['z'].copy()

    @property
    def rss(self):
        """pandas.Series : The Root Sum of Squares of the x, y, z axes."""
        if 'rss' not in self._signals.columns:
            sqr = np.square(self._signals[['x', 'y', 'z']])
            sumsqr = np.sum(sqr, axis=1)
            self._signals['rss'] = np.sqrt(sumsqr)
        return self._signals['rss'].copy()
