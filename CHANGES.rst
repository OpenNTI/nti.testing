=========
 Changes
=========

3.1.0 (2021-09-08)
==================

- Add support for Python 3.9.

- Drop support for Python 3.5.

- Add the module alias ``nti.testing.mock``, which is either the
  standard library ``unittest.mock``, or the backport ``mock``. This
  allows easy imports when backwards compatibility matters.

- Make ``mock``, ``mock.Mock`` and various other API attributes,
  like ``is_true``, available directly from the ``nti.testing`` namespace.

3.0.0 (2020-06-16)
==================

- Add support for Python 3.8.

- Require zope.interface 5.1. This lets the interface matchers produce
  much more informative error messages.

- Add ``nti.testing.zodb`` with helpers for dealing with ZODB. This
  makes ZODB 5.6 or above a required dependency.

2.2.1 (2019-09-10)
==================

- Make transaction cleanup safer if the default transaction manager
  has been made explicit.

  Also, reset the default transaction manager to implicit.

  See `issue 17 <https://github.com/NextThought/nti.testing/issues/17>`_.


2.2.0 (2018-08-24)
==================

- Add support for Python 3.7.

- Make ``time_monotonically_increases`` also handle ``time.gmtime``
  and add a helper for using it in layers.


2.1.0 (2017-10-23)
==================

- Make ``Acquisition`` an optional dependency. If it is not installed,
  the ``aq_inContextOf`` matcher will always return False.

- Remove dependency on ``fudge``. Instead, we now use ``unittest.mock`` on
  Python 3, or its backport ``mock`` on Python 2. See `issue 11
  <https://github.com/NextThought/nti.testing/issues/11>`_.

- Refactor ZCML configuration support to share more code and
  documentation. See `issue 10
  <https://github.com/NextThought/nti.testing/issues/10>`_.

- The layer ``ConfiguringLayerMixin`` and the base class
  ``SharedConfiguringTestBase`` now default to running
  configuration in the package the subclass is defined in, just as
  subclasses of ``ConfiguringTestBase`` did.

2.0.1 (2017-10-18)
==================

- The validation matchers (``validated_by`` and ``not_validated_by``)
  now consider it a failure (by default) if the validate method raises
  anything other than ``zope.interface.exceptions.Invalid`` (which
  includes the ``zope.schema`` exceptions like ``WrongType``).
  Previously, they accepted any exception as meaning the object was
  invalid, but this could hide bugs in the actual validation method
  itself. You can supply the ``invalid`` argument to the matchers to
  loosen or tighten this as desired. (Giving ``invalid=Exception``
  will restore the old behaviour.)
  See `issue 7 <https://github.com/NextThought/nti.testing/issues/7>`_.


2.0.0 (2017-04-12)
==================

- Add support for Python 3.6.

- Remove ``unicode_literals``.

- Substantially rework ``time_monotonically_increases`` for greater
  safety. Fixes `issue 5 <https://github.com/NextThought/nti.testing/issues/5>`_.

1.0.0 (2016-07-28)
==================

- Add Python 3 support.

- Initial PyPI release.
