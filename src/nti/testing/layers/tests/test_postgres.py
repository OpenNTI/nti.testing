# -*- coding: utf-8 -*-
"""
Tests for postgres.py

"""

import unittest


class TestBasic(unittest.TestCase):

    def test_imports(self):
        from .. import postgres
        self.assertIsNotNone(postgres)

class TestLayer(unittest.TestCase):

    def test_setUp(self):
        from ..postgres import DatabaseLayer
        try:
            DatabaseLayer.setUp()
            try:
                DatabaseLayer.testSetUp()
                # Might want to contextlib.redirect_stdout
                # around this call.
                DatabaseLayer.print_size_report()
            finally:
                DatabaseLayer.testTearDown()
        finally:
            DatabaseLayer.tearDown()

if __name__ == '__main__':
    unittest.main()
