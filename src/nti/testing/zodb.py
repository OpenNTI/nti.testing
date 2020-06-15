# -*- coding: utf-8 -*-
"""
Support for testing of ZODB applications.

.. versionadded:: 3.0.0

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gc
import sys


import transaction
from transaction.interfaces import NoTransaction

import ZODB
from ZODB.interfaces import IDatabase
from ZODB.DemoStorage import DemoStorage
from zope import component
from zope.exceptions import print_exception
from zope.exceptions import format_exception

from .layers import ZopeComponentLayer

PYPY = hasattr(sys, 'pypy_version_info')

__all__ = [
    'mock_db_trans',
    'ZODBLayer',
    'reset_db_caches',
]

# The exceptions are not expected to be caught. They indicate errors
# to fix.
class _BaseException(Exception):
    default_message = 'Unknown'
    def __init__(self, t, v, tb):
        msg = self.default_message
        if t:
            msg = ''.join(format_exception(t, v, tb))
        Exception.__init__(self, msg)

class _TransactionManagerModeChanged(_BaseException):
    default_message = 'The transaction manager explicit mode changed'

class _TransactionChanged(_BaseException):
    default_message = 'The body changed the active transaction'

class mock_db_trans(object):
    """
    A context manager that begins and commits a database transaction.

    This class may be subclassed; there are some extension points
    to allow customization.

    This class is not designed for concurrency.

    Entering this context manager begins a transaction using the
    thread-local global transaction manager and returns a connection
    open to the database given in the *db* parameter. Exiting this
    context manager commits the transaction (or aborts it if it is
    doomed).

    It is an error to enter this context manager with a transaction
    already in progress. The global transaction may be committed or aborted
    before exiting this transaction, but no new transaction may be opened. During
    execution of the body, the transaction manager is in explicit mode;
    it is an error if this is changed during the body.
    """

    #: The connection that was opened. Valid after entering and before exiting.
    conn = None

    #: The file to which unexpected exceptions that cannot be raised are printed.
    #: If `None`, exceptions will be written to `sys.stderr`
    exc_file = None

    def __init__(self, db=None):
        """
        :param db: The :class:`ZODB.DB` to open. If none is given,
            then the :attr:`ZODBLayer.db` will be used.
        """
        self.db = db if db is not None else ZODBLayer.db
        self.__txm_was_explicit = None
        self.__current_transaction = None

    def on_connection_opened(self, conn):
        """
        Called when the connection to the DB has been opened.

        Subclasses may override to perform initialization.
        The DB may have been used before, so check its state and don't assume
        a complete initialization must happen.
        """

    def __enter__(self):
        txm = transaction.manager
        self.__txm_was_explicit = txm.explicit
        txm.explicit = True
        try:
            self.__current_transaction = txm.begin()
            self.conn = conn = self.db.open()
            self.on_connection_opened(conn)
        except:
            # Could be several things:
            # Already in a transaction is definitely a user error.
            # Failure to open the DB: Probably also a user error.
            # Failure to setup the DB: Possibly a user error, or error in a
            # subclass.
            txm.explicit = self.__txm_was_explicit
            if self.__current_transaction:
                self._clean_up_one_transaction(self.__current_transaction, True)

            if self.conn is not None:
                self.conn.close()
            self.conn = None
            self.__current_transaction = None
            raise
        return self.conn

    def _clean_up_one_transaction(self, tx, abort_only):
        try:
            if abort_only or tx.isDoomed():
                tx.abort()
            else:
                tx.commit()
        except:
            tx.abort() # idempotent with transaction 3
            raise

    def _report_exception(self, msg, t, v, tb):
        f = self.exc_file or sys.stderr
        print(msg, file=f)
        print_exception(t, v, tb, file=f, with_filenames=False)

    def _close_connection(self, conn, ignore_errors):
        catch = Exception if ignore_errors else ()
        try:
            conn.close()
        except catch:
            self._report_exception("Unexpected error closing connection; ignored.", *sys.exc_info())

    def __exit__(self, t, v, tb):
        # Returning a True value from __exit__ suppresses any
        # exception raised in the body.
        body_raised = t is not None
        abort_only = body_raised # Should we commit our transaction, or only abort it?
        error_in_body = None # Did the body do something wrong?
        # Assuming we're still on the same thread and this hasn't been reset.
        txm = transaction.manager
        tx = self.__current_transaction
        if not txm.explicit:
            abort_only = True
            error_in_body = _TransactionManagerModeChanged(t, v, tb)

        try:
            if txm.get() is not tx:
                # Remember, .get() could raise.
                self._clean_up_one_transaction(txm.get(), abort_only=True)
                error_in_body = _TransactionChanged(t, v, tb)
        except NoTransaction:
            abort_only = True # It's already gone, so just abort it
            error_in_body = _TransactionChanged(t, v, tb)

        try:
            self._clean_up_one_transaction(tx, abort_only)
        except Exception: # pylint:disable=broad-except
            if not body_raised:
                # The body had no issue, but the commit did. Raise the commit error,
                # but let the finally block know not to shadow it.
                body_raised = True
                raise
            self._report_exception(
                "Failed to cleanup trans, but body raised exception too. "
                "This exception will be ignored.",
                *sys.exc_info())
            # So let the body exception propagate
        finally:
            txm.explicit = self.__txm_was_explicit
            self._close_connection(self.conn, ignore_errors=body_raised)
            self.conn = self.__current_transaction = None
        reset_db_caches(self.db)
        if error_in_body:
            raise error_in_body # pylint:disable=raising-bad-type



def reset_db_caches(db=None, collect=False):
    """
    Minimize the caches of all connections found in the *db*.

    If the *db* is not given, then the one from the :class:`ZODBLayer`
    is used.

    On PyPy, or if *collect* is true, this will invoke
    :func:`gc.collect` to help remove any weak references to objects
    that were ejected from the cache.
    """
    result = -1
    if db is None:
        db = ZODBLayer.db
    if db is not None:
        for conn in db.pool:
            conn.cacheMinimize()
        if PYPY or collect:
            result = gc.collect()
    return result

class ZODBLayer(ZopeComponentLayer):
    """
    Test layer that creates a ZODB database using
    :class:`ZODB.DemoStorage.DemoStorage` and registers it as the
    no-name :class:`ZODB.interfaces.IDatabase` in the global component
    registry. It is also available in the :attr:`db` attribute of this
    object.
    """

    #: The DB that was created.
    db = None

    @classmethod
    def setUp(cls):
        db = cls.db = ZODB.DB(DemoStorage())
        component.getGlobalSiteManager().registerUtility(db, IDatabase)

    @classmethod
    def tearDown(cls):
        db = cls.db
        cls.db = None
        if db is not None:
            db.close()
            reg_db = component.getGlobalSiteManager().queryUtility(IDatabase)
            if reg_db is db:
                component.getGlobalSiteManager().unregisterUtility(db, IDatabase)

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass
