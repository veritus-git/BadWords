#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: menus.py
ROLE: GUI Widget
DESCRIPTION:
Context menus with their own solid background. A QMenu otherwise inherits stylesheets such as
"background: transparent" from the panels it opens over, and the text underneath shows through.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

import config


def context_menu(parent):
    menu = QMenu(parent)
    menu.setAttribute(Qt.WA_TranslucentBackground, False)
    menu.setAutoFillBackground(True)
    menu.setStyleSheet(f"""
        QMenu {{ background-color: #222222; color: #e6e6e6; border: 1px solid #3a3a3a;
                 border-radius: {config.S(6)}px; padding: {config.S(5)}px; }}
        QMenu::item {{ background: transparent; padding: {config.S(6)}px {config.S(18)}px {config.S(6)}px {config.S(12)}px;
                       border-radius: {config.S(4)}px; }}
        QMenu::item:selected {{ background-color: #23a559; color: #ffffff; }}
        QMenu::item:disabled {{ color: #6a6a6a; }}
        QMenu::separator {{ height: 1px; background: #3a3a3a; margin: {config.S(4)}px {config.S(6)}px; }}
        QMenu::right-arrow {{ width: {config.S(8)}px; height: {config.S(8)}px; }}
    """)
    return menu
