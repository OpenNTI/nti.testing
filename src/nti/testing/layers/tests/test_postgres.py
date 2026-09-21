# -*- coding: utf-8 -*-
"""
Tests for postgres.py

"""

# stdlib imports
import unittest
from unittest.mock import patch as Patch


class TestBasic(unittest.TestCase):

    def test_imports(self):
        from .. import postgres
        self.assertIsNotNone(postgres)

    def test_patched_get_pg_version(self):
        from packaging.version import InvalidVersion

        from .. import postgres

        # Some of the invalid inputs that used to cause this seem
        # to no longer do that, possibly we could remove this patch
        with Patch.object(postgres, '_orig_get_pg_version2',
                          return_value='15.3-0+deb12u1'):
            ver = postgres.patched_get_pg_version()
            self.assertEqual(ver, '15.3-0+deb12u1' )

            with Patch('testgres.utils.PgVer', autospec=True, side_effect=InvalidVersion):
                ver = postgres.patched_get_pg_version()
                self.assertEqual(ver, postgres.REPLACEMENT_PG_VERSION_FOR_ERROR)


class TestLayer(unittest.TestCase):

    def test_cover(self):
        # stdlib imports
        import contextlib
        import io
        import os
        from subprocess import CalledProcessError

        from psycopg2.errors import UndefinedTable

        from ..postgres import DatabaseBackupLayerHelper as Backup
        from ..postgres import DatabaseLayer
        from ..postgres import DatabaseTestCase
        from ..postgres import SchemaDatabaseLayer

        test = DatabaseTestCase()
        test.layer = DatabaseLayer

        class Schema(SchemaDatabaseLayer):
            SCHEMA_FILE = os.path.abspath(
                os.path.join(os.path.dirname(__file__),
                             'full_schema.sql')
            )

        try:
            DatabaseLayer.setUp()
            try:
                DatabaseLayer.testSetUp()
                with contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    with DatabaseLayer.borrowed_connection() as conn:
                        cur = conn.cursor()
                        cur.execute('CREATE TABLE foo(id serial)')
                        conn.commit()
                        DatabaseLayer.truncate_table(conn, 'foo')
                        DatabaseLayer.truncate_table(conn, 'dne')
                    DatabaseLayer.connection.rollback()
                    test.assert_row_count_in_table(0, 'foo')
                    DatabaseLayer.vacuum('foo', verbose=True, size_report=True)
                    DatabaseLayer.print_size_report()
                    DatabaseLayer.connection.rollback()
                    DatabaseLayer.drop_relation('foo')
                    DatabaseLayer.drop_relation('foo', idempotent=True)
                    with self.assertRaises(UndefinedTable):
                        DatabaseLayer.drop_relation('foo')

                    Schema.setUp()
                    Schema.testSetUp()
                    Schema.testTearDown()
                    test.assert_row_count_in_table(0, 'baz')

                    with self.assertRaises(CalledProcessError):
                        Schema.SCHEMA_FILE = '/tmp/dne'
                        Schema.setUp()

                    Schema.tearDown()

                    Backup.push(DatabaseLayer)
                    Backup.pop(DatabaseLayer)
            finally:
                DatabaseLayer.testTearDown()
        finally:
            DatabaseLayer.tearDown()

if __name__ == '__main__':
    unittest.main()
