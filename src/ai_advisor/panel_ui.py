"""AI Advisor panel widget: AIPanel dialog + QThread worker. All Qt code lives here."""

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from ai_advisor import client, clips, mapping
from ai_advisor.panel import (STRINGS, STATUS_HEX, _cfg_from, _job_test_connection,
                              ai_json_path, job_add_markers, job_assemble_clips,
                              job_find_clips, job_list_models, job_suggest_edits,
                              load_ai_prefs, save_ai_prefs)

# ── Worker ───────────────────────────────────────────────────────────────────


class _AIWorker(QThread):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self._fn = fn
        self._args = args

    def run(self):
        try:
            result = self._fn(*self._args, progress=lambda m: self.progress.emit(m))
            self.done.emit(result)
        except Exception as e:  # noqa: BLE001 — surfaced to the panel, never crashes the app
            self.failed.emit(f"{type(e).__name__}: {e}")


# ── Panel ────────────────────────────────────────────────────────────────────

_CARD_QSS = ("QFrame {{ background: #222; border: 1px solid #333; border-radius: 6px; }}"
             "QFrame QLabel {{ border: none; }}")


class AIPanel(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.gui = main_window
        self.os_doc = main_window.engine.os_doc
        self.resolve_handler = getattr(main_window, "resolve_handler", None)
        self._prefs = load_ai_prefs(self.os_doc)
        self._worker = None
        self._edits = []
        self._clips = []

        self.setWindowTitle("BadWords — AI Advisor")
        self.setMinimumSize(560, 520)
        self._t = lambda key: STRINGS[self._lang()].get(key, key)

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)
        self.tabs.addTab(self._build_advisor_tab(), self._t("tab_advisor"))
        self.tabs.addTab(self._build_settings_tab(), self._t("tab_settings"))
        self._load_saved_clips()
        self._refresh_action_states()

    # ── helpers ──────────────────────────────────────────────────────────
    def _lang(self):
        try:
            lang = (self.os_doc.get_all_prefs() or {}).get("language", "en")
        except Exception:
            lang = "en"
        return lang if lang in STRINGS else "en"

    def _words_data(self):
        canvas = getattr(self.gui, "text_canvas", None)
        return getattr(canvas, "words_data", None) or []

    def _resolve_ok(self):
        return bool(self.resolve_handler and self.resolve_handler.timeline)

    def _refresh_action_states(self):
        has_words = bool(self._words_data())
        self.btn_edits.setEnabled(has_words and self._worker is None)
        self.btn_clips.setEnabled(has_words and self._worker is None)
        resolve_on = self._resolve_ok()
        self.btn_preview.setEnabled(resolve_on)
        self.btn_markers.setEnabled(resolve_on and self._worker is None)
        self.btn_assemble.setEnabled(resolve_on and self._worker is None)

    def _start_job(self, on_done, fn, *args):
        """Single active worker; `on_done(result)` is invoked with the job result."""
        if self._worker is not None:
            return
        self.lbl_status.setText(self._t("lbl_working"))
        self._worker = _AIWorker(fn, *args, parent=self)
        self._worker.progress.connect(lambda m: self.lbl_status.setText(m))
        self._worker.done.connect(on_done)
        self._worker.failed.connect(self._on_job_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._refresh_action_states()
        self._worker.start()

    def _on_worker_finished(self):
        self._worker = None
        self.lbl_status.setText(self._t("lbl_idle"))
        self._refresh_action_states()

    def _on_job_failed(self, message):
        self.lbl_status.setText(message)
        QMessageBox.warning(self, self._t("err_title"), message)

    # ── Advisor tab ──────────────────────────────────────────────────────
    def _build_advisor_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        self.btn_edits = QPushButton(self._t("btn_edits"))
        self.btn_clips = QPushButton(self._t("btn_clips"))
        self.btn_accept_all = QPushButton(self._t("btn_accept_all"))
        for b, cb in ((self.btn_edits, self._suggest_edits),
                      (self.btn_clips, self._find_clips),
                      (self.btn_accept_all, self._accept_all)):
            row.addWidget(b)
            b.clicked.connect(cb)
        row.addStretch()
        lay.addLayout(row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.results_host = QWidget()
        self.results_lay = QVBoxLayout(self.results_host)
        self.results_lay.addStretch()
        self.scroll.setWidget(self.results_host)
        lay.addWidget(self.scroll, 1)

        self.lbl_status = QLabel(self._t("lbl_no_results"))
        lay.addWidget(self.lbl_status)

        actions = QHBoxLayout()
        self.btn_apply = QPushButton(self._t("btn_apply").format(n=0))
        self.btn_preview = QPushButton(self._t("btn_preview"))
        self.btn_markers = QPushButton(self._t("btn_markers"))
        self.btn_assemble = QPushButton(self._t("btn_assemble"))
        self.btn_apply.clicked.connect(self._apply_edits)
        self.btn_preview.clicked.connect(self._preview_first_clip)
        self.btn_markers.clicked.connect(self._add_markers)
        self.btn_assemble.clicked.connect(self._assemble_clips)
        for b in (self.btn_apply, self.btn_preview, self.btn_markers, self.btn_assemble):
            actions.addWidget(b)
        lay.addLayout(actions)
        return w

    def _clear_results(self):
        while self.results_lay.count() > 1:  # keep trailing stretch
            item = self.results_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_card(self, build_row):
        card = QFrame()
        card.setStyleSheet(_CARD_QSS)
        lay = QVBoxLayout(card)
        build_row(lay)
        self.results_lay.insertWidget(self.results_lay.count() - 1, card)
        return card

    def _show_edits(self):
        self._clear_results()
        for s in self._edits:
            self._add_card(lambda lay, s=s: self._build_edit_card(lay, s))
        self._update_apply_label()

    def _build_edit_card(self, lay, s):
        hexc = STATUS_HEX.get(s.get("status"), "#888")
        quote = QLabel(f"<b style='color:{hexc}'>{s.get('quote', '')}</b>")
        quote.setWordWrap(True)
        lay.addWidget(quote)
        meta = (f"{s['start']:.1f}s → {s['end']:.1f}s · {s.get('category', 'other')} · "
                f"{s.get('action')}:{s.get('status')} · conf {s.get('confidence', 0):.2f}")
        if not s.get("mapped"):
            meta += f" · <i>{self._t('lbl_unmapped')}</i>"
        if s.get("reason"):
            meta += f"<br>{s['reason']}"
        info = QLabel(meta)
        info.setWordWrap(True)
        lay.addWidget(info)
        row = QHBoxLayout()
        row.addStretch()
        s.setdefault("accepted", None)
        btn_ok = QPushButton(self._t("btn_accept"))
        btn_no = QPushButton(self._t("btn_reject"))
        for b, val in ((btn_ok, True), (btn_no, False)):
            b.setCheckable(True)
            b.setChecked(s["accepted"] is val)
            b.clicked.connect(lambda _=False, st=s, v=val, bb=b:
                              self._toggle_accept(st, v, bb))
            row.addWidget(b)
        btn_ok.setEnabled(bool(s.get("mapped")))
        lay.addLayout(row)

    def _toggle_accept(self, suggestion, value, button):
        suggestion["accepted"] = value if button.isChecked() else None
        self._update_apply_label()

    def _update_apply_label(self):
        n = sum(1 for s in self._edits if s.get("mapped") and s.get("accepted"))
        self.btn_apply.setText(self._t("btn_apply").format(n=n))
        self.btn_apply.setEnabled(n > 0 and self._worker is None)

    def _show_clips(self):
        self._clear_results()
        for c in self._clips:
            self._add_card(lambda lay, c=c: self._build_clip_card(lay, c))

    def _build_clip_card(self, lay, c):
        c.setdefault("accepted", False)
        c.setdefault("marker_added", False)
        title = QLabel(f"<b>{c['title']}</b> · {self._t('lbl_score')} "
                       f"{c.get('score', 0):.2f} · {c.get('platform')}")
        title.setWordWrap(True)
        lay.addWidget(title)
        info = QLabel(f"{c['start']:.1f}s → {c['end']:.1f}s ({c['end'] - c['start']:.0f}s)"
                      + (f"<br>{c['hook']}" if c.get("hook") else "")
                      + (f"<br><i>{c['reason']}</i>" if c.get("reason") else ""))
        info.setWordWrap(True)
        lay.addWidget(info)
        row = QHBoxLayout()
        row.addStretch()
        btn_prev = QPushButton(self._t("btn_preview"))
        btn_prev.clicked.connect(lambda _=False, c=c: self._preview_clip(c))
        chk = QCheckBox()
        chk.setChecked(c["accepted"])
        chk.toggled.connect(lambda v, cc=c: cc.__setitem__("accepted", v))
        row.addWidget(btn_prev)
        row.addWidget(chk)
        if c.get("marker_added"):
            row.addWidget(QLabel("●"))
        lay.addLayout(row)

    # ── actions ──────────────────────────────────────────────────────────
    def _suggest_edits(self):
        if not self._words_data():
            QMessageBox.information(self, self._t("err_title"), self._t("lbl_need_transcript"))
            return
        cfg = _cfg_from(self._prefs)
        self._start_job(self._on_job_done, job_suggest_edits, cfg, self._words_data())

    def _find_clips(self):
        if not self._words_data():
            QMessageBox.information(self, self._t("err_title"), self._t("lbl_need_transcript"))
            return
        cfg = _cfg_from(self._prefs)
        self._start_job(self._on_job_done, job_find_clips, cfg, self._words_data(),
                        list(self._prefs.get("ai_platforms") or ["shorts"]))

    def _on_job_done(self, result):
        if result["kind"] == "edits":
            self._edits = result["items"]
            self._show_edits()
            self._update_apply_label()
        else:
            self._clips = result["items"]
            self._show_clips()
            self._write_ai_json()

    def _accept_all(self):
        if not self._edits:
            return
        for s in self._edits:
            if s.get("mapped"):
                s["accepted"] = True
        self._show_edits()

    def _apply_edits(self):
        try:
            n = mapping.apply_accepted_edits(self.gui, self._edits)
        except Exception as e:  # noqa: BLE001 — containment per spec
            self._log_and_warn(f"apply_accepted_edits failed: {e}")
            return
        self.lbl_status.setText(self._t("lbl_applied").format(n=n))

    def _preview_clip(self, clip):
        if not self._resolve_ok():
            QMessageBox.information(self, self._t("err_title"), self._t("lbl_need_resolve"))
            return
        try:
            self.resolve_handler.jump_to_seconds(float(clip["start"]))
        except Exception as e:  # noqa: BLE001
            self._log_and_warn(f"jump_to_seconds failed: {e}")

    def _preview_first_clip(self):
        for c in self._clips:
            if c.get("accepted"):
                self._preview_clip(c)
                return

    def _add_markers(self):
        payloads = clips.build_marker_payloads(
            self._clips, self.resolve_handler.fps,
            self.resolve_handler.get_timeline_start_frame())
        if not payloads:
            return
        color = self._prefs.get("ai_marker_color", "Purple")
        self._start_job(lambda n: self._on_markers_done(n, payloads),
                        job_add_markers, self.resolve_handler, payloads, color)

    def _on_markers_done(self, count, payloads):
        for c in self._clips:
            for _frame, name, _note, _dur in payloads:
                if f"[AI] {c.get('title')}" == name:
                    c["marker_added"] = True
        self._show_clips()
        self._write_ai_json()
        self.lbl_status.setText(self._t("lbl_markers").format(n=count))

    def _assemble_clips(self):
        accepted = [c for c in self._clips if c.get("accepted")]
        if not accepted:
            return
        if not self._resolve_ok():
            QMessageBox.information(self, self._t("err_title"), self._t("lbl_need_resolve"))
            return
        self.resolve_handler.refresh_context()
        original_tl_name = self.resolve_handler.timeline.GetName()
        fps = self.resolve_handler.fps
        self._start_job(
            lambda name: self.lbl_status.setText(self._t("lbl_assembled").format(name=name)),
            job_assemble_clips, self.resolve_handler, original_tl_name, accepted, fps)

    def _write_ai_json(self):
        try:
            clips.write_ai_json(ai_json_path(self.gui), self._clips,
                                {"base_url": self._prefs["ai_base_url"],
                                 "model": self._prefs["ai_model"]})
        except Exception as e:  # noqa: BLE001 — persistence is best-effort
            self._log_and_warn(f"write_ai_json failed: {e}")

    def _load_saved_clips(self):
        data = clips.read_ai_json(ai_json_path(self.gui))
        if data:
            self._clips = data
            self._show_clips()
            self.lbl_status.setText(self._t("lbl_load_saved").format(n=len(data)))

    def _log_and_warn(self, message):
        try:
            from osdoc import log_error
            log_error(f"[ai_advisor] {message}")
        except Exception:
            pass
        QMessageBox.warning(self, self._t("err_title"), message)

    # ── Settings tab ─────────────────────────────────────────────────────
    def _build_settings_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        prow = QHBoxLayout()
        prow.addWidget(QLabel(self._t("lbl_preset")))
        self.cb_preset = QComboBox()
        self.cb_preset.addItems(["lmstudio", "ollama", "custom"])
        prow.addWidget(self.cb_preset, 1)
        lay.addLayout(prow)

        self.ed_base_url = QLineEdit(self._prefs["ai_base_url"])
        lay.addWidget(QLabel(self._t("lbl_base_url")))
        lay.addWidget(self.ed_base_url)

        self.ed_api_key = QLineEdit(self._prefs["ai_api_key"])
        self.ed_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        lay.addWidget(QLabel(self._t("lbl_api_key")))
        lay.addWidget(self.ed_api_key)

        mrow = QHBoxLayout()
        self.cb_model = QComboBox()
        self.cb_model.setEditable(True)
        self.cb_model.setCurrentText(self._prefs["ai_model"])
        mrow.addWidget(self.cb_model, 1)
        self.btn_refresh_models = QPushButton(self._t("btn_refresh_models"))
        self.btn_refresh_models.clicked.connect(self._refresh_models)
        mrow.addWidget(self.btn_refresh_models)
        lay.addWidget(QLabel(self._t("lbl_model")))
        lay.addLayout(mrow)

        grow = QHBoxLayout()
        self.sp_temperature = QDoubleSpinBox()
        self.sp_temperature.setRange(0.0, 2.0)
        self.sp_temperature.setSingleStep(0.1)
        self.sp_temperature.setValue(float(self._prefs["ai_temperature"]))
        self.sp_max_chars = QSpinBox()
        self.sp_max_chars.setRange(2000, 200000)
        self.sp_max_chars.setValue(int(self._prefs["ai_max_chars"]))
        self.sp_timeout = QSpinBox()
        self.sp_timeout.setRange(10, 900)
        self.sp_timeout.setValue(int(self._prefs["ai_timeout_s"]))
        for label, widget in ((self._t("lbl_temperature"), self.sp_temperature),
                              (self._t("lbl_max_chars"), self.sp_max_chars),
                              (self._t("lbl_timeout"), self.sp_timeout)):
            box = QVBoxLayout()
            box.addWidget(QLabel(label))
            box.addWidget(widget)
            grow.addLayout(box)
        lay.addLayout(grow)

        crow = QHBoxLayout()
        crow.addWidget(QLabel(self._t("lbl_marker_color")))
        self.cb_marker_color = QComboBox()
        try:
            import config
            self.cb_marker_color.addItems(list(config.RESOLVE_COLORS_HEX.keys()))
        except Exception:
            self.cb_marker_color.addItems(["Purple"])
        self.cb_marker_color.setCurrentText(self._prefs["ai_marker_color"])
        crow.addWidget(self.cb_marker_color, 1)
        lay.addLayout(crow)

        lay.addWidget(QLabel(self._t("lbl_platforms")))
        self._platform_checks = []
        prow2 = QHBoxLayout()
        for name in ("shorts", "tiktok", "reels"):
            chk = QCheckBox(name)
            chk.setChecked(name in (self._prefs.get("ai_platforms") or ["shorts"]))
            self._platform_checks.append(chk)
            prow2.addWidget(chk)
        prow2.addStretch()
        lay.addLayout(prow2)

        self.lbl_cloud_warning = QLabel(self._t("lbl_cloud_warning"))
        self.lbl_cloud_warning.setWordWrap(True)
        self.lbl_cloud_warning.setStyleSheet("color: #e2a91c;")
        lay.addWidget(self.lbl_cloud_warning)

        trow = QHBoxLayout()
        self.btn_test = QPushButton(self._t("btn_test"))
        self.btn_test.clicked.connect(self._test_connection)
        trow.addWidget(self.btn_test)
        trow.addStretch()
        lay.addLayout(trow)
        lay.addStretch()

        for widget, prop in ((self.cb_preset, "currentTextChanged"),
                             (self.ed_base_url, "textChanged"),
                             (self.ed_api_key, "textChanged"),
                             (self.cb_model, "currentTextChanged"),
                             (self.sp_temperature, "valueChanged"),
                             (self.sp_max_chars, "valueChanged"),
                             (self.sp_timeout, "valueChanged"),
                             (self.cb_marker_color, "currentTextChanged")):
            getattr(widget, prop).connect(self._save_settings)
        for chk in self._platform_checks:
            chk.toggled.connect(self._save_settings)
        self.cb_preset.currentTextChanged.connect(self._apply_preset)
        self._update_cloud_warning()
        return w

    def _collect_settings(self):
        platforms = [c.text() for c in self._platform_checks if c.isChecked()] or ["shorts"]
        return {
            "ai_provider_preset": self.cb_preset.currentText(),
            "ai_base_url": self.ed_base_url.text().strip(),
            "ai_api_key": self.ed_api_key.text(),
            "ai_model": self.cb_model.currentText().strip(),
            "ai_temperature": self.sp_temperature.value(),
            "ai_max_chars": self.sp_max_chars.value(),
            "ai_timeout_s": self.sp_timeout.value(),
            "ai_marker_color": self.cb_marker_color.currentText(),
            "ai_platforms": platforms,
        }

    def _save_settings(self, *_):
        self._prefs.update(self._collect_settings())
        save_ai_prefs(self.os_doc, self._prefs)
        self._update_cloud_warning()

    def _apply_preset(self, preset):
        base = client.DEFAULT_BASE_URLS.get(preset)
        if base:
            self.ed_base_url.setText(base)

    def _update_cloud_warning(self):
        url = self.ed_base_url.text().lower()
        local = any(h in url for h in ("localhost", "127.0.0.1", "[::1]"))
        self.lbl_cloud_warning.setVisible(not local)

    def _refresh_models(self):
        cfg = _cfg_from(self._collect_settings())
        self._start_job(self._on_models_done, job_list_models, cfg)

    def _on_models_done(self, models):
        current = self.cb_model.currentText()
        self.cb_model.clear()
        self.cb_model.addItems(models)
        if current:
            self.cb_model.setCurrentText(current)

    def _test_connection(self):
        self._save_settings()
        cfg = _cfg_from(self._prefs)
        self._start_job(lambda desc: self.lbl_status.setText(str(desc)),
                        _job_test_connection, cfg)

    # ── lifecycle ────────────────────────────────────────────────────────
    def closeEvent(self, event):
        if self._worker is not None:
            self._worker.requestInterruption()
            self._worker.wait(5000)
        event.accept()
