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
from bitten.model import *
from bitten.report.lint import PyLintChartGenerator


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


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PyLintChartGeneratorTestCase))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
