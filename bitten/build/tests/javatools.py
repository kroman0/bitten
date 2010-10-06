# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2006 Matthew Good <matt@matt-good.net>
# Copyright (C) 2007-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

import os
import os.path
import shutil
import tempfile
import unittest

from bitten.build import javatools
from bitten.recipe import Context, Recipe

class CoberturaTestCase(unittest.TestCase):
    xml_template="""<?xml version="1.0"?>
<!DOCTYPE coverage SYSTEM "http://cobertura.sourceforge.net/xml/coverage-02.dtd">

<coverage timestamp="1148533713840">
  <sources>
    <source>src</source>
  </sources>
  <packages>
    <package name="test">
      <classes>%s
      </classes>
    </package>
  </packages>
</coverage>"""

    def setUp(self):
        self.basedir = os.path.realpath(tempfile.mkdtemp())
        self.ctxt = Context(self.basedir)

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def _create_file(self, *path, **kw):
        filename = os.path.join(self.basedir, *path)
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        fd = file(filename, 'w')
        content = kw.get('content')
        if content is not None:
            fd.write(content)
        fd.close()
        return filename[len(self.basedir) + 1:]

    def test_basic(self):
        filename = self._create_file('coverage.xml', content=self.xml_template % """
        <class name="test.TestClass" filename="test/TestClass.java">
          <lines>
            <line number="1" hits="0" branch="false"/>
            <line number="2" hits="1" branch="false"/>
            <line number="3" hits="0" branch="false"/>
            <line number="4" hits="2" branch="false"/>
          </lines>
        </class>""")
        javatools.cobertura(self.ctxt, file_=filename)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('coverage', category)
        self.assertEqual(1, len(xml.children))

        elem = xml.children[0]
        self.assertEqual('coverage', elem.name)
        self.assertEqual('src/test/TestClass.java', elem.attr['file'])
        self.assertEqual('test.TestClass', elem.attr['name'])
        self.assertEqual(4, elem.attr['lines'])
        self.assertEqual(50, elem.attr['percentage'])

    def test_skipped_lines(self):
        filename = self._create_file('coverage.xml', content=self.xml_template % """
        <class name="test.TestClass" filename="test/TestClass.java">
          <lines>
            <line number="1" hits="0" branch="false"/>
            <line number="3" hits="1" branch="false"/>
          </lines>
        </class>""")
        javatools.cobertura(self.ctxt, file_=filename)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('coverage', category)
        self.assertEqual(1, len(xml.children))

        elem = xml.children[0]
        self.assertEqual('coverage', elem.name)
        self.assertEqual('src/test/TestClass.java', elem.attr['file'])
        self.assertEqual('test.TestClass', elem.attr['name'])
        self.assertEqual(2, elem.attr['lines'])
        self.assertEqual(50, elem.attr['percentage'])

        line_hits = elem.children[0]
        self.assertEqual('line_hits', line_hits.name)
        self.assertEqual('0 - 1', line_hits.children[0])

    def test_interface(self):
        filename = self._create_file('coverage.xml', content=self.xml_template % """
        <class name="test.TestInterface" filename="test/TestInterface.java">
          <lines>
          </lines>
        </class>""")
        javatools.cobertura(self.ctxt, file_=filename)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('coverage', category)
        self.assertEqual(1, len(xml.children))

        elem = xml.children[0]
        self.assertEqual('coverage', elem.name)
        self.assertEqual('src/test/TestInterface.java', elem.attr['file'])
        self.assertEqual('test.TestInterface', elem.attr['name'])
        self.assertEqual(0, elem.attr['lines'])
        self.assertEqual(0, elem.attr['percentage'])

class PyTestTestCase(unittest.TestCase):
    xml_template = """<testsuite name="%(name)s" errors="%(errors)d"
        failures="%(failures)d" skips="%(skips)d" tests="%(tests)d" time="%(time)f">
    %(body)s
</testsuite>
"""
    def setUp(self):
        self.basedir = os.path.realpath(tempfile.mkdtemp())
        self.ctxt = Context(self.basedir)

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def _xml_file(self, body, name="", errors=0, failures=0, skips=0, tests=0, time=0.01):
        if tests == 0:
            tests = errors + failures + skips
        (fd, path) = tempfile.mkstemp(prefix="junit", suffix=".xml", dir=self.basedir, text=True)
        stream = os.fdopen(fd, "w")
        content = self.xml_template % dict(body=body, name=name, errors=errors,
                failures=failures, skips=skips, tests=tests, time=time)
        stream.write(content)
        stream.close()
        return path

    def test_simple(self):
        body = '<testcase classname="_test.test_event" name="test_simple" time="0.0002"></testcase>'
        filename = self._xml_file(body, tests=1)
        javatools.junit(self.ctxt, file_=filename)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('test', category)
        self.assertEqual(1, len(xml.children))

        elem = xml.children[0]
        self.assertEqual('test', elem.name)
        self.assertEqual('test_simple', elem.attr['name'])
        self.assertEqual('success', elem.attr['status'])
        self.assertEqual(0, len(elem.children))

    def test_setup_fail(self):
        """Check that py.test setup failures are handled"""
        body = '<testcase classname="_test.test_event" name="test_simple" time="0">' \
             + '<error message="test setup failure">request = &lt;FuncargRequest for &lt;Function...</error>' \
             + '</testcase>'
        filename = self._xml_file(body, errors=1)
        javatools.junit(self.ctxt, file_=filename)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('test', category)
        self.assertEqual(1, len(xml.children))

        elem = xml.children[0]
        self.assertEqual('test', elem.name)
        self.assertEqual('test_simple', elem.attr['name'])
        self.assertEqual('error', elem.attr['status'])
        self.assertEqual(1, len(elem.children))

        trace = elem.children[0]
        self.assertEqual('traceback', trace.name)
        self.assertEqual(1, len(trace.children))
        self.assertEqual('request = <FuncargRequest for <Function...', trace.children[0])

        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual(Recipe.ERROR, type)

        self.assertEqual(0, len(self.ctxt.output))

    def test_skipped_tests(self):
        """Check that skipped tests (here: xfail in py.test) are not considered an error"""
        body = '<testcase classname="_test.test_event" name="test_simple" time="0.06">' \
             + '<skipped/></testcase>'
        filename = self._xml_file(body, skips=1)
        javatools.junit(self.ctxt, file_=filename)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('test', category)
        self.assertEqual(1, len(xml.children))

        elem = xml.children[0]
        self.assertEqual('test', elem.name)
        self.assertEqual('test_simple', elem.attr['name'])
        self.assertEqual('ignore', elem.attr['status'])
        self.assertEqual(1, len(elem.children))

        trace = elem.children[0]
        self.assertEqual('traceback', trace.name)
        self.assertEqual(0, len(trace.children))

        self.assertEqual(0, len(self.ctxt.output))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CoberturaTestCase, 'test'))
    suite.addTest(unittest.makeSuite(PyTestTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
