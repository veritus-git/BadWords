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
from PySide6.QtCore import QThread, Signal

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
        try:
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
                raise RuntimeError("Analysis pipeline failed to produce results.")
            self.finished_ok.emit(words_data, segments_data)
        except Exception as e:
            import traceback
            from osdoc import log_error
            log_error(f"AnalysisWorker error: {e}\n{traceback.format_exc()}")
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
                self.proxy_ready.emit(res_path)
            else:
                self.proxy_failed.emit("Rendered proxy file not produced")
        except Exception as e:
            self.proxy_failed.emit(str(e))





