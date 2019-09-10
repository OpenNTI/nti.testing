#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
nti.testing.

Importing this module has side-effects when zope.testing is
importable:

    - Add a zope.testing cleanup to ensure that transactions never
      last past the boundary of a test. If a test begins a transaction
      and then fails to abort or commit it, subsequent uses of the
      transaction package may find that they are in a bad state,
      unable to clean up resources. For example, the dreaded
      ``ConnectionStateError: Cannot close a connection joined to a
      transaction``.

    - A zope.testing cleanup also ensures that the global transaction manager
      is in its default implicit mode, at least for the current thread.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import transaction
import zope.testing.cleanup

__docformat__ = "restructuredtext en"

def transactionCleanUp():
    try:
        transaction.abort()
    except transaction.interfaces.NoTransaction:
        # An explicit transaction manager, with nothing
        # to do. Perfect.
        pass
    finally:
        # Note that we don't catch any other transaction errors.
        # Those usually mean there's a bug in a resource manager joined
        # to the transaction and it should fail the test.
        transaction.manager.explicit = False


zope.testing.cleanup.addCleanUp(transactionCleanUp)
