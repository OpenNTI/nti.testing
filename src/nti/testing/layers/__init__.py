#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test layer support.

.. versionchanged:: 4.0.0

   This is now a package with sub-modules. Existing imports continue
   to work.

"""

import sys
import unittest


from .cleanup import GCLayerMixin
from .cleanup import SharedCleanupLayer
from .zope import ZopeComponentLayer
from .zope import ConfiguringLayerMixin

def find_test():
    """
    The layer support in :class:`nose2.plugins.layers.Layers`
    optionally supplies the test case object to ``testSetUp``
    and ``testTearDown``, but ``zope.testrunner`` does not do
    this. If you need access to the test, you can use an idiom like this::

        @classmethod
        def testSetUp(cls, test=None):
            test = test or find_test()
    """

    i = 2
    while True:
        try:
            frame = sys._getframe(i) # pylint:disable=protected-access
            i += 1
        except ValueError: # pragma: no cover
            return None

        if isinstance(frame.f_locals.get('self'), unittest.TestCase):
            return frame.f_locals['self']
        if isinstance(frame.f_locals.get('test'), unittest.TestCase):
            return frame.f_locals['test']

__all__ = [
    'GCLayerMixin',
    'SharedCleanupLayer',
    'ZopeComponentLayer',
    'ConfiguringLayerMixin',
    'find_test',
]
