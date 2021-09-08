from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import doctest
import os
import unittest


class TestImport(unittest.TestCase):
    def test_import(self):
        for name in ('base', 'layers', 'matchers', 'time'):
            __import__('nti.testing.' + name)

    def test_mock_direct_import(self):
        from nti.testing.mock import Mock
        from nti.testing import mock
        self.assertIs(mock.Mock, Mock)

    def test_mock_module_identity(self):
        from nti.testing import mock
        try:
            from unittest import mock as stdmock
        except ImportError: # pragma: no cover
            # Python 2
            import mock as stdmock

        self.assertIs(mock, stdmock)

def test_suite():
    here = os.path.dirname(__file__)

    suite = unittest.defaultTestLoader.loadTestsFromName(__name__)
    suite.addTest(doctest.DocFileSuite(
        'test_component_cleanup_broken.txt'))

    readmedir = here
    while not os.path.exists(os.path.join(readmedir, 'setup.py')):
        readmedir = os.path.dirname(readmedir)
    readme = os.path.join(readmedir, 'README.rst')
    suite.addTest(doctest.DocFileSuite(
        readme,
        module_relative=False,
        optionflags=doctest.ELLIPSIS,
    ))
    return suite
