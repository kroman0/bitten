# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2007-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

import os
import shutil
import tempfile
import unittest

from bitten.slave import BuildSlave, ExitSlave
from bitten.slave import encode_multipart_formdata

class BuildSlaveTestCase(unittest.TestCase):

    def setUp(self):
        self.work_dir = tempfile.mkdtemp(prefix='bitten_test')
        self.slave = BuildSlave([], work_dir=self.work_dir)

    def tearDown(self):
        shutil.rmtree(self.work_dir)

    def _create_file(self, *path):
        filename = os.path.join(self.work_dir, *path)
        fd = file(filename, 'w')
        fd.close()
        return filename

    def test_quit_raises(self):
        self.assertRaises(ExitSlave, self.slave.quit)

class MultiPartEncodeTestCase(unittest.TestCase):

    def setUp(self):
        self.work_dir = tempfile.mkdtemp(prefix='bitten_test')

    def tearDown(self):
        shutil.rmtree(self.work_dir)

    def test_mutlipart_encode_one(self):
        fields = {
            'foo': 'bar',
            'foofile': ('test.txt', 'contents of foofile'),
        }
        body, content_type = encode_multipart_formdata(fields)
        boundary = content_type.split(';')[1].strip().split('=')[1]
        self.assertEquals('multipart/form-data; boundary=%s' % boundary,
                                    content_type)
        self.assertEquals('--%s\r\nContent-Disposition: form-data; ' \
                'name="foo"\r\n\r\nbar\r\n--%s\r\nContent-Disposition: ' \
                'form-data; name="foofile"; filename="test.txt"\r\n' \
                'Content-Type: application/octet-stream\r\n\r\n' \
                'contents of foofile\r\n--%s--\r\n' % (
                            boundary,boundary,boundary), body)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BuildSlaveTestCase, 'test'))
    suite.addTest(unittest.makeSuite(MultiPartEncodeTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
