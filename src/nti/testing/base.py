#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base test classes and functions for setting up ZCA.

In some cases, you may be better off using :mod:`zope.component.testlayer`.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import gc
import os
import platform
import sys
import unittest

import six
from six import with_metaclass

from zope import component
from zope.component import eventtesting
from zope.component.hooks import setHooks
from zope.configuration import config
from zope.configuration import xmlconfig
from zope.dottedname import resolve as dottedname
import zope.testing.cleanup

from hamcrest import assert_that
from hamcrest import is_

from . import transactionCleanUp

logger = __import__('logging').getLogger(__name__)


_marker = object()

class AbstractConfiguringObject(object):
    """
    A class for executing ZCML configuration.

    Other than the attributes that are documented on this class,
    users are not expected to use this class or subclass it.
    """

    #: Class attribute naming a sequence of package objects or strings
    #: naming packages. These will be configured, in order, using
    #: ZCML. The ``configure.zcml`` package from each package will be
    #: loaded. Instead of a package object, each item can be a tuple
    #: of (filename, package); in that case, the given file (usually
    #: ``meta.zcml``) will be loaded from the given package.
    set_up_packages = ()

    #: Class attribute naming a sequence of strings to be added as
    #: features before loading the configuration. By default, this is
    #: ``devmode`` and ``testmode``. (Devmode is suitable for running
    #: the application, testmode is only suitable for unit tests.)
    features = ('devmode', 'testmode')

    #: Class attribute that is a boolean defaulting to True. When
    #: true, the :mod:`zope.component.eventtesting` module will be
    #: configured.
    #:
    #: .. note:: If there are any ``set_up_packages`` you are
    #:           responsible for ensuring that the :mod:`zope.component`
    #:           configuration is loaded.
    configure_events = True

    #: Instance attribute defined by :meth:`setUp` that is the :class:`~.ConfigurationMachine`
    #: that was used to load configuration data (if any). This can be
    #: used by individual methods to load more configuration data
    #: using :meth:`configure_packages` or the methods from
    #: :mod:`zope.configuration`
    configuration_context = None

    @staticmethod
    def _doSetUp(obj):
        obj._doSetUpSuper() # pylint:disable=protected-access
        setHooks() # zope.component.hooks registers a zope.testing.cleanup to reset these
        if obj.configure_events:
            if obj.set_up_packages:
                # If zope.component is being configured, we wind up with duplicates if we let
                # eventtesting fully configure itself
                component.provideHandler(eventtesting.events.append, (None,))
            else:
                eventtesting.setUp() # pragma: no cover

        obj.configuration_context = obj.configure_packages(
            set_up_packages=obj.set_up_packages,
            features=obj.features,
            context=obj.configuration_context,
            package=obj.get_configuration_package())

    @staticmethod
    def _do_configure_packages(obj,
                               set_up_packages=(),
                               features=(),
                               context=_marker,
                               configure_events=True, # unused
                               package=None):
        obj.configuration_context = _configure(
            obj,
            set_up_packages=set_up_packages,
            features=features,
            context=(context if context is not _marker else obj.configuration_context),
            package=package)
        return obj.configuration_context

    @staticmethod
    def _doTearDown(obj, clear_configuration_context=True, super_tear_down=None):
        # always safe to clear events
        eventtesting.clearEvents() # redundant with zope.testing.cleanup
        # we never actually want to do this, it's not needed and can mess up other fixtures
        # resetHooks()
        transactionCleanUp()
        if clear_configuration_context:
            obj.configuration_context = None
        if super_tear_down is not None:
            super_tear_down()
        else:
            obj._doTearDownSuper() # pylint:disable=protected-access


    @staticmethod
    def get_configuration_package_for_class(klass):
        """
        Return the package that ``.`` means when configuring packages.

        For test classes that exist in a subpackage called ``tests`` in
        a module beginning with ``test``, this defaults to the parent
        package. E.g., if *klass* is
        ``nti.appserver.tests.test_app.TestApp`` then this is
        ``nti.appserver``.
        """
        module = klass.__module__
        if not module: # pragma: no cover
            return None

        module_parts = module.split('.')
        if module_parts[-1].startswith('test') and module_parts[-2] == 'tests':
            module = '.'.join(module_parts[0:-2])

        package = sys.modules[module]
        return package


class AbstractTestBase(zope.testing.cleanup.CleanUp, unittest.TestCase):
    """
    Base class for testing. Inherits the setup and teardown functions for
    :class:`zope.testing.cleanup.CleanUp`; one effect this has is to cause
    the component registry to be reset after every test.

    .. note:: Do not use this when you use :func:`module_setup` and
        :func:`module_teardown`, as the inherited :meth:`setUp` will
        undo the effects of the module setup.
    """

    def get_configuration_package(self):
        """
        See :meth:`AbstractConfiguringObject.get_configuration_package_for_class`.
        """
        return AbstractConfiguringObject.get_configuration_package_for_class(self.__class__)

_shared_cleanups = []

def addSharedCleanUp(func, args=(), kw=None):
    """
    Registers a cleanup to happen for every test, regardless of whether
    the test is using shared configuration or not.
    """
    _shared_cleanups.append((func, args, kw or {}))
    zope.testing.cleanup.addCleanUp(func, args, kw or {})

def sharedCleanup():
    """
    Clean up things that should be cleared for every test, even
    in a shared test base.
    """
    for func, args, kw in _shared_cleanups:
        func(*args, **kw)

class SharedTestBaseMetaclass(type):
    """
    A metaclass that converts the nose-specific use of ``setUpClass``
    and ``tearDownClass`` into a layer that also works with zope.testrunner
    (which is generally better than nose2).

    This works because nose2 picks one or the other, and it chooses layers
    over setUp/tearDownClass---only one of them is called. (If that changes,
    it's easy to workaround.)
    """

    def __new__(mcs, name, bases, cdict): # pylint:disable=bad-mcs-classmethod-argument
        the_type = type.__new__(mcs, name, bases, cdict)
        # TODO: Based on certain features of the the_type
        # like set_up_packages and features, we can probably
        # cache and share layers, which will help speed up
        # test runs
        class layer(object):
            __name__ = name
            __mro__ = __bases__ = (object,)

            @classmethod
            def setUp(cls):
                the_type.setUpClass()
            @classmethod
            def tearDown(cls):
                the_type.tearDownClass()
            @classmethod
            def testSetUp(cls):
                pass
            @classmethod
            def testTearDown(cls):
                pass
        the_type.layer = layer
        layer.__name__ = name
        return the_type

_is_pypy = platform.python_implementation() == 'PyPy'

class AbstractSharedTestBase(with_metaclass(SharedTestBaseMetaclass, unittest.TestCase)):
    """
    Base class for testing that can share most global data (e.g., ZCML
    configuration) between unit tests. This is far more efficient, if
    the global data (e.g., ZCA component registry) is otherwise
    cleaned up or not mutated between tests.

    Under zope.testing and nose2, this is handled by treating the class
    as a *layer* through :class:`SharedTestBaseMetaclass`.

    """

    #: Class-level attribute that determines whether
    #: we should only collect garbage when tearing down the class.
    HANDLE_GC = False

    @classmethod
    def setUpClass(cls):
        """
        Subclasses must call this method. It cleans up the global state.

        It also disables garbage collection until
        :meth:`tearDownClass` is called if :attr:`HANDLE_GC` is True. This
        way, we can collect just one generation and be sure to clean
        up any weak references that were created during this run.
        (Which is necessary, as ZCA heavily uses weak references, and
        when that is mixed with IComponents instances that are in a
        ZODB, if weak references persist and aren't cleaned, bad
        things can happen. See ``nti.dataserver.site`` for details.)
        This is ``False`` by default for speed; set it to true if your
        TestCase will be creating new (possibly synthetic) sites/site
        managers.
        """

        zope.testing.cleanup.cleanUp()
        if cls.HANDLE_GC:
            cls.__isenabled = gc.isenabled()
            if not _is_pypy:
                gc.disable() # PyPy GC is fast

    @classmethod
    def tearDownClass(cls):
        """
        Subclasses must call this method. It cleans up global state
        and performs garbage collection if :attr:`HANDLE_GC` is true.
        """
        zope.testing.cleanup.cleanUp()
        if cls.HANDLE_GC:
            if cls.__isenabled:
                gc.enable()

            gc.collect(0) # collect now to clean up weak refs
            gc.collect(0) # PyPy sometimes needs two cycles to get them all

            assert_that(gc.garbage, is_([]))

    def setUp(self):
        """
        Invokes :func:`sharedCleanup` for every test.
        """
        sharedCleanup()

    def tearDown(self):
        """
        Invokes :func:`sharedCleanup` for every test.
        """
        sharedCleanup()



def _configure(self=None,
               set_up_packages=(),
               features=('devmode', 'testmode'),
               context=None,
               package=None):

    features = set(features) if features is not None else set()

    # This is normally created by a slug, but tests may not always
    # load the slug
    if os.getenv('DATASERVER_DIR_IS_BUILDOUT'): # pragma: no cover
        features.add('in-buildout')


    # zope.component.globalregistry conveniently adds
    # a zope.testing.cleanup.CleanUp to reset the globalSiteManager
    if context is None and (features or package):
        context = config.ConfigurationMachine()
        context.package = package
        xmlconfig.registerCommonDirectives(context)

    for feature in features:
        context.provideFeature(feature)

    if set_up_packages:
        logger.debug("Configuring %s with features %s", set_up_packages, features)

        for i in set_up_packages:
            __traceback_info__ = (i, self)
            if isinstance(i, tuple):
                filename = i[0]
                package = i[1]
            else:
                filename = 'configure.zcml'
                package = i

            if isinstance(package, six.string_types):
                package = dottedname.resolve(package)

            try:
                context = xmlconfig.file(filename, package=package, context=context)
            except IOError as e:
                # Did we pass in a test module (__name__) and there is no
                # configuration in that package? In that case, we want to
                # configure the parent package for sure
                module_path = getattr(package, '__file__', '')
                if (module_path
                        and 'tests' in module_path
                        and os.path.join(os.path.dirname(module_path), filename) == e.filename):
                    parent_package_name = '.'.join(package.__name__.split('.')[:-2])
                    package = dottedname.resolve(parent_package_name)
                    context = xmlconfig.file(filename, package=package, context=context)
                else: # pragma: no cover
                    raise

    return context


class ConfiguringTestBase(AbstractConfiguringObject,
                          AbstractTestBase):
    """
    Test case that can be subclassed when ZCML configuration is desired.

    Configuration is established by the class attributes documented
    on :class:`AbstractConfiguringObject`.

    .. note:: The ZCML configuration is executed for each test.
    """

    def _doSetUpSuper(self):
        super(ConfiguringTestBase, self).setUp()

    setUp = AbstractConfiguringObject._doSetUp

    #: Configure additional packages. This should only be done in the ``setUp`` method
    #: of a subclass. Note that this is called by ``setUp``.
    configure_packages = AbstractConfiguringObject._do_configure_packages

    def configure_string(self, zcml_string):
        """
        Execute the given ZCML string.

        Tests may use this after ``setUp`` is called (this includes in the
        implementation of your own ``setUp`` function).
        """
        self.configuration_context = xmlconfig.string(zcml_string, self.configuration_context)
        return self.configuration_context

    def _doTearDownSuper(self):
        super(ConfiguringTestBase, self).tearDown()

    tearDown = AbstractConfiguringObject._doTearDown

class SharedConfiguringTestBase(AbstractConfiguringObject,
                                AbstractSharedTestBase):
    """
    Test case that can be subclassed when ZCML configuration is desired.

    Configuration is established by the class attributes documented on
    :class:`AbstractConfiguringObject`. (The ``configuration_context`` is also
    a class attribute.)

    .. note:: The ZCML configuration is only executed once, before
        any tests are run.
    """

    @classmethod
    def _doSetUpSuper(cls):
        super(SharedConfiguringTestBase, cls).setUpClass()

    setUpClass = classmethod(AbstractConfiguringObject._doSetUp)

    #: Configure additional packages. This should only be done in the ``setUpClass``
    #: method of a subclass after calling the super class. Note that this is called by
    #: ``setUpClass``.
    configure_packages = classmethod(AbstractConfiguringObject._do_configure_packages)

    #: .. seealso:: :meth:`~.AbstractConfiguringObject.get_configuration_package_for_class`
    #: .. versionadded:: 2.1.0
    get_configuration_package = classmethod(
        AbstractConfiguringObject.get_configuration_package_for_class
    )

    @classmethod
    def _doTearDownSuper(cls):
        super(SharedConfiguringTestBase, cls).tearDownClass()

    tearDownClass = classmethod(AbstractConfiguringObject._doTearDown)

    def tearDown(self):
        AbstractConfiguringObject._doTearDown(
            self,
            clear_configuration_context=False,
            super_tear_down=super(SharedConfiguringTestBase, self).tearDown)


def module_setup(set_up_packages=(),
                 features=('devmode', 'testmode'),
                 configure_events=True):
    """
    A module-level fixture for configuring packages.

    Either import this as ``setUpModule`` at the module level, or call
    it to perform module level set up from your own function with that name.
    If you use this, you must also use :func:`module_teardown`.

    This is an alternative to using :class:`ConfiguringTestBase`; the
    two should generally not be mixed in a module. It can also be used
    with Nose's `with_setup` function.
    """
    zope.testing.cleanup.setUp()
    setHooks()
    if configure_events:
        if set_up_packages:
            component.provideHandler(eventtesting.events.append, (None,))
        else:
            eventtesting.setUp()

    _configure(set_up_packages=set_up_packages, features=features)

def module_teardown():
    """
    Tears down the module-level fixture for configuring packages
    established by :func:`module_setup`.

    Either import this as ``tearDownModule`` at the module level, or
    call it to perform module level tear down froum your own function
    with that name.

    This is an alternative to using :class:`ConfiguringTestBase`; the
    two should generally not be mixed in a module.
    """
    eventtesting.clearEvents() # redundant with zope.testing.cleanup
    # we never actually want to do this, it's not needed and can mess up other fixtures
    # resetHooks()
    zope.testing.cleanup.tearDown()

# The cleanup that we get by importing just zope.interface and
# zope.component has a problem: zope.component installs adapter hooks
# that cause the use of interfaces as functions to direct through the
# current site manager (as does the global component API). This
# adapter hook is a cached function of an implementation detail of the
# site manager: siteManager.adapters.adapter_hook.
#
# If no site is ever set, this caches the adapter_hook of the globalSiteManager.
#
# When the zope.component cleanup runs, it swizzles out the internals
# of the globalSiteManager by re-running __init__. However, it does
# not clear the cached adapter_hook. Thus, subsequent uses of the
# adapter hook (interface calls, or use of the global component API)
# continue to use the *old* adapter registry (which is no longer easy
# to access and inspect, especially when the C hook optimizations are
# in use) If any non-ZCML registrations are made (or the next test
# loads a subset of the ZCML the previous test did) then this
# manifests as strange adapter failures.
#
# This is obviously all implementation detail. So rather than "fix" the problem
# ourself, the solution is to import zope.site.site to ensure that the site gets
# cleaned up and the adapter_hook cache thrown away
# This problem never manifests itself in code that has already imported zope.site,
# and it seems to be an assumption that code that uses zope.component also uses zope.site
# (though we have some code that doesn't explicitly do so)

# This is detailed in test_component_broken.txt
# submitted as https://bugs.launchpad.net/zope.component/+bug/1100501
# transferred to github as https://github.com/zopefoundation/zope.component/pull/1
#import zope.site.site
# This is identified as fixed in zope.component 4.2.0


# Zope.mimetype registers hundreds and thousands of objects
# doing that for each test makes them take SO much longer
# Unfortunately, as noted above, zope.testing.cleanup.CleanUp
# installs something to reset the gsm, so it's not possible
# to simply pre-cache like the below:
# try:
#   import zope.mimetype
#   _configure(None, (('meta.zcml',zope.mimetype),
#                      ('meta.zcml',zope.component),
#                      zope.mimetype))
# except ImportError:
#   pass

# Attempting to runaround the testing cleanup by
# using a different base doesn't quite work,
# some things are still using the old one
# globalregistry.base = BaseComponents()
