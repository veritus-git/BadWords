#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: __init__.py
ROLE: Configuration
DESCRIPTION:
Python package initialization file.
"""

from .app_constants import *
from .analysis_params import *
from .palette import *
from .settings_defaults import *
from .languages import *
from i18n import get_trans, TRANS, SUPPORTED_LANGS
