# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

import doctest
import unittest

from trac.db import DatabaseManager
from trac.test import EnvironmentStub, Mock
from bitten.model import *
from bitten.report import coverage
from bitten.report.coverage import TestCoverageChartGenerator

def env_stub_with_tables():
    env = EnvironmentStub()
    db = env.get_db_cnx()
    cursor = db.cursor()
    connector, _ = DatabaseManager(env)._get_connector()
    for table in schema:
        for stmt in connector.to_sql(table):
            cursor.execute(stmt)
    return env

class TestCoverageChartGeneratorTestCase(unittest.TestCase):

    def setUp(self):
        self.env = env_stub_with_tables()
        self.env.path = ''

    def test_supported_categories(self):
        generator = TestCoverageChartGenerator(self.env)
        self.assertEqual(['coverage'], generator.get_supported_categories())

    def test_no_reports(self):
        req = Mock()
        config = Mock(name='trunk', min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)
        generator = TestCoverageChartGenerator(self.env)
        template, data = generator.generate_chart_data(req, config, 'coverage')
        self.assertEqual('json.txt', template)
        data = data['json']
        self.assertEqual('Test Coverage', data['title'])
        actual_data = data['data']
        self.assertEqual('Lines of code', actual_data[0]['label'])
        self.assertEqual('Coverage', actual_data[1]['label'])

    def test_single_platform(self):
        config = Mock(name='trunk', min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)
        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo',
                        category='coverage')
        report.items += [{'lines': '12', 'percentage': '25'}]
        report.insert()

        req = Mock()
        generator = TestCoverageChartGenerator(self.env)
        template, data = generator.generate_chart_data(req, config, 'coverage')
        self.assertEqual('json.txt', template)
        data = data['json']
        self.assertEqual('Test Coverage', data['title'])
        actual_data = data['data']
        self.assertEqual('123', actual_data[0]['data'][0][0])
        self.assertEqual('Lines of code', actual_data[0]['label'])
        self.assertEqual(12, actual_data[0]['data'][0][1])
        self.assertEqual('Coverage', actual_data[1]['label'])
        self.assertEqual(3, actual_data[1]['data'][0][1])

    def test_multi_platform(self):
        config = Mock(name='trunk', min_rev_time=lambda env: 0, 
                      max_rev_time=lambda env: 1000)
        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo',
                        category='coverage')
        report.items += [{'lines': '12', 'percentage': '25'}]
        report.insert()
        build = Build(self.env, config='trunk', platform=2, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo',
                        category='coverage')
        report.items += [{'lines': '12', 'percentage': '50'}]
        report.insert()

        req = Mock()
        generator = TestCoverageChartGenerator(self.env)
        template, data = generator.generate_chart_data(req, config, 'coverage')
        self.assertEqual('json.txt', template)
        data = data['json']
        self.assertEqual('Test Coverage', data['title'])
        actual_data = data['data']
        self.assertEqual('123', actual_data[0]['data'][0][0])
        self.assertEqual('Lines of code', actual_data[0]['label'])
        self.assertEqual(12, actual_data[0]['data'][0][1])
        self.assertEqual('Coverage', actual_data[1]['label'])
        self.assertEqual(6, actual_data[1]['data'][0][1])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCoverageChartGeneratorTestCase))
    suite.addTest(doctest.DocTestSuite(coverage))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
