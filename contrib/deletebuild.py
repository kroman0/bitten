# -*- coding: utf-8 -*-
#
# Maintained by Simon Cross <hodegstar+bittencontrib@gmail.com>
#
# Copyright (C) 2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

"""Utility for deleting duplicate builds encounted while upgrading
to schema version 10."""

import os

from trac.env import Environment
from trac.attachment import Attachment
from trac.resource import Resource

__version__ = "1.0a1"

class BuildDeleter(object):
    """Class for deleting a build."""

    def __init__(self, env_path):
        self.env = Environment(env_path)
        self.logs_dir = self.env.config.get('bitten', 'logs_dir', 'log/bitten')

    def _log_files(self, cursor, build):
        """Return a list of log files."""
        cursor.execute("SELECT filename FROM bitten_log WHERE build=%s",
            (build,))
        rows = cursor.fetchall()

        all_files = []
        for row in rows:
            filename = row[0]
            file_prefix = os.path.join(self.logs_dir, filename)
            for suffix in ['', '.level', '.levels']:
                log_file = file_prefix + suffix
                if os.path.isfile(log_file):
                    all_files.append(log_file)

        return all_files

    def discover(self, build):
        """Print a summary of what is linked to the build."""
        print "Items to delete for build %r" % (build,)
        print "-------------------------------"

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        print "Attachments for build resource:"
        cursor.execute("SELECT config FROM bitten_build WHERE id=%s", (build,))
        config = cursor.fetchone()[0]
        print "  %s/%s" % (config, build)

        print "Log files:"
        print " ", "\n  ".join(self._log_files(cursor, build))

        print "Rows from bitten_log with ids:"
        cursor.execute("SELECT id FROM bitten_log WHERE build=%s", (build,))
        print " ", "\n  ".join(str(row[0]) for row in cursor.fetchall())

        print "Rows from bitten_report with ids:"
        cursor.execute("SELECT id FROM bitten_report WHERE build=%s", (build,))
        print " ", "\n  ".join(str(row[0]) for row in cursor.fetchall())
        print "Rows from bitten_report_item with report set to these ids will"
        print "also be deleted."

        print "Rows from bitten_step for this build with names:"
        cursor.execute("SELECT name FROM bitten_step WHERE build=%s", (build,))
        print " ", "\n  ".join(str(row[0]) for row in cursor.fetchall())

        print "Row from bitten_build with id:"
        cursor.execute("SELECT id FROM bitten_build WHERE id=%s", (build,))
        print " ", "\n  ".join(str(row[0]) for row in cursor.fetchall())

    def remove(self, build):
        """Delete what is linked to the build."""
        print "Deleting items for build %r" % (build,)

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        print "Determining associated config."
        cursor.execute("SELECT config FROM bitten_build WHERE id=%s", (build,))
        config = cursor.fetchone()[0]

        print "Collecting log files."
        filenames = self._log_files(cursor, build)

        try:
            print "Deleting bitten_log entries."
            cursor.execute("DELETE FROM bitten_log WHERE build=%s", (build,))

            print "Deleting bitten_report_item_entries."
            cursor.execute("DELETE FROM bitten_report_item WHERE report IN ("
                "SELECT bitten_report.id FROM bitten_report "
                "WHERE bitten_report.build=%s"
                ")", (build,))

            print "Deleting bitten_report entires."
            cursor.execute("DELETE FROM bitten_report WHERE build=%s",
                (build,))

            print "Deleting bitten_step entries."
            cursor.execute("DELETE FROM bitten_step WHERE build=%s", (build,))

            print "Delete bitten_build entry."
            cursor.execute("DELETE FROM bitten_build WHERE id=%s", (build,))
        except:
            db.rollback()
            print "Build deletion failed. Database rolled back."
            raise

        print "Bitten database changes committed."
        db.commit()

        print "Removing log files."
        for filename in filenames:
            os.remove(filename)

        print "Removing attachments."
        resource = Resource('build', '%s/%s' % (config, build))
        Attachment.delete_all(self.env, 'build', resource.id, db)


def main():
    from optparse import OptionParser

    parser = OptionParser(usage='usage: %prog env_path build_id',
                          version='%%prog %s' % __version__)

    options, args = parser.parse_args()

    if len(args) != 2:
        parser.error('incorrect number of arguments')

    env_path, build_id = args

    deleter = BuildDeleter(env_path)
    deleter.discover(build_id)
    proceed = raw_input('Continue [y/n]? ')
    if proceed == 'y':
        deleter.remove(build_id)


if __name__ == "__main__":
    import sys
    sys.exit(main())
