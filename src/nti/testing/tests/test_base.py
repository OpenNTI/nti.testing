#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_

from nti.testing import base
from nti.testing.matchers import has_attr

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


    def test_shared_test_base_cover(self):
        # Just coverage.
        import gc
        class MyTest(base.AbstractSharedTestBase):
            HANDLE_GC = True
            def test_thing(self):
                pass

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
                pass

        mt = MyTest('test_thing')
        mt.setUp()
        mt.configure_string('<configure xmlns="http://namespaces.zope.org/zope" />')
        mt.tearDown()

    def test_shared_configuring_base(self):
        import zope.traversing.tests.test_traverser
        class MyTest(base.SharedConfiguringTestBase):
            set_up_packages = ('zope.component',
                               ('configure.zcml', 'zope.component'),
                               zope.traversing.tests.test_traverser)

            def test_thing(self):
                pass

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
