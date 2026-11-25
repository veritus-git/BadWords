#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: analysis_worker.py
ROLE: Background Handler
DESCRIPTION:
Background thread processing analysis jobs without freezing the GUI.
"""

import inspect
import os
import traceback
from PySide6.QtCore import QThread, Signal


def is_technical_analysis_error(exc: Exception, msg: str = "") -> bool:
    """
    Returns True ONLY for unexpected technical errors that should generate a crash report.
    User-side network/firewall errors, disk-full conditions, missing input files, and
    cancellations are filtered out so user noise never pollutes telemetry.
    """
    text = f"{exc} {msg}".lower()
    if exc.__class__.__name__ == "ModelDownloadError":
        if "no space left" in text or "errno 28" in text:
            return False
        return bool(getattr(exc, "technical", False))

    non_bug_markers = (
        "no space left",
        "errno 28",
        "no such file",
        "does not exist",
        "not found",
        "no audio",
        "no clips",
        "empty audio",
        "cancelled",
        "canceled",
        "localentrynotfounderror",
        "connectionerror",
        "connecttimeout",
        "readtimeout",
        "name resolution",
        "getaddrinfo",
        "network is unreachable",
        "firewall",
    )
    if any(m in text for m in non_bug_markers):
        return False
    return True


def _maybe_send_analysis_crash_report(engine, exc: Exception, tb_text: str):
    """Submits an opt-in sanitized crash report for unexpected AnalysisWorker failures."""
    try:
        from startup import crash_report
        src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os_doc = getattr(engine, "os_doc", None) if engine is not None else None
        app_data_dir = getattr(os_doc, "app_data_dir", None) if os_doc is not None else None
        if crash_report.get_auto_crash_report_pref(src_dir, app_data_dir=app_data_dir) is not True:
            return
        err_msg = f"{type(exc).__name__}: {exc}"
        crash_report.send_report_async(
            err_msg,
            tb_text=tb_text,
            src_dir=src_dir,
            timeout=15,
            category="Auto crash (AnalysisWorker)",
            app_data_dir=app_data_dir,
            bypass_rate_limit=False,
        )
    except Exception:
        pass


class AnalysisWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    chunk_ready = Signal(dict)
    finished_ok = Signal(object, object)
    error = Signal(str)

    def __init__(self, engine, pipeline_func_name, settings):
        super().__init__()
        self.engine = engine
        self.pipeline_func_name = pipeline_func_name
        self.settings = settings

    def run(self):
        captured_tb = ""
        try:
            if hasattr(self.engine, "last_pipeline_error"):
                self.engine.last_pipeline_error = None
            func = getattr(self.engine, self.pipeline_func_name)
            sig = inspect.signature(func)
            kwargs = {
                'callback_status': self.status.emit,
                'callback_progress': self.progress.emit,
            }
            if 'callback_chunk' in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                kwargs['callback_chunk'] = self.chunk_ready.emit

            words_data, segments_data = func(
                self.settings,
                **kwargs
            )
            if words_data is None and segments_data is None:
                pipe_err = getattr(self.engine, "last_pipeline_error", None)
                if isinstance(pipe_err, tuple) and len(pipe_err) == 2 and isinstance(pipe_err[0], Exception):
                    captured_tb = str(pipe_err[1] or "")
                    raise pipe_err[0]
                raise RuntimeError("Analysis pipeline failed to produce results.")
            self.finished_ok.emit(words_data, segments_data)
        except Exception as e:
            from osdoc import log_error
            tb_text = captured_tb or traceback.format_exc()
            log_error(f"AnalysisWorker error: {e}\n{tb_text}")
            if is_technical_analysis_error(e, str(e)):
                _maybe_send_analysis_crash_report(self.engine, e, tb_text)
            self.error.emit(str(e))


class BackgroundProxyWorker(QThread):
    proxy_ready = Signal(str)
    proxy_failed = Signal(str)

    def __init__(self, engine, clips_info: list, output_proxy_mp4: str, target_fps: float = 30.0):
        super().__init__()
        self.engine = engine
        self.clips_info = clips_info
        self.output_proxy_mp4 = output_proxy_mp4
        self.target_fps = target_fps
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            import os
            ok = self.engine.generate_preview_proxy(
                self.clips_info,
                self.output_proxy_mp4,
                target_fps=self.target_fps,
                is_cancelled_cb=lambda: self._is_cancelled
            )
            if self._is_cancelled:
                return
            if ok and os.path.isfile(self.output_proxy_mp4) and os.path.getsize(self.output_proxy_mp4) > 0:
                self.proxy_ready.emit(self.output_proxy_mp4)
            else:
                self.proxy_failed.emit("Proxy generation returned False")
        except Exception as e:
            self.proxy_failed.emit(str(e))


class ResolveTimelineProxyWorker(QThread):
    proxy_ready = Signal(str)
    proxy_failed = Signal(str)
    progress = Signal(int)

    def __init__(self, engine, timeline_name: str, export_path: str, unique_id: str):
        super().__init__()
        self.engine = engine
        self.timeline_name = timeline_name
        self.export_path = export_path
        self.unique_id = unique_id
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            import os
            handler = getattr(self.engine, 'resolve_handler', None)
            if not handler:
                self.proxy_failed.emit("Resolve handler not available")
                return

            def on_progress(p):
                if not self._is_cancelled:
                    self.progress.emit(p)

            res_path = handler.render_timeline_video_proxy(
                self.timeline_name,
                self.export_path,
                self.unique_id,
                progress_callback=on_progress,
                is_cancelled_cb=lambda: self._is_cancelled
            )
            if self._is_cancelled:
                return

            if res_path and os.path.isfile(res_path) and os.path.getsize(res_path) > 0:
                audio_wav = getattr(self.engine, 'current_analysis_audio_path', None) or getattr(self.engine, 'last_audio_path', None)
                if audio_wav and os.path.isfile(audio_wav) and hasattr(self.engine, 'mux_audio_into_proxy'):
                    self.engine.mux_audio_into_proxy(res_path, audio_wav)
                if self._is_cancelled:
                    return
                self.proxy_ready.emit(res_path)
            else:
                self.proxy_failed.emit("Rendered proxy file not produced")
        except Exception as e:
            self.proxy_failed.emit(str(e))





