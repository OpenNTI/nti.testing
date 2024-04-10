#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test layers for working with Zope libraries.

"""

import gc
import logging


from zope import component
from zope.component import eventtesting
from zope.component.hooks import setHooks

from .. import transactionCleanUp
from ..base import AbstractConfiguringObject
from .cleanup import SharedCleanupLayer

logger = logging.getLogger(__name__)

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
        component.getGlobalSiteManager().__init__('base') # pylint:disable=unnecessary-dunder-call
        gc.collect()
        cls.configuration_context = None
