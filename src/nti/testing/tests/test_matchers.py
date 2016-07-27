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

    def test_provides(self):

        from zope import interface

        class IThing(interface.Interface):
            pass

        @interface.implementer(IThing)
        class Thing(object):
            pass

        assert_that(Thing(), matchers.provides(IThing))
        assert_that(calling(assert_that).with_args(self, matchers.provides(IThing)),
                    raises(AssertionError, "object providing"))

    def test_implements(self):

        from zope import interface

        class IThing(interface.Interface):
            pass

        @interface.implementer(IThing)
        class Thing(object):
            pass

        assert_that(Thing, matchers.implements(IThing))
        assert_that(calling(assert_that).with_args(self, matchers.implements(IThing)),
                    raises(AssertionError, "object implementing"))


    def test_verifiably_provides(self):

        from zope import interface

        class IThing(interface.Interface):
            thing = interface.Attribute("thing")

            def method():
                "method"

        @interface.implementer(IThing)
        class Thing(object):
            thing = 1

            def method(self):
                return 1

        assert_that(Thing(), matchers.verifiably_provides(IThing, IThing))
        assert_that(calling(assert_that).with_args(self, matchers.verifiably_provides(IThing)),
                    raises(AssertionError, "does not implement"))

        broken_thing = Thing()
        broken_thing.method = None
        assert_that(calling(assert_that).with_args(broken_thing, matchers.verifiably_provides(IThing)),
                    raises(AssertionError, "violates its contract"))

        del Thing.thing
        assert_that(calling(assert_that).with_args(Thing(), matchers.verifiably_provides(IThing)),
                    raises(AssertionError, "failed to provide attribute"))

    def test_validly_provides(self):

        from zope import interface
        from zope.schema import Int

        class IThing(interface.Interface):
            thing = Int()

        @interface.implementer(IThing)
        class Thing(object):
            thing = 1

        assert_that(Thing(), matchers.validly_provides(IThing, IThing))
        assert_that(calling(assert_that).with_args(self, matchers.validly_provides(IThing)),
                    raises(AssertionError, "does not implement"))

        broken_thing = Thing()
        broken_thing.thing = "not an int"

        assert_that(calling(assert_that).with_args(broken_thing, matchers.validly_provides(IThing)),
                    raises(AssertionError, "has attribute"))

    def test_validated_by(self):
        from zope.schema import Int

        assert_that(1, matchers.validated_by(Int()))
        assert_that('', matchers.not_validated_by(Int()))
        assert_that(calling(assert_that).with_args('', matchers.validated_by(Int())),
                    raises(AssertionError, "failed to validate"))

    def test_dict(self):

        d = matchers.TypeCheckedDict(key_class=int, notify=lambda k, v: None)

        d[1] = 'abc'

        assert_that(calling(d.__setitem__).with_args('abc', 'def'),
                    raises(AssertionError, "instance of int"))

    def test_in_context(self):

        class Thing(object):
            pass

        parent = Thing()
        child = Thing()
        child.__parent__ = parent

        assert_that(child, matchers.aq_inContextOf(parent))
        assert_that(calling(assert_that).with_args(parent, matchers.aq_inContextOf(self)),
                    raises(AssertionError, "object in context of"))

        # fake wrapper
        child.aq_inContextOf = lambda thing: thing == child.__parent__
        assert_that(child, matchers.aq_inContextOf(parent))
