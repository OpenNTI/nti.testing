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

    def _check_methods(self, layer, extra_methods=()):
        default_methods = ('setUp', 'tearDown', 'testSetUp', 'testTearDown')
        for meth in default_methods + extra_methods:
            getattr(layer, meth)()

    def test_gc(self):

        gcm = layers.GCLayerMixin()
        self._check_methods(gcm, ('setUpGC', 'tearDownGC'))

    def test_shared_cleanup(self):
        self._check_methods(layers.SharedCleanupLayer)

    def test_zcl(self):
        self._check_methods(layers.ZopeComponentLayer)

    def test_configuring_layer_mixin(self):
        class Layer(layers.ConfiguringLayerMixin):
            set_up_packages = ('zope.component',)

        self._check_methods(Layer, ('setUpPackages', 'tearDownPackages'))
