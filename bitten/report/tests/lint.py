# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2007-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

import unittest

from trac.db import DatabaseManager
from trac.test import EnvironmentStub, Mock
from trac.web.href import Href
from trac.web.chrome import Chrome
from bitten.model import *
from bitten.report.lint import PyLintChartGenerator, PyLintSummarizer
from bitten.web_ui import BittenChrome
from genshi import Stream


def MockRequest():
    return Mock(method='GET', chrome={},
                href=Href('/'), perm=(), tz=None, abs_href=Href('/'),
                authname=None, form_token=None, session=None)


class PyLintChartGeneratorTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub()
        self.env.path = ''

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        connector, _ = DatabaseManager(self.env)._get_connector()
        for table in schema:
            for stmt in connector.to_sql(table):
                cursor.execute(stmt)

    def test_supported_categories(self):
        generator = PyLintChartGenerator(self.env)
        self.assertEqual(['lint'], generator.get_supported_categories())

    def test_no_reports(self):
        req = Mock()
        config = Mock(name='trunk', min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)
        generator = PyLintChartGenerator(self.env)
        template, data = generator.generate_chart_data(req, config, 'lint')
        self.assertEqual('json.txt', template)
        data = data['json']
        self.assertEqual('Lint Problems by Type', data['title'])
        actual_data = data['data']
        self.assertEqual('Total Problems', actual_data[0]['label'])
        self.assertEqual('Convention', actual_data[1]['label'])
        self.assertEqual('Error', actual_data[2]['label'])
        self.assertEqual('Refactor', actual_data[3]['label'])
        self.assertEqual('Warning', actual_data[4]['label'])

    def test_single_platform(self):
        config = Mock(name='trunk', min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)
        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo', category='lint')
        report.items += [{'category': 'convention'}, {'category': 'warning'},
                         {'category': 'error'}, {'category': 'refactor'},
                         {'category': 'warning'}, {'category': 'error'},
                         {'category': 'refactor'}, {'category': 'error'},
                         {'category': 'refactor'}, {'category': 'refactor'}]
        report.insert()

        req = Mock()
        generator = PyLintChartGenerator(self.env)
        template, data = generator.generate_chart_data(req, config, 'lint')
        self.assertEqual('json.txt', template)
        data = data['json']
        self.assertEqual('Lint Problems by Type', data['title'])
        actual_data = data['data']
        self.assertEqual('123', actual_data[0]['data'][0][0])

        self.assertEqual('Total Problems', actual_data[0]['label'])
        self.assertEqual(10, actual_data[0]['data'][0][1])
        self.assertEqual('Convention', actual_data[1]['label'])
        self.assertEqual(1, actual_data[1]['data'][0][1])
        self.assertEqual('Error', actual_data[2]['label'])
        self.assertEqual(3, actual_data[2]['data'][0][1])
        self.assertEqual('Refactor', actual_data[3]['label'])
        self.assertEqual(4, actual_data[3]['data'][0][1])
        self.assertEqual('Warning', actual_data[4]['label'])
        self.assertEqual(2, actual_data[4]['data'][0][1])

    def test_multi_platform(self):
        config = Mock(name='trunk', min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)

        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo', category='lint')
        report.items += [{'category': 'error'}, {'category': 'refactor'}]
        report.insert()

        build = Build(self.env, config='trunk', platform=2, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo', category='lint')
        report.items += [{'category': 'convention'}, {'category': 'warning'}]
        report.insert()

        req = Mock()
        generator = PyLintChartGenerator(self.env)
        template, data = generator.generate_chart_data(req, config, 'lint')
        self.assertEqual('json.txt', template)
        data = data['json']
        self.assertEqual('Lint Problems by Type', data['title'])
        actual_data = data['data']
        self.assertEqual('123', actual_data[0]['data'][0][0])

        self.assertEqual('Total Problems', actual_data[0]['label'])
        self.assertEqual(4, actual_data[0]['data'][0][1])
        self.assertEqual('Convention', actual_data[1]['label'])
        self.assertEqual(1, actual_data[1]['data'][0][1])
        self.assertEqual('Error', actual_data[2]['label'])
        self.assertEqual(1, actual_data[2]['data'][0][1])
        self.assertEqual('Refactor', actual_data[3]['label'])
        self.assertEqual(1, actual_data[3]['data'][0][1])
        self.assertEqual('Warning', actual_data[4]['label'])
        self.assertEqual(1, actual_data[4]['data'][0][1])


class PyLintChartSummarizerTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub(enable=['trac.*', 'bitten.*'])
        self.env.path = ''

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        connector, _ = DatabaseManager(self.env)._get_connector()
        for table in schema:
            for stmt in connector.to_sql(table):
                cursor.execute(stmt)

        BittenChrome(self.env)

    def test_supported_categories(self):
        summarizer = PyLintSummarizer(self.env)
        self.assertEqual(['lint'], summarizer.get_supported_categories())

    def test_no_reports(self):
        req = MockRequest()
        config = Mock(name='trunk', min_rev_time=lambda env: 0,
                      max_rev_time=lambda env: 1000, path='tmp/')
        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        step = BuildStep(self.env, build=build.id, name='foo',
                         status=BuildStep.SUCCESS)
        step.insert()

        summarizer = PyLintSummarizer(self.env)
        template, data = summarizer.render_summary(req, config, build, step,
                                                   'lint')
        self.assertEqual('bitten_summary_lint.html', template)
        self.assertEqual([], data['data'])
        self.assertEqual({'category': {'convention': 0, 'refactor': 0,
                                       'warning': 0, 'error': 0},
                          'files': 0, 'lines': 0, 'type': {}}, data['totals'])

        stream = Chrome(self.env).render_template(req, template,
                                                  {'data': data}, 'text/html',
                                                  fragment=True)
        stream = Stream(list(stream))
        for i, category in enumerate(("Convention", "Refactor", "Warning",
                                      "Error", "Totals")):
            text = stream.select('//tbody[@class="totals"]//td[%d]/text()'
                                 % (i + 1)).render()
            self.assertEqual('0', text, "Expected total for %r to have "
                             "value '0' but got %r" % (category, text))

    def test_basic_report(self):
        req = MockRequest()
        config = Mock(name='trunk', min_rev_time=lambda env: 0,
                      max_rev_time=lambda env: 1000, path='tmp/')
        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        step = BuildStep(self.env, build=build.id, name='foo',
                         status=BuildStep.SUCCESS)
        step.insert()
        report = Report(self.env, build=build.id, step='foo', category='lint')
        for line, category in enumerate(['convention', 'warning', 'error',
                                         'refactor', 'warning', 'error',
                                         'refactor', 'error', 'refactor',
                                         'refactor']):
            report.items.append({'category': category, 'file': 'foo.py',
                                 'lines': line, 'type': 'unknown'})
        report.insert()
        summarizer = PyLintSummarizer(self.env)
        template, data = summarizer.render_summary(req, config, build, step,
                                                   'lint')
        self.assertEqual('bitten_summary_lint.html', template)
        self.assertEqual([{'category': {'warning': 2, 'error': 3,
                                        'refactor': 4, 'convention': 1},
                           'catnames': ['warning', 'error', 'refactor',
                                        'convention'],
                           'lines': 10, 'href': '/browser/tmp/foo.py',
                           'file': 'foo.py', 'type': {'unknown': 10}}],
                         data['data'])
        self.assertEqual({'category': {'convention': 1, 'refactor': 4,
                                       'warning': 2, 'error': 3},
                          'files': 1, 'lines': 10, 'type': {'unknown': 10}},
                         data['totals'])

        stream = Chrome(self.env).render_template(req, template,
                                                  {'data': data}, 'text/html',
                                                  fragment=True)
        stream = Stream(list(stream))
        file_text = stream.select('//td[@class="file"]/a/text()').render()
        self.assertEqual("foo.py", file_text)
        for i, (category, cnt) in enumerate([
                ("Convention", 1), ("Refactor", 4),
                ("Warning", 2), ("Error", 3),
                ("Totals", 10)
                ]):
            text = stream.select('//tbody[@class="totals"]//td[%d]/text()'
                                 % (i + 1)).render().strip()
            self.assertEqual(str(cnt), text, "Expected total for %r to have "
                             "value '%d' but got %r" % (category, cnt, text))
            text_file = stream.select('//table/tbody[1]//td[%d]/text()'
                                 % (i + 2)).render().strip()
            self.assertEqual(str(cnt), text_file, "Expected category %r for "
                             "foo.py to have value '%d' but got %r" %
                             (category, cnt, text_file))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PyLintChartGeneratorTestCase))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
