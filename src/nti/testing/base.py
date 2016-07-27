#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base test classes and functions for setting up ZCA.

$Id: base.py 42673 2014-07-05 14:43:39Z jason.madden $
"""

from __future__ import print_function, unicode_literals, absolute_import, division



logger = __import__('logging').getLogger(__name__)

import os
import sys
import unittest

import zope.testing.cleanup

import transaction
import gc

import six
from six import with_metaclass

class AbstractTestBase(zope.testing.cleanup.CleanUp, unittest.TestCase):
    """
    Base class for testing. Inherits the setup and teardown functions for
    :class:`zope.testing.cleanup.CleanUp`; one effect this has is to cause
    the component registry to be reset after every test.

    .. note:: Do not use this when you use :func:`module_setup` and :func:`module_teardown`,
        as the inherited :meth:`setUp` will undo the effects of the module setup.
    """

    def get_configuration_package( self ):
        """
        Return the package that "." means when configuring packages. For test classes that exist
        in a subpackage called 'tests' in a module beginning with 'test', this defaults to the parent package.
        E.g., if self is 'nti.appserver.tests.test_app.TestApp' then this is 'nti.appserver'
        """
        module = self.__class__.__module__
        if module:
            module_parts = module.split( '.' )
            if module_parts[-1].startswith( 'test' ) and module_parts[-2] == 'tests':
                module = '.'.join( module_parts[0:-2] )

            package = sys.modules[module]
            return package

_shared_cleanups = []

def addSharedCleanUp(func, args=(), kw=None):
    """Registers a cleanup to happen for every test,
    regardless of whether the test is using shared configuration or not."""
    _shared_cleanups.append( (func, args, kw or {}) )
    zope.testing.cleanup.addCleanUp( func, args, kw or {})

def sharedCleanup():
    """
    Clean up things that should be cleared for every test, even
    in a shared test base"""
    for func, args, kw in _shared_cleanups:
        func(*args, **kw)

class _SharedTestBaseMetaclass(type):
    """
    A metaclass that converts the nose-specific use of setUpClass
    and tearDownClass into a layer that also works with zope.testrunner
    (which is generally better than nose2).

    This works because nose2 picks one or the other, and it chooses layers
    over setUp/tearDownClass---only one of them is called. (If that changes,
    it's easy to workaround.)
    """

    def __new__(mcs, name, bases, cdict):
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

import platform
_is_pypy = platform.python_implementation() == 'PyPy'

class AbstractSharedTestBase(with_metaclass(_SharedTestBaseMetaclass, unittest.TestCase)):
    """
    Base class for testing that can share most global data (e.g., ZCML
    configuration) between unit tests. This is far more efficient, if
    the global data (e.g., ZCA component registry) is otherwise
    cleaned up or not mutated between tests.

    """

    HANDLE_GC = False

    @classmethod
    def setUpClass(cls):
        """
        Subclasses must call this method. It cleans up the global state.

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
        if cls.HANDLE_GC:
            cls.__isenabled = gc.isenabled()
            if not _is_pypy:
                gc.disable() # PyPy GC is fast

    @classmethod
    def tearDownClass(cls):
        zope.testing.cleanup.cleanUp()
        if cls.HANDLE_GC:
            if cls.__isenabled:
                gc.enable()

            gc.collect(0) # collect now to clean up weak refs
            if _is_pypy:
                gc.collect(0) # PyPy sometimes needs two cycles to get them all
            assert_that( gc.garbage, is_( [] ) )

    def setUp(self):
        sharedCleanup()

    def tearDown(self):
        sharedCleanup()


from zope import component
from zope.configuration import xmlconfig, config
from zope.component.hooks import setHooks
from zope.dottedname import resolve as dottedname
from zope.component import eventtesting

def _configure(self=None, set_up_packages=(), features=('devmode','testmode'), context=None, package=None):

    features = set(features) if features is not None else set()

    # This is normally created by a slug, but tests may not always
    # load the slug
    if os.getenv('DATASERVER_DIR_IS_BUILDOUT'): # pragma: no cover
        features.add( 'in-buildout' )


    # zope.component.globalregistry conveniently adds
    # a zope.testing.cleanup.CleanUp to reset the globalSiteManager
    if context is None and (features or package):
        context = config.ConfigurationMachine()
        context.package = package
        xmlconfig.registerCommonDirectives( context )

    for feature in features:
        context.provideFeature( feature )

    if set_up_packages:
        logger.debug( "Configuring %s with features %s", set_up_packages, features )

        for i in set_up_packages:
            __traceback_info__ = (i, self)
            if isinstance( i, tuple ):
                filename = i[0]
                package = i[1]
            else:
                filename = 'configure.zcml'
                package = i

            if isinstance(package, six.string_types):
                package = dottedname.resolve( package )

            try:
                context = xmlconfig.file( filename, package=package, context=context )
            except IOError as e:
                # Did we pass in a test module (__name__) and there is no
                # configuration in that package? In that case, we want to
                # configure the parent package for sure
                module_path = getattr( package, '__file__', None )
                if (module_path
                    and 'tests' in module_path
                    and os.path.join(os.path.dirname(module_path), filename) == e.filename):
                    parent_package_name = '.'.join(package.__name__.split('.')[:-2])
                    package = dottedname.resolve( parent_package_name )
                    context = xmlconfig.file( filename, package=package, context=context )
                else: # pragma: no cover
                    raise

    return context

_marker = object()
class ConfiguringTestBase(AbstractTestBase):
    """
    Test case that can be subclassed when ZCML configuration is desired.

    This class defines these class level attributes:

    .. py:attribute:: set_up_packages
        A sequence of package objects or strings naming packages. These will be configured, in order, using
        ZCML. The ``configure.zcml`` package from each package will be loaded. Instead
        of a package object, each item can be a tuple of (filename, package); in that case,
        the given file (usually ``meta.zcml``) will be loaded from the given package.

    .. py:attribute:: features
        A sequence of strings to be added as features before loading the configuration. By default,
        this is ``devmode`` and ``testmode``. (Devmode is suitable for running the application, testmode
        is only suitable for unit tests.)

    .. py:attribute:: configure_events
        A boolean defaulting to True. When true, the :mod:`zope.component.eventtesting` module will
        be configured. NOTE: If there are any ``set_up_packages`` you are responsibosile for ensuring
        that the :mod:`zope.component` configuration is loaded.

    When the meth:`setUp` method runs, one instance attribute is defined:

    .. py:attribute:: configuration_context
        The :class:`config.ConfigurationMachine` that was used to load configuration data (if any).
        This can be used by individual methods to load more configuration data using
        :meth:`configure_packages` or the methods from :mod:`zope.configuration`

    """

    set_up_packages = ()
    features = ('devmode','testmode')
    configuration_context = None
    configure_events = True

    def setUp( self ):
        super(ConfiguringTestBase,self).setUp()
        setHooks() # zope.component.hooks registers a zope.testing.cleanup to reset these
        if self.configure_events:
            if self.set_up_packages:
                # If zope.component is being configured, we wind up with duplicates if we let
                # eventtesting fully configure itself
                component.provideHandler( eventtesting.events.append, (None,) )
            else:
                eventtesting.setUp() # pragma: no cover

        self.configuration_context = self.configure_packages( set_up_packages=self.set_up_packages,
                                                              features=self.features,
                                                              context=self.configuration_context,
                                                              package=self.get_configuration_package() )



    def configure_packages(self, set_up_packages=(), features=(), context=_marker, configure_events=True, package=None ):
        self.configuration_context = _configure( self,
                                                 set_up_packages=set_up_packages,
                                                 features=features,
                                                 context=(context if context is not _marker else self.configuration_context),
                                                 package=package)
        return self.configuration_context

    def configure_string( self, zcml_string ):
        """
        Execute the given ZCML string.
        """
        self.configuration_context = xmlconfig.string( zcml_string, self.configuration_context )
        return self.configuration_context

    def tearDown( self ):
        # always safe to clear events
        eventtesting.clearEvents() # redundant with zope.testing.cleanup
        #resetHooks() we never actually want to do this, it's not needed and can mess up other fixtures
        del self.configuration_context
        super(ConfiguringTestBase,self).tearDown()

class SharedConfiguringTestBase(AbstractSharedTestBase):
    """
    Test case that can be subclassed when ZCML configuration is desired.

    This class defines these class level attributes:

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


    """

    set_up_packages = ()
    features = ('devmode','testmode')
    configuration_context = None
    configure_events = True

    @classmethod
    def setUpClass( cls ):
        super(SharedConfiguringTestBase,cls).setUpClass()
        setHooks() # zope.component.hooks registers a zope.testing.cleanup to reset these
        if cls.configure_events:
            if cls.set_up_packages:
                component.provideHandler( eventtesting.events.append, (None,) )
            else:
                eventtesting.setUp() # pragma: no cover
        cls.configuration_context = cls.configure_packages(set_up_packages=cls.set_up_packages,
                                                           features=cls.features,
                                                           context=cls.configuration_context)

    @classmethod
    def configure_packages(cls, set_up_packages=(), features=(), context=None ):
        cls.configuration_context = _configure(self=cls,
                                               set_up_packages=set_up_packages,
                                               features=features,
                                               context=context or cls.configuration_context)
        return cls.configuration_context

    @classmethod
    def tearDownClass( cls ):
        # always safe to clear events
        eventtesting.clearEvents() # redundant with zope.testing.cleanup
        # resetHooks() we never actually want to do this, it's not needed and can mess up other fixtures
        super(SharedConfiguringTestBase,cls).tearDownClass()

    def tearDown( self ):
        # Some tear down needs to happen always
        eventtesting.clearEvents()
        transaction.abort() # see comments above
        super(SharedConfiguringTestBase,self).tearDown()


def module_setup( set_up_packages=(), features=('devmode','testmode'), configure_events=True):
    """
    Either import this as ``setUpModule`` at the module level, or call
    it to perform module level set up from your own function with that name.

    This is an alternative to using :class:`ConfiguringTestBase`; the two should
    generally not be mixed in a module. It can also be used with Nose's `with_setup` function.
    """
    zope.testing.cleanup.setUp()
    setHooks()
    if configure_events:
        if set_up_packages:
            component.provideHandler( eventtesting.events.append, (None,) )
        else:
            eventtesting.setUp()

    _configure( set_up_packages=set_up_packages, features=features )

def module_teardown():
    """
    Either import this as ``tearDownModule`` at the module level, or call
    it to perform module level tear down froum your own function with that name.

    This is an alternative to using :class:`ConfiguringTestBase`; the two should
    generally not be mixed in a module.
    """
    eventtesting.clearEvents() # redundant with zope.testing.cleanup
    # resetHooks() we never actually want to do this, it's not needed and can mess up other fixtures
    zope.testing.cleanup.tearDown()

# The cleanup that we get by importing just zope.interface and zope.component
# has a problem:
# zope.component installs adapter hooks that cause the use of interfaces
# as functions to direct through the current site manager (as does the global component API).
# This adapter hook is a cached function of an implementation detail of the site manager:
# siteManager.adapters.adapter_hook.
#
# If no site is ever set, this caches the adapter_hook of the globalSiteManager.
#
# When the zope.component cleanup runs, it swizzles out the internals of the
# globalSiteManager by re-running __init__. However, it does not clear the cached
# adapter_hook. Thus, subsequent uses of the adapter hook (interface calls, or use
# of the global component API) continue to use the *old* adapter registry (which is no
# longer easy to access and inspect, especially when the C hook optimizations are in use)
# If any non-ZCML registrations are made (or the next test loads a subset of the ZCML the previous test
# did) then this manifests as strange adapter failures.
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
#   _configure( None, (('meta.zcml',zope.mimetype),
#                      ('meta.zcml',zope.component),
#                      zope.mimetype) )
# except ImportError:
#   pass

# Attempting to runaround the testing cleanup by
# using a different base doesn't quite work,
# some things are still using the old one
# globalregistry.base = BaseComponents()

from hamcrest import assert_that
from hamcrest import is_
