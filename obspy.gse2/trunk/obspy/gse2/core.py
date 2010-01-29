# -*- coding: utf-8 -*-
"""
GSE2 bindings to ObsPy core module.
"""

from obspy.core import Trace, UTCDateTime, Stream
from obspy.gse2 import libgse2
import numpy as np


def isGSE2(filename):
    """
    Checks whether a file is GSE2 or not. Returns True or False.
    
    :param filename: GSE2 file to be read.
    """
    # Open file.
    try:
        f = open(filename)
        data = f.read(4)
    except:
        return False
    f.close()
    if data == 'WID2':
        return True
    return False


convert_dict = {
    'station': 'station',
    'samp_rate':'sampling_rate',
    'n_samps': 'npts',
    'channel': 'channel',
    'calib': 'calib',
}

gse2_extra = [
    'instype',
    'datatype',
    'vang',
    'hang',
    'auxid',
    'calper',
]


def readGSE2(filename, headonly=False, verify_chksum=True, **kwargs):
    """
    Reads a GSE2 file and returns a Stream object.
    
    GSE2 files containing multiple WID2 entries/traces are supported.
    This function should NOT be called directly, it registers via the
    obspy :func:`~obspy.core.stream.read` function, call this instead.
    
    :param filename: GSE2 file to be read.
    :param headonly: If True read only head of GSE2 file
    :param verify_chksum: If True verify Checksum and raise Exception if it
        is not correct
    :return: :class:`~obspy.core.stream.Stream` object containing header and
        data

    Example
    -------
    >>> from obspy.core import read # doctest: +SKIP
    >>> st = read("loc_RJOB20050831023349.z") # doctest: +SKIP
    """
    traces = []
    # read GSE2 file
    f = open(filename, 'rb')
    for _k in xrange(10000): # avoid endless loop
        pos = f.tell()
        widi = f.readline()[0:4]
        if widi == '': # end of file
            break
        elif widi != 'WID2':
            continue
        else: # valid gse2 part
            f.seek(pos)
            if headonly:
                header = libgse2.readHead(f)
            else:
                header, data = libgse2.read(f, verify_chksum=verify_chksum)
            # assign all header entries to a new dictionary compatible with an 
            # Obspy Trace object.
            new_header = {}
            for i, j in convert_dict.iteritems():
                new_header[j] = header[i]
            # assign gse specific header entries
            new_header['gse2'] = {}
            for i in gse2_extra:
                new_header['gse2'][i] = header[i]
            # Calculate start time.
            new_header['starttime'] = UTCDateTime(
                header['d_year'], header['d_mon'], header['d_day'],
                header['t_hour'], header['t_min'], 0) + header['t_sec']
            if headonly:
                traces.append(Trace(header=new_header))
            else:
                traces.append(Trace(header=new_header, data=data))
    f.close()
    return Stream(traces=traces)


def writeGSE2(stream_object, filename, **kwargs):
    """
    Write GSE2 file from a Stream object.

    :param stream_object: The ObsPy Stream object to write.
    :param filename: Name of file to write.
    """
    #
    # Translate the common (renamed) entries
    f = open(filename, 'wb')
    for trace in stream_object:
        header = {}
        for _j, _k in convert_dict.iteritems():
            try:
                header[_j] = trace.stats[_k]
            except:
                pass
        for _j in gse2_extra:
            try:
                header[_j] = trace.stats.gse2[_j]
            except:
                pass
        # year, month, day, hour, min, sec
        try:
            (header['d_year'],
             header['d_mon'],
             header['d_day'],
             header['t_hour'],
             header['t_min'],
             header['t_sec']) = trace.stats.starttime.timetuple()[0:6]
            header['t_sec'] += trace.stats.starttime.microsecond / 1.0e6
        except:
            raise
        # be nice and adapt type if necessary
        trace.data = np.require(trace.data, 'int', ['C_CONTIGUOUS'])
        libgse2.write(header, trace.data, f, **kwargs)
    f.close()
