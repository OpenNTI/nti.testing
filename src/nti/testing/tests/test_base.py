#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for base.py.

.. $Id$
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from nti.testing import base
from nti.testing.matchers import has_attr

from hamcrest import assert_that
from hamcrest import is_

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

class TestBase(unittest.TestCase):

    def test_package(self):
        import nti.testing

        class MyTest(base.AbstractTestBase):
            pass

        b = MyTest('get_configuration_package')
        assert_that(b.get_configuration_package(),
                    is_(nti.testing))

    def test_cleanup(self):
        called = [0]
        def func():
            called[0] += 1

        base.addSharedCleanUp(func)
        base.sharedCleanup()
        assert_that(called[0], is_(1))

        import zope.testing

        zope.testing.cleanup.cleanUp()
        assert_that(called[0], is_(2))

        base._shared_cleanups.remove((func, (), {}))

    def test_explicit_transaction_cleanup(self):
        import transaction
        import zope.testing
        transaction.manager.explicit = True
        transaction.begin()

        zope.testing.cleanup.cleanUp()
        assert_that(transaction.manager, has_attr('explicit', False))

    def test_explicit_transaction_cleanup_no_transaction(self):
        import transaction
        import zope.testing
        transaction.manager.explicit = True
        zope.testing.cleanup.cleanUp()
        assert_that(transaction.manager, has_attr('explicit', False))

    def test_shared_test_base_cover(self):
        # Just coverage.
        import gc
        class MyTest(base.AbstractSharedTestBase):
            HANDLE_GC = True
            def test_thing(self):
                raise AssertionError("Not called")

        MyTest.setUpClass()
        assert_that(gc.isenabled(), is_(False if not base._is_pypy else True))
        MyTest.tearDownClass()
        assert_that(gc.isenabled(), is_(True))

        MyTest('test_thing').setUp()
        MyTest('test_thing').tearDown()


    def test_configuring_base(self):
        import zope.traversing.tests.test_traverser
        class MyTest(base.ConfiguringTestBase):
            set_up_packages = ('zope.component',
                               ('configure.zcml', 'zope.component'),
                               zope.traversing.tests.test_traverser)

            def test_thing(self):
                raise AssertionError("Not called")

        mt = MyTest('test_thing')
        mt.setUp() # pylint:disable=no-value-for-parameter
        mt.configure_string('<configure xmlns="http://namespaces.zope.org/zope" />')
        mt.tearDown() # pylint:disable=no-value-for-parameter

    def test_shared_configuring_base(self):
        import zope.traversing.tests.test_traverser
        class MyTest(base.SharedConfiguringTestBase):
            layer = None # replaced by metaclass
            set_up_packages = ('zope.component',
                               ('configure.zcml', 'zope.component'),
                               zope.traversing.tests.test_traverser)

            def test_thing(self):
                raise AssertionError("Not called")

        MyTest.setUpClass()
        MyTest.tearDownClass()

        # It should have a layer automatically
        assert_that(MyTest, has_attr('layer', has_attr('__name__', 'MyTest')))

        MyTest.layer.setUp()
        MyTest.layer.testSetUp()
        MyTest.layer.testTearDown()
        MyTest.layer.tearDown()

        MyTest('test_thing').tearDown()

    def test_module_setup(self):
        base.module_setup()
        base.module_setup(set_up_packages=('zope.component',))
        base.module_teardown()
