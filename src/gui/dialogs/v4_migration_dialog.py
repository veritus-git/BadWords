#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: v4_migration_dialog.py
ROLE: GUI Dialog
DESCRIPTION:
One-time milestone notification displayed after upgrading from 3.x to 4.0.0,
informing the user about the standalone desktop app transformation and native launchers.
"""

import sys
import webbrowser
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QCursor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
)

_MIGRATION_TEXTS = {
    "pl": {
        "badge": "BADWORDS 4.0.0",
        "heading": "Zaktualizowano do BadWords 4.0.0!",
        "body": (
            "Twoja instalacja została pomyślnie zaktualizowana do wersji 4.0.0.\n\n"
            "Od wersji 4.0.0 BadWords stało się nie tylko zaawansowanym pluginem do DaVinci Resolve, "
            "ale także pełnoprawną, samostojącą aplikacją desktopową z dedykowanymi launcherami i integracją systemową.\n\n"
            "Zalecamy pobranie najnowszego oficjalnego instalatora ze strony GitHub Releases, "
            "aby zainstalować dedykowany launcher aplikacji oraz dodać skróty w systemie."
        ),
        "btn_github": "Pobierz nowy instalator (GitHub)",
        "btn_close": "Rozumiem / Zamknij",
    },
    "en": {
        "badge": "BADWORDS 4.0.0",
        "heading": "Updated to BadWords 4.0.0!",
        "body": (
            "Your installation has been successfully updated to version 4.0.0.\n\n"
            "Starting with version 4.0.0, BadWords is not only an advanced DaVinci Resolve plugin, "
            "but also a full standalone desktop application with dedicated native launchers and system integration.\n\n"
            "We recommend downloading the official installer from GitHub Releases "
            "to set up native launchers, desktop shortcuts, and full system integration."
        ),
        "btn_github": "Download New Installer (GitHub)",
        "btn_close": "Got it / Close",
    },
    "de": {
        "badge": "BADWORDS 4.0.0",
        "heading": "Auf BadWords 4.0.0 aktualisiert!",
        "body": (
            "Ihre Installation wurde erfolgreich auf Version 4.0.0 aktualisiert.\n\n"
            "Ab Version 4.0.0 ist BadWords nicht nur ein DaVinci Resolve-Plugin, "
            "sondern auch eine vollwertige, eigenständige Desktop-Anwendung mit nativen Launchern.\n\n"
            "Wir empfehlen, das offizielle Installationsprogramm von GitHub Releases herunterzuladen, "
            "um Desktop-Verknüpfungen und die Systemintegration einzurichten."
        ),
        "btn_github": "Neuen Installer herunterladen (GitHub)",
        "btn_close": "Verstanden / Schließen",
    },
    "es": {
        "badge": "BADWORDS 4.0.0",
        "heading": "¡Actualizado a BadWords 4.0.0!",
        "body": (
            "Tu instalación se ha actualizado correctamente a la versión 4.0.0.\n\n"
            "A partir de la versión 4.0.0, BadWords no es solo un complemento para DaVinci Resolve, "
            "sino también una aplicación de escritorio independiente con lanzadores nativos.\n\n"
            "Recomendamos descargar el instalador oficial desde GitHub Releases "
            "para configurar los accesos directos y la integración en el sistema."
        ),
        "btn_github": "Descargar nuevo instalador (GitHub)",
        "btn_close": "Entendido / Cerrar",
    },
    "fr": {
        "badge": "BADWORDS 4.0.0",
        "heading": "Mis à jour vers BadWords 4.0.0 !",
        "body": (
            "Votre installation a été mise à jour avec succès vers la version 4.0.0.\n\n"
            "À partir de la version 4.0.0, BadWords n'est plus seulement un plugin DaVinci Resolve, "
            "mais aussi une application de bureau autonome avec lanceurs natifs.\n\n"
            "Nous vous recommandons de télécharger le programme d'installation officiel sur GitHub Releases "
            "pour configurer les raccourcis et l'intégration système."
        ),
        "btn_github": "Télécharger le nouvel installateur (GitHub)",
        "btn_close": "Compris / Fermer",
    },
    "it": {
        "badge": "BADWORDS 4.0.0",
        "heading": "Aggiornato a BadWords 4.0.0!",
        "body": (
            "La tua installazione è stata aggiornata con successo alla versione 4.0.0.\n\n"
            "A partire dalla versione 4.0.0, BadWords non è solo un plugin per DaVinci Resolve, "
            "ma anche un'applicazione desktop autonoma completa con launcher nativi.\n\n"
            "Ti consigliamo di scaricare l'installer ufficiale da GitHub Releases "
            "per configurare i collegamenti sul desktop e l'integrazione di sistema."
        ),
        "btn_github": "Scarica nuovo installer (GitHub)",
        "btn_close": "Ho capito / Chiudi",
    },
    "nl": {
        "badge": "BADWORDS 4.0.0",
        "heading": "Bijgewerkt naar BadWords 4.0.0!",
        "body": (
            "Uw installatie is succesvol bijgewerkt naar versie 4.0.0.\n\n"
            "Vanaf versie 4.0.0 is BadWords niet alleen een DaVinci Resolve-plug-in, "
            "maar ook een volwaardige standalone desktop-applicatie met native launchers.\n\n"
            "We raden aan het officiële installatieprogramma van GitHub Releases te downloaden "
            "om snelkoppelingen en systeemintegratie in te stellen."
        ),
        "btn_github": "Nieuwe installer downloaden (GitHub)",
        "btn_close": "Begrepen / Sluiten",
    },
    "pt": {
        "badge": "BADWORDS 4.0.0",
        "heading": "Atualizado para BadWords 4.0.0!",
        "body": (
            "Sua instalação foi atualizada com sucesso para a versão 4.0.0.\n\n"
            "A partir de la versão 4.0.0, o BadWords é não apenas um plugin para DaVinci Resolve, "
            "mas também um aplicativo desktop independente com inicializadores nativos.\n\n"
            "Recomendamos baixar o instalador oficial no GitHub Releases "
            "para configurar atalhos na área de trabalho e integração ao sistema."
        ),
        "btn_github": "Baixar novo instalador (GitHub)",
        "btn_close": "Entendi / Fechar",
    },
    "ru": {
        "badge": "BADWORDS 4.0.0",
        "heading": "Обновлено до BadWords 4.0.0!",
        "body": (
            "Ваша установка была успешно обновлена до версии 4.0.0.\n\n"
            "Начиная с версии 4.0.0, BadWords — это не только плагин для DaVinci Resolve, "
            "но и полноценное автономное приложение с нативными лаунчерами.\n\n"
            "Мы рекомендуем скачать официальный установщик со страницы GitHub Releases, "
            "чтобы настроить ярлыки на рабочем столе и интеграцию с системой."
        ),
        "btn_github": "Скачать новый установщик (GitHub)",
        "btn_close": "Понятно / Закрыть",
    },
    "uk": {
        "badge": "BADWORDS 4.0.0",
        "heading": "Оновлено до BadWords 4.0.0!",
        "body": (
            "Вашу установку успішно оновлено до версії 4.0.0.\n\n"
            "Починаючи з версії 4.0.0, BadWords — це не лише плагін для DaVinci Resolve, "
            "але й повноцінний автономний застосунок із нативними лаунчерами.\n\n"
            "Ми рекомендуємо завантажити офіційний інсталятор зі сторінки GitHub Releases, "
            "щоб налаштувати ярлики на робочому столі та інтеграцію із системою."
        ),
        "btn_github": "Завантажити новий інсталятор (GitHub)",
        "btn_close": "Зрозуміло / Закрити",
    },
}


class V4MigrationDialog(QDialog):
    def __init__(self, lang: str = "en", parent=None):
        super().__init__(parent)
        self.user_choice = "close"
        self._drag_pos = None

        t = _MIGRATION_TEXTS.get(lang, _MIGRATION_TEXTS["en"])

        self.setWindowTitle(t["heading"])
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(680)

        self.setStyleSheet("""
            QDialog, QFrame, QWidget {
                background: transparent;
                background-color: transparent;
                color: #e6e6e6;
                font-family: 'Segoe UI', 'Ubuntu', 'Helvetica Neue', sans-serif;
            }
            #MainCard {
                background-color: #181818;
                border: 1px solid #282828;
                border-radius: 12px;
            }
            QLabel {
                background: transparent;
                background-color: transparent;
            }
            #BadgeLabel {
                background-color: #0d2e18;
                color: #39ff7a;
                border: 1px solid #1a572d;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 9pt;
                font-weight: bold;
            }
            #HeadingLabel {
                background: transparent;
                background-color: transparent;
                color: #ffffff;
                font-size: 13.5pt;
                font-weight: bold;
            }
            #BodyLabel {
                background: transparent;
                background-color: transparent;
                color: #cccccc;
                font-size: 10pt;
                line-height: 1.5;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 9.5pt;
                font-weight: bold;
            }
            #PrimaryBtn {
                background-color: #238636;
                color: #ffffff;
                border: 1px solid #2ea043;
            }
            #PrimaryBtn:hover {
                background-color: #2ea043;
            }
            #SecondaryBtn {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
            }
            #SecondaryBtn:hover {
                background-color: #30363d;
                color: #ffffff;
            }
            #CloseBtn {
                background-color: transparent;
                color: #8b949e;
                border: none;
                font-size: 11pt;
                padding: 2px 6px;
            }
            #CloseBtn:hover {
                color: #ffffff;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setSizeConstraint(QVBoxLayout.SetFixedSize)
        outer.setContentsMargins(20, 20, 20, 20)

        card = QFrame(self)
        card.setObjectName("MainCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        top_row = QHBoxLayout()
        badge = QLabel(t["badge"])
        badge.setObjectName("BadgeLabel")
        top_row.addWidget(badge)
        top_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self._on_close)
        top_row.addWidget(close_btn)
        card_layout.addLayout(top_row)

        heading = QLabel(t["heading"])
        heading.setObjectName("HeadingLabel")
        heading.setAttribute(Qt.WA_TranslucentBackground, True)
        heading.setWordWrap(True)
        card_layout.addWidget(heading)

        body = QLabel(t["body"])
        body.setObjectName("BodyLabel")
        body.setAttribute(Qt.WA_TranslucentBackground, True)
        body.setWordWrap(True)
        card_layout.addWidget(body)

        card_layout.addSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_close = QPushButton(t["btn_close"])
        btn_close.setObjectName("SecondaryBtn")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self._on_close)
        btn_row.addWidget(btn_close)

        btn_gh = QPushButton(t["btn_github"])
        btn_gh.setObjectName("PrimaryBtn")
        btn_gh.setCursor(Qt.PointingHandCursor)
        btn_gh.clicked.connect(self._on_github)
        btn_row.addWidget(btn_gh)

        card_layout.addLayout(btn_row)
        outer.addWidget(card)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None

    def _on_github(self):
        self.user_choice = "github"
        try:
            webbrowser.open("https://github.com/veritus-git/BadWords#-installation--setup")
        except Exception:
            pass
        self.accept()

    def _on_close(self):
        self.user_choice = "close"
        self.reject()
