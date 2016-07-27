from __future__ import print_function, division, absolute_import

import unittest
import doctest

class TestImport(unittest.TestCase):
    def test_import(self):
        for name in ('base', 'layers', 'matchers', 'time'):
            __import__('nti.testing.' + name)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestImport))
    suite.addTest(doctest.DocFileSuite(
        'test_component_cleanup_broken.txt'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
