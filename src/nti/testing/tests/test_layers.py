#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for layers.py.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from nti.testing import layers

from hamcrest import assert_that
from hamcrest import is_

__docformat__ = "restructuredtext en"


class TestLayers(unittest.TestCase):

    def test_find_test(self):

        def func():
            assert_that(layers.find_test(), is_(self))

        func()

        def via_test(test):
            func()

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

        for meth in ('setUp', 'tearDown', 'testSetUp', 'testTearDown',
                     'setUpPackages', 'tearDownPackages'):
            getattr(Layer, meth)()
