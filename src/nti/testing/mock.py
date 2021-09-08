#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys

# This module exists on disk to satisfy static linters;
# it replaces itself when loaded.
try:
    from unittest import mock
except ImportError: # pragma: no cover
    # Python 2
    import mock

# More for static linters
Mock = mock.Mock
MagicMock = mock.MagicMock
patch = mock.patch

sys.modules[__name__] = mock
