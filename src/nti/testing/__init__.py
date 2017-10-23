#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
nti.testing.

Importing this module has side-effects when zope.testing is in use:


Ensure that transactions never last past the boundary of a test. If a
test begins a transaction and then fails to abort or commit it,
subsequent uses of the transaction package may find that they are in a
bad state, unable to clean up resources. For example, the dreaded
``ConnectionStateError: Cannot close a connection joined to a
transaction``
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import transaction
import zope.testing.cleanup

__docformat__ = "restructuredtext en"


zope.testing.cleanup.addCleanUp(transaction.abort)
