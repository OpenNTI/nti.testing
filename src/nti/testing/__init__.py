#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id: __init__.py 24710 2013-09-25 14:49:07Z jason.madden $
"""

from __future__ import print_function, unicode_literals, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.testing.cleanup

# Ensure that transactions never last past the boundary
# of a test. If a test begins a transaction and then fails to abort or commit it,
# subsequent uses of the transaction package may find that they are in a bad
# state, unable to clean up resources. For example, the dreaded
# ConnectionStateError: Cannot close a connection joined to a transaction
import transaction
zope.testing.cleanup.addCleanUp( transaction.abort )
