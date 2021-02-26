#
# Copyright (c) 2021, Motion Workshop
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
import io
import os
import unittest

import shadow.fileio


class TestTakeIO(unittest.TestCase):

    def test_read(self):
        prefix = shadow.fileio.find_newest_take()

        self.assertIsInstance(prefix, str)

        with open('{}/data.mStream'.format(prefix), 'rb') as f:
            info, node_list, data = shadow.fileio.read_stream(f)

        self.assertIsInstance(info, dict)
        self.assertIsInstance(node_list, tuple)
        self.assertIsInstance(data, array.array)

        self.assertIsInstance(info.get('version'), int)
        self.assertIsInstance(info.get('uuid'), str)
        self.assertIsInstance(info.get('num_node'), int)
        self.assertIsInstance(info.get('frame_stride'), int)
        self.assertIsInstance(info.get('num_frame'), int)
        self.assertIsInstance(info.get('channel_mask'), int)
        self.assertIsInstance(info.get('h'), float)
        self.assertIsInstance(info.get('location'), tuple)
        self.assertIsInstance(info.get('geomagnetic'), tuple)
        self.assertIsInstance(info.get('timestamp'), str)

        self.assertEqual(info.get('num_node', 0) * 2, len(node_list))
        self.assertEqual(info.get('h'), 0.01)
        self.assertEqual(len(info.get('location')), 3)
        self.assertEqual(len(info.get('geomagnetic')), 3)

        # num_frame * frame_stride / sizeof(float) == len(data)
        self.assertEqual(
            int(info.get('num_frame', 0) * info.get('frame_stride', 0) / 4),
            len(data))

        with open('{}/take.mTake'.format(prefix)) as f:
            node_map = shadow.fileio.make_node_map(f, node_list)

        self.assertIsInstance(node_map, dict)

        for node_id in node_map:
            self.assertIsInstance(node_id, str)

            node = node_map[node_id]
            self.assertIsInstance(node, dict)

            for channel_id in node:
                self.assertIsInstance(channel_id, str)

                channel = node[channel_id]
                self.assertIsInstance(channel, tuple)

                self.assertEqual(len(channel), 2)

                self.assertIsInstance(channel[0], int)
                self.assertIsInstance(channel[1], int)

                self.assertLess(channel[0], channel[1])

        # Trim off the YYYY-MM-DD/NNNN portion of the take path prefix. Use it
        # to test the other variant of find_newest_take that part of the path.
        a, number = os.path.split(prefix)
        b, date = os.path.split(a)

        prefix_name = shadow.fileio.find_newest_take(
            os.path.join(date, number))

        self.assertIsInstance(prefix_name, str)

        self.assertEqual(prefix, prefix_name)

        # Read the stream into memory so we can mess it up for testing.
        with open('{}/data.mStream'.format(prefix), 'rb') as f:
            buf = f.read()

        # Read one frame at a time.
        with io.BytesIO(buf) as f:
            # Just read the header portion of the stream.
            info, node_list = shadow.fileio.read_header(f)

            self.assertIsInstance(info, dict)
            self.assertIsInstance(node_list, tuple)

            # Read one frame at a time.
            for i in range(info.get('num_frame', 0)):
                frame = shadow.fileio.read_frame(f, info)
                self.assertEqual(
                    int(info.get('frame_stride', 0) / 4),
                    len(frame))

        # Incorrect format.
        bad_buf = int(1).to_bytes(4, byteorder='little') + buf[4:]
        with io.BytesIO(bad_buf) as f:
            with self.assertRaises(ValueError):
                shadow.fileio.read_stream(f)

        # Incorrect version header.
        bad_buf = buf[0:8] + int(1).to_bytes(4, byteorder='little') + buf[12:]
        with io.BytesIO(bad_buf) as f:
            with self.assertRaises(ValueError):
                shadow.fileio.read_stream(f)


if __name__ == '__main__':
    unittest.main()
