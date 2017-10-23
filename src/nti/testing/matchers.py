#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hamcrest matchers for testing.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import collections
import pprint

import six
from zope import interface
from zope.interface.exceptions import BrokenImplementation
from zope.interface.exceptions import BrokenMethodImplementation
from zope.interface.exceptions import DoesNotImplement
from zope.interface.exceptions import Invalid
from zope.interface.verify import verifyObject
from zope.schema import ValidationError
from zope.schema import getValidationErrors


import hamcrest
from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import is_
from hamcrest import is_not
from hamcrest.core.base_description import BaseDescription
from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.library.collection.is_empty import empty

__docformat__ = "restructuredtext en"


has_length = has_length # Export
is_empty = empty # bwc

has_attr = hamcrest.library.has_property

class BoolMatcher(BaseMatcher):
    def __init__(self, value):
        super(BoolMatcher, self).__init__()
        self.value = value

    def _matches(self, item):
        return bool(item) == self.value

    def describe_to(self, description):
        description.append_text('object with bool() value ').append(str(self.value))

    def __repr__(self):
        return 'object with bool() value ' + str(self.value)

def is_true():
    """
    Matches an object with a true boolean value.
    """
    return BoolMatcher(True)

def is_false():
    """
    Matches an object with a false boolean value.
    """
    return BoolMatcher(False)

class Provides(BaseMatcher):

    def __init__(self, iface):
        super(Provides, self).__init__()
        self.iface = iface

    def _matches(self, item):
        return self.iface.providedBy(item)

    def describe_to(self, description):
        description.append_text('object providing') \
                                 .append(str(self.iface))

    def __repr__(self):
        return 'object providing' + str(self.iface)

def provides(iface):
    """
    Matches an object that provides the given interface.
    """
    return Provides(iface)


class VerifyProvides(BaseMatcher):

    def __init__(self, iface):
        super(VerifyProvides, self).__init__()
        self.iface = iface

    def _matches(self, item):
        try:
            verifyObject(self.iface, item)
        except Invalid:
            return False
        else:
            return True

    def describe_to(self, description):
        description.append_text('object verifiably providing ').append(str(self.iface.__name__))

    def describe_mismatch(self, item, mismatch_description):
        x = None
        md = mismatch_description
        md.append_text(str(type(item)))
        try:
            verifyObject(self.iface, item)
        except BrokenMethodImplementation as x:
            md.append_text(str(x).replace('\n', ''))
        except BrokenImplementation as x:
            md.append_text(' failed to provide attribute "')
            md.append_text(x.name).append_text('"').append_text(' from ')
            md.append_text(self.iface[x.name].interface.getName())
        except DoesNotImplement as x:
            md.append_text(" does not implement the interface; it does implement ")
            md.append_text(str(list(interface.providedBy(item))))
        except Invalid as x: # pragma: no cover
            md.append_text(str(x).replace('\n', ''))


def verifiably_provides(*ifaces):
    """
    Matches if the object verifiably provides the correct interface(s),
    as defined by ``zope.interface``. This means having the right attributes
    and methods with the right signatures.

    .. note:: This does **not** test schema compliance. For that
        (stricter) test, see :func:`validly_provides`.
    """
    if len(ifaces) == 1:
        return VerifyProvides(ifaces[0])

    return hamcrest.all_of(*[VerifyProvides(x) for x in ifaces])

class VerifyValidSchema(BaseMatcher):
    def __init__(self, iface):
        super(VerifyValidSchema, self).__init__()
        self.iface = iface

    def _matches(self, item):
        errors = getValidationErrors(self.iface, item)
        return not errors

    def describe_to(self, description):
        description.append_text('object validly providing ').append(str(self.iface))

    def describe_mismatch(self, item, mismatch_description):
        x = None
        md = mismatch_description
        md.append_text(str(type(item)))

        errors = getValidationErrors(self.iface, item)

        for attr, exc in errors:
            try:
                raise exc
            except ValidationError:
                md.append_text(' has attribute "')
                md.append_text(attr)
                md.append_text('" with error "')
                md.append_text(repr(exc))
                md.append_text('"\n\t ')
            except Invalid as x: # pragma: no cover
                md.append_text(str(x).replace('\n', ''))

def validly_provides(*ifaces):
    """
    Matches if the object verifiably and validly provides the given
    schema (interface(s)).

    Verification is done with zope.interface and
    :func:`verifiably_provides`, while validation is done with
    zope.schema's ``getValidationErrors`` function.
    """
    if len(ifaces) == 1:
        the_schema = ifaces[0]
        return hamcrest.all_of(verifiably_provides(the_schema), VerifyValidSchema(the_schema))

    prov = verifiably_provides(*ifaces)
    valid = [VerifyValidSchema(x) for x in ifaces]

    return hamcrest.all_of(prov, *valid)

class Implements(BaseMatcher):

    def __init__(self, iface):
        super(Implements, self).__init__()
        self.iface = iface

    def _matches(self, item):
        return self.iface.implementedBy(item)

    def describe_to(self, description):
        description.append_text('object implementing') \
                                 .append(self.iface)

def implements(iface):
    """
    Matches if the object implements (is a factory for) the given
    interface.
    """
    return Implements(iface)


class ValidatedBy(BaseMatcher):

    def __init__(self, field, invalid=Invalid):
        super(ValidatedBy, self).__init__()
        self.field = field
        self.invalid = invalid

    def _matches(self, item):
        try:
            self.field.validate(item)
        except self.invalid:
            return False
        else:
            return True

    def describe_to(self, description):
        description.append_text('data validated by').append(repr(self.field))

    def describe_mismatch(self, item, mismatch_description):
        ex = None
        try:
            self.field.validate(item)
        except self.invalid as e:
            ex = e

        mismatch_description.append_text(repr(self.field))
        mismatch_description.append_text(' failed to validate ')
        mismatch_description.append_text(repr(item))
        mismatch_description.append_text(' with ')
        mismatch_description.append_text(repr(ex))

def validated_by(field, invalid=Invalid):
    """
    Matches if the data is validated by the given ``IField``.

    :keyword exception invalid: The types of exceptions that are considered
        invalid. Anything other than this is allowed to be raised.

    .. versionchanged:: 2.0.1
       Add ``invalid`` and change it from ``Exception`` to
       :class:`zope.interface.exceptions.Invalid`
    """
    return ValidatedBy(field, invalid=invalid)

def not_validated_by(field, invalid=Invalid):
    """
    Matches if the data is NOT validated by the given IField.

    :keyword exception invalid: The types of exceptions that are considered
        invalid. Anything other than this is allowed to be raised.

    .. versionchanged:: 2.0.1
       Add ``invalid`` and change it from ``Exception`` to
       :class:`zope.interface.exceptions.Invalid`
    """
    return is_not(validated_by(field, invalid=invalid))


try:
    from Acquisition import aq_inContextOf as _aq_inContextOf
except ImportError: # pragma: no cover
    # acquisition not installed
    def _aq_inContextOf(child, parent):
        return False

class AqInContextOf(BaseMatcher):
    def __init__(self, parent):
        super(AqInContextOf, self).__init__()
        self.parent = parent

    def _matches(self, item):
        if hasattr(item, 'aq_inContextOf'): # wrappers
            return item.aq_inContextOf(self.parent)
        return _aq_inContextOf(item, self.parent) # not wrapped, but maybe __parent__ chain

    def describe_to(self, description):
        description.append_text('object in context of').append(repr(self.parent))

def aq_inContextOf(parent):
    """
    Matches if the data is in the acquisition context of
    the given object.
    """
    return AqInContextOf(parent)

# Patch hamcrest for better descriptions of maps (json data)
# and sequences
if six.PY3: # pragma: no cover
    from io import StringIO
else:
    from cStringIO import StringIO

_orig_append_description_of = BaseDescription.append_description_of
def _append_description_of_map(self, value):
    if not hasattr(value, 'describe_to'):
        if isinstance(value, (collections.Mapping, collections.Sequence)):
            sio = StringIO()
            pprint.pprint(value, sio)
            self.append(sio.getvalue())
            return self
    return _orig_append_description_of(self, value)

BaseDescription.append_description_of = _append_description_of_map


class TypeCheckedDict(dict):
    "A dictionary that ensures keys and values are of the required type when set"

    def __init__(self, key_class=object, val_class=object, notify=None):
        dict.__init__(self)
        self.key_class = key_class
        self.val_class = val_class
        self.notify = notify

    def __setitem__(self, key, val):
        assert_that(key, is_(self.key_class))
        assert_that(val, is_(self.val_class))
        dict.__setitem__(self, key, val)
        if self.notify:
            self.notify(key, val)
