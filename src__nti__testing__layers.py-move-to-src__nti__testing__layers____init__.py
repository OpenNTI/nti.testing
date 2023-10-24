#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test layer support.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import gc
import sys
import unittest


from zope import component
from zope.component import eventtesting
from zope.component.hooks import setHooks
import zope.testing.cleanup

from . import transactionCleanUp
from .base import AbstractConfiguringObject
from .base import sharedCleanup

from hamcrest import assert_that
from hamcrest import is_

__docformat__ = "restructuredtext en"

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



class ZopeComponentLayer(SharedCleanupLayer):
    """
    Test layer that can be subclassed when zope.component will be used.

    This does nothing but set up the hooks and the event handlers.
    """

    @classmethod
    def setUp(cls):
        setHooks() # zope.component.hooks registers a zope.testing.cleanup to reset these


    @classmethod
    def tearDown(cls):
        # always safe to clear events
        eventtesting.clearEvents() # redundant with zope.testing.cleanup
        # we never actually want to do this, it's not needed and can mess up other fixtures
        # resetHooks()

    @classmethod
    def testSetUp(cls):
        setHooks() # ensure these are still here; cheap and easy

    @classmethod
    def testTearDown(cls):
        # Some tear down needs to happen always
        eventtesting.clearEvents()
        transactionCleanUp()

_marker = object()

class ConfiguringLayerMixin(AbstractConfiguringObject):
    """
    Inherit from this layer *at the leaf level* to perform configuration.
    You should have already inherited from :class:`ZopeComponentLayer`.

    To use this layer, subclass it and define a set of packages. This
    should be done EXACTLY ONCE for each set of packages; things that
    add to the set of packages should generally extend that layer
    class. You must call :meth:`setUpPackages` and :meth:`tearDownPackages`
    from your ``setUp`` and ``tearDown`` methods.

    See :class:`~.AbstractConfiguringObject` for documentation on
    the class attributes to configure.
    """

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
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        # Must implement
        pass

    #: .. seealso:: :meth:`~.AbstractConfiguringObject.get_configuration_package_for_class`
    #: .. versionadded:: 2.1.0
    get_configuration_package = classmethod(
        AbstractConfiguringObject.get_configuration_package_for_class
    )

    @classmethod
    def setUpPackages(cls):
        """
        Set up the configured packages.
        """
        logger.info('Setting up packages %s for layer %s', cls.set_up_packages, cls)
        gc.collect()
        cls.configuration_context = cls.configure_packages(
            set_up_packages=cls.set_up_packages,
            features=cls.features,
            context=cls.configuration_context,
            package=cls.get_configuration_package())
        component.provideHandler(eventtesting.events.append, (None,))
        gc.collect()

    configure_packages = classmethod(AbstractConfiguringObject._do_configure_packages)

    @classmethod
    def tearDownPackages(cls):
        """
        Tear down all configured packages in the global site manager.
        """
        # This is a duplicate of zope.component.globalregistry
        logger.info('Tearing down packages %s for layer %s', cls.set_up_packages, cls)
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
            frame = sys._getframe(i) # pylint:disable=protected-access
            i = i + 1
        except ValueError: # pragma: no cover
            return None
        else:
            if isinstance(frame.f_locals.get('self'), unittest.TestCase):
                return frame.f_locals['self']
            if isinstance(frame.f_locals.get('test'), unittest.TestCase):
                return frame.f_locals['test']
