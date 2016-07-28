=============
 nti.testing
=============

Support for writing tests, particularly in a Zope3/ZTK environment,
using either nose2 or zope.testing.

Installation
============

nti.testing can be installed using pip, either from the git repository
or from PyPI::

  pip install nti.testing


PyHamcrest
==========

nti.testing provides a group of `PyHamcrest`_ matchers. There are both
general-purpose matchers and matchers that are of use to users of
`zope.interface`_ and `zope.schema`_.


.. _PyHamcrest: https://pyhamcrest.readthedocs.io/en/latest/
.. _zope.interface: https://pypi.python.org/pypi/zope.interface
.. _zope.schema: https://pypi.python.org/pypi/zope.schema


Matchers can be imported from the ``nti.testing.matchers`` module.

Basic Matchers
--------------

``is_true`` and ``is_false`` check the ``bool`` value of a supplied
object (we're using literals for explanation purposes, but it
obviously makes more sense, and reads better, when the matched object
is a variable, often of a more complex type)::

   >>> from hamcrest import assert_that, is_
   >>> from nti.testing.matchers import is_true, is_false
   >>> assert_that("Hi", is_true())
   >>> assert_that(0, is_false())

Interface Matchers
------------------

Next we come to matchers that support basic use of ``zope.interface``.

We can check that an object provides an interface and that a factory
implements it::

   >>> from zope.interface import Interface, Attribute, implementer
   >>> class IThing1(Interface):
   ...     pass
   >>> class IThing2(Interface):
   ...     pass
   >>> class IThings(IThing1, IThing2):
   ...     got_that_thing_i_sent_you = Attribute("Did you get that thing?")
   >>> @implementer(IThings)
   ... class Thing(object):
   ...     pass

   >>> from nti.testing.matchers import provides, implements
   >>> assert_that(Thing(), provides(IThings))
   >>> assert_that(Thing, implements(IThings))

The attentive reader will have noticed that ``IThings`` defines an
attribute that our implementation doesn't *actually* provide. This is
where the next stricter check comes in. ``verifiably_provides`` uses
the interface machinery to determine that all attributes and methods
specified by the interface are present as described::


  >>> from nti.testing.matchers import verifiably_provides
  >>> assert_that(Thing(), verifiably_provides(IThing2, IThing1))
  >>> assert_that(Thing(), verifiably_provides(IThings))
  Traceback (most recent call last):
  ...
  AssertionError:...
  Expected: object verifiably providing IThings
       but: <class 'Thing'> failed to provide attribute "got_that_thing_i_sent_you" from IThings
  <BLANKLINE>

``zope.interface`` can only check whether or not an attribute or
method is present. To place (arbitrary) tighter constraints on the
values of the attributes, we can step up to ``zope.schema`` and the
``validly_provides`` matcher::

  >>> from zope.schema import Bool
  >>> class IBoolThings(IThing1, IThing2):
  ...     got_that_thing_i_sent_you = Bool()
  >>> @implementer(IBoolThings)
  ... class BoolThing(object):
  ...     pass

``validly_provides`` is a superset of ``verifiably_provides``::

  >>> from nti.testing.matchers import validly_provides
  >>> assert_that(BoolThing(), validly_provides(IThing1, IThing2))
  >>> assert_that(BoolThing(), validly_provides(IBoolThings))
  Traceback (most recent call last):
  ...
  AssertionError:...
  Expected: (object verifiably providing IBoolThings and object validly providing <InterfaceClass ....IBoolThings>)
       but: object verifiably providing IBoolThings <class 'BoolThing'> failed to provide attribute "got_that_thing_i_sent_you" from IBoolThings
  <BLANKLINE>

For finer grained control, we can compare data against schema fields::

  >>> from nti.testing.matchers import validated_by, not_validated_by
  >>> field = IBoolThings.get('got_that_thing_i_sent_you')
  >>> assert_that(True, is_(validated_by(field)))
  >>> assert_that(None, is_(not_validated_by(field)))

Parent/Child Relationships
--------------------------

The ``aq_inContextOf`` matcher uses the concepts from Acquisition to
check parent/child relationships::

  >>> from nti.testing.matchers import aq_inContextOf
  >>> class Parent(object):
  ...     pass
  >>> class Child(object):
  ...     __parent__ = None
  >>> parent = Parent()
  >>> child = Child()
  >>> child.__parent__ = parent

  >>> assert_that(child, aq_inContextOf(parent))

Test Fixtures
=============

Support for test fixtures can be found in ``nti.testing.base`` and
``nti.testing.layers``. The ``base`` package includes fully-fleshed
out base classes for direct use, while the ``layers`` package includes
mixins that can be used to construct your own test layers.

The ``base`` package makes a distinction between "normal" and "shared"
fixtures. Normal fixtures are those that are used for a single test
case. They are established via ``setUp`` and torn down via
``tearDown``.

In contrast, shared fixtures are expected to endure for the duration
of all the tests in the class or all the tests in the layer. These are
best used when the fixture is expensive to create. Anything that
extends from ``base.AbstractSharedTestBase`` creates a shared fixture.
Through the magic of metaclasses, such a subclass can also be assigned
as the ``layer`` property of another class to be used as a test layer
that can be shared across more than one class.

The most important bases are ``base.ConfiguringTestBase`` and
``base.SharedConfiguringTestBase``. These are both fixtures for
configuring ZCML, either from existing packages or complete file
paths. To use these, subclass them and define class attributes
``set_up_packages`` and (if necessary) ``features``::

  >>> from nti.testing.base import ConfiguringTestBase
  >>> import zope.security
  >>> class MyConfiguringTest(ConfiguringTestBase):
  ...     set_up_packages = (
  ...         'zope.component', # the default configuration by name
  ...          # a named file in a named package
  ...          ('ftesting.zcml', 'zope.traversing.tests'),
  ...          # an imported module
  ...          zope.security,
  ...          # Our own package; in a test, this will mean the parent
  ...          # package
  ...          ".")

We would then proceed to write our test methods. The packages that we
specified will be set up and torn down around every test method. In
addition, the ``zope.testing`` cleanup functions will also run around
every test method.
