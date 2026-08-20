#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: preferences.py
ROLE: Core Engine
DESCRIPTION:
Management of persistent user preferences.
"""

import os
import sys
import json
import time
import threading
import shutil
import subprocess
import urllib.request
import re
import traceback
import platform
import random
import difflib  # Essential for on-the-fly fuzzy matching

import config
import algorithms
from osdoc import log_info, log_error

class PreferencesMixin:
    # ==========================================
    # PREFERENCES MANAGEMENT
    def txt(self, key: str, **kwargs) -> str:
        import config
        prefs = self.load_preferences() or {}
        lang = prefs.get("gui_lang", "en")
        text = config.TRANS.get(lang, config.TRANS["en"]).get(key, key)
        if kwargs: return text.format(**kwargs)
        return text

    def save_preferences(self, settings_dict):
        """Delegates all preference saving to OSDoctor's smart router.
        Keys are automatically routed to user.json or settings.json.
        """
        self.os_doc.save_all_prefs(settings_dict)

    def load_preferences(self):
        """Delegates all preference loading to OSDoctor's smart router.
        Returns a merged dict of user data + settings.
        """
        return self.os_doc.get_all_prefs()

    def send_telemetry_ping(self, event_name="app_started"):
        """
        Asynchronously sends a telemetry ping to PostHog.
        Only sends with user consent and only once per version.
        """
        try:
            # 1. Check opt-in flag — account for string parsing from JSON
            opt_in = self.os_doc.get_telemetry_pref("telemetry_opt_in")
            if opt_in not in [True, "True", "true", 1, "1"]:
                log_info("Telemetry: Oczekuje na zgode lub zgoda zostala odrzucona.")
                return 
            
            last_ping = self.os_doc.get_telemetry_pref("last_pinged_version")
            current_version = config.VERSION
            
            if last_ping == current_version:
                log_info(f"Telemetry: Ping for version {current_version} already sent. Skipping.")
                return 

            if getattr(self, "_telemetry_pinging", False):
                log_info("Telemetry: Ping attempt already in progress. Skipping duplicate thread.")
                return
                
            self._telemetry_pinging = True
            
            # Global marker allowing identification as "Update" even after full app removal
            global_marker = os.path.join(self.os_doc.home_dir, ".badwords_installed")
            
            if not last_ping:
                if os.path.exists(global_marker):
                    install_type = "Update"
                else:
                    install_type = "New Install"
                    try:
                        with open(global_marker, "w", encoding="utf-8") as f:
                            f.write(current_version)
                    except Exception: pass
            else:
                install_type = "Update"
                try:
                    if not os.path.exists(global_marker):
                        with open(global_marker, "w", encoding="utf-8") as f:
                            f.write(current_version)
                except Exception: pass
                
            uuid_str = self.os_doc.get_telemetry_pref("analytics_uuid") or "unknown"
            allow_geo = self.os_doc.get_telemetry_pref("telemetry_allow_geo")
            machine_id = self.os_doc.get_telemetry_pref("analytics_uuid") or ""
            
            def _ping_thread():
                import ssl
                try:
                    # distinct_id duplicated in properties and at top level for safety (PostHog API requirement)
                    payload = {
                        "api_key": getattr(config, "POSTHOG_API_KEY", ""),
                        "event": event_name,
                        "distinct_id": uuid_str, 
                        "properties": {
                            "distinct_id": uuid_str,
                            "version": current_version,
                            "os": self.os_doc.os_type,
                            "install_type": install_type,
                            "$lib": "urllib_python"
                        }
                    }
                    if not allow_geo:
                        payload["properties"]["$geoip_disable"] = True
                    
                    if machine_id == "762c22f5-0dbe-8238-43d4-31c0d0d33d5a":
                        payload["properties"]["is_dev_env"] = True
                        log_info("Dev environment recognized. Telemetry ping flagged as is_dev_env.")
                    
                    if not payload["api_key"] or "TUTAJ_WKLEISZ" in payload["api_key"]:
                        log_info("Telemetry skip: Default/Empty API Key in config.")
                        return

                    data = json.dumps(payload).encode('utf-8')
                    host = getattr(config, "POSTHOG_HOST", "https://eu.i.posthog.com")
                    url = f"{host.rstrip('/')}/capture/"
                    
                    # Removed User-Agent, added Accept. Prevents blocking by Cloudflare.
                    headers = {
                        'Content-Type': 'application/json',
                        'Accept': '*/*'
                    }
                    req = urllib.request.Request(url, data=data, headers=headers)
                    
                    # OMINIECIE PROBLEMU Z BRAKIEM CERTYFIKATOW SSL W PORTABLE PYTHON
                    try:
                        import certifi
                        ctx = ssl.create_default_context(cafile=certifi.where())
                    except ImportError:
                        ctx = ssl.create_default_context()
                    
                    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                        if response.getcode() == 200:
                            self.os_doc.set_telemetry_pref("last_pinged_version", current_version)
                            log_info(f"Telemetry ping sent successfully ({install_type} - {current_version}).")
                        else:
                            log_error(f"Telemetry ping failed with HTTP code {response.getcode()}")
                except Exception as e:
                    log_error(f"Telemetry ping HTTP request failed: {e}")
                finally:
                    self._telemetry_pinging = False

            threading.Thread(target=_ping_thread, daemon=True).start()

        except Exception as e:
            self._telemetry_pinging = False
            log_error(f"Telemetry initialization failed: {e}")

    def save_project_state(self, file_path, data_packet):
        try:
            # Optimize floats
            optimized_words = []
            for w in data_packet.get("words_data", []):
                w_clean = w.copy()
                w_clean['start'] = round(w['start'], 3)
                w_clean['end'] = round(w['end'], 3)
                if 'seg_start' in w_clean: w_clean['seg_start'] = round(w['seg_start'], 3)
                if 'seg_end' in w_clean: w_clean['seg_end'] = round(w['seg_end'], 3)
                optimized_words.append(w_clean)

            # Optimize chapters floats if present
            chapters = data_packet.get("chapters", [])
            for ch in chapters:
                if "words" in ch:
                    ch_words = []
                    for w in ch["words"]:
                        w_clean = w.copy()
                        w_clean['start'] = round(w['start'], 3)
                        w_clean['end'] = round(w['end'], 3)
                        if 'seg_start' in w_clean: w_clean['seg_start'] = round(w['seg_start'], 3)
                        if 'seg_end' in w_clean: w_clean['seg_end'] = round(w['seg_end'], 3)
                        ch_words.append(w_clean)
                    ch["words"] = ch_words

            project_state = data_packet.copy()
            project_state["version"] = config.VERSION
            project_state["timestamp"] = time.time()
            project_state["words_data"] = optimized_words
            if "chapters" in project_state:
                project_state["chapters"] = chapters

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_state, f, separators=(',', ':'))
            return True
        except Exception as e:
            log_error(f"Save Project Error: {e}")
            raise e

    def load_project_state(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                project_state = json.load(f)
            
            words = project_state.get("words_data", [])
            segments = self._reconstruct_segments(words)
            
            return project_state, segments
        except Exception as e:
            log_error(f"Load Project Error: {e}")
            raise e

    def _reconstruct_segments(self, words_data):
        segments = []
        current_seg = []
        for w in words_data:
            if w.get('is_segment_start') and current_seg:
                segments.append(current_seg)
                current_seg = []
            current_seg.append(w)
        if current_seg: segments.append(current_seg)
        return segments

    def save_bws(self, file_path, data_packet, audio_path=None, drt_path=None,
                 assembly_recipe=None, timeline_fingerprint=None, media_inventory=None):
        """
        Save project as .bws archive (ZIP-based).

        Archive structure:
            project.json           — transcript data, chapters, source info
            manifest.json          — archive metadata, fingerprints, file inventory
            audio/source.flac       — source audio converted to FLAC (preview-only)
            timeline/source.drt    — original unedited DaVinci timeline (optional)
            recipes/assembly_ops.json — FFmpeg recipe to recreate assembled audio
        """
        import zipfile
        import hashlib
        from datetime import datetime, timezone

        try:
            # 1. Build optimized project.json (reuse existing logic)
            optimized_words = self._optimize_words_floats(data_packet.get("words_data", []))
            chapters = data_packet.get("chapters", [])
            for ch in chapters:
                if "words" in ch:
                    ch["words"] = self._optimize_words_floats(ch["words"])

            project_state = data_packet.copy()
            project_state["version"] = config.VERSION
            project_state["timestamp"] = time.time()
            project_state["words_data"] = optimized_words
            if "chapters" in project_state:
                project_state["chapters"] = chapters

            # Strip absolute audio path from words_data for portability
            for w in project_state.get("words_data", []):
                w.pop("meta_audio_path", None)
            for ch in project_state.get("chapters", []):
                for w in ch.get("words", []):
                    w.pop("meta_audio_path", None)

            project_json_bytes = json.dumps(project_state, separators=(',', ':')).encode('utf-8')

            # 2. Convert WAV → FLAC (if audio available)
            flac_temp_path = None
            if audio_path and os.path.exists(audio_path):
                flac_temp_path = audio_path.rsplit('.', 1)[0] + '_bws_preview.flac'
                if not self._convert_wav_to_flac(audio_path, flac_temp_path):
                    flac_temp_path = None  # Fallback: no audio in archive

            # 3. Build manifest
            manifest = {
                "bws_version": 2,
                "badwords_version": config.VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "platform": platform.system(),
                "timeline_fingerprint": timeline_fingerprint,
                "timeline_name": (data_packet.get("transcription_source") or {}).get("timeline_name", ""),
                "resolve_project": self._get_resolve_project_name(),
                "media_inventory": media_inventory or [],
                "files": {}
            }

            # 4. Create ZIP
            with zipfile.ZipFile(file_path, 'w') as zf:
                # project.json (compressed)
                zf.writestr('project.json', project_json_bytes, compress_type=zipfile.ZIP_DEFLATED)
                manifest["files"]["project.json"] = {"size": len(project_json_bytes)}

                # audio/source.flac (stored — already compressed by Vorbis)
                if flac_temp_path and os.path.exists(flac_temp_path):
                    zf.write(flac_temp_path, 'audio/source.flac', compress_type=zipfile.ZIP_STORED)
                    manifest["files"]["audio/source.flac"] = {"size": os.path.getsize(flac_temp_path)}

                # timeline/source.drt (stored — already a ZIP itself)
                if drt_path and os.path.exists(drt_path):
                    zf.write(drt_path, 'timeline/source.drt', compress_type=zipfile.ZIP_STORED)
                    manifest["files"]["timeline/source.drt"] = {"size": os.path.getsize(drt_path)}

                # recipes/assembly_ops.json (compressed)
                if assembly_recipe:
                    recipe_bytes = json.dumps(assembly_recipe, separators=(',', ':')).encode('utf-8')
                    zf.writestr('recipes/assembly_ops.json', recipe_bytes, compress_type=zipfile.ZIP_DEFLATED)
                    manifest["files"]["recipes/assembly_ops.json"] = {"size": len(recipe_bytes)}

                # manifest.json (compressed, written last so file sizes are known)
                manifest_bytes = json.dumps(manifest, indent=2).encode('utf-8')
                zf.writestr('manifest.json', manifest_bytes, compress_type=zipfile.ZIP_DEFLATED)

            log_info(f"save_bws: wrote {file_path} ({os.path.getsize(file_path)} bytes)")

            # Cleanup temp FLAC
            if flac_temp_path and os.path.exists(flac_temp_path):
                try: os.remove(flac_temp_path)
                except Exception: pass

            return True

        except Exception as e:
            log_error(f"save_bws error: {e}\n{traceback.format_exc()}")
            # Cleanup temp FLAC on error
            if flac_temp_path and os.path.exists(flac_temp_path):
                try: os.remove(flac_temp_path)
                except Exception: pass
            raise e

    def load_bws(self, file_path):
        """
        Load project from .bws archive.

        Returns:
            (project_state, segments, bws_extras)
            bws_extras is a dict with:
                - audio_path: str|None — path to extracted FLAC in temp
                - drt_path: str|None — path to extracted DRT in temp
                - assembly_recipe: dict|None — FFmpeg recipe for assembled audio
                - manifest: dict — full manifest
                - media_inventory: list — source file references
                - timeline_fingerprint: str|None — SHA-256 content hash
        """
        import zipfile

        try:
            temp_dir = self.os_doc.get_temp_folder()
            bws_extract_dir = os.path.join(temp_dir, f"bws_import_{int(time.time())}")
            os.makedirs(bws_extract_dir, exist_ok=True)

            manifest = {}
            audio_path = None
            drt_path = None
            assembly_recipe = None

            with zipfile.ZipFile(file_path, 'r') as zf:
                namelist = zf.namelist()

                # 1. Read project data
                project_state = json.loads(zf.read('project.json'))

                # 2. Read manifest
                if 'manifest.json' in namelist:
                    manifest = json.loads(zf.read('manifest.json'))

                # 3. Extract audio to temp
                if 'audio/source.flac' in namelist:
                    audio_path = os.path.join(bws_extract_dir, 'source.flac')
                    with zf.open('audio/source.flac') as src, open(audio_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)

                # 4. Extract DRT to temp
                if 'timeline/source.drt' in namelist:
                    drt_path = os.path.join(bws_extract_dir, 'source.drt')
                    with zf.open('timeline/source.drt') as src, open(drt_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)

                # 5. Read assembly recipe
                if 'recipes/assembly_ops.json' in namelist:
                    assembly_recipe = json.loads(zf.read('recipes/assembly_ops.json'))

            # Inject audio path into words_data so AudioPreview can find it
            words = project_state.get('words_data', [])
            if audio_path and words:
                words[0]['meta_audio_path'] = audio_path

            segments = self._reconstruct_segments(words)

            bws_extras = {
                "audio_path": audio_path,
                "drt_path": drt_path,
                "assembly_recipe": assembly_recipe,
                "manifest": manifest,
                "media_inventory": manifest.get("media_inventory", []),
                "timeline_fingerprint": manifest.get("timeline_fingerprint"),
                "timeline_name": manifest.get("timeline_name", ""),
                "resolve_project": manifest.get("resolve_project", ""),
                "extract_dir": bws_extract_dir,
            }

            log_info(f"load_bws: loaded from {file_path} "
                     f"(audio={'yes' if audio_path else 'no'}, "
                     f"drt={'yes' if drt_path else 'no'}, "
                     f"recipe={'yes' if assembly_recipe else 'no'})")

            return project_state, segments, bws_extras

        except Exception as e:
            log_error(f"load_bws error: {e}\n{traceback.format_exc()}")
            raise e

