=========
 Changes
=========


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
