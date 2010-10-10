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
import sys
import shutil
import tempfile
import unittest

from bitten.slave import BuildSlave, ExitSlave
from bitten.util import xmlio
from bitten.slave import encode_multipart_formdata

class DummyResponse(object):
    def __init__(self, code):
        self.code = code

class TestSlave(BuildSlave):

    def __init__(self, filename, work_dir):
        BuildSlave.__init__(self, [filename], work_dir=work_dir)
        self.results = []

    def _gather(self, method, url, body=None, headers=None):
        self.results.append(xmlio.parse(body))
        return DummyResponse(201)

    def _execute_step(self, _build_url, recipe, step):
        old_local, old_request = self.local, self.request
        try:
            self.local, self.request = False, self._gather
            return BuildSlave._execute_step(self, 'dummy_build', recipe, step)
        finally:
            self.local, self.request = old_local, old_request

class BuildSlaveTestCase(unittest.TestCase):

    def setUp(self):
        self.work_dir = tempfile.mkdtemp(prefix='bitten_test')
        self.python_path = xmlio._escape_attr(sys.executable)

    def tearDown(self):
        shutil.rmtree(self.work_dir)

    def _create_file(self, *path):
        filename = os.path.join(self.work_dir, *path)
        fd = file(filename, 'w')
        fd.close()
        return filename

    def _run_slave(self, recipe):
        results = []
        filename = self._create_file("recipe.xml")
        recipe_file = file(filename, "wb")
        recipe_file.write(recipe)
        recipe_file.close()
        slave = TestSlave(filename, self.work_dir)
        slave.run()
        return slave.results

    def test_quit_raises(self):
        self.slave = BuildSlave([], work_dir=self.work_dir)
        self.assertRaises(ExitSlave, self.slave.quit)

    def test_simple_recipe(self):
        results = self._run_slave("""
        <build xmlns:sh="http://bitten.edgewall.org/tools/sh"
            >
            <step id="print">
                <sh:exec executable="%s" args='-c "print (\\"Hello\\")"' />
            </step>    
        </build>""" % self.python_path)

        result = results[0]
        self.assertEqual(result.attr["step"], "print")
        self.assertEqual(result.attr["status"], "success")
        log = list(result)[0]
        msg = list(log)[0]
        self.assertEqual(str(msg), '<message level="info">Hello</message>')

    def test_non_utf8(self):
        results = self._run_slave("""
        <build xmlns:sh="http://bitten.edgewall.org/tools/sh"
            >
            <step id="print">
                <sh:exec executable="%s" args='-c "print (\\"\\xe9\\")"' />
            </step>    
        </build>""" % self.python_path)

        result = results[0]
        self.assertEqual(result.attr["step"], "print")
        self.assertEqual(result.attr["status"], "success")
        log = list(result)[0]
        msg = list(log)[0]
        # check replacement character (\uFFFD) was generated correctly
        self.assertEqual(str(msg).decode("utf-8"),
            u'<message level="info">\uFFFD</message>')

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
