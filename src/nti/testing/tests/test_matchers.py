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
from hamcrest import calling
from hamcrest import raises

from nti.testing import base
from nti.testing import matchers

class TestMatchers(unittest.TestCase):

    def test_bool(self):
        assert_that(True, matchers.is_true())
        assert_that(1, matchers.is_true())

        assert_that(False, matchers.is_false())
        assert_that(0, matchers.is_false())


        assert_that(calling(assert_that).with_args(1, matchers.is_false()),
                    raises(AssertionError))

        assert_that(calling(assert_that).with_args(u'', matchers.is_true()),
                    raises(AssertionError))
        assert_that(calling(assert_that).with_args(b'', matchers.is_true()),
                    raises(AssertionError))
