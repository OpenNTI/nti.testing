#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for matchers.py.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import unittest

from hamcrest import assert_that
from hamcrest import calling

from hamcrest import raises

from nti.testing import matchers

__docformat__ = "restructuredtext en"


# pylint:disable=inherit-non-class,redundant-u-string-prefix


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

            def method(): # pylint:disable=no-method-argument
                "method"

        @interface.implementer(IThing)
        class Thing(object):
            thing = 1

            def method(self):
                raise AssertionError("Not called")

        assert_that(Thing(), matchers.verifiably_provides(IThing, IThing))
        # We have a nice multi-line error message, but we can only match one line at a time
        for line in (
                'verifiably providing .*IThing',
                'Using class.*has failed to implement',
                'Does not declaratively implement',
                'thing attribute was not provided',
                r'method\(\) attribute was not provided',
        ):
            assert_that(calling(assert_that).with_args(self, matchers.verifiably_provides(IThing)),
                        raises(AssertionError, line))

        broken_thing = Thing()
        broken_thing.method = None
        assert_that(calling(assert_that).with_args(broken_thing,
                                                   matchers.verifiably_provides(IThing)),
                    raises(AssertionError, r"The contract of.*method\(\) is violated"))

        del Thing.thing
        assert_that(calling(assert_that).with_args(Thing(), matchers.verifiably_provides(IThing)),
                    raises(AssertionError, "thing attribute was not provided"))

    def test_validly_provides(self):

        from zope import interface
        from zope.schema import Int

        class IThing(interface.Interface):
            thing = Int()

        @interface.implementer(IThing)
        class Thing(object):
            thing = 1

        assert_that(Thing(), matchers.validly_provides(IThing, IThing))
        # We have a nice multi-line error message, but we can only match one line at a time
        for line in (
                'verifiably providing .*IThing.*validly providing.*IThing',
                'Using class.*has failed to implement',
                'Does not declaratively implement',
                'thing attribute was not provided'
        ):
            assert_that(calling(assert_that).with_args(self, matchers.validly_provides(IThing)),
                        raises(AssertionError, line))

        broken_thing = Thing()
        broken_thing.thing = "not an int"

        assert_that(calling(assert_that).with_args(broken_thing, matchers.validly_provides(IThing)),
                    raises(AssertionError, "has attribute"))

    def test_validated_by(self):
        from zope.schema import Int
        from zope.schema.interfaces import WrongType

        assert_that(1, matchers.validated_by(Int()))
        assert_that('', matchers.not_validated_by(Int()))
        with self.assertRaises(WrongType):
            assert_that('', matchers.not_validated_by(Int(), invalid=NameError))
        assert_that(calling(assert_that).with_args('', matchers.validated_by(Int())),
                    raises(AssertionError, "failed to validate"))

    def test_validated_by_defaults_to_Invalid(self):
        from zope.interface.exceptions import Invalid
        class Validator(object):
            def validate(self, o):
                raise o

        validator = Validator()
        class Arbitrary(Exception):
            pass

        with self.assertRaises(Arbitrary):
            assert_that(Arbitrary(), matchers.validated_by(validator))

        assert_that(calling(assert_that).with_args(Invalid(),
                                                   matchers.validated_by(validator)),
                    raises(AssertionError, "failed to validate"))

        assert_that(calling(assert_that).with_args(Arbitrary,
                                                   matchers.validated_by(validator,
                                                                         invalid=Exception)),
                    raises(AssertionError, "failed to validate"))


    def test_dict(self):

        d = matchers.TypeCheckedDict(key_class=int, notify=lambda k, v: None)

        d[1] = 'abc'

        assert_that(calling(d.__setitem__).with_args('abc', 'def'),
                    raises(AssertionError, "instance of int"))

    def test_in_context(self):
        # pylint:disable=attribute-defined-outside-init
        class Thing(object):
            def __init__(self, name, parent=None):
                self.__name__ = name
                if parent:
                    self.__parent__ = parent
            def __repr__(self):
                return '<Thing %s>' % (self.__name__,)

        parent = Thing('parent')
        child = Thing('child', parent)
        sibling = Thing('sibling', parent)

        assert_that(child, matchers.aq_inContextOf(parent))

        with self.assertRaises(AssertionError) as exc:
            assert_that(parent, matchers.aq_inContextOf('ROOT'))
        ex = str(exc.exception)
        del exc
        self.assertIn('object in context of', ex)
        self.assertIn('<Thing parent> was not in the context of \'ROOT\'\n; its lineage is []', ex)

        with self.assertRaises(AssertionError) as exc:
            assert_that(sibling, matchers.aq_inContextOf(child))
        ex = str(exc.exception)
        del exc
        self.assertIn('object in context of', ex)
        self.assertIn('<Thing sibling> was not in the context of <Thing child>', ex)
        self.assertIn('its lineage is [<Thing parent>]', ex)


        # fake wrapper
        child.aq_inContextOf = lambda thing: thing == child.__parent__
        assert_that(child, matchers.aq_inContextOf(parent))

    def test_in_context_no_Acquisition(self):
        # pylint:disable=protected-access
        orig_in_context = matchers._aq_inContextOf
        matchers._aq_inContextOf = matchers._aq_inContextOf_NotImplemented
        try:
            with self.assertRaises(AssertionError) as exc:
                assert_that(self, matchers.aq_inContextOf(self))

        finally:
            matchers._aq_inContextOf = orig_in_context

        ex = str(exc.exception)
        del exc
        self.assertIn('object in context of', ex)
        self.assertIn('Acquisition was not installed', ex)
