#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test support for working with clocks and time.

$Id: time.py 28485 2013-12-24 18:47:17Z jason.madden $
"""

from __future__ import print_function, unicode_literals, absolute_import, division

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import functools
import fudge

def time_monotonically_increases(func):
    """
    Decorate a unittest method with this function to cause the value of :func:`time.time` to
    monotonically increase by one each time it is called. This ensures things like
    last modified dates always increase.
    """
    @fudge.patch('time.time')
    @functools.wraps(func)
    def wrapper( *args, **kwargs ):
        if isinstance(args[0], fudge.Fake):
            fake_time = args[0]
            args = args[1:]
        else:
            # self, fake_time
            assert isinstance(args[1], fudge.Fake)
            fake_time = args[1]
            args = list(args)
            del args[1]

        # make time monotonically increasing
        i = [0]
        def incr():
            i[0] += 1
            return i[0]
        fake_time.is_callable()
        fake_time._callable.call_replacement = incr
        fake_time()
        func( *args, **kwargs )
    return wrapper
