# -*- coding: iso8859-1 -*-
#
# Copyright (C) 2005 Christopher Lenz <cmlenz@gmx.de>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.cmlenz.net/wiki/License.

import os
import shutil
import tempfile
import unittest

from bitten.build import pythontools, BuildError
from bitten.recipe import Context, Recipe


class TraceTestCase(unittest.TestCase):

    def setUp(self):
        self.basedir = os.path.realpath(tempfile.mkdtemp())
        self.ctxt = Context(self.basedir)
        self.summary = open(os.path.join(self.basedir, 'test-coverage.txt'),
                            'w')
        self.coverdir = os.path.join(self.basedir, 'coverage')
        os.mkdir(self.coverdir)

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def test_missing_param_summary(self):
        self.summary.close()
        self.assertRaises(AssertionError, pythontools.trace, self.ctxt,
                          coverdir='coverage')

    def test_missing_param_coverdir(self):
        self.summary.close()
        self.assertRaises(AssertionError, pythontools.trace, self.ctxt,
                          summary='test-coverage.txt')

    def test_empty_summary(self):
        self.summary.write('line  cov%  module  (path)')
        self.summary.close()
        pythontools.trace(self.ctxt, summary=self.summary.name,
                          coverdir=self.coverdir)
        type, function, xml = self.ctxt.output.pop()
        self.assertEqual(Recipe.REPORT, type)
        self.assertEqual(0, len(xml.children))



class UnittestTestCase(unittest.TestCase):

    def setUp(self):
        self.basedir = os.path.realpath(tempfile.mkdtemp())
        self.ctxt = Context(self.basedir)
        self.results_xml = open(os.path.join(self.basedir, 'test-results.xml'),
                                'w')

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def test_missing_file_param(self):
        self.results_xml.close()
        self.assertRaises(AssertionError, pythontools.unittest, self.ctxt)

    def test_empty_results(self):
        self.results_xml.write('<?xml version="1.0"?>'
                              '<unittest-results>'
                              '</unittest-results>')
        self.results_xml.close()
        pythontools.unittest(self.ctxt, self.results_xml.name)
        type, function, xml = self.ctxt.output.pop()
        self.assertEqual(Recipe.REPORT, type)
        self.assertEqual(0, len(xml.children))

    def test_successful_test(self):
        self.results_xml.write('<?xml version="1.0"?>'
                              '<unittest-results>'
                              '<test duration="0.12" status="success"'
                              '      file="%s"'
                              '      name="test_foo (pkg.BarTestCase)"/>'
                              '</unittest-results>'
                              % os.path.join(self.ctxt.basedir, 'bar_test.py'))
        self.results_xml.close()
        pythontools.unittest(self.ctxt, self.results_xml.name)
        type, function, xml = self.ctxt.output.pop()
        self.assertEqual(Recipe.REPORT, type)
        self.assertEqual(1, len(xml.children))
        test_elem = xml.children[0]
        self.assertEqual('test', test_elem.name)
        self.assertEqual('0.12', test_elem.attr['duration'])
        self.assertEqual('success', test_elem.attr['status'])
        self.assertEqual('bar_test.py', test_elem.attr['file'])
        self.assertEqual('test_foo (pkg.BarTestCase)', test_elem.attr['name'])

    def test_file_path_normalization(self):
        self.results_xml.write('<?xml version="1.0"?>'
                              '<unittest-results>'
                              '<test duration="0.12" status="success"'
                              '      file="%s"'
                              '      name="test_foo (pkg.BarTestCase)"/>'
                              '</unittest-results>'
                              % os.path.join(self.ctxt.basedir, 'bar_test.py'))
        self.results_xml.close()
        pythontools.unittest(self.ctxt, self.results_xml.name)
        type, function, xml = self.ctxt.output.pop()
        self.assertEqual('bar_test.py', xml.children[0].attr['file'])

    def test_missing_file_attribute(self):
        self.results_xml.write('<?xml version="1.0"?>'
                              '<unittest-results>'
                              '<test duration="0.12" status="success"'
                              '      name="test_foo (pkg.BarTestCase)"/>'
                              '</unittest-results>')
        self.results_xml.close()
        pythontools.unittest(self.ctxt, self.results_xml.name)
        type, function, xml = self.ctxt.output.pop()
        self.assertEqual(None, xml.children[0].attr.get('file'))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TraceTestCase, 'test'))
    suite.addTest(unittest.makeSuite(UnittestTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
