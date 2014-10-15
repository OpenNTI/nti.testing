#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hamcrest matchers for testing.

$Id: matchers.py 37276 2014-04-16 13:53:09Z jason.madden $
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest.core.base_matcher import BaseMatcher
import hamcrest

# Increase verbosity of deprecations

class BoolMatcher(BaseMatcher):
	def __init__( self, value ):
		super(BoolMatcher,self).__init__()
		self.value = value

	def _matches( self, item ):
		return bool(item) == self.value

	def describe_to( self, description ):
		description.append_text( 'object with bool() value ' ).append( str(self.value) )

	def __repr__( self ):
		return 'object with bool() value ' + str(self.value)

def is_true():
	"""
	Matches an object with the bool value of True.
	"""
	return BoolMatcher(True)

def is_false():
	"""
	Matches an object with the bool() value of False.
	"""
	return BoolMatcher(False)

class Provides(BaseMatcher):

	def __init__( self, iface ):
		super(Provides,self).__init__( )
		self.iface = iface

	def _matches( self, item ):
		return self.iface.providedBy( item )

	def describe_to( self, description ):
		description.append_text( 'object providing') \
								 .append( str(self.iface) )

	def __repr__( self ):
		return 'object providing' + str(self.iface)

def provides( iface ):
	return Provides( iface )

from zope import interface
from zope.interface.verify import verifyObject
from zope.interface.exceptions import Invalid, BrokenImplementation, BrokenMethodImplementation, DoesNotImplement
from zope.schema import getValidationErrors, ValidationError
class VerifyProvides(BaseMatcher):

	def __init__( self, iface ):
		super(VerifyProvides,self).__init__()
		self.iface = iface

	def _matches( self, item ):
		try:
			verifyObject(self.iface, item )
		except Invalid:
			return False
		else:
			return True

	def describe_to( self, description ):
		description.append_text( 'object verifiably providing ' ).append( str(self.iface.__name__) )

	def describe_mismatch( self, item, mismatch_description ):
		x = None
		mismatch_description.append_text( str(type(item))  )
		try:
			verifyObject( self.iface, item )
		except BrokenMethodImplementation as x:
			mismatch_description.append_text( str(x).replace( '\n', '' ) )
		except BrokenImplementation as x:
			mismatch_description.append_text( ' failed to provide attribute "').append_text( x.name ).append_text( '"' ).append_text( ' from ' ).append_text( self.iface[x.name].interface.getName() )
		except DoesNotImplement as x:
			mismatch_description.append_text( " does not implement the interface; it does implement " ).append_text( str(list(interface.providedBy(item))) )
		except Invalid as x:
			#mismatch_description.append_description_of( item ).append_text( ' has no attr ').append_text( self.attr )
			mismatch_description.append_text( str(x).replace( '\n', '' ) )


def verifiably_provides(*ifaces):
	"Matches if the object provides the correct interface. NOTE: This does NOT test schema compliance."
	if len(ifaces) == 1:
		return VerifyProvides(ifaces[0])

	return hamcrest.all_of( *[VerifyProvides(x) for x in ifaces] )

class VerifyValidSchema(BaseMatcher):
	def __init__( self, iface ):
		super(VerifyValidSchema,self).__init__()
		self.iface = iface

	def _matches( self, item ):
		errors = getValidationErrors( self.iface, item )
		return not errors

	def describe_to( self, description ):
		description.append_text( 'object validly providing ' ).append( str(self.iface) )

	def describe_mismatch( self, item, mismatch_description ):
		x = None
		mismatch_description.append_text( str(type(item))  )


		errors = getValidationErrors( self.iface, item )

		for attr, exc in errors:
			try:
				raise exc
			except ValidationError:
				mismatch_description.append_text( ' has attribute "').append_text( attr ).append_text( '" with error "' ).append_text( repr(exc) ).append_text( '"\n\t ' )
			except Invalid as x:
				#mismatch_description.append_description_of( item ).append_text( ' has no attr ').append_text( self.attr )
				mismatch_description.append_text( str(x).replace( '\n', '' ) )

def validly_provides(*ifaces):
	"Matches if the object verifiably and validly provides the given schema (interface)"
	if len(ifaces) == 1:
		the_schema = ifaces[0]
		return hamcrest.all_of( verifiably_provides( the_schema ), VerifyValidSchema(the_schema) )

	prov = verifiably_provides(*ifaces)
	valid = [VerifyValidSchema(x) for x in ifaces]

	return hamcrest.all_of( prov, *valid )

class Implements(BaseMatcher):

	def __init__( self, iface ):
		super(Implements,self).__init__( )
		self.iface = iface

	def _matches( self, item ):
		return self.iface.implementedBy( item )

	def describe_to( self, description ):
		description.append_text( 'object implementing') \
								 .append( self.iface )

def implements( iface ):
	return Implements( iface )


class ValidatedBy(BaseMatcher):

	def __init__( self, field ):
		super(ValidatedBy,self).__init__()
		self.field = field

	def _matches( self, data ):
		try:
			self.field.validate( data )
		except Exception:
			return False
		else:
			return True

	def describe_to( self, description ):
		description.append_text( 'data validated by' ).append( repr(self.field) )

	def describe_mismatch( self, item, mismatch_description ):
		ex = None
		try:
			self.field.validate( item )
		except Exception as e:
			ex = e

		mismatch_description.append_text( repr( self.field ) ).append_text( ' failed to validate ' ).append_text( repr( item ) ).append_text( ' with ' ).append_text( repr( ex ) )

try:
	from Acquisition import aq_inContextOf as _aq_inContextOf
except ImportError:
	# acquisition not installed
	def _aq_inContextOf( child, parent ):
		return False
class AqInContextOf(BaseMatcher):
	def __init__( self, parent ):
		super(AqInContextOf,self).__init__()
		self.parent = parent

	def _matches( self, child ):
		if hasattr( child, 'aq_inContextOf' ): # wrappers
			return child.aq_inContextOf( self.parent )
		return _aq_inContextOf( child, self.parent ) # not wrapped, but maybe __parent__ chain

	def describe_to( self, description ):
		description.append_text( 'object in context of').append( repr( self.parent ) )

def aq_inContextOf( parent ):
	"""
	Matches if the data is in the acquisition context of
	the given object.
	"""
	return AqInContextOf( parent )

def validated_by( field ):
	""" Matches if the data is validated by the given IField """
	return ValidatedBy( field )
from hamcrest import is_not
def not_validated_by( field ):
	""" Matches if the data is NOT validated by the given IField. """
	return is_not( validated_by( field ) )
from hamcrest import has_length
has_length = has_length
from hamcrest.library.collection.is_empty import empty
is_empty = empty # bwc

has_attr = hamcrest.library.has_property

# Patch hamcrest for better descriptions of maps (json data)
from hamcrest.core.base_description import BaseDescription
from cStringIO import StringIO
import collections
import pprint
_orig_append_description_of = BaseDescription.append_description_of
def _append_description_of_map(self, value):
	if not hasattr( value, 'describe_to' ):
		if (isinstance( value, collections.Mapping ) or isinstance(value,collections.Sequence)):
			sio = StringIO()
			pprint.pprint( value, sio )
			self.append( sio.getvalue() )
			return self
	return _orig_append_description_of( self, value )

BaseDescription.append_description_of = _append_description_of_map

from hamcrest import assert_that
from hamcrest import is_

class TypeCheckedDict(dict):
	"A dictionary that ensures keys and values are of the required type when set"

	def __init__( self, key_class=object, val_class=object, notify=None ):
		dict.__init__( self )
		self.key_class = key_class
		self.val_class = val_class
		self.notify = notify

	def __setitem__( self, key, val ):
		assert_that( key, is_( self.key_class ) )
		assert_that( val, is_( self.val_class ) )
		dict.__setitem__( self, key, val )
		if self.notify:
			self.notify( key, val )
