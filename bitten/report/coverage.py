# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2007-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

from genshi.builder import tag
from trac.core import *
from trac.mimeview.api import IHTMLPreviewAnnotator
from trac.resource import Resource
from trac.util.datefmt import to_timestamp
from trac.web.api import IRequestFilter
from trac.web.chrome import add_stylesheet, add_ctxtnav, add_warning
from bitten.api import IReportChartGenerator, IReportSummarizer
from bitten.model import BuildConfig, Build, Report

__docformat__ = 'restructuredtext en'


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
  AND build.rev_time >= %%s AND build.rev_time <= %%s
GROUP BY build.rev_time, build.rev, build.platform
ORDER BY build.rev_time""" % (db.cast('item_lines.value', 'int'),
                              db.cast('item_lines.value', 'int'),
                              db.cast('item_percentage.value', 'int')),
                              (config.name, 
                               config.min_rev_time(self.env),
                               config.max_rev_time(self.env)))

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

        data = {'title': 'Test Coverage',
                'data': [
                    {'label': 'Lines of code', 'data': [[item[0], item[1]] for item in coverage], 'lines': {'fill': True}},
                    {'label': 'Coverage', 'data': [[item[0], item[2]] for item in coverage]},
                ],
                'options': {
                    'legend': {'position': 'sw', 'backgroundOpacity': 0.7},
                    'xaxis': {'tickDecimals': 0},
                    'yaxis': {'tickDecimals': 0},
                },
               }
        return 'json.txt', {"json": data}


class TestCoverageSummarizer(Component):
    implements(IReportSummarizer)

    # IReportSummarizer methods

    def get_supported_categories(self):
        return ['coverage']

    def render_summary(self, req, config, build, step, category):
        assert category == 'coverage'

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
SELECT item_name.value AS unit, item_file.value AS file,
       max(item_lines.value) AS loc, max(item_percentage.value) AS cov
FROM bitten_report AS report
 LEFT OUTER JOIN bitten_report_item AS item_name
  ON (item_name.report=report.id AND item_name.name='name')
 LEFT OUTER JOIN bitten_report_item AS item_file
  ON (item_file.report=report.id AND item_file.item=item_name.item AND
      item_file.name='file')
 LEFT OUTER JOIN bitten_report_item AS item_lines
  ON (item_lines.report=report.id AND item_lines.item=item_name.item AND
      item_lines.name='lines')
 LEFT OUTER JOIN bitten_report_item AS item_percentage
  ON (item_percentage.report=report.id AND
      item_percentage.item=item_name.item AND
      item_percentage.name='percentage')
WHERE category='coverage' AND build=%s AND step=%s
GROUP BY file, item_name.value
ORDER BY item_name.value""", (build.id, step.name))

        units = []
        total_loc, total_cov = 0, 0
        for unit, file, loc, cov in cursor:
            try:
                loc, cov = int(loc), float(cov)
            except TypeError:
                continue # no rows
            if loc:
                d = {'name': unit, 'loc': loc, 'cov': int(cov)}
                if file:
                    d['href'] = req.href.browser(config.path, file, rev=build.rev, annotate='coverage')
                units.append(d)
                total_loc += loc
                total_cov += loc * cov

        coverage = 0
        if total_loc != 0:
            coverage = total_cov // total_loc

        return 'bitten_summary_coverage.html', {
            'units': units,
            'totals': {'loc': total_loc, 'cov': int(coverage)}
        }


class TestCoverageAnnotator(Component):
    """
    >>> from genshi.builder import tag
    >>> from trac.test import Mock, MockPerm
    >>> from trac.mimeview import Context
    >>> from trac.util.datefmt import to_datetime, utc
    >>> from trac.web.href import Href
    >>> from bitten.model import BuildConfig, Build, Report
    >>> from bitten.report.tests.coverage import env_stub_with_tables
    >>> env = env_stub_with_tables()
    >>> repos = Mock(get_changeset=lambda x: Mock(date=to_datetime(12345, utc)))
    >>> env.get_repository = lambda: repos

    >>> BuildConfig(env, name='trunk', path='trunk').insert()
    >>> Build(env, rev=123, config='trunk', rev_time=12345, platform=1).insert()
    >>> rpt = Report(env, build=1, step='test', category='coverage')
    >>> rpt.items.append({'file': 'foo.py', 'line_hits': '5 - 0'})
    >>> rpt.insert()

    >>> ann = TestCoverageAnnotator(env)
    >>> req = Mock(href=Href('/'), perm=MockPerm(),
    ...                 chrome={'warnings': []}, args={})

    Version in the branch should not match:
    >>> context = Context.from_request(req, 'source', '/branches/blah/foo.py', 123)
    >>> ann.get_annotation_data(context)
    []

    Version in the trunk should match:
    >>> context = Context.from_request(req, 'source', '/trunk/foo.py', 123)
    >>> data = ann.get_annotation_data(context)
    >>> print data
    [u'5', u'-', u'0']

    >>> def annotate_row(lineno, line):
    ...     row = tag.tr()
    ...     ann.annotate_row(context, row, lineno, line, data)
    ...     return row.generate().render('html')

    >>> annotate_row(1, 'x = 1')
    '<tr><th class="covered">5</th></tr>'
    >>> annotate_row(2, '')
    '<tr><th></th></tr>'
    >>> annotate_row(3, 'y = x')
    '<tr><th class="uncovered">0</th></tr>'
    """
    implements(IRequestFilter, IHTMLPreviewAnnotator)

    # IRequestFilter methods

    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        """ Adds a 'Coverage' context navigation menu item. """
        resource = data and data.get('context') \
                        and data.get('context').resource or None
        if resource and isinstance(resource, Resource) \
                    and resource.realm=='source' and data.get('file') \
                    and not req.args.get('annotate', '') == 'coverage':
            add_ctxtnav(req, tag.a('Coverage',
                    title='Annotate file with test coverage '
                          'data (if available)',
                    href=req.href.browser(resource.id, 
                        annotate='coverage', rev=req.args.get('rev'),
                        created=data.get('rev')),
                    rel='nofollow'))
        return template, data, content_type

    # IHTMLPreviewAnnotator methods

    def get_annotation_type(self):
        return 'coverage', 'Cov', 'Code coverage'

    def get_annotation_data(self, context):
        add_stylesheet(context.req, 'bitten/bitten_coverage.css')

        resource = context.resource

        # attempt to use the version passed in with the request,
        # otherwise fall back to the latest version of this file.
        version = context.req.args.get('rev', resource.version)
        # get the last change revision for the file so that we can
        # pick coverage data as latest(version >= file_revision)
        created = context.req.args.get('created', resource.version)

        repos = self.env.get_repository()        
        version_time = to_timestamp(repos.get_changeset(version).date)
        if version != created:
            created_time = to_timestamp(repos.get_changeset(created).date)
        else:
            created_time = version_time

        self.log.debug("Looking for coverage report for %s@%s [%s:%s]..." % (
                        resource.id, str(resource.version), created, version))

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
                SELECT b.id, b.rev, i2.value
                FROM bitten_config AS c
                    INNER JOIN bitten_build AS b ON c.name=b.config
                    INNER JOIN bitten_report AS r ON b.id=r.build
                    INNER JOIN bitten_report_item AS i1 ON r.id=i1.report
                    INNER JOIN bitten_report_item AS i2 ON (i1.item=i2.item
                                                    AND i1.report=i2.report)
                WHERE i2.name='line_hits'
                    AND b.rev_time>=%s
                    AND b.rev_time<=%s
                    AND i1.name='file'
                    AND """ + db.concat('c.path', "'/'", 'i1.value') + """=%s
                ORDER BY b.rev_time DESC LIMIT 1""" ,
            (created_time, version_time, resource.id.lstrip('/')))

        row = cursor.fetchone()
        if row:
            build_id, build_rev, line_hits = row
            coverage = line_hits.split()
            self.log.debug("Coverage annotate for %s@%s using build %d: %s",
                            resource.id, build_rev, build_id, coverage)
            return coverage
        add_warning(context.req, "No coverage annotation found for "
                                 "/%s for revision range [%s:%s]." % (
                                 resource.id.lstrip('/'), version, created))
        return []

    def annotate_row(self, context, row, lineno, line, data):
        from genshi.builder import tag
        lineno -= 1 # 0-based index for data
        if lineno >= len(data):
            row.append(tag.th())
            return
        row_data = data[lineno]
        if row_data == '-':
            row.append(tag.th())
        elif row_data == '0':
            row.append(tag.th(row_data, class_='uncovered'))
        else:
            row.append(tag.th(row_data, class_='covered'))
