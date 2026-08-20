class UndoManager:
    def __init__(self, main_window, canvas):
        from collections import deque
        self.main_window = main_window
        self.canvas = canvas
        self.max_size = 50
        self.undo_stack = deque(maxlen=self.max_size)
        self.redo_stack = deque(maxlen=self.max_size)

    def push(self, action):
        if not action or not action.get('changes'):
            return
        self.undo_stack.append(action)
        self.redo_stack.clear()
        
        if hasattr(self.main_window, 'autosave_manager'):
            self.main_window.autosave_manager.schedule(self.main_window._build_autosave_payload)

    def undo(self):
        if not self.undo_stack: return
        action = self.undo_stack.pop()
        redo_action = self._apply_action(action)
        self.redo_stack.append(redo_action)
        self.canvas.update()
        
        if hasattr(self.main_window, 'autosave_manager'):
            self.main_window.autosave_manager.schedule(self.main_window._build_autosave_payload)

    def redo(self):
        if not self.redo_stack: return
        action = self.redo_stack.pop()
        undo_action = self._apply_action(action)
        self.undo_stack.append(undo_action)
        self.canvas.update()
        
        if hasattr(self.main_window, 'autosave_manager'):
            self.main_window.autosave_manager.schedule(self.main_window._build_autosave_payload)

    def _apply_action(self, action):
        reverse_changes = {}
        id_map = {wo['id']: wo for wo in self.canvas.words_data}
        layer_engine = getattr(self.main_window, '_calculate_visual_layer', None)

        for wid, state in action['changes'].items():
            word_obj = id_map.get(wid)
            if not word_obj: continue

            # Save current state for reverse action
            reverse_changes[wid] = {
                'status': word_obj.get('status'),
                'manual_status': word_obj.get('manual_status'),
                'algo_status': word_obj.get('algo_status'),
                'is_auto': word_obj.get('is_auto'),
                'selected': word_obj.get('selected')
            }

            # Apply restored state
            word_obj['status'] = state.get('status')
            word_obj['manual_status'] = state.get('manual_status')
            if 'algo_status' in state:
                word_obj['algo_status'] = state.get('algo_status')
            word_obj['is_auto'] = state.get('is_auto')
            word_obj['selected'] = state.get('selected')
            word_obj['overlay_suppressed'] = True

            if layer_engine:
                layer_engine(word_obj)

        return {"type": "paint", "changes": reverse_changes}


