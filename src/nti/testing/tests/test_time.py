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

from nti.testing.time import time_monotonically_increases

class TestTime(unittest.TestCase):

    def _check_time(self):
        import time
        for _ in range(10):
            now = time.time()
            then = time.time()
            assert_that( now, is_(then - 1) )

    @time_monotonically_increases
    def test_increases_in_method(self):
        self._check_time()

    def test_increases_in_func(self):

        @time_monotonically_increases
        def f():
            self._check_time()

        f()

if __name__ == '__main__':
    unittest.main()
