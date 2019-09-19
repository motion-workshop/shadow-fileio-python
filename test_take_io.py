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
import unittest
import array

import take_io


class TestTakeIO(unittest.TestCase):

    def test_read(self):
        prefix = take_io.find_newest_take()

        self.assertIsInstance(prefix, str)

        info, node_list, data = take_io.read('{}/data.mStream'.format(prefix))

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
        self.assertEqual(len(info.get('location')), 3)
        self.assertEqual(len(info.get('geomagnetic')), 3)

        node_map = take_io.make_node_map(
            '{}/take.mTake'.format(prefix), node_list)

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


if __name__ == '__main__':
    unittest.main()
