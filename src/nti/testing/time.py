#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test support for working with clocks and time.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import functools
from threading import Lock
import time
from time import time as _real_time
from time import gmtime as _real_gmtime

import six

from nti.testing.mock import Mock

__docformat__ = "restructuredtext en"

_current_time = _real_time()


class _TimeWrapper(object):

    def __init__(self, granularity=1.0):
        self._granularity = granularity
        self._lock = Lock()
        self.fake_gmtime = Mock()
        self.fake_time = Mock()
        self._configure_fakes()

    def _configure_fakes(self):
        def incr():
            global _current_time # pylint:disable=global-statement
            with self._lock:
                _current_time = max(_real_time(), _current_time + self._granularity)
            return _current_time
        self.fake_time.side_effect = incr

        def incr_gmtime(*seconds):
            if seconds:
                assert len(seconds) == 1
                now = seconds[0]
            else:
                now = incr()
            return _real_gmtime(now)
        self.fake_gmtime.side_effect = incr_gmtime

    def install_fakes(self):
        time.time = self.fake_time
        time.gmtime = self.fake_gmtime

    __enter__ = install_fakes

    def close(self, *args):
        time.time = _real_time
        time.gmtime = _real_gmtime

    __exit__ = close

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper



def time_monotonically_increases(func_or_granularity):
    """
    Decorate a unittest method with this function to cause the value
    of :func:`time.time` (and :func:`time.gmtime`) to monotonically
    increase by one each time it is called. This ensures things like
    last modified dates always increase.

    We make three guarantees about the value of :func:`time.time`
    returned while the decorated function is running:

        1. It is always *at least* the value of the *real*
           :func:`time.time`;

        2. Each call returns a value greater than the previous call;

        3. Those two constraints hold across different invocations of
           functions decorated.

    This decorator can be applied to a method in a test case::

        class TestThing(unittest.TestCase)
            @time_monotonically_increases
            def test_method(self):
              t = time.time()
               ...

    It can also be applied to a bare function taking any number of
    arguments::

        @time_monotonically_increases
        def utility_function(a, b, c=1):
           t = time.time()
           ...

    By default, the time will be incremented in 1.0 second intervals.
    You can specify a particular granularity as an argument; this is
    useful to keep from running too far ahead of the real clock::

        @time_monotonically_increases(0.1)
        def smaller_increment():
            t1 = time.time()
            t2 = time.time()
            assrt t2 == t1 + 0.1

    .. seealso:: `nti.testing.time.reset_monotonic_time`

    .. versionchanged:: 2.1
       Add support for ``time.gmtime``.
    .. versionchanged:: 2.1
       Now thread safe.
    .. versionchanged:: 2.0
       The decorated function returns whatever the passed function returns.
    .. versionchanged:: 2.0
       Properly handle more than one argument to the underlying function.
    .. versionchanged:: 2.0
       Ensure that the values returned are at least the real time. Previously
       they were integers starting at 0.
    .. versionchanged:: 2.0
       Ensure that the values returned are increasing even across different
       invocations of a decorated function or different decorated functions. Previously
       different functions would return the same sequence.
    .. versionchanged:: 2.0
       Allow specifying the granularity of clock increments. Keep at
       1.0 seconds for backwards compatibility by default.
    """
    if isinstance(func_or_granularity, (six.integer_types, float)):
        # We're being used as a factory.
        wrapper_factory = _TimeWrapper(func_or_granularity)
        return wrapper_factory

    # We're being used bare
    wrapper_factory = _TimeWrapper()
    return wrapper_factory(func_or_granularity)


def reset_monotonic_time(value=0.0):
    """
    Make the monotonic clock return the real time on its next
    call.

    .. versionadded:: 2.0
    """

    global _current_time # pylint:disable=global-statement
    _current_time = value


class MonotonicallyIncreasingTimeLayerMixin(object):
    """
    A helper for layers that need time to increase monotonically.

    You can either mix this in to a layer object, or instantiate it
    and call the methods directly.

    .. versionadded:: 2.2
    """

    def __init__(self, granularity=1.0):
        self.time_manager = _TimeWrapper(granularity)

    def testSetUp(self):
        self.time_manager.install_fakes()

    def testTearDown(self):
        self.time_manager.close()
        reset_monotonic_time()
