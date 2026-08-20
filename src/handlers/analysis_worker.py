from PySide6.QtCore import QThread, Signal

class AnalysisWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
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
            words_data, segments_data = func(
                self.settings,
                callback_status=self.status.emit,
                callback_progress=self.progress.emit
            )
            self.finished_ok.emit(words_data, segments_data)
        except Exception as e:
            self.error.emit(str(e))




