#
# Utility functions to read a Shadow binary take stream and associated
# metadata.
#
# Each take is stored in a folder. The folders are named by date and with an
# ascending number for that day.
#
#   ~/Documents/Motion/take/2019-06-26/0001
#
# Inside the take folder there are at least three files.
#
#    take.mTake
#    configuration.mNode
#    data.mStream
#
# The mTake format (JSON) describes the recording, its time stamps and
# durations, and contains the mapping from the take data to the skeletal
# definition.
#
# The mNode format (JSON) describes the skeleton and the attachments of
# hardware to the body segments. The mNode format is analagous to the
# configuration or device list shown in the Shadow software.
#
# The mStream format (binary) contains the frame data. All stream data is
# stored in little endian byte order. The stream starts with a 128 byte header
# that lists the number of nodes M, followed by an M x 8 byte header that lists
# the node keys and which channels are active per node, and then followed by N
# frames of data.
#
#
# Copyright (c) 2019, Motion Workshop
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
import array
from datetime import datetime, timedelta
import json
import os
import re
import struct
import time
import uuid


def read_stream(f):
    """Read a take binary data stream file (mStream format). The stream file
    contains a header that defines the number of node and channels followed by
    the pool of measurement data.

    with open('data.mStream') as f:
        info, node_list, data = read_stream(f)
    """

    # Read the binary stream header. Fixed size of 128 bytes. Padded with
    # extra integers.
    header = struct.unpack('<3I16s4I7f1Q12I', f.read(128))

    # Verify the magic header bytes. Sanity check.
    if header[0] != 0xFF787878 or header[1] != 0x05397A69:
        raise ValueError(
            "missing take file format signature in \"{}\"".format(
                filename))

    # Require take stream version 2 or 3.
    if header[2] not in (2, 3):
        raise ValueError(
            "missing take file format version in \"{}\"".format(
                filename))

    # There are a variable number of node key/mask integer pairs after the
    # fixed length header. 8 bytes * number of nodes.
    num_node = header[4]
    node_list = struct.unpack(
        '{}I'.format(2 * num_node),
        f.read(8 * num_node))

    # The frame count may or may not be present since this is a streaming
    # format.
    num_frame = header[6]
    if num_frame == 0:
        pos = f.tell()
        f.seek(0, 2)
        data_bytes = f.tell() - pos
        f.seek(pos)

        if data_bytes % header[5] == 0:
            num_frame = int(data_bytes / header[5])

    info = {
        'version': header[2],
        'uuid': str(uuid.UUID(bytes=header[3])),
        'num_node': num_node,
        'frame_stride': header[5],
        'num_frame': num_frame,
        'channel_mask': header[7],
        'h': header[8],
        'location': header[9:12],
        'geomagnetic': header[12:15],
        'timestamp': str(
            datetime.fromtimestamp(header[15]) +
            timedelta(microseconds=header[16])
        ),
        'flags': header[17]
    }

    # The rest of the data is a pool of single precision floats.
    data = array.array('f', f.read())

    return info, node_list, data


def make_node_map(f, node_list):
    """Read a take JSON document (mTake format) and create a lookup list of
    string named nodes and channels into the big pool of take data. Use the
    channel names from the take document. Use the channel masks from the
    node_list which is from the take data stream header itself.

    with open('take.mTake') as f:
        node_map = make_node_map(f, [1, 256, 2, 1024, 3, 256, ...])

    Generates a nested dict object. The first level are the node ids. The
    second level are the channel names and global offsets into the big frame
    buffer.

    {
        'Hips': {
            'Gq': (0, 4),
            'c': (4, 8)
        },
        'LeftLeg': {
            'Gq': (8, 12),
            'c': (12, 16),
            'a': (16, 19)
        },
        ...
    }

    """

    #
    # Parse the JSON take definition to get the node key to id name mapping.
    # Also grab the names as well.
    #
    tree = json.load(f)

    #
    # Flat list of the key, id, and name fields for each node in the take. This
    # is the way to get the string id and string name of the nodes since these
    # are not stored in the take stream file.
    #
    id_list = [
        {
            'key': item.get('key'),
            'id': item.get('id'),
            'name': item.get('name')
        }
        for item in tree.get('items', [])
    ]

    #
    # Create a name mapping from node.channel to the index base and bound
    # into the data pool.
    #   node_map['id']['channel'] = (base, bound)
    #   node_map['Hips']['Gq'] = (0, 4)
    #
    channel_stride = [
        4, 4, 4, 3, 3, 3, 3, 4,
        3, 3, 3, 1,
        3, 3, 3, 1,
        1, 1, 1, 1, 1, 1, 1, 1, 4, 1, 1, 4
    ]
    channel_name = [
        'Gq', 'Gdq', 'Lq', 'r', 'la', 'lv', 'lt', 'c',
        'a', 'm', 'g', 'temp',
        'A', 'M', 'G', 'Temp',
        'dt', 'timestamp', 'systemtime',
        'ea', 'em', 'eg', 'eq', 'ec', 'p', 'atm', 'elev', 'Bq'
    ]

    node_map = {}
    itr = 0
    for i, node in enumerate(id_list):
        mask = node_list[2 * i + 1]

        # For each node, iterate through the active channels.
        obj = {}
        for j in range(len(channel_stride)):
            channel = 1 << j
            if 0 == mask & channel:
                continue

            obj[channel_name[j]] = (itr, itr + channel_stride[j])
            itr = itr + channel_stride[j]

        node_map[node['id']] = obj

    return node_map


def find_newest_take(name=None):
    """Search the Motion user data folder for the most recently recorded take
    path.

    Returns something like (where the ... path is platform dependent):
    [...]/Documents/Motion/take/2019-06-26/0001
    """
    prefix = os.path.expanduser('~/Documents/Motion/take')

    if name is None:
        #
        # Search for the newest date in the take/YYYY-MM-DD folders.
        #
        date = ''
        with os.scandir(prefix) as it:
            for entry in it:
                if not entry.is_dir():
                    continue
                if not re.search(r'\d{4}\-\d{2}\-\d{2}', entry.name):
                    continue
                if entry.name > date:
                    date = entry.name

        prefix = os.path.join(prefix, date)

        #
        # Search for the largest take number in the take/YYYY-MM-DD/nnnn
        # folders.
        #
        number = ''
        with os.scandir(prefix) as it:
            for entry in it:
                if not entry.is_dir():
                    continue
                if not re.search(r'\d{4}', entry.name):
                    continue
                if entry.name > number:
                    number = entry.name

        prefix = os.path.join(prefix, number)
    else:
        prefix = os.path.join(prefix, name)

    return str(os.path.normpath(prefix))


def main():
    print(find_newest_take())


if __name__ == '__main__':
    main()
