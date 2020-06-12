# -*- coding: utf-8 -*-
"""
Tests for zodb.py

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest

import transaction
from transaction.interfaces import NoTransaction
from nti.testing import zodb

# pylint:disable=protected-access,pointless-string-statement

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

        with zodb.mock_db_trans(MockDB()):
            self.assertIsNotNone(transaction.get())

        transaction.manager.explicit = True
        with self.assertRaises(NoTransaction):
            transaction.get()

    def test_sets_txm_explicit(self):
        with zodb.mock_db_trans(MockDB()):
            self.assertTrue(transaction.manager.explicit)
        self.assertFalse(transaction.manager.explicit)

    def test_error_if_mode_changed(self):
        with self.assertRaises(zodb._TransactionManagerModeChanged):
            with zodb.mock_db_trans(MockDB()):
                transaction.manager.explicit = False

    def test_error_if_mode_changed_and_error_in_body(self):
        with self.assertRaises(zodb._TransactionManagerModeChanged) as exc:
            with zodb.mock_db_trans(MockDB()):
                transaction.manager.explicit = False
                raise Exception("BodyError")
        # The backing exception is included
        self.assertIn('BodyError', str(exc.exception))

    def test_error_if_tx_ended(self):
        with self.assertRaises(zodb._TransactionChanged):
            with zodb.mock_db_trans(MockDB()):
                transaction.commit()

    def test_error_if_tx_changed(self):
        with self.assertRaises(zodb._TransactionChanged):
            with zodb.mock_db_trans(MockDB()):
                transaction.commit()
                transaction.begin()

    def test_error_if_tx_changed_aborts_new(self):
        transaction.manager.explicit = True
        with self.assertRaises(zodb._TransactionChanged):
            with zodb.mock_db_trans(MockDB()):
                transaction.commit()
                transaction.begin()
        with self.assertRaises(NoTransaction):
            transaction.get()

    def test_returns_connection_it_closes(self):
        with zodb.mock_db_trans(MockDB()) as conn:
            self.assertIsInstance(conn, MockConn)

        self.assertTrue(conn.closed)
        self.assertTrue(conn.minimized)

    def test_aborts_doomed_tx(self):
        aborted = []
        with zodb.mock_db_trans(MockDB()):
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

        with self.assertRaises(BodyEx): # TODO: Stub out traceback.print_exc
            with zodb.mock_db_trans(MockDB()) as conn:
                conn.close = e
                raise BodyEx

    def test_aborts_on_abort_error(self):
        aborted = []
        class AbortEx(Exception):
            pass
        with self.assertRaises(AbortEx):
            with zodb.mock_db_trans(MockDB()):
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
            with zodb.mock_db_trans(MockDB()):
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
        with self.assertRaises(BodyEx):
            with zodb.mock_db_trans(MockDB()):
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

    def test_error_in_on_opened(self):
        class OpenEx(Exception):
            pass

        class MyFalse(object):
            __nonzero__ = __bool__ = lambda _self: False

        transaction.manager.explicit = MyFalse()
        class MyMock(zodb.mock_db_trans):
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
