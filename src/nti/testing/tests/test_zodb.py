# -*- coding: utf-8 -*-
"""
Tests for zodb.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import io
import gc
import unittest

import transaction
from transaction.interfaces import NoTransaction
from zope import interface
from nti.testing import zodb

# pylint:disable=protected-access,pointless-string-statement

NativeStringIO = io.BytesIO if str is bytes else io.StringIO

class MockDB(object):

    def __init__(self):
        self.pool = []

    def open(self):
        conn = MockConn()
        self.pool.append(conn)
        return conn


class MockConn(object):
    closed = False
    minimized = False
    def close(self):
        self.closed = True

    def cacheMinimize(self):
        self.minimized = True


class MockDBTrans(zodb.mock_db_trans):

    def __init__(self, db=None):
        if db is None:
            db = MockDB()
        super(MockDBTrans, self).__init__(db)
        self.exc_file = NativeStringIO()

class TestMockDBTrans(unittest.TestCase):

    def setUp(self):
        self._was_explicit = transaction.manager.explicit
        transaction.manager.explicit = False

    def tearDown(self):
        transaction.manager.explicit = self._was_explicit
        transaction.abort()

    def test_begins_ends_transaction(self):
        transaction.manager.explicit = True
        with self.assertRaises(NoTransaction):
            transaction.get()

        with MockDBTrans():
            self.assertIsNotNone(transaction.get())

        transaction.manager.explicit = True
        with self.assertRaises(NoTransaction):
            transaction.get()

    def test_sets_txm_explicit(self):
        with MockDBTrans():
            self.assertTrue(transaction.manager.explicit)
        self.assertFalse(transaction.manager.explicit)

    def test_error_if_mode_changed(self):
        with self.assertRaises(zodb._TransactionManagerModeChanged):
            with MockDBTrans():
                transaction.manager.explicit = False

    def test_error_if_mode_changed_and_error_in_body(self):
        with self.assertRaises(zodb._TransactionManagerModeChanged) as exc:
            with MockDBTrans():
                transaction.manager.explicit = False
                raise Exception("BodyError")
        # The backing exception is included
        self.assertIn('BodyError', str(exc.exception))

    def test_error_if_tx_ended(self):
        with self.assertRaises(zodb._TransactionChanged):
            with MockDBTrans():
                transaction.commit()

    def test_error_if_tx_changed(self):
        with self.assertRaises(zodb._TransactionChanged):
            with MockDBTrans():
                transaction.commit()
                transaction.begin()

    def test_error_if_tx_changed_aborts_new(self):
        transaction.manager.explicit = True
        with self.assertRaises(zodb._TransactionChanged):
            with MockDBTrans():
                transaction.commit()
                transaction.begin()
        with self.assertRaises(NoTransaction):
            transaction.get()

    def test_returns_connection_it_closes(self):
        with MockDBTrans() as conn:
            self.assertIsInstance(conn, MockConn)

        self.assertTrue(conn.closed)
        self.assertTrue(conn.minimized)

    def test_aborts_doomed_tx(self):
        aborted = []
        with MockDBTrans():
            transaction.doom()
            tx = transaction.get()
            abort = tx.abort

            def _abort():
                abort()
                aborted.append(1)
            tx.abort = _abort

        self.assertEqual(aborted, [1])

    def test_closing_conn_error_not_shadow_body_error(self):
        class ConnEx(Exception):
            pass

        class BodyEx(Exception):
            pass

        def e():
            raise ConnEx

        mock_db_trans = MockDBTrans()
        with self.assertRaises(BodyEx):
            with mock_db_trans as conn:
                conn.close = e
                raise BodyEx

        msg = mock_db_trans.exc_file.getvalue()
        self.assertIn('Unexpected error closing connection', msg)
        self.assertIn('Module nti.testing.zodb', msg)


    def test_aborts_on_abort_error(self):
        aborted = []
        class AbortEx(Exception):
            pass
        with self.assertRaises(AbortEx):
            with MockDBTrans():
                transaction.doom()
                tx = transaction.get()
                abort = tx.abort

                def _abort():
                    abort()
                    aborted.append(1)
                    del tx.abort
                    raise AbortEx
                tx.abort = _abort

        self.assertEqual(aborted, [1])

    def test_aborts_on_commit_error(self):
        committed = []
        class CommitEx(Exception):
            pass
        with self.assertRaises(CommitEx):
            with MockDBTrans():
                tx = transaction.get()
                commit = tx.commit

                def _commit():
                    commit()
                    committed.append(1)
                    del tx.commit
                    raise CommitEx
                tx.commit = _commit

        self.assertEqual(committed, [1])

    def test_abort_error_does_not_shadow_body_error(self):
        aborted = []
        class AbortEx(Exception):
            pass
        class BodyEx(Exception):
            pass
        mock_db_trans = MockDBTrans()
        with self.assertRaises(BodyEx):
            with mock_db_trans:
                transaction.doom()
                tx = transaction.get()
                abort = tx.abort

                def _abort():
                    abort()
                    aborted.append(1)
                    del tx.abort
                    raise AbortEx
                tx.abort = _abort
                raise BodyEx

        self.assertEqual(aborted, [1])
        msg = mock_db_trans.exc_file.getvalue()
        self.assertIn('Failed to cleanup trans', msg)
        self.assertIn('Module nti.testing.zodb', msg)

    def test_error_in_on_opened(self):
        class OpenEx(Exception):
            pass

        class MyFalse(object):
            __nonzero__ = __bool__ = lambda _self: False

        transaction.manager.explicit = MyFalse()
        class MyMock(MockDBTrans):
            seen_tx = None
            aborted = False
            def on_connection_opened(self, conn):
                # pylint:disable=no-member
                self.seen_tx = self._mock_db_trans__current_transaction
                abort = self.seen_tx.abort
                def _abort():
                    abort()
                    self.aborted = True
                    del self.seen_tx.abort
                self.seen_tx.abort = _abort
                raise OpenEx

        db = MockDB()
        my_mock = MyMock(db)
        with self.assertRaises(OpenEx):
            with my_mock:
                "We never get here"

        # The txm mode was restored
        self.assertFalse(transaction.manager.explicit)
        self.assertIsInstance(transaction.manager.explicit, MyFalse)
        # the conn was opened, and then closed
        self.assertTrue(db.pool[0].closed)
        self.assertIsNone(my_mock.conn)
        # The transaction that was opened is cleaned up
        self.assertTrue(my_mock.aborted)


class TestZODBLayer(unittest.TestCase):

    layer = zodb.ZODBLayer

    def test_registration(self):
        from ZODB.interfaces import IDatabase
        from zope import component
        gsm = component.getGlobalSiteManager()
        reg_db = gsm.getUtility(IDatabase)
        self.assertIsNotNone(reg_db)
        self.assertIs(reg_db, self.layer.db)

    def test_premature_teardown(self):
        self.layer.tearDown()
        from ZODB.interfaces import IDatabase
        from zope import component
        gsm = component.getGlobalSiteManager()
        reg_db = gsm.queryUtility(IDatabase)
        self.assertIsNone(reg_db)

        self.layer.setUp()


class IExtra(interface.Interface): # pylint:disable=inherit-non-class
    "An extra interface"

class IExtra2(interface.Interface): # pylint:disable=inherit-non-class
    "Another extra interface"

class Object(object):

    def __init__(self, *args):
        pass

class TestResetDbCaches(unittest.TestCase):
    layer = zodb.ZODBLayer

    def setUp(self):
        super(TestResetDbCaches, self).setUp()
        gc.disable()

    def tearDown(self):
        gc.enable()
        super(TestResetDbCaches, self).tearDown()

    def test_persistent_site_closed(self):
        from zope.site.site import LocalSiteManager
        from ZODB import DB
        from ZODB.DemoStorage import DemoStorage

        interface.classImplements(LocalSiteManager, IExtra)

        db = DB(DemoStorage())
        transaction.begin()
        conn = db.open()
        site_man = LocalSiteManager(None)
        conn.root()[0] = site_man
        site_man.registerAdapter(Object, [IExtra], IExtra2)
        site_man.getAdapter(LocalSiteManager(None), IExtra2)
        transaction.commit()
        conn.close()

        zodb.reset_db_caches(db)
        IExtra.changed(None) # pylint:disable=no-value-for-parameter

    def test_arguments(self):
        # Don't pass the DB, let it get the one from the layer.
        # But do ask for collect, so we get something non-negative on
        # all platforms.
        collected = zodb.reset_db_caches(collect=True)
        self.assertNotEqual(collected, -1)
