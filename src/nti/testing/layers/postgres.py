# -*- coding: utf-8 -*-
"""
Support for using :mod:`testgres` to create and use a Postgres
instance as a layer.

There is also support for benchmarking and saving databeses for
later examination.

.. versionadded:: 4.0.0

The APIs are preliminary and may change.

This is only supported on platforms that can install ``psycopg2``.

"""
from contextlib import contextmanager
import functools
import os
import sys
import unittest
from unittest.mock import patch

#import psycopg2
#import psycopg2.extras
#import psycopg2.pool

try:
    from psycopg2 import ProgrammingError
except ImportError:
    ThreadedConnectionPool = None
    DictCursor = None
    class IntegrityError(Exception):
        """Never thrown"""
    ProgrammingError = InternalError = IntegrityError
else:
    from psycopg2.pool import ThreadedConnectionPool
    from psycopg2.extras import DictCursor
    from psycopg2 import IntegrityError
    from psycopg2 import InternalError

import testgres


if 'PG_CONFIG' not in os.environ:
    # Set up for macports and fedora, using files that exist.
    # Otherwise, don't set it, assume things are on the path.
    for option in (
        '/opt/local/lib/postgresql11/bin/pg_config',
        '/usr/pgsql-11/bin/pg_config',
    ):
        if os.path.isfile(option):
            # TODO: Check exec bit
            os.environ['PG_CONFIG'] = option
            break

# If True, save the database to a pg_dump
# file on teardown. The file name will be printed.''
SAVE_DATABASE_ON_TEARDOWN = False
SAVE_DATABASE_FILENAME = None

# If the path to a database dump file that exists, the database
# will be restored from this file on setUp.
LOAD_DATABASE_ON_SETUP = None

if 'NTI_SAVE_DB' in os.environ:
    # NTI_SAVE_DB is either 1/on/true (case-insensitive)
    # or a file name.
    val = os.environ['NTI_SAVE_DB']
    if val.lower() in {'0', 'off', 'false', 'no'}:
        SAVE_DATABASE_ON_TEARDOWN = False
    else:
        SAVE_DATABASE_ON_TEARDOWN = True
        if val.lower() not in {'1', 'on', 'true', 'yes'}:
            SAVE_DATABASE_FILENAME = val


if 'NTI_LOAD_DB_FILE' in os.environ:
    LOAD_DATABASE_ON_SETUP = os.environ['NTI_LOAD_DB_FILE']


def patched_get_pg_version(*args, **kwargs):
    # We patch  this in testgres.node, so its ok to import
    # the original. In version 1.10, they changed the signature
    # of this function, so be sure to accept whatever it does and
    # pass it on. In version 1.11, this was replaced with
    # get_pg_version2, which does the same thing just takes
    # more arguments.
    from testgres.utils import get_pg_version2
    from testgres.node import PgVer
    from packaging.version import InvalidVersion

    # Some installs of postgres return
    # strings that the version parser doesn't like;
    # notably the Python images get a debian build that says
    # "15.3-0+deb12u1" which get_pg_version() chops down to
    # "15.3-0+". If it can't be parsed, then return a fake.

    try:
        version = get_pg_version2(*args, **kwargs)
        PgVer(version)
    except InvalidVersion:
        print('testgres: Got invalid postgres version', version)
        # The actual version string looks like "postgres (PostgreSQL) 15.4",
        # and get_pg_version() processes that down to this
        version = "15.4"
        print('testgres: Substituting version', version)

    return version

class DatabaseLayer(object):
    """
    A test layer that creates the database, and sets each
    test up in its own connection, aborting the transaction when
    done.
    """

    #: The name of the database within the node. We only create
    #: the default databases, so this should be 'postgres'
    DATABASE_NAME = 'postgres'

    #: A `testgres.node.PostgresNode`, created for the layer.
    #: A psycopg2 connection to it is located in the :attr:`connection`
    #: attribute (similarly for :attr:`connection_pool`), while
    #: a DSN connection string is in :attr:`postgres_dsn`
    postgres_node = None

    #: A string you can use to connect to Postgres.
    postgres_dsn = None

    #: A string you can pass to SQLAlchemy
    postgres_uri = None

    #: Set for each test.
    connection = None

    #: Set for each test.
    cursor = None

    connection_pool = None


    connection_pool_klass = ThreadedConnectionPool
    connection_pool_minconn = 1
    connection_pool_maxconn = 51

    @classmethod
    def setUp(cls):
        testgres.configure_testgres()

        with patch('testgres.node.get_pg_version2', new=patched_get_pg_version):
            node = cls.postgres_node = testgres.get_new_node()

        # init takes about about 2 -- 3 seconds
        node.init(
            # Use the encoding as UTF-8. Set the locale as POSIX
            # instead of inheriting it (in JAM's environment, the locale
            # and thus collation and ctype is en_US.UTF8; this turns out to be
            # up to 40% slower than POSIX).
            # We could explicitly specify 'en-x-icu' on each column, if we required
            # ICU support, but it cannot be used as a default collation.
            initdb_params=[
                "-E", "UTF8",
                '--locale', 'POSIX',
                # Don't force to disk; this may save some minor init time.
                '--no-sync',
            ],
            log_statement='none',
            # Disable unix sockets. Some platforms might try to put this
            # in a directory we can't write to
            unix_sockets=False
        )
        # Speed up bulk inserts
        # These settings appeared to make no difference for the
        # 2 million security insert or the 500K security mapping insert;
        # likely because the final table sizes are < 300MB, so the default max size of
        # 1GB is more than enough.
        node.append_conf('fsync = off')
        node.append_conf('full_page_writes = off')
        node.append_conf('min_wal_size = 500MB')
        node.append_conf('max_wal_size = 2GB')
        # 'replica' is the default. If we use 'minimal' we could be
        # a bit faster, but that's not exactly realistic. Plus,
        # using 'minimal' disables the WAL backup functionality.
        # If we set to 'minimal', we must also set 'max_wal_senders' to 0.
        node.append_conf('wal_level = replica')
        node.append_conf('wal_compression = on')
        node.append_conf('wal_writer_delay = 10000ms')
        node.append_conf('wal_writer_flush_after = 10MB')

        node.append_conf('temp_buffers = 500MB')
        node.append_conf('work_mem = 500MB')
        node.append_conf('maintenance_work_mem = 500MB')
        node.append_conf('shared_buffers = 500MB')

        node.append_conf('max_connections = 100')

        # auto-explain for slow queries
        if 'benchmark' in ' '.join(sys.argv):
            print("Enabling BENCHMARK SETTINGS")
            node.append_conf('shared_preload_libraries = auto_explain')
            node.append_conf('auto_explain.log_min_duration = 40ms')
            node.append_conf('auto_explain.log_nested_statements = on')
            node.append_conf('auto_explain.log_analyze = on')
            node.append_conf('auto_explain.log_timing = on')
            node.append_conf('auto_explain.log_triggers = on')

        # PG 11 only, when --with-llvm was used to compile.
        # It seems if it can't be used, it's ignored? It errors on 10 though,
        # but we only support 11
        node.append_conf('jit = on')


        node.start()
        cls.connection_pool = cls.connection_pool_klass(
            cls.connection_pool_minconn,
            cls.connection_pool_maxconn,
            dbname=cls.DATABASE_NAME,
            host='localhost',
            port=cls.postgres_node.port,
            cursor_factory=DictCursor,
        )

        cls.postgres_dsn = "host=%s dbname=%s port=%s" %  (
            node.host, cls.DATABASE_NAME, node.port
        )
        cls.postgres_uri = "postgresql://%s:%s/%s" % (
            cls.postgres_node.host,
            cls.postgres_node.port,
            cls.DATABASE_NAME
        )

        with cls.borrowed_connection() as conn:
            with conn.cursor() as cur:
                i = cls.__get_db_info(cur)
                print(f"({i['version']} {i['current_database']}/{i['current_schema']} "
                      f"{i['Encoding']}-{i['Collate']}) ", end="")

    @classmethod
    def tearDown(cls):
        cls.connection_pool.closeall()
        cls.connection_pool = None

        cls.postgres_node.__exit__(None, None, None)
        cls.postgres_node = None

    @classmethod
    def testSetUp(cls):
        # XXX: Errors here cause the tearDown method to not get called.
        cls.connection = cls.connection_pool.getconn()
        cls.cursor = cls.connection.cursor()

    @classmethod
    def testTearDown(cls):
        cls.connection.rollback() # Make sure we're able to execute
        cls.cursor.execute('UNLISTEN *')
        cls.cursor.close()
        cls.cursor = None
        cls.connection_pool.putconn(cls.connection)
        cls.connection = None

    @classmethod
    def __get_db_info(cls, cur):
        query = """
        SELECT version() as version,
               d.datname as "Name",
               pg_catalog.pg_get_userbyid(d.datdba) as "Owner",
               pg_catalog.pg_encoding_to_char(d.encoding) as "Encoding",
               d.datcollate as "Collate",
               d.datctype as "Ctype",
               pg_catalog.array_to_string(d.datacl, E'\n') AS "Access privileges",
               current_database() as "current_database",
               current_schema() as "current_schema"
        FROM pg_catalog.pg_database d
        WHERE d.datname = %s
        """
        cur.execute(query, (cls.DATABASE_NAME,))
        row = cur.fetchone()
        return dict(row)

    @classmethod
    @contextmanager
    def borrowed_connection(cls):
        """
        Context manager that returns a connection from the connection
        pool.
        """
        conn = cls.connection_pool.getconn()
        try:
            yield conn
        finally:
            cls.connection_pool.putconn(conn)


    @classmethod
    def truncate_table(cls, conn, table_name):
        """Transactionally truncate the given *table_name* using *conn*"""
        try:

            with conn.cursor() as cur:
                cur.execute(
                    'TRUNCATE TABLE ' + table_name + ' CASCADE'
                )
        except (ProgrammingError, InternalError):
            # Table doesn't exist, not a full schema,
            # ignore.
            # OR:
            # Already aborted
            import traceback
            traceback.print_exc()
            conn.rollback()
        else:
            # Is PostgreSQL, TRUNCATE is transactional!
            # Awesome!
            conn.commit()

    @classmethod
    def drop_relation(cls, relation, kind='TABLE', idempotent=False):
        """Drops the *relation* of type *kind* (default table), in new transaction."""
        with cls.borrowed_connection() as conn:
            with conn.cursor() as cur:
                if idempotent:
                    cur.execute(f"DROP {kind} IF EXISTS {relation}")
                else:
                    cur.execute(f"DROP {kind} {relation}")
            conn.commit()

    @classmethod
    def vacuum(cls, *tables, **kwargs):
        verbose = ''
        if kwargs.pop('verbose', False):
            verbose = ', VERBOSE'

        with cls.borrowed_connection() as conn:
            conn.autocommit = True
            # FULL rewrites all tables and takes forever.
            # FREEZE is simpler and compacts tables
            stmt = f'VACUUM (FREEZE, ANALYZE {verbose}) '
            tables = tables or ('',)
            with conn.cursor() as cur:
                # VACUUM cannot run inside a transaction block...
                for t in tables:
                    cur.execute(stmt + t)
            conn.autocommit = False
            if verbose:
                for n in conn.notices:
                    print(n)
                del conn.notices[:]
        if kwargs.pop('size_report', True):
            cls.print_size_report()

    ONLY_PRINT_SIZE_OF_TABLES = None

    @classmethod
    def print_size_report(cls):
        extra_query = ''
        if cls.ONLY_PRINT_SIZE_OF_TABLES:
            t = cls.ONLY_PRINT_SIZE_OF_TABLES
            extra_query = f"AND table_name = '{t}'"
        query = f"""
        SELECT table_name,
            pg_size_pretty(total_bytes) AS total,
            pg_size_pretty(index_bytes) AS INDEX,
            pg_size_pretty(toast_bytes) AS toast,
            pg_size_pretty(table_bytes) AS TABLE
        FROM (
        SELECT *, total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes FROM (
        SELECT c.oid,nspname AS table_schema, relname AS TABLE_NAME
              , c.reltuples AS row_estimate
              , pg_total_relation_size(c.oid) AS total_bytes
              , pg_indexes_size(c.oid) AS index_bytes
              , pg_total_relation_size(reltoastrelid) AS toast_bytes
          FROM pg_class c
          LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE relkind = 'r'
            ) a
        ) a
        WHERE (table_name NOT LIKE 'pg_%' and table_name not like 'abstract_%'
          {extra_query}
        )
        AND table_schema <> 'pg_catalog' and table_schema <> 'information_schema'
        ORDER BY total_bytes DESC
        """

        with cls.borrowed_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)

                rows = [dict(row) for row in cur]

        keys = ['table_name', 'total', 'index', 'toast', 'table']

        rows.insert(0, {k: k for k in keys})
        print()
        fmt = "| {table_name:35s} | {total:10s} | {index:10s} | {toast:10s} | {table:10s}"
        for row in rows:
            if not extra_query and row['total'] in {
                '72 kB', '32 kB', '24 kB', '16 kB', '8192 bytes'
            }:
                continue
            print(fmt.format(
                **{k: v if v else '<null>' for k, v in row.items()}
            ))


class SchemaDatabaseLayer(DatabaseLayer):
    """
    A test layer that adds our schema.
    """

    SCHEMA_FILE = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', '..', '..', '..', '..',
        'full_schema.sql'
    ))

    @classmethod
    def run_files(cls, *files):
        for fname in files:
            code, stdout, stderr = cls.postgres_node.psql(
                filename=fname,
                ON_ERROR_STOP=1
            )
            if code:
                break

        if code:
            import subprocess
            stdout = stdout.decode("utf-8")
            stderr = stderr.decode('utf-8')
            print(stdout)
            print(stderr)
            raise subprocess.CalledProcessError(
                code,
                'psql',
                stdout,
                stderr
            )

    @classmethod
    def _tangle_schema_if_needed(cls):
        # If the schema files do not exist, or db.org is newer
        # than they are, run emacs to weave the files together.
        # This requires a working emacs with org-mode available.
        from pathlib import Path
        import subprocess

        cwd = Path(".")
        # Each org file tangles to at least one sql file.
        org_to_sql = {
            org: org.with_suffix('.sql')
            for org in cwd.glob("*.org")
        }
        org_to_sql[Path("db.org")] = Path("full_schema.sql")

        for org, sql in org_to_sql.items():
            if not org.exists():
                continue
            if sql.exists() and sql.stat().st_mtime >= org.stat().st_mtime:
                continue
            print(f"\nDatabase schema files outdated; tangling {org}")
            ex = None
            try:
                output = subprocess.check_output([
                    "emacs",
                    "--batch",
                    "--eval",
                    f'''(progn
                    (package-initialize)
                    (require 'org)
                    (org-babel-tangle-file "{org}")
                    )'''
                ], stderr=subprocess.STDOUT)
            except FileNotFoundError as e:
                output = str(e).encode('utf-8')
                ex = e
            except subprocess.CalledProcessError as e:
                output = ex.output
                ex = e # pylint:disable=redefined-variable-type

            output = output.decode('utf-8')

            if ex is not None or 'Tangled 0' in output:
                print("Failed to tangle database schema; "
                      "(check file paths):\n",
                      output,
                      file=sys.stderr)
                sys.exit(1)

    @classmethod
    def setUp(cls):
        cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(cls.SCHEMA_FILE))
            # XXX: Do exceptions here prevent the super tearDown()
            # from being called?
            cls._tangle_schema_if_needed()

            to_run = [cls.SCHEMA_FILE]
            if os.path.exists("prereq.sql"):
                to_run.insert(0, "prereq.sql")
            cls.run_files(*to_run)
        finally:
            os.chdir(cwd)

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass

class DatabaseBackupLayerHelper:
    """
    A layer helper that works with another layer to

    * create a backup of the current database on `push`;
    * make that backup active;
    * switch the connection pool to that backup
    * reverse all of that on layer `pop`

    Note that this consists of modifying values in the `DatabaseLayer`,
    so the *layer* parameter must extend that.
    """

    _nodes = []
    _pools = []

    @classmethod
    def push(cls, layer):
        current_node = DatabaseLayer.postgres_node
        cls._nodes.append(current_node)
        cls._pools.append(DatabaseLayer.connection_pool)

        with layer.borrowed_connection() as conn:
            with conn.cursor() as cur:
                # If we don't checkpoint here, then the backup waits
                # for the next WAL checkpoint to happen. We may not have
                # written much to the WAL, so we could wait until a time limit
                # expires, which is ofter 30+ seconds. We don't want to wait.
                cur.execute('CHECKPOINT')

        # A streaming backup uses a replication slot, but it
        # does the copy in parallel.
        backup = current_node.backup(xlog_method='stream')
        DatabaseLayer.postgres_node = new_node = backup.spawn_primary()
        new_node.start()
        DatabaseLayer.connection_pool = layer.connection_pool_klass(
            layer.connection_pool_minconn,
            layer.connection_pool_maxconn,
            dbname=layer.DATABASE_NAME,
            host='localhost',
            port=new_node.port,
            cursor_factory=DictCursor
        )

    @classmethod
    def pop(cls, layer): # pylint:disable=unused-argument
        DatabaseLayer.tearDown() # Closes the current node, and the connection pool
        DatabaseLayer.postgres_node = cls._nodes.pop()
        DatabaseLayer.connection_pool = cls._pools.pop()


_persistent_base = (
    # If we're loading a file, it has the schema
    # info.

    SchemaDatabaseLayer
    if not LOAD_DATABASE_ON_SETUP
    else DatabaseLayer
)

class PersistentDatabaseLayer(_persistent_base):
    """
    A layer that establishes persistent data visible to
    all of its tests (and all of its sub-layers).

    Sub-layers need to check whether they should
    clean up or not, because we may be saving the database file.

    It's important to have a fairly linear layer
    setup, or layers that don't interfere with each other.
    """

    @classmethod
    def setUp(cls):
        if LOAD_DATABASE_ON_SETUP:
            print(f" (Loading database from {LOAD_DATABASE_ON_SETUP}) ",
                  end='',
                  flush=True)
            cls.postgres_node.restore(LOAD_DATABASE_ON_SETUP)
            cls.vacuum()

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass

    @classmethod
    def persistent_layer_skip_teardown(cls):
        """
        Should persistent layers, that write data intended to be
        visible between tests (and in sub-layers) tear down that data
        when the layer is torn down? If we're saving the database, we
        don't want to do that.

        Raising NotImplementedError causes the testrunner to assume
        it's python resources that are the problem and continue in a new
        subprocess, which doesn't help (and may hurt?). So you must check this as a
        boolean.
        """
        return SAVE_DATABASE_ON_TEARDOWN

    @classmethod
    def persistent_layer_skip_setup(cls):
        """
        Should persistent layers skip their setup because
        we loaded a save file?
        """
        return LOAD_DATABASE_ON_SETUP

    @classmethod
    def tearDown(cls):
        if SAVE_DATABASE_ON_TEARDOWN:
            tmp_fname = cls.postgres_node.dump(format='custom')
            result_fname = tmp_fname
            if SAVE_DATABASE_FILENAME:
                import shutil
                result_fname = SAVE_DATABASE_FILENAME
                while os.path.exists(result_fname):
                    result_fname += '.1'
                shutil.move(tmp_fname, result_fname)
            print(f" (Database dumped to {result_fname}) ", end='')

def persistent_skip_setup(func):

    @functools.wraps(func)
    def maybe_skip_setup(cls):
        if cls.persistent_layer_skip_setup():
            return
        func(cls)
    return maybe_skip_setup

def persistent_skip_teardown(func):
    @functools.wraps(func)
    def f(cls):
        if cls.persistent_layer_skip_teardown():
            return
        func(cls)
    return f

class DatabaseTestCase(unittest.TestCase):
    """
    A helper test base containing some functions useful for both
    benchmarking and unit testing.
    """
    # pylint:disable=no-member

    @contextmanager
    def assertRaisesIntegrityError(self, match=None):
        if match:
            with self.assertRaisesRegex(IntegrityError, match) as exc:
                yield exc
        else:
            with self.assertRaises(IntegrityError) as exc:
                yield exc

        # We can't do any queries after an error is raised
        # until we rollback.
        self.layer.connection.rollback()
        return exc

    def assert_row_count_in_query(self, expected_count, query):
        cur = self.layer.cursor

        cur.execute('SELECT COUNT(*) FROM ' + query)
        row = cur.fetchone()
        count = row[0]

        self.assertEqual(expected_count, count, query)

    def assert_row_count_in_table(self, expected_count, table_name):
        __traceback_info__ = table_name
        self.assert_row_count_in_query(expected_count, table_name)

    def assert_row_count_in_cursor(self, rowcount, cursor=None):
        cur = cursor if cursor is not None else self.layer.cursor
        self.assertEqual(cur.rowcount, rowcount)
