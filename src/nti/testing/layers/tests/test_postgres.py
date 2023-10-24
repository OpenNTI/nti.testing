# -*- coding: utf-8 -*-
"""
Tests for postgres.py

"""

import unittest


class TestBasic(unittest.TestCase):

    def test_imports(self):
        from .. import postgres
        self.assertIsNotNone(postgres)

if __name__ == '__main__':
    unittest.main()
