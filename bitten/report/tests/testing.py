# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

import unittest

from trac.db import DatabaseManager
from trac.test import EnvironmentStub, Mock
from trac.web.href import Href
from bitten.model import *
from bitten.report.testing import TestResultsChartGenerator, \
                    TestResultsSummarizer


class TestResultsChartGeneratorTestCase(unittest.TestCase):

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
        generator = TestResultsChartGenerator(self.env)
        self.assertEqual(['test'], generator.get_supported_categories())

    def test_no_reports(self):
        req = Mock()
        config = Mock(name='trunk', min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)
        generator = TestResultsChartGenerator(self.env)
        template, data = generator.generate_chart_data(req, config, 'test')
        self.assertEqual('json.txt', template)
        data = data['json']
        self.assertEqual('Unit Tests', data['title'])
        actual_data = data['data']
        self.assertEqual([], actual_data[0]['data'])
        self.assertEqual('Total', actual_data[0]['label'])
        self.assertEqual('Failures', actual_data[1]['label'])

    def test_single_platform(self):
        config = Mock(name='trunk', min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)
        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo', category='test')
        report.items += [{'status': 'success'}, {'status': 'failure'},
                         {'status': 'success'}]
        report.insert()

        req = Mock()
        generator = TestResultsChartGenerator(self.env)
        template, data = generator.generate_chart_data(req, config, 'test')
        self.assertEqual('json.txt', template)
        data = data['json']
        self.assertEqual('Unit Tests', data['title'])
        actual_data = data['data']
        self.assertEqual('123', actual_data[0]['data'][0][0])
        self.assertEqual('Total', actual_data[0]['label'])
        self.assertEqual(3, actual_data[0]['data'][0][1])
        self.assertEqual('Failures', actual_data[1]['label'])
        self.assertEqual(1, actual_data[1]['data'][0][1])

    def test_multi_platform(self):
        config = Mock(name='trunk', min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)

        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo', category='test')
        report.items += [{'status': 'success'}, {'status': 'failure'},
                         {'status': 'success'}]
        report.insert()

        build = Build(self.env, config='trunk', platform=2, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo', category='test')
        report.items += [{'status': 'success'}, {'status': 'failure'},
                         {'status': 'failure'}]
        report.insert()

        req = Mock()
        generator = TestResultsChartGenerator(self.env)
        template, data = generator.generate_chart_data(req, config, 'test')
        self.assertEqual('json.txt', template)
        data = data['json']
        self.assertEqual('Unit Tests', data['title'])
        actual_data = data['data']
        self.assertEqual('123', actual_data[0]['data'][0][0])
        self.assertEqual('Total', actual_data[0]['label'])
        self.assertEqual(3, actual_data[0]['data'][0][1])
        self.assertEqual('123', actual_data[1]['data'][0][0])
        self.assertEqual('Failures', actual_data[1]['label'])
        self.assertEqual(2, actual_data[1]['data'][0][1])
        self.assertEqual('123', actual_data[2]['data'][0][0])
        self.assertEqual('Ignored', actual_data[2]['label'])
        self.assertEqual(0, actual_data[2]['data'][0][1])


class TestResultsSummarizerTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub()
        self.env.path = ''

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        connector, _ = DatabaseManager(self.env)._get_connector()
        for table in schema:
            for stmt in connector.to_sql(table):
                cursor.execute(stmt)

    def test_testcase_errors_and_failures(self):
        config = Mock(name='trunk', path='/somewhere', 
                      min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)
        step = Mock(name='foo')

        build = Build(self.env, config=config.name, platform=1, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step=step.name,
                        category='test')
        report.items += [{'fixture': 'test_foo',
                          'name': 'foo', 'file': 'foo.c',
                          'type': 'test', 'status': 'success'},
                         {'fixture': 'test_bar',
                          'name': 'bar', 'file': 'bar.c',
                          'type': 'test', 'status': 'error',
                          'traceback': 'Error traceback'},
                         {'fixture': 'test_baz',
                          'name': 'baz', 'file': 'baz.c',
                          'type': 'test', 'status': 'failure',
                          'traceback': 'Failure reason'}]
        report.insert()

        req = Mock(href=Href('trac'))
        generator = TestResultsSummarizer(self.env)
        template, data = generator.render_summary(req,
                                            config, build, step, 'test')
        self.assertEquals('json.txt', template)
        self.assertEquals(data['totals'],
                {'ignore': 0, 'failure': 1, 'success': 1, 'error': 1})
        for fixture in data['fixtures']:
            if fixture.has_key('failures'):
                if fixture['failures'][0]['status'] == 'error':
                    self.assertEquals('test_bar', fixture['name'])
                    self.assertEquals('Error traceback',
                                      fixture['failures'][0]['traceback'])
                if fixture['failures'][0]['status'] == 'failure':
                    self.assertEquals('test_baz', fixture['name'])
                    self.assertEquals('Failure reason',
                                      fixture['failures'][0]['traceback'])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestResultsChartGeneratorTestCase))
    suite.addTest(unittest.makeSuite(TestResultsSummarizerTestCase))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
