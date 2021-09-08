#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The ``nti.testing`` module exposes the most commonly used API from the
submodules (for example, ``nti.testing.is_true`` is just an alias for
``nti.testing.matchers.is_true``). The submodules may contain other
functions, though, so be sure to look at their documentation.

Importing this module has side-effects when :mod:`zope.testing` is
importable:

    - Add a zope.testing cleanup to ensure that transactions never
      last past the boundary of a test. If a test begins a transaction
      and then fails to abort or commit it, subsequent uses of the
      transaction package may find that they are in a bad state,
      unable to clean up resources. For example, the dreaded
      ``ConnectionStateError: Cannot close a connection joined to a
      transaction``.

    - A zope.testing cleanup also ensures that the global transaction
      manager is in its default implicit mode, at least for the
      current thread.

.. versionchanged:: 3.1.0

    The :mod:`mock` module, or its backwards compatibility backport for
    Python 2.7, is now available as an attribute of this module, and as
    the module named ``nti.testing.mock``. Thus, for compatibility with
    both Python 2 and Python 3, you can write ``from nti.testing import
    mock`` or ``from nti.testing.mock import Mock``, or even just
    ``from nti.testing import Mock``.

.. versionchanged:: 3.1.0

   Expose the most commonly used attributes of some submodules as API on this
   module itself.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import transaction
import zope.testing.cleanup

from . import mock
from .mock import Mock

from .matchers import is_true
from .matchers import is_false
from .matchers import provides
from .matchers import implements
from .matchers import verifiably_provides
from .matchers import validly_provides
from .matchers import validated_by
from .matchers import not_validated_by
from .matchers import aq_inContextOf

from .time import time_monotonically_increases


__docformat__ = "restructuredtext en"

def transactionCleanUp():
    """
    Implement the transaction cleanup described in the module documentation.
    """
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

__all__ = [
    # Things defined here we want to export
    # if they do 'from nti.testing import *'
    # This also defines what Sphinx documents for this module.
    'transactionCleanUp',
    'mock',
    'Mock',
    # API Convenience exports.
    # * matchers
    'is_true',
    'is_false',
    'provides',
    'implements',
    'verifiably_provides',
    'validly_provides',
    'validated_by',
    'not_validated_by',
    'aq_inContextOf',
    # * time
    'time_monotonically_increases',
    # Sub-modules that should be imported with
    # * imports as well. We generally don't want anything
    # imported; it's better to use direct imports.
]
