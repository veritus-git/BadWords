#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: story_panel.py
ROLE: GUI Activity Panel
DESCRIPTION:
Story board: the interview as blocks of sentences. "Edit" holds the blocks in the order they
play, "Not used" the rest. Drag to reorder or to move between the two lists. The Edit list is
the story that Assemble and Play edit follow (non-linear order allowed).
"""

from gui.theme import qc

from PySide6.QtCore import Qt, QSize, QRectF, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QListWidget, QListWidgetItem, QAbstractItemView,
    QStyledItemDelegate, QStyle, QMenu
)

import config
from gui.widgets.labels import QLabel
from gui.widgets.buttons import QPushButton
from .script_panel import wrap_activity_panel

BLOCK_ROLE = Qt.UserRole + 1
MAX_TEXT_LINES = 4


def _decode(value):
    """Blocks are stored as "first,last" text so they survive drag and drop between lists."""
    try:
        f, l = str(value).split(",")
        return int(f), int(l)
    except Exception:
        return None


def _encode(block):
    return f"{int(block[0])},{int(block[1])}"


def _mmss(seconds):
    seconds = int(round(max(0.0, seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


class _BlockDelegate(QStyledItemDelegate):
    """Paints a block as a card: IDs and length on top, what is said underneath."""

    def __init__(self, board, view):
        super().__init__(view)
        self.board = board
        self.view = view

    def _text_rect_width(self):
        # Always leave room for the scrollbar: it appears after the heights are measured
        sb = self.view.verticalScrollBar().sizeHint().width()
        return max(60, self.view.width() - sb - config.S(28))

    def _body(self, block):
        return self.board.block_text(block)

    def sizeHint(self, option, index):
        block = _decode(index.data(BLOCK_ROLE))
        if not block:
            return QSize(0, 0)
        fm = QFontMetrics(self.view.font())
        w = self._text_rect_width()
        body_h = fm.boundingRect(0, 0, w, 10000, Qt.TextWordWrap, self._body(block)).height()
        body_h = min(body_h, fm.lineSpacing() * MAX_TEXT_LINES)
        return QSize(w, body_h + fm.lineSpacing() + config.S(22))

    def paint(self, painter, option, index):
        block = _decode(index.data(BLOCK_ROLE))
        if not block:
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(option.rect).adjusted(config.S(3), config.S(3), -config.S(3), -config.S(2))
        selected = bool(option.state & QStyle.State_Selected)
        playing = self.board.is_playing_block(block)
        painter.setPen(QPen(qc(config.BTN_BG) if (selected or playing) else qc("#3a3a3a"), 1.2))
        painter.setBrush(qc("#2c3a31") if playing else qc("#262626"))
        painter.drawRoundedRect(r, config.S(5), config.S(5))

        fm = QFontMetrics(self.view.font())
        pad = config.S(8)
        head = QRectF(r.left() + pad, r.top() + config.S(5), r.width() - 2 * pad, fm.lineSpacing())
        # Drag handle: two columns of three dots
        painter.setPen(Qt.NoPen)
        painter.setBrush(qc("#5a5a5a"))
        dot = config.S(2.4)
        cx, cy = head.left() + config.S(2), head.center().y()
        for dx in (0, config.S(5)):
            for dy in (-config.S(5), 0, config.S(5)):
                painter.drawEllipse(QRectF(cx + dx - dot / 2, cy + dy - dot / 2, dot, dot))
        label_rect = head.adjusted(config.S(14), 0, 0, 0)
        painter.setPen(qc("#8a8a8a"))
        painter.drawText(label_rect, Qt.AlignLeft | Qt.AlignVCenter, self.board.block_label(block))
        cl = self.board.block_clarity(block)
        tag_x = label_rect.left() + fm.horizontalAdvance(self.board.block_label(block)) + config.S(10)
        if cl is not None:
            # Clarity: a small dot and number after the IDs (green clear, amber so-so, red hard to hear)
            lw = fm.horizontalAdvance(self.board.block_label(block))
            dot_col = QColor("#3fb950" if cl >= 80 else ("#d29922" if cl >= 60 else "#f85149"))
            cx0 = label_rect.left() + lw + config.S(10)
            painter.setPen(Qt.NoPen)
            painter.setBrush(dot_col)
            d = config.S(6)
            painter.drawEllipse(QRectF(cx0, head.center().y() - d / 2, d, d))
            painter.setPen(qc("#8a8a8a"))
            painter.drawText(QRectF(cx0 + d + config.S(4), head.top(), config.S(40), head.height()),
                             Qt.AlignLeft | Qt.AlignVCenter, str(cl))
            tag_x = cx0 + d + config.S(10) + fm.horizontalAdvance(str(cl))
        if self.board.block_avoid(block):
            # Tagged "Avoid" by the editor: an orange pill
            tag = self.board.win.txt("board_avoid")
            small = QFont(painter.font())
            small.setPointSizeF(max(6.0, small.pointSizeF() * 0.78))
            small.setBold(True)
            sfm = QFontMetrics(small)
            tr = QRectF(tag_x, head.top() + 1, sfm.horizontalAdvance(tag) + config.S(10), head.height() - 2)
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(235, 110, 0, 60))
            painter.drawRoundedRect(tr, tr.height() / 2, tr.height() / 2)
            painter.setFont(small)
            painter.setPen(QColor("#ff9d4d"))
            painter.drawText(tr, Qt.AlignCenter, tag)
            painter.restore()
        dur = _mmss(self.board.block_duration(block))
        painter.drawText(head, Qt.AlignRight | Qt.AlignVCenter, dur)
        if playing:
            # "Playing" tag left of the length, in the accent colour
            tag = self.board.win.txt("board_playing")
            small = painter.font()
            small.setPointSizeF(max(6.0, small.pointSizeF() * 0.78))
            small.setBold(True)
            sfm = QFontMetrics(small)
            tw = sfm.horizontalAdvance(tag) + config.S(10)
            tr = QRectF(head.right() - fm.horizontalAdvance(dur) - config.S(8) - tw, head.top() + 1, tw, head.height() - 2)
            painter.setPen(Qt.NoPen)
            accent = qc(config.BTN_BG)
            soft = QColor(accent)
            soft.setAlpha(50)
            painter.setBrush(soft)
            painter.drawRoundedRect(tr, tr.height() / 2, tr.height() / 2)
            painter.setFont(small)
            painter.setPen(accent.lighter(130))
            painter.drawText(tr, Qt.AlignCenter, tag)
            painter.setFont(self.view.font())

        body = QRectF(head.left(), head.bottom() + config.S(3), head.width(),
                      r.bottom() - head.bottom() - config.S(8))
        text = self._body(block)
        lines_h = fm.boundingRect(0, 0, int(body.width()), 10000, Qt.TextWordWrap, text).height()
        if lines_h > body.height() + 1:
            # Too long for the card: cut to the visible lines and end with an ellipsis
            while text and fm.boundingRect(0, 0, int(body.width()), 10000, Qt.TextWordWrap,
                                           text + "…").height() > body.height() + 1:
                text = text[:max(0, int(len(text) * 0.92) - 1)].rstrip()
            text += "…"
        painter.setPen(qc("#e6e6e6"))
        painter.drawText(body, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, text)
        painter.restore()


class _BlockList(QListWidget):
    def __init__(self, board, parent=None):
        super().__init__(parent)
        self.board = board
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setResizeMode(QListWidget.Adjust)
        self.setWordWrap(True)
        self.setSpacing(0)
        self.setItemDelegate(_BlockDelegate(board, self))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setStyleSheet(f"""
            QListWidget {{ background: #1b1b1b; border: 1px solid #303030; border-radius: {config.S(4)}px;
                          outline: none; }}
            QListWidget::item {{ background: transparent; border: none; }}
            QListWidget::item:selected {{ background: transparent; }}
        """)
        self.model().rowsInserted.connect(board.schedule_sync)
        self.model().rowsRemoved.connect(board.schedule_sync)
        self.model().rowsMoved.connect(board.schedule_sync)
        self.itemDoubleClicked.connect(lambda it: board.play_block(_decode(it.data(BLOCK_ROLE))))
        self.customContextMenuRequested.connect(lambda pos: board.show_menu(self, pos))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.doItemsLayout()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self is self.board.list_edit:
            self.board.move_selected(self, self.board.list_unused)
            return
        super().keyPressEvent(event)


class StoryBoard(QWidget):
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.sentences = []
        self._syncing = False
        self._ops_ctx = None  # (ops, fps, offset) for block lengths after the cuts
        self._sync_timer = QTimer(self)
        self._sync_timer.setSingleShot(True)
        self._sync_timer.setInterval(0)
        self._sync_timer.timeout.connect(self._sync_story)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))
        lay.setSpacing(config.S(8))

        row = QHBoxLayout()
        title = QLabel(win.txt("board_title"))
        title.setStyleSheet(f"font-size: {config.FS(12)}pt; font-weight: bold;")
        row.addWidget(title)
        row.addStretch()
        row.addWidget(win._create_info_icon("tt_board"))
        lay.addLayout(row)

        # Actions in a 2 x 2 grid of equal buttons: they fit a narrow panel without being cut off
        from PySide6.QtWidgets import QGridLayout, QSizePolicy, QLineEdit
        self.btn_fill = QPushButton(win.txt("board_fill"))
        self.btn_fill.setToolTip(win.txt("tt_board_fill"))
        self.btn_fill.clicked.connect(self.fill_from_transcript)
        self.btn_ai = QPushButton(win.txt("board_import_ai"))
        self.btn_ai.clicked.connect(lambda: win._on_import_ai_story())
        self.btn_copy_ai = QPushButton(win.txt("board_copy_ai"))
        self.btn_copy_ai.setToolTip(win.txt("tt_board_copy_ai"))
        self.btn_copy_ai.clicked.connect(lambda: win._on_copy_ai_transcript())
        self.btn_review = QPushButton(win.txt("board_review_cuts"))
        self.btn_review.setToolTip(win.txt("tt_board_review_cuts"))
        self.btn_review.clicked.connect(lambda: win._on_review_cuts())
        grid = QGridLayout()
        grid.setHorizontalSpacing(config.S(6))
        grid.setVerticalSpacing(config.S(6))
        for n, b in enumerate((self.btn_fill, self.btn_ai, self.btn_copy_ai, self.btn_review)):
            b.setCursor(Qt.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            b.setMinimumHeight(config.S(26))
            b.setStyleSheet(f"""
                QPushButton {{ background: #2a2a2a; color: #d0d0d0; border: 1px solid #3a3a3a;
                    border-radius: {config.S(4)}px; padding: {config.S(3)}px {config.S(4)}px; font-size: {config.FS(8.5)}pt; }}
                QPushButton:hover {{ color: #ffffff; border-color: #555; }}
                QPushButton:disabled {{ color: #555; }}
            """)
            grid.addWidget(b, n // 2, n % 2)
        lay.addLayout(grid)

        # Target length for the AI (and to compare the edit against)
        row_t = QHBoxLayout()
        row_t.setSpacing(config.S(6))
        lbl_t = QLabel(win.txt("board_target"))
        lbl_t.setStyleSheet(f"color: #a0a0a0; font-size: {config.FS(9)}pt;")
        row_t.addWidget(lbl_t)
        self.edit_target = QLineEdit()
        self.edit_target.setPlaceholderText("2:00")
        self.edit_target.setToolTip(win.txt("tt_board_target"))
        self.edit_target.setFixedWidth(config.S(64))
        self.edit_target.setStyleSheet(f"""QLineEdit {{ background: #1e1e1e; color: #e6e6e6; border: 1px solid #3a3a3a;
            border-radius: {config.S(4)}px; padding: {config.S(2)}px {config.S(6)}px; }}""")
        cur = (win.engine.load_preferences() or {}).get('story_target_s')
        if cur:
            self.edit_target.setText(_mmss(cur))
        self.edit_target.editingFinished.connect(self._on_target_changed)
        row_t.addWidget(self.edit_target)
        row_t.addStretch()
        lay.addLayout(row_t)

        # EDIT · blocks · length (wraps rather than being cut), with Clear for the edit list
        self.lbl_edit = QLabel("")
        self.lbl_edit.setWordWrap(True)
        self.lbl_edit.setStyleSheet(f"color: #b0b0b0; font-size: {config.FS(9)}pt; font-weight: bold;")
        row_e = QHBoxLayout()
        row_e.setSpacing(config.S(6))
        row_e.addWidget(self.lbl_edit, 1)
        self.btn_clear = QPushButton(win.txt("btn_story_clear"))
        self.btn_clear.clicked.connect(self.clear_edit)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: #a0a0a0; border: 1px solid #3a3a3a;
                border-radius: {config.S(4)}px; padding: {config.S(2)}px {config.S(6)}px; font-size: {config.FS(8.5)}pt; }}
            QPushButton:hover {{ color: #ffffff; border-color: #555; }}
        """)
        row_e.addWidget(self.btn_clear, 0, Qt.AlignTop)
        lay.addLayout(row_e)
        self.lbl_empty = QLabel(win.txt("board_empty"))
        self.lbl_empty.setWordWrap(True)
        self.lbl_empty.setStyleSheet(f"color: #777777; font-size: {config.FS(9)}pt;")
        lay.addWidget(self.lbl_empty)
        self.list_edit = _BlockList(self)
        lay.addWidget(self.list_edit, 3)

        self.lbl_unused = QLabel("")
        self.lbl_unused.setStyleSheet(f"color: #b0b0b0; font-size: {config.FS(9)}pt; font-weight: bold;")
        lay.addWidget(self.lbl_unused)
        self.list_unused = _BlockList(self)
        lay.addWidget(self.list_unused, 2)

        self._refresh_labels()

    # ------------------------------------------------------------------ data
    def block_text(self, block):
        f, l = block
        return " ".join(s["text"] for s in self.sentences[f:l + 1])

    def block_label(self, block):
        f, l = block
        a, b = self.sentences[f]["id"], self.sentences[l]["id"]
        return a if f == l else f"{a}–{b}"

    def block_clip(self, block):
        f, l = block
        return {"cut_start": self.sentences[f]["cut_start"], "cut_end": self.sentences[l]["cut_end"],
                "start_id": self.sentences[f]["id"], "end_id": self.sentences[l]["id"]}

    def block_avoid(self, block):
        return any(s.get("avoid") for s in self.sentences[block[0]:block[1] + 1])

    def block_clarity(self, block):
        vals = [s.get("clarity") for s in self.sentences[block[0]:block[1] + 1] if s.get("clarity") is not None]
        return int(round(sum(vals) / len(vals))) if vals else None

    def block_duration(self, block):
        ctx = self._ops_ctx
        if ctx is None:
            return self.sentences[block[1]]["cut_end"] - self.sentences[block[0]]["cut_start"]
        import algorithms
        ops, fps, offset = ctx
        kept = algorithms.apply_story_order(ops, [self.block_clip(block)], fps, offset)
        return sum(o['e'] - o['s'] for o in kept) / fps

    def is_playing_block(self, block):
        return block == getattr(self, "_playing_block", None)

    def set_playing_time(self, t):
        """Highlight the Edit block that contains source time t (seconds), or none."""
        found = None
        if self.sentences and t is not None:
            offset = float((self.win.engine.load_preferences() or {}).get("offset", 0.133)) if hasattr(self.win, "engine") else 0.133
            for i in range(self.list_edit.count()):
                b = _decode(self.list_edit.item(i).data(BLOCK_ROLE))
                if b and self.sentences[b[0]]["cut_start"] + offset <= t < self.sentences[b[1]]["cut_end"] + offset:
                    found = b
                    if found != getattr(self, "_playing_block", None):
                        self.list_edit.scrollToItem(self.list_edit.item(i))
                    break
        if found != getattr(self, "_playing_block", None):
            self._playing_block = found
            self.list_edit.viewport().update()

    def edit_blocks(self):
        return [_decode(self.list_edit.item(i).data(BLOCK_ROLE)) for i in range(self.list_edit.count())]

    def _make_item(self, block):
        it = QListWidgetItem(f"{block[0]:06d}")  # sort key only; the delegate paints the card
        it.setData(BLOCK_ROLE, _encode(block))
        it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
        return it

    # ------------------------------------------------------------------ loading
    def load(self, sentences, edit_blocks, unused_blocks=None):
        """Show `edit_blocks` (play order) and `unused_blocks`; if unused is None, everything else."""
        self.sentences = list(sentences)
        self._ops_ctx = self.win._story_ops_context() if hasattr(self.win, "_story_ops_context") else None
        if unused_blocks is None:
            import algorithms
            used = {i for f, l in edit_blocks for i in range(f, l + 1)}
            unused_blocks = algorithms.moment_blocks(self.sentences, [i for i in range(len(self.sentences)) if i not in used])
        self._syncing = True
        try:
            self.list_edit.clear()
            self.list_unused.clear()
            for b in edit_blocks:
                self.list_edit.addItem(self._make_item(b))
            for b in unused_blocks:
                self.list_unused.addItem(self._make_item(b))
        finally:
            self._syncing = False
        self._sync_story()

    def fill_from_transcript(self):
        import algorithms
        _, sentences = self.win._build_ai_transcript()
        if not sentences:
            return
        # Parts tagged Avoid start in Not used
        good = [i for i, s in enumerate(sentences) if not s.get("avoid")]
        bad = [i for i, s in enumerate(sentences) if s.get("avoid")]
        self.load(sentences, algorithms.moment_blocks(sentences, good), algorithms.moment_blocks(sentences, bad))

    def load_ai_story(self, sentences, story):
        """Mirror an imported AI edit: its clips become the Edit list, the rest goes to Not used."""
        index = {s["id"]: i for i, s in enumerate(sentences)}
        blocks = []
        for c in story.get("clips", []):
            f, l = index.get(c.get("start_id")), index.get(c.get("end_id"))
            if f is not None and l is not None and f <= l:
                blocks.append((f, l))
        if story.get("keep_source_order"):
            blocks.sort()
        self.load(sentences, blocks)

    def clear_edit(self):
        if not self.sentences:
            return
        import algorithms
        self.load(self.sentences, [], algorithms.moment_blocks(self.sentences))

    # ------------------------------------------------------------------ sync
    def schedule_sync(self, *args):
        if not self._syncing:
            self._sync_timer.start()

    def _sync_story(self):
        self._syncing = True
        try:
            self.list_unused.sortItems()  # Not used stays in recording order
        finally:
            self._syncing = False
        blocks = self.edit_blocks()
        self.win._set_story_from_board([self.block_clip(b) for b in blocks] if blocks else None)
        self._refresh_labels()
        self._save()

    # ------------------------------------------------------------------ persistence
    def _path(self):
        if not hasattr(self.win, "_ai_story_map_path"):
            return None
        base = self.win._ai_story_map_path()
        return base[:-5] + ".board.json" if base.endswith(".json") else base + ".board.json"

    def _save(self):
        path = self._path()
        if not path or not self.sentences:
            return
        import json, os
        unused = [_decode(self.list_unused.item(i).data(BLOCK_ROLE)) for i in range(self.list_unused.count())]
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "sentences": self.sentences,
                           "edit": [list(b) for b in self.edit_blocks()], "unused": [list(b) for b in unused]}, f)
        except Exception:
            pass

    def maybe_restore(self):
        """Bring back the board saved for this timeline, once, when its transcript is loaded."""
        path = self._path()
        if not path or path == getattr(self, "_restored_for", None):
            return
        self._restored_for = path
        if self.sentences:
            return
        import json, os
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sentences = data["sentences"]
            n = len(sentences)
            ok = lambda b: 0 <= b[0] <= b[1] < n
            edit = [tuple(b) for b in data.get("edit", []) if ok(b)]
            unused = [tuple(b) for b in data.get("unused", []) if ok(b)]
            if edit or unused:
                self.load(sentences, edit, unused)
        except Exception:
            pass

    def _target_s(self):
        return (self.win.engine.load_preferences() or {}).get('story_target_s') or None

    def _on_target_changed(self):
        """'2:00', '2m', '90s' or '90' -> seconds; empty clears the target."""
        import re
        txt = self.edit_target.text().strip().lower().replace(",", ".")
        secs = None
        m = re.fullmatch(r"(\d+):(\d{1,2})", txt)
        if m:
            secs = int(m.group(1)) * 60 + int(m.group(2))
        elif re.fullmatch(r"\d+(\.\d+)?\s*m(in)?", txt):
            secs = float(re.match(r"[\d.]+", txt).group(0)) * 60
        elif re.fullmatch(r"\d+(\.\d+)?\s*s?", txt):
            secs = float(re.match(r"[\d.]+", txt).group(0))
        prefs = self.win.engine.load_preferences() or {}
        if txt and not secs:  # not a length: keep the previous target
            self.edit_target.setText(_mmss(prefs['story_target_s']) if prefs.get('story_target_s') else "")
            return
        prefs['story_target_s'] = int(round(secs)) if secs else None
        self.win.engine.save_preferences(prefs)
        self.edit_target.setText(_mmss(secs) if secs else "")
        self._refresh_labels()

    def _refresh_labels(self):
        n = self.list_edit.count()
        story = getattr(self.win, "_story", None) or {}
        dur = story.get("duration", 0.0) if n else 0.0
        target = self._target_s()
        text = self.win.txt("board_edit").format(blocks=n, duration=_mmss(dur))
        color = "#b0b0b0"
        if target and n:
            text += " / " + _mmss(target)
            color = "#3fb950" if abs(dur - target) <= 0.1 * target else "#d29922"
        self.lbl_edit.setText(text)
        self.lbl_edit.setStyleSheet(f"color: {color}; font-size: {config.FS(9)}pt; font-weight: bold;")
        self.lbl_unused.setText(self.win.txt("board_unused").format(blocks=self.list_unused.count()))
        self.lbl_empty.setVisible(n == 0)
        self.btn_clear.setEnabled(n > 0)

    # ------------------------------------------------------------------ actions
    def play_block(self, block):
        if not block:
            return
        ap = getattr(self.win, "audio_preview", None)
        if ap is None:
            return
        if not ap.btn_play_edit.isChecked() and self.list_edit.count():
            ap.btn_play_edit.setChecked(True)
        offset = float((self.win.engine.load_preferences() or {}).get("offset", 0.133))
        ap.seek_source_time(self.sentences[block[0]]["cut_start"] + offset)
        if ap.player.playbackState() != ap.player.PlaybackState.PlayingState:
            ap.toggle_play()

    def move_selected(self, src, dst):
        items = src.selectedItems()
        if not items:
            return
        self._syncing = True
        try:
            for it in items:
                block = _decode(it.data(BLOCK_ROLE))
                src.takeItem(src.row(it))
                dst.addItem(self._make_item(block))
        finally:
            self._syncing = False
        self._sync_story()

    def _split(self, lst, item):
        f, l = _decode(item.data(BLOCK_ROLE))
        row = lst.row(item)
        self._syncing = True
        try:
            lst.takeItem(row)
            for k, i in enumerate(range(f, l + 1)):
                lst.insertItem(row + k, self._make_item((i, i)))
        finally:
            self._syncing = False
        self._sync_story()

    def _join_next(self, lst, item):
        row = lst.row(item)
        nxt = lst.item(row + 1)
        if nxt is None:
            return
        (f, l), (f2, l2) = _decode(item.data(BLOCK_ROLE)), _decode(nxt.data(BLOCK_ROLE))
        if f2 != l + 1:
            return
        self._syncing = True
        try:
            lst.takeItem(row + 1)
            item.setData(BLOCK_ROLE, _encode((f, l2)))
        finally:
            self._syncing = False
        lst.doItemsLayout()
        self._sync_story()

    def show_menu(self, lst, pos):
        item = lst.itemAt(pos)
        if item is None:
            return
        if not item.isSelected():
            lst.clearSelection()
            item.setSelected(True)
        t = self.win.txt
        from gui.widgets.menus import context_menu
        menu = context_menu(self)
        menu.addAction(t("board_play"), lambda: self.play_block(_decode(item.data(BLOCK_ROLE))))
        if lst is self.list_edit:
            menu.addAction(t("board_remove"), lambda: self.move_selected(self.list_edit, self.list_unused))
            menu.addAction(t("board_to_top"), lambda: self._move_to(item, 0))
            menu.addAction(t("board_to_end"), lambda: self._move_to(item, self.list_edit.count() - 1))
        else:
            menu.addAction(t("board_add"), lambda: self.move_selected(self.list_unused, self.list_edit))
        menu.addSeparator()
        f, l = _decode(item.data(BLOCK_ROLE))
        a_split = menu.addAction(t("board_split"), lambda: self._split(lst, item))
        a_split.setEnabled(l > f)
        nxt = lst.item(lst.row(item) + 1)
        a_join = menu.addAction(t("board_join"), lambda: self._join_next(lst, item))
        a_join.setEnabled(nxt is not None and _decode(nxt.data(BLOCK_ROLE))[0] == l + 1)
        menu.exec(lst.viewport().mapToGlobal(pos))

    def _move_to(self, item, row):
        lst = self.list_edit
        block = _decode(item.data(BLOCK_ROLE))
        self._syncing = True
        try:
            lst.takeItem(lst.row(item))
            lst.insertItem(row, self._make_item(block))
        finally:
            self._syncing = False
        self._sync_story()

    def refresh_lengths(self, ctx):
        """Cut settings changed: recompute block lengths from (ops, fps, offset)."""
        self._ops_ctx = ctx
        if self.sentences:
            self.list_edit.viewport().update()
            self.list_unused.viewport().update()
            self._refresh_labels()


def build_story_panel(win) -> QFrame:
    """Build the Story board activity panel and bind it to the main window."""
    win.story_board = StoryBoard(win)
    return wrap_activity_panel(win.story_board)
