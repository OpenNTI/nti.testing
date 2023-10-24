#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for cleaning up:

- Garbage collection
- Registered cleanups.

.. versionadded:: 4.0.0

"""

import gc

import zope.testing.cleanup

from ..base import sharedCleanup

from hamcrest import assert_that
from hamcrest import is_


logger = __import__('logging').getLogger(__name__)

class GCLayerMixin(object):
    """
    Mixin this layer class and call :meth:`setUpGC` from
    your layer `setUp` method and likewise for the teardowns
    when you want to do GC.
    """

    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        # Must implement
        pass

    @classmethod
    def setUpGC(cls):
        """
        This method disables GC until :meth:`tearDownGC` is called.
        You should call it from your layer ``setUp`` method.

        It also cleans up the zope.testing state.
        """
        zope.testing.cleanup.cleanUp()
        cls.__isenabled = gc.isenabled()
        gc.disable()

    @classmethod
    def tearDownGC(cls):
        """
        This method executes zope.testing's cleanup and then renables
        GC. You should call if from your layer ``tearDown`` method.
        """
        zope.testing.cleanup.cleanUp()

        if cls.__isenabled:
            gc.enable()

        gc.collect(0) # collect one generation now to clean up weak refs
        assert_that(gc.garbage, is_([]))


class SharedCleanupLayer(object):
    """
    Mixin this layer when you need cleanup functions
    that run for every test.
    """

    @classmethod
    def setUp(cls):
        # You MUST implement this, otherwise zope.testrunner
        # will call the super-class again
        zope.testing.cleanup.cleanUp()

    @classmethod
    def tearDown(cls):
        # You MUST implement this, otherwise zope.testrunner
        # will call the super-class again
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls):
        """
        Calls :func:`~.sharedCleanup` for every test.
        """
        sharedCleanup()

    @classmethod
    def testTearDown(cls):
        """
        Calls :func:`~.sharedCleanup` for every test.
        """
        sharedCleanup()
