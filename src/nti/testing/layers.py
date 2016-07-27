#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test layer support.

$Id: layers.py 42910 2014-07-10 18:11:05Z jason.madden $
"""

from __future__ import print_function, unicode_literals, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
#pylint: disable=W0212


import sys
import unittest

import zope.testing.cleanup

import transaction
import gc

from .base import sharedCleanup

from hamcrest import assert_that
from hamcrest import is_

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
    def testSetUp( cls ):
        pass

    @classmethod
    def testTearDown(cls):
        # Must implement
        pass

    @classmethod
    def setUpGC(cls):
        """
        Subclasses must NOT call this method. It cleans up the global state.

        It also disables garbage collection until tearDown is called
        if ``HANDLE_GC`` is True. This way, we can collect just one
        generation and be sure to clean up any weak references that
        were created during this run. (Which is necessary, as ZCA
        heavily uses weak references, and when that is mixed with
        IComponents instances that are in a ZODB, if weak references
        persist and aren't cleaned, bad things can happen. See
        ``nti.dataserver.site`` for details.) This is ``False`` by
        default for speed; set it to true if your TestCase will be
        creating new (possibly synthetic) sites/site managers.
        """
        zope.testing.cleanup.cleanUp()
        cls.__isenabled = gc.isenabled()
        gc.disable()

    @classmethod
    def tearDownGC(cls):
        zope.testing.cleanup.cleanUp()

        if cls.__isenabled:
            gc.enable()

        gc.collect( 0 ) # collect one generation now to clean up weak refs
        assert_that( gc.garbage, is_( [] ) )

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
        sharedCleanup()

    @classmethod
    def testTearDown(cls):
        sharedCleanup()


from zope import component
from zope.component.hooks import setHooks
from zope.component import eventtesting
from .base import _configure

class ZopeComponentLayer(SharedCleanupLayer):
    """
    Test layer that can be subclassed when ZCML configuration is desired.

    This does nothing but set up the hooks and the event handlers.
    """

    @classmethod
    def setUp( cls ):
        setHooks() # zope.component.hooks registers a zope.testing.cleanup to reset these


    @classmethod
    def tearDown( cls ):
        # always safe to clear events
        eventtesting.clearEvents() # redundant with zope.testing.cleanup
        # resetHooks()  we never actually want to do this, it's not needed and can mess up other fixtures

    @classmethod
    def testSetUp(cls):
        setHooks() # ensure these are still here; cheap and easy

    @classmethod
    def testTearDown( cls ):
        # Some tear down needs to happen always
        eventtesting.clearEvents()
        transaction.abort() # see comments above

_marker = object()

class ConfiguringLayerMixin(object):
    """
    Inherit from this layer *at the leaf level* to perform configuration.
    You should have already inherited from ZopeComponentLayer.

    .. py:attribute:: set_up_packages
        A sequence of package objects or strings naming packages. These will be configured, in order, using
        ZCML. The ``configure.zcml`` package from each package will be loaded. Instead
        of a package object, each item can be a tuple of (filename, package); in that case,
        the given file (usually ``meta.zcml``) will be loaded from the given package.

    .. py:attribute:: features
        A sequence of strings to be added as features before loading the configuration. By default,
        this is ``devmode`` and ``testmode``.

    .. py:attribute:: configure_events
        A boolean defaulting to True. When true, the :mod:`zope.component.eventtesting` module will
        be configured.  NOTE: If there are any ``set_up_packages`` you are resposionsible for ensuring
        that the :mod:`zope.component` configuration is loaded.


    When the meth:`setUp` method runs, one class attribute is defined:

    .. py:attribute:: configuration_context
        The :class:`config.ConfigurationMachine` that was used to load configuration data (if any).
        This can be used by individual methods to load more configuration data.


    To use this layer, subclass it and define a set of packages. This should
    be done EXACTLY ONCE for each set of packages; things that add to the set
    of packages should generally extend that layer class.

    """

    set_up_packages = ()
    features = ('devmode','testmode')
    configuration_context = None

    @classmethod
    def setUp(cls):
        # You MUST implement this, otherwise zope.testrunner
        # will call the super-class again
        pass

    @classmethod
    def tearDown(cls):
        # You MUST implement this, otherwise zope.testrunner
        # will call the super-class again
        pass

    @classmethod
    def testSetUp( cls ):
        pass

    @classmethod
    def testTearDown(cls):
        # Must implement
        pass

    @classmethod
    def setUpPackages(cls):
        logger.info( 'Setting up packages %s for layer %s', cls.set_up_packages, cls )
        gc.collect()
        cls.configuration_context = cls.configure_packages(set_up_packages=cls.set_up_packages,
                                                            features=cls.features,
                                                            context=cls.configuration_context)
        component.provideHandler( eventtesting.events.append, (None,) )
        gc.collect()

    @classmethod
    def configure_packages(cls, set_up_packages=(), features=(), context=None ):
        cls.configuration_context = _configure(self=cls,
                                               set_up_packages=set_up_packages,
                                               features=features,
                                               context=context or cls.configuration_context)
        return cls.configuration_context

    @classmethod
    def tearDownPackages(cls):
        # This is a duplicate of zope.component.globalregistry
        logger.info( 'Tearing down packages %s for layer %s', cls.set_up_packages, cls )
        gc.collect()
        component.getGlobalSiteManager().__init__('base')
        gc.collect()
        cls.configuration_context = None


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
            frame = sys._getframe(i)
            i = i + 1
        except ValueError: # pragma: no cover
            return None
        else:
            if isinstance(frame.f_locals.get('self'), unittest.TestCase):
                return frame.f_locals['self']
            if isinstance(frame.f_locals.get('test'), unittest.TestCase):
                return frame.f_locals['test']
