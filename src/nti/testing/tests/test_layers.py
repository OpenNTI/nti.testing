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

from nti.testing import layers

class TestLayers(unittest.TestCase):

    def test_find_test(self):

        def foo():
            assert_that(layers.find_test(), is_(self))

        foo()

        def via_test(test):
            foo()

        via_test(self)

    def test_gc(self):

        gcm = layers.GCLayerMixin()

        for meth in 'setUp', 'tearDown', 'testSetUp', 'testTearDown', 'setUpGC', 'tearDownGC':
            getattr(gcm, meth)()

    def test_shared_cleanup(self):

        gcm = layers.SharedCleanupLayer()

        for meth in 'setUp', 'tearDown', 'testSetUp', 'testTearDown':
            getattr(gcm, meth)()

    def test_zcl(self):

        gcm = layers.ZopeComponentLayer()

        for meth in 'setUp', 'tearDown', 'testSetUp', 'testTearDown':
            getattr(gcm, meth)()

    def test_configuring_layer_mixin(self):

        class Layer(layers.ConfiguringLayerMixin):
            set_up_packages = ('zope.component',)

        for meth in 'setUp', 'tearDown', 'testSetUp', 'testTearDown', 'setUpPackages', 'tearDownPackages':
            getattr(Layer, meth)()
