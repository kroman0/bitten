# -*- coding: iso8859-1 -*-
#
# Copyright (C) 2005 Christopher Lenz <cmlenz@gmx.de>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.cmlenz.net/wiki/License.

import unittest

from trac.test import EnvironmentStub, Mock
from trac.web.clearsilver import HDFWrapper
from bitten.model import *
from bitten.trac_ext.charts import *


class TestResultsChartGeneratorTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        for table in schema:
            for stmt in db.to_sql(table):
                cursor.execute(stmt)

    def test_supported_categories(self):
        generator = TestResultsChartGenerator(self.env)
        self.assertEqual(['test'], generator.get_supported_categories())

    def test_no_reports(self):
        req = Mock(hdf=HDFWrapper())
        config = Mock(name='trunk')
        generator = TestResultsChartGenerator(self.env)
        template = generator.generate_chart_data(req, config, 'test')
        self.assertEqual('bitten_chart_tests.cs', template)
        self.assertEqual('Unit Tests', req.hdf['chart.title'])
        self.assertEqual('', req.hdf['chart.data.0.0'])
        self.assertEqual('Total', req.hdf['chart.data.1.0'])
        self.assertEqual('Failures', req.hdf['chart.data.2.0'])

    def test_single_platform(self):
        config = Mock(name='trunk')
        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo', category='test')
        report.items += [{'status': 'success'}, {'status': 'failure'},
                         {'status': 'success'}]
        report.insert()

        req = Mock(hdf=HDFWrapper())
        generator = TestResultsChartGenerator(self.env)
        template = generator.generate_chart_data(req, config, 'test')
        self.assertEqual('bitten_chart_tests.cs', template)
        self.assertEqual('Unit Tests', req.hdf['chart.title'])
        self.assertEqual('', req.hdf['chart.data.0.0'])
        self.assertEqual('[123]', req.hdf['chart.data.0.1'])
        self.assertEqual('Total', req.hdf['chart.data.1.0'])
        self.assertEqual('3', req.hdf['chart.data.1.1'])
        self.assertEqual('Failures', req.hdf['chart.data.2.0'])
        self.assertEqual('1', req.hdf['chart.data.2.1'])

    def test_multi_platform(self):
        config = Mock(name='trunk')

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

        req = Mock(hdf=HDFWrapper())
        generator = TestResultsChartGenerator(self.env)
        template = generator.generate_chart_data(req, config, 'test')
        self.assertEqual('bitten_chart_tests.cs', template)
        self.assertEqual('Unit Tests', req.hdf['chart.title'])
        self.assertEqual('', req.hdf['chart.data.0.0'])
        self.assertEqual('[123]', req.hdf['chart.data.0.1'])
        self.assertEqual('Total', req.hdf['chart.data.1.0'])
        self.assertEqual('3', req.hdf['chart.data.1.1'])
        self.assertEqual('Failures', req.hdf['chart.data.2.0'])
        self.assertEqual('2', req.hdf['chart.data.2.1'])


class TestCoverageChartGeneratorTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        for table in schema:
            for stmt in db.to_sql(table):
                cursor.execute(stmt)

    def test_supported_categories(self):
        generator = TestCoverageChartGenerator(self.env)
        self.assertEqual(['coverage'], generator.get_supported_categories())

    def test_no_reports(self):
        req = Mock(hdf=HDFWrapper())
        config = Mock(name='trunk')
        generator = TestCoverageChartGenerator(self.env)
        template = generator.generate_chart_data(req, config, 'coverage')
        self.assertEqual('bitten_chart_coverage.cs', template)
        self.assertEqual('Test Coverage', req.hdf['chart.title'])
        self.assertEqual('', req.hdf['chart.data.0.0'])
        self.assertEqual('Lines of code', req.hdf['chart.data.1.0'])
        self.assertEqual('Coverage', req.hdf['chart.data.2.0'])

    def test_single_platform(self):
        config = Mock(name='trunk')
        build = Build(self.env, config='trunk', platform=1, rev=123,
                      rev_time=42)
        build.insert()
        report = Report(self.env, build=build.id, step='foo',
                        category='coverage')
        report.items += [{'lines': '12', 'percentage': '25'}]
        report.insert()

        req = Mock(hdf=HDFWrapper())
        generator = TestCoverageChartGenerator(self.env)
        template = generator.generate_chart_data(req, config, 'coverage')
        self.assertEqual('bitten_chart_coverage.cs', template)
        self.assertEqual('Test Coverage', req.hdf['chart.title'])
        self.assertEqual('', req.hdf['chart.data.0.0'])
        self.assertEqual('[123]', req.hdf['chart.data.0.1'])
        self.assertEqual('Lines of code', req.hdf['chart.data.1.0'])
        self.assertEqual('12', req.hdf['chart.data.1.1'])
        self.assertEqual('Coverage', req.hdf['chart.data.2.0'])
        self.assertEqual('3', req.hdf['chart.data.2.1'])

    def test_multi_platform(self):
        config = Mock(name='trunk')
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

        req = Mock(hdf=HDFWrapper())
        generator = TestCoverageChartGenerator(self.env)
        template = generator.generate_chart_data(req, config, 'coverage')
        self.assertEqual('bitten_chart_coverage.cs', template)
        self.assertEqual('Test Coverage', req.hdf['chart.title'])
        self.assertEqual('', req.hdf['chart.data.0.0'])
        self.assertEqual('[123]', req.hdf['chart.data.0.1'])
        self.assertEqual('Lines of code', req.hdf['chart.data.1.0'])
        self.assertEqual('12', req.hdf['chart.data.1.1'])
        self.assertEqual('Coverage', req.hdf['chart.data.2.0'])
        self.assertEqual('6', req.hdf['chart.data.2.1'])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestResultsChartGeneratorTestCase))
    suite.addTest(unittest.makeSuite(TestCoverageChartGeneratorTestCase))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
