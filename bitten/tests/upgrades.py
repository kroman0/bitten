# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

import unittest
import logging

import warnings
warnings.filterwarnings('ignore', '^Unknown table')
warnings.filterwarnings('ignore', '^the sets module is deprecated')

from trac.core import TracError
from trac.test import EnvironmentStub
from trac.db import Table, Column, Index, DatabaseManager
from bitten.upgrades import update_sequence, drop_index
from bitten import upgrades, main, model

import os
import shutil
import tempfile


class BaseUpgradeTestCase(unittest.TestCase):

    schema = None
    other_tables = []

    def setUp(self):
        self.env = EnvironmentStub()
        if hasattr(self.env, 'dburi'):
            # Trac gained support for testing against different databases in 0.11.5
            # If this support is available, we copy the test db uri configuration
            # into the main test config so it can be picked up by
            # upgrades.parse_scheme()
            self.env.config.set('trac', 'database', self.env.dburi)
        self.env.path = tempfile.mkdtemp()
        logs_dir = self.env.config.get("bitten", "logs_dir", "log/bitten")
        if os.path.isabs(logs_dir):
            raise ValueError("Should not have absolute logs directory for temporary test")
        logs_dir = os.path.join(self.env.path, logs_dir)
        self.logs_dir = logs_dir

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        for table_name in self.other_tables:
            cursor.execute("DROP TABLE IF EXISTS %s" % (table_name,))

        connector, _ = DatabaseManager(self.env)._get_connector()
        for table in self.schema:
            cursor.execute("DROP TABLE IF EXISTS %s" % (table.name,))
            for stmt in connector.to_sql(table):
                cursor.execute(stmt)

        db.commit()

    def tearDown(self):
        shutil.rmtree(self.env.path)
        del self.logs_dir
        del self.env


class LogWatcher(logging.Handler):

    def __init__(self, level=0):
        logging.Handler.__init__(self, level=0)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class UpgradeHelperTestCase(BaseUpgradeTestCase):

    schema = [
        Table('test_update_sequence', key='id')[
            Column('id', auto_increment=True), Column('name'),
        ],
        Table('test_drop_index', key='id')[
            Column('id', type='int'), Column('name', size=20),
            Index(['name'])
        ],
    ]

    def test_update_sequence(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        for rowid, name in [(1, 'a'), (2, 'b'), (3, 'c')]:
            cursor.execute("INSERT INTO test_update_sequence (id, name)"
                " VALUES (%s, %s)", (rowid, name))
        update_sequence(self.env, db, 'test_update_sequence', 'id')

        cursor.execute("INSERT INTO test_update_sequence (name)"
            " VALUES (%s)", ('d',))

        cursor.execute("SELECT id FROM test_update_sequence WHERE name = %s",
            ('d',))
        row = cursor.fetchone()
        self.assertEqual(row[0], 4)

    def test_drop_index(self):
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        cursor.execute("INSERT INTO test_drop_index (id, name)"
            " VALUES (%s, %s)", (1, 'a'))

        def do_drop():
            drop_index(self.env, db, 'test_drop_index', 'test_drop_index_name_idx')

        # dropping the index should succeed the first time and fail the next
        do_drop()
        self.assertRaises(Exception, do_drop)


class UpgradeScriptsTestCase(BaseUpgradeTestCase):

    schema = [
        # Sytem
        Table('system', key='name')[
            Column('name'), Column('value')
        ],
        # Config
        Table('bitten_config', key='name')[
            Column('name'), Column('path'), Column('label'),
            Column('active', type='int'), Column('description')
        ],
        # Platform
        Table('bitten_platform', key='id')[
            Column('id', auto_increment=True), Column('config'), Column('name')
        ],
        Table('bitten_rule', key=('id', 'propname'))[
            Column('id'), Column('propname'), Column('pattern'),
            Column('orderno', type='int')
        ],
        # Build
        Table('bitten_build', key='id')[
            Column('id', auto_increment=True), Column('config'), Column('rev'),
            Column('rev_time', type='int'), Column('platform', type='int'),
            Column('slave'), Column('started', type='int'),
            Column('stopped', type='int'), Column('status', size=1),
            Index(['config', 'rev', 'slave'])
        ],
        Table('bitten_slave', key=('build', 'propname'))[
            Column('build', type='int'), Column('propname'), Column('propvalue')
        ],
        # Build Step
        Table('bitten_step', key=('build', 'name'))[
            Column('build', type='int'), Column('name'), Column('description'),
            Column('status', size=1), Column('log'),
            Column('started', type='int'), Column('stopped', type='int')
        ],
    ]

    other_tables = [
        'bitten_log',
        'bitten_log_message',
        'bitten_report',
        'bitten_report_item',
        'bitten_error',
        'old_step',
        'old_config_v2',
        'old_log_v5',
        'old_log_v8',
        'old_rule_v9',
        'old_build_v11',
    ]

    basic_data = [
        ['system',
            ('name', 'value'), [
                ('bitten_version', '1'),
            ]
        ],
        ['bitten_config',
            ('name',), [
                ('test_config',),
            ]
        ],
        ['bitten_platform',
            ('config', 'name'), [
                ('test_config', 'test_plat'),
            ]
        ],
        ['bitten_build',
            ('id', 'config', 'rev', 'platform', 'rev_time'), [
                (12, 'test_config', '123', 1, 456),
            ]
        ],
        ['bitten_step',
            ('build', 'name', 'log'), [
                (12, 'step1', None),
                (12, 'step2', "line1\nline2"),
            ]
        ],
    ]

    def _do_upgrade(self):
        """Do an full upgrade."""
        import inspect
        db = self.env.get_db_cnx()

        versions = sorted(upgrades.map.keys())
        for version in versions:
            for function in upgrades.map.get(version):
                self.assertTrue(inspect.getdoc(function))
                function(self.env, db)

        db.commit()

    def _insert_data(self, data):
        """Insert data for upgrading."""
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        for table, cols, vals in data:
            cursor.executemany("INSERT INTO %s (%s) VALUES (%s)"
                % (table, ','.join(cols),
                ','.join(['%s' for c in cols])),
                vals)

        db.commit()

    def _check_basic_upgrade(self):
        """Check the results of an upgrade of basic data."""
        configs = list(model.BuildConfig.select(self.env,
            include_inactive=True))
        platforms = list(model.TargetPlatform.select(self.env))
        builds = list(model.Build.select(self.env))
        steps = list(model.BuildStep.select(self.env))
        logs = list(model.BuildLog.select(self.env))

        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0].name, 'test_config')

        self.assertEqual(len(platforms), 1)
        self.assertEqual(platforms[0].config, 'test_config')
        self.assertEqual(platforms[0].name, 'test_plat')

        self.assertEqual(len(builds), 1)
        self.assertEqual(builds[0].id, 12)
        self.assertEqual(builds[0].config, 'test_config')
        self.assertEqual(builds[0].rev, '123')
        self.assertEqual(builds[0].platform, 1)
        self.assertEqual(builds[0].rev_time, 456)

        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].build, 12)
        self.assertEqual(steps[0].name, 'step1')
        self.assertEqual(steps[1].build, 12)
        self.assertEqual(steps[1].name, 'step2')

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].build, 12)
        self.assertEqual(logs[0].step, 'step2')
        log_file = logs[0].get_log_file(logs[0].filename)
        self.assertEqual(file(log_file, "rU").read(), "line1\nline2\n")

        # check final sequences
        for tbl, col in [
            ('bitten_build', 'id'),
            ('bitten_log', 'id'),
            ('bitten_platform', 'id'),
            ('bitten_report', 'id'),
        ]:
            self._check_sequence(tbl, col)

    def _check_sequence(self, tbl, col):
        scheme = upgrades.parse_scheme(self.env)
        if scheme == "postgres":
            self._check_postgres_sequence(tbl, col)

    def _check_postgres_sequence(self, tbl, col):
        """Check a PostgreSQL sequence for the given table and column."""
        seq = '%s_%s_seq' % (tbl, col)
        cursor = self.env.get_db_cnx().cursor()
        cursor.execute("SELECT MAX(%s) FROM %s" % (col, tbl))
        current_max = cursor.fetchone()[0] or 0 # if currently None
        cursor.execute("SELECT nextval('%s')" % (seq,))
        current_seq = cursor.fetchone()[0] - 1
        self.assertEqual(current_max, current_seq,
            "On %s (col: %s) expected column max (%d) "
            "and sequence value (%d) to match"
            % (tbl, col, current_max, current_seq))

    def test_null_upgrade(self):
        self._do_upgrade()

    def test_basic_upgrade(self):
        self._insert_data(self.basic_data)
        self._do_upgrade()
        self._check_basic_upgrade()

    def test_upgrade_via_buildsetup(self):
        self._insert_data(self.basic_data)
        db = self.env.get_db_cnx()
        build_setup = main.BuildSetup(self.env)
        self.assertTrue(build_setup.environment_needs_upgrade(db))
        build_setup.upgrade_environment(db)
        self._check_basic_upgrade()

        # check bitten table version
        cursor = db.cursor()
        cursor.execute("SELECT value FROM system WHERE name='bitten_version'")
        rows = cursor.fetchall()
        self.assertEqual(rows, [(str(model.schema_version),)])

    def test_fix_log_levels_misnaming(self):
        logfiles = {
            "1.log": "",
            "2.log": "",
            "3.log": "",
            "1.log.level": "info\n",
            "2.log.levels": "info\ninfo\n",
            "3.log.level": "warn\n",
            "3.log.levels": "warn\nwarn\n",
            "4.log.level": "error\n",
        }
        expected_deletions = [
            "4.log.level",
        ]

        os.makedirs(self.logs_dir)
        for filename, data in logfiles.items():
            path = os.path.join(self.logs_dir, filename)
            logfile = open(path, "w")
            logfile.write(data)
            logfile.close()

        logwatch = LogWatcher(logging.INFO)
        self.env.log.setLevel(logging.INFO)
        self.env.log.addHandler(logwatch)

        upgrades.fix_log_levels_misnaming(self.env, None)

        filenames = sorted(os.listdir(self.logs_dir))
        for filename in filenames:
            path = os.path.join(self.logs_dir, filename)
            origfile = filename in logfiles and filename or filename.replace("levels", "level")
            self.assertEqual(logfiles[origfile], open(path).read())
            self.assertTrue(filename not in expected_deletions)

        self.assertEqual(len(filenames), len(logfiles) - len(expected_deletions))

        logs = sorted(logwatch.records, key=lambda rec: rec.getMessage())
        self.assertEqual(len(logs), 5)
        self.assertTrue(logs[0].getMessage().startswith(
            "Deleted 1 stray log level (0 errors)"))
        self.assertTrue(logs[1].getMessage().startswith(
            "Deleted stray log level file 4.log.level"))
        self.assertTrue(logs[2].getMessage().startswith(
            "Error renaming"))
        self.assertTrue(logs[3].getMessage().startswith(
            "Renamed 1 incorrectly named log level files from previous migrate (1 errors)"))
        self.assertTrue(logs[4].getMessage().startswith(
            "Renamed incorrectly named log level file"))

    def test_remove_stray_log_levels_files(self):
        logfiles = {
            "1.log": "",
            "1.log.levels": "info\n",
            "2.log.levels": "info\ninfo\n",
        }
        expected_deletions = [
            "2.log.levels",
        ]

        os.makedirs(self.logs_dir)
        for filename, data in logfiles.items():
            path = os.path.join(self.logs_dir, filename)
            logfile = open(path, "w")
            logfile.write(data)
            logfile.close()

        logwatch = LogWatcher(logging.INFO)
        self.env.log.setLevel(logging.INFO)
        self.env.log.addHandler(logwatch)

        upgrades.remove_stray_log_levels_files(self.env, None)

        filenames = sorted(os.listdir(self.logs_dir))
        for filename in filenames:
            path = os.path.join(self.logs_dir, filename)
            self.assertEqual(logfiles[filename], open(path).read())
            self.assertTrue(filename not in expected_deletions)

        self.assertEqual(len(filenames), len(logfiles) - len(expected_deletions))

        logs = sorted(logwatch.records, key=lambda rec: rec.getMessage())
        self.assertEqual(len(logs), 2)
        self.assertTrue(logs[0].getMessage().startswith(
            "Deleted 1 stray log levels (0 errors)"))
        self.assertTrue(logs[1].getMessage().startswith(
            "Deleted stray log levels file 2.log.levels"))

    def test_migrate_logs_to_files_with_logs_dir(self):
        os.makedirs(self.logs_dir)
        self.assertRaises(TracError, upgrades.migrate_logs_to_files,
            self.env, None)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UpgradeHelperTestCase, 'test'))
    suite.addTest(unittest.makeSuite(UpgradeScriptsTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
