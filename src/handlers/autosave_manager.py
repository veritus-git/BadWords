class AutoSaveManager:
    """Transparent background auto-save with debouncing."""
    
    def __init__(self, engine, saves_dir):
        from PySide6.QtCore import QTimer
        import os
        self._engine = engine
        os.makedirs(saves_dir, exist_ok=True)
        self._save_path = os.path.join(saves_dir, "recovery.bws")
        self._meta_path = os.path.join(saves_dir, "recovery_meta.json")
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_save)
        self._pending_packet_fn = None
        self._DEBOUNCE_MS = 3000
    
    def schedule(self, data_packet_fn):
        """Schedule an auto-save. data_packet_fn is called only when save fires."""
        self._pending_packet_fn = data_packet_fn
        if not self._timer.isActive():
            self._timer.start(self._DEBOUNCE_MS)
    
    def _do_save(self):
        """Execute auto-save in background thread — invisible to user."""
        if not self._pending_packet_fn: return
        try:
            result = self._pending_packet_fn()
            if isinstance(result, tuple) and len(result) == 2:
                packet, bws_extras = result
            else:
                packet, bws_extras = result, {}
        except Exception:
            return
        import threading
        threading.Thread(target=self._save_worker, args=(packet, bws_extras), daemon=True).start()
    
    def _save_worker(self, packet, bws_extras=None):
        try:
            import json, time, os
            import config
            
            bws_extras = bws_extras or {}
            # Try to grab audio path if available
            audio_path = bws_extras.get("audio_path")
            if not audio_path:
                words = packet.get("words_data", [])
                if words and words[0].get("meta_audio_path"):
                    audio_path = words[0].get("meta_audio_path")
                
            self._engine.save_bws(
                self._save_path, 
                packet, 
                audio_path=audio_path,
                drt_path=bws_extras.get("drt_path"),
                assembly_recipe=bws_extras.get("assembly_recipe"),
                timeline_fingerprint=bws_extras.get("timeline_fingerprint"),
                media_inventory=bws_extras.get("media_inventory")
            )
            # Write metadata alongside for crash recovery
            t_name = packet.get("transcription_source", {}).get("timeline_name", "")
            meta = {
                "timeline_name": t_name,
                "project_name": t_name,
                "resolve_project": self._engine._get_resolve_project_name(),
                "saved_at": time.time(),
                "timestamp": time.strftime("%H:%M:%S"),
                "badwords_version": config.VERSION
            }
            with open(self._meta_path, 'w') as f:
                json.dump(meta, f)
        except Exception as e:
            from osdoc import log_error
            log_error(f"AutoSave failed: {e}")

