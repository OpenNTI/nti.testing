from __future__ import print_function, division, absolute_import

import unittest
import doctest
import os
import re
from zope.testing import renormalizing


class TestImport(unittest.TestCase):
    def test_import(self):
        for name in ('base', 'layers', 'matchers', 'time'):
            __import__('nti.testing.' + name)

checker = renormalizing.RENormalizing([
    # Python 3 bytes add a "b".
    (re.compile(r'b(".*?")'), r"\1"),
    (re.compile(r"b('.*?')"), r"\1"),
    # Windows shows result from 'u64' as long?
    (re.compile(r"(\d+)L"), r"\1"),
    # Python 3 adds module name to exceptions.
    (re.compile("ZODB.POSException.ConflictError"), r"ConflictError"),
    (re.compile("ZODB.POSException.POSKeyError"), r"POSKeyError"),
    (re.compile("ZODB.POSException.ReadConflictError"), r"ReadConflictError"),
    (re.compile("ZODB.POSException.Unsupported"), r"Unsupported"),
    (re.compile("ZODB.interfaces.BlobError"), r"BlobError"),
    # XXX document me
    (re.compile(r'\%(sep)s\%(sep)s' % dict(sep=os.path.sep)), '/'),
    (re.compile(r'\%(sep)s' % dict(sep=os.path.sep)), '/'),
])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestImport))
    suite.addTest(doctest.DocFileSuite(
        'test_component_cleanup_broken.txt'))

    if os.path.exists('../../../../README.rst'):
        suite.addTest(doctest.DocFileSuite(
            '../../../../README.rst',
            optionflags=doctest.ELLIPSIS,
            checker=checker,
        ))
    elif os.path.exists('README.rst'):
        # tox
        suite.addTest(doctest.DocFileSuite(
            os.path.abspath("README.rst"),
            module_relative=False,
            optionflags=doctest.ELLIPSIS,
            checker=checker,
        ))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
