# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2007 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

import re

from trac.core import *
from trac.web import IRequestHandler
from bitten.model import BuildConfig
from bitten.trac_ext.api import IReportChartGenerator


class ReportChartController(Component):
    implements(IRequestHandler)

    generators = ExtensionPoint(IReportChartGenerator)

    # IRequestHandler methods

    def match_request(self, req):
        match = re.match(r'/build/([\w.-]+)/chart/(\w+)', req.path_info)
        if match:
            req.args['config'] = match.group(1)
            req.args['category'] = match.group(2)
            return True

    def process_request(self, req):
        category = req.args.get('category')
        config = BuildConfig.fetch(self.env, name=req.args.get('config'))

        for generator in self.generators:
            if category in generator.get_supported_categories():
                template = generator.generate_chart_data(req, config,
                                                         category)
                break
        else:
            raise TracError('Unknown report category "%s"' % category)

        return template, 'text/xml'


class TestResultsChartGenerator(Component):
    implements(IReportChartGenerator)

    # IReportChartGenerator methods

    def get_supported_categories(self):
        return ['test']

    def generate_chart_data(self, req, config, category):
        assert category == 'test'

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
SELECT build.rev, build.platform, item_status.value AS status, COUNT(*) AS num
FROM bitten_build AS build
 LEFT OUTER JOIN bitten_report AS report ON (report.build=build.id)
 LEFT OUTER JOIN bitten_report_item AS item_status
  ON (item_status.report=report.id AND item_status.name='status')
WHERE build.config=%s AND report.category='test'
GROUP BY build.rev_time, build.rev, build.platform, item_status.value
ORDER BY build.rev_time, build.platform""", (config.name,))

        prev_rev = None
        prev_platform, platform_total = None, 0
        tests = []
        for rev, platform, status, num in cursor:
            if rev != prev_rev:
                tests.append([rev, 0, 0])
                prev_rev = rev
                platform_total = 0
            if platform != prev_platform:
                prev_platform = platform
                platform_total = 0

            platform_total += num
            tests[-1][1] = max(platform_total, tests[-1][1])
            if status != 'success':
                tests[-1][2] = max(num, tests[-1][2])

        req.hdf['chart.title'] = 'Unit Tests'
        req.hdf['chart.data'] = [
            [''] + ['[%s]' % item[0] for item in tests],
            ['Total'] + [item[1] for item in tests],
            ['Failures'] + [item[2] for item in tests]
        ]

        return 'bitten_chart_tests.cs'


class TestCoverageChartGenerator(Component):
    implements(IReportChartGenerator)

    # IReportChartGenerator methods

    def get_supported_categories(self):
        return ['coverage']

    def generate_chart_data(self, req, config, category):
        assert category == 'coverage'

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
SELECT build.rev, SUM(%s) AS loc, SUM(%s * %s / 100) AS cov
FROM bitten_build AS build
 LEFT OUTER JOIN bitten_report AS report ON (report.build=build.id)
 LEFT OUTER JOIN bitten_report_item AS item_lines
  ON (item_lines.report=report.id AND item_lines.name='lines')
 LEFT OUTER JOIN bitten_report_item AS item_percentage
  ON (item_percentage.report=report.id AND item_percentage.name='percentage' AND
      item_percentage.item=item_lines.item)
WHERE build.config=%%s AND report.category='coverage'
GROUP BY build.rev_time, build.rev, build.platform
ORDER BY build.rev_time""" % (db.cast('item_lines.value', 'int'),
                              db.cast('item_lines.value', 'int'),
                              db.cast('item_percentage.value', 'int')),
                              (config.name,))

        prev_rev = None
        coverage = []
        for rev, loc, cov in cursor:
            if rev != prev_rev:
                coverage.append([rev, 0, 0])
            if loc > coverage[-1][1]:
                coverage[-1][1] = int(loc)
            if cov > coverage[-1][2]:
                coverage[-1][2] = int(cov)
            prev_rev = rev

        req.hdf['chart.title'] = 'Test Coverage'
        req.hdf['chart.data'] = [
            [''] + ['[%s]' % item[0] for item in coverage],
            ['Lines of code'] + [item[1] for item in coverage],
            ['Coverage'] + [int(item[2]) for item in coverage]
        ]

        return 'bitten_chart_coverage.cs'
