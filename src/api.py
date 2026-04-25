#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: api.py
ROLE: Logic Layer / DaVinci Resolve Communication
DESCRIPTION:
Translates internal script commands into specific DaVinci Resolve API calls.
Manages timeline, project, and media pool objects.
Acts as the executor for commands from the Engine.
"""

import sys
import time
import os
import re

# Import OSDoctor (as per architecture)
try:
    from osdoc import log_error, log_info
except ImportError:
    # Fallback for testing without osdoc
    def log_error(m): print(f"[ERR] {m}")
    def log_info(m): print(f"[INFO] {m}")

class ResolveHandler:
    def __init__(self, os_doctor):
        """
        Initializes the API handler.
        
        Args:
            os_doctor (OSDoctor): Instance to retrieve system paths.
        """
        self.os_doc = os_doctor
        self.resolve = None
        self.project = None
        self.project_manager = None
        self.media_pool = None
        self.timeline = None
        self.fps = 24.0
        
        # Attempt to load script module
        self._load_resolve_script_module()
        self._connect()

    def _load_resolve_script_module(self):
        """Dynamically imports DaVinciResolveScript using path from OSDoctor."""
        api_path = self.os_doc.get_resolve_api_path()
        if not api_path: return

        try:
            sys.path.append(api_path)
            import DaVinciResolveScript as bmd # type: ignore
            self.bmd = bmd
        except ImportError:
            log_error("Could not import DaVinciResolveScript module.")

    def _connect(self):
        """Establishes connection to the running Resolve instance."""
        try:
            # If imported correctly, get the object
            if hasattr(self, 'bmd'):
                self.resolve = self.bmd.scriptapp("Resolve")
            
            # Fallback if module import failed but we are inside Resolve's python env
            if not self.resolve:
                # Sometimes the object is available globally as 'resolve'
                import __main__
                if hasattr(__main__, "resolve"):
                    self.resolve = __main__.resolve

            if self.resolve:
                self.project_manager = self.resolve.GetProjectManager()
                self.project = self.project_manager.GetCurrentProject()
                if self.project:
                    self.media_pool = self.project.GetMediaPool()
                    self.timeline = self.project.GetCurrentTimeline()
                    self.fps = self.timeline.GetSetting("timelineFrameRate")
                    # Handle string fps (e.g. "24.00")
                    try: self.fps = float(self.fps)
                    except: self.fps = 24.0
                    
                    log_info(f"Connected to Resolve. Project: {self.project.GetName()}, FPS: {self.fps}")
                else:
                    log_error("No project is open in Resolve.")
            else:
                log_error("Could not connect to Resolve API object.")
        except Exception as e:
            log_error(f"Connection Error: {e}")

    def refresh_context(self):
        """Re-fetches current project/timeline in case user switched them."""
        self._connect()

    def get_timeline_start_frame(self):
        """Gets the starting timecode of the timeline in frames."""
        if not self.timeline: return 0  # Default to 0 instead of 3600*fps to act safe
        try:
            return int(self.timeline.GetStartFrame())
        except:
            return 86400 # Fallback 01:00:00:00 at 24fps

    def jump_to_seconds(self, seconds):
        """Moves playhead to a specific second in the timeline."""
        if not self.resolve or not self.timeline: return
        
        # Open Edit Page first
        self.resolve.OpenPage("edit")
        
        start_tc = self.get_timeline_start_frame()
        target_frame = start_tc + int(seconds * self.fps)
        
        self.timeline.SetCurrentTimecode(self._frames_to_tc(target_frame))

    def _frames_to_tc(self, frames):
        """Helper to convert frames to SMPTE Timecode string."""
        fps = int(self.fps)
        if fps == 0: fps = 24
        
        f = frames % fps
        s = (frames // fps) % 60
        m = (frames // (fps * 60)) % 60
        h = (frames // (fps * 3600))
        
        return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"

    def render_audio(self, unique_id, export_path, timeline_name=None, track_indices=None):
        """
        Renders audio from the specified timeline to a WAV file.

        Args:
            unique_id (str): Unique file name prefix.
            export_path (str): Directory to write the WAV file to.
            timeline_name (str|None): Name of the timeline to render. If None,
                uses the currently active timeline.
            track_indices (list[int]|None): 1-based list of audio track indices
                to include. If None or empty, all tracks are rendered (default
                backward-compatible behaviour).

        Returns:
            str|None: Absolute path to the rendered WAV file, or None on failure.
        """
        if not self.project or not self.timeline:
            return None

        target_file = os.path.join(export_path, f"{unique_id}.wav")

        # ── 1. Switch to the requested timeline (if specified) ────────────────
        original_timeline = self.timeline
        switched_timeline = False

        if timeline_name and timeline_name != self.timeline.GetName():
            tl_count = self.project.GetTimelineCount()
            for i in range(1, tl_count + 1):
                tl = self.project.GetTimelineByIndex(i)
                if tl.GetName() == timeline_name:
                    self.project.SetCurrentTimeline(tl)
                    self.timeline = tl
                    switched_timeline = True
                    log_info(f"Switched to timeline: {timeline_name}")
                    break
            if not switched_timeline:
                log_error(f"Timeline '{timeline_name}' not found. Using current timeline.")

        render_timeline = self.timeline

        # ── 2. Mute / solo audio tracks (if specific tracks were requested) ───
        mute_state_backup = []  # List of indices we explicitly muted
        track_isolated = False
        working_set_name = None

        if track_indices:
            a_track_count = render_timeline.GetTrackCount("audio")
            
            # If all tracks are selected, we skip isolation entirely!
            if len(track_indices) == a_track_count:
                track_indices = None

        if track_indices:
            for _set_name, _get_name in [
                ("SetTrackEnable",   "GetTrackEnable"),
                ("SetTrackEnable",   "GetIsTrackEnabled"),
                ("SetTrackEnabled",  "GetIsTrackEnabled"),
                ("SetTrackEnabled",  "GetTrackEnable"),
            ]:
                if track_isolated:
                    break
                try:
                    _set = getattr(render_timeline, _set_name)
                    _get = getattr(render_timeline, _get_name)
                    if not callable(_set) or not callable(_get):
                        continue

                    # Only mute tracks that are CURRENTLY enabled AND NOT in track_indices
                    for idx in range(1, a_track_count + 1):
                        is_enabled = bool(_get("audio", idx))
                        if is_enabled and (idx not in track_indices):
                            _set("audio", idx, False)
                            mute_state_backup.append(idx)

                    track_isolated = True
                    working_set_name = _set_name
                    log_info(f"Track isolation via {_set_name} / {_get_name}: {track_indices}")
                except Exception:
                    mute_state_backup.clear()

            if not track_isolated:
                log_error("Track isolation unavailable in this Resolve version — rendering all audio tracks instead.")

        # ── 3. Configure render and execute ──────────────────────────────────
        render_ok = False
        try:
            self.project.LoadRenderPreset("Audio Only")

            self.project.SetRenderSettings({
                "SelectAllFrames": 1,
                "TargetDir":       export_path,
                "CustomName":      unique_id,
                "ExportVideo":     False,
                "ExportAudio":     True,
                "AudioCodec":      "wav",
                "AudioBitDepth":   16,
                "AudioSampleRate": 48000,
            })

            pid = self.project.AddRenderJob()
            started = self.project.StartRendering(pid)
            if not started:
                self.project.StartRendering()

            time.sleep(0.5)

            while self.project.IsRenderingInProgress():
                time.sleep(1)

            status = self.project.GetRenderJobStatus(pid)
            self.project.DeleteRenderJob(pid)

            render_ok = status.get("JobStatus") == "Complete"
            if not render_ok:
                log_error(f"Render failed. Status: {status}")

        except Exception as e:
            log_error(f"Render error: {e}")
            render_ok = False

        finally:
            # ── 4. Always return to Edit page FIRST ───────────────────────────
            # Resolve silently ignores timeline manipulations if the active page
            # is Deliver (which StartRendering may switch to).
            if self.resolve:
                try:
                    self.resolve.OpenPage("edit")
                    time.sleep(1.0) # slightly longer wait to ensure UI is ready
                except Exception:
                    pass

            # ── 5. Restore muted tracks ──────────────────────────────────────
            if mute_state_backup and working_set_name:
                try:
                    _set = getattr(render_timeline, working_set_name)
                    if callable(_set):
                        for idx in mute_state_backup:
                            _set("audio", idx, True) # we only muted them, so we unmute them
                except Exception as restore_err:
                    log_error(f"Track restore via {working_set_name} failed: {restore_err}")

            # ── 6. Restore original timeline ──────────────────────────────────
            if switched_timeline and original_timeline:
                try:
                    self.project.SetCurrentTimeline(original_timeline)
                    self.timeline = original_timeline
                except Exception as tl_err:
                    log_error(f"Could not restore original timeline: {tl_err}")

        return target_file if render_ok else None

    def get_all_timelines(self):
        """
        Returns a list of all timeline names in the current project.

        Returns:
            list[str]: Timeline names, or [] if no project / no timelines.
        """
        if not self.project:
            return []
        try:
            count = self.project.GetTimelineCount()
            names = []
            for i in range(1, count + 1):
                tl = self.project.GetTimelineByIndex(i)
                if tl:
                    names.append(tl.GetName())
            return names
        except Exception as e:
            log_error(f"get_all_timelines error: {e}")
            return []

    def get_audio_tracks(self, timeline_name=None):
        """
        Returns a list of audio track labels for the specified timeline.
        Only tracks that contain at least one clip are included — empty
        placeholder tracks are excluded.

        Args:
            timeline_name (str|None): Name of the timeline. If None or matches
                the current timeline, the active timeline is used.

        Returns:
            list[str]: Labels like ['A1', 'A3'] (only populated tracks), or [].
        """
        if not self.project:
            return []
        try:
            target_tl = self.timeline

            if timeline_name and (not target_tl or target_tl.GetName() != timeline_name):
                count = self.project.GetTimelineCount()
                for i in range(1, count + 1):
                    tl = self.project.GetTimelineByIndex(i)
                    if tl and tl.GetName() == timeline_name:
                        target_tl = tl
                        break

            if not target_tl:
                return []

            a_count = target_tl.GetTrackCount("audio")
            populated = []
            
            # Resolve's SWIG objects might return None for unknown methods
            _get_name_fn = getattr(target_tl, "GetTrackName", None)
            
            for i in range(1, a_count + 1):
                try:
                    items = target_tl.GetItemListInTrack("audio", i)
                    has_content = bool(items)
                    if has_content:
                        # Try to get the actual user-defined track name
                        track_name = ""
                        if callable(_get_name_fn):
                            try:
                                track_name = _get_name_fn("audio", i)
                            except Exception:
                                pass
                                
                        if not track_name:
                            track_name = f"Audio {i}"
                            
                        populated.append(track_name)
                except Exception:
                    # If the call fails, skip this track safely
                    pass
            return populated

        except Exception as e:
            log_error(f"get_audio_tracks error: {e}")
            return []


    def get_next_badwords_edit_index(self, original_name):
        """
        Calculates the next suffix index for the new timeline.
        """
        # Strip existing suffix
        base_name = re.sub(r" BadWords Edit \d+$", "", original_name)
        
        # Scan existing timelines
        count = 0
        count_map = self.project.GetTimelineCount()
        
        idx = 1
        for i in range(1, count_map + 1):
            tl = self.project.GetTimelineByIndex(i)
            name = tl.GetName()
            if name.startswith(f"{base_name} BadWords Edit "):
                try:
                    curr_idx = int(name.split(" BadWords Edit ")[-1])
                    if curr_idx >= idx: idx = curr_idx + 1
                except: pass
        
        return base_name, idx

    def find_timeline_item_recursive(self, folder, name):
        """Recursively finds a timeline MediaPoolItem by name."""
        for clip in folder.GetClipList():
            if clip.GetClipProperty("Type") == "Timeline" and clip.GetName() == name:
                return clip
        
        for sub in folder.GetSubFolderList():
            res = self.find_timeline_item_recursive(sub, name)
            if res: return res
        return None

    def delete_item(self, item):
        if self.media_pool and item:
            try:
                self.media_pool.DeleteClips([item])
            except:
                pass

    # ── XML Pre-filter Pipeline ─────────────────────────────────────────────

    def export_timeline_xml(self, timeline_name, output_path):
        """
        Exports the named timeline as FCP7 XML to output_path.
        Returns True on success, False otherwise.
        """
        try:
            target_tl = None
            count = self.project.GetTimelineCount()
            for i in range(1, count + 1):
                tl = self.project.GetTimelineByIndex(i)
                if tl.GetName() == timeline_name:
                    target_tl = tl
                    break

            if not target_tl:
                log_error(f"export_timeline_xml: timeline '{timeline_name}' not found.")
                return False

            export_type = getattr(self.resolve, 'EXPORT_FCP_7_XML', None)
            if export_type is None:
                log_error("export_timeline_xml: resolve.EXPORT_FCP_7_XML constant not available.")
                return False

            result = target_tl.Export(output_path, export_type)
            if result:
                log_info(f"Exported timeline XML: {output_path}")
            else:
                log_error(f"export_timeline_xml: Export() returned False for '{timeline_name}'.")
            return bool(result)
        except Exception as e:
            log_error(f"export_timeline_xml error: {e}")
            return False

    def filter_xml_tracks(self, input_path, output_path, track_indices):
        """
        Filters an FCP7 XML file to keep only the specified audio track indices (1-based).
        Video tracks are preserved intact — media paths are untouched.
        Returns True on success, False otherwise.
        """
        try:
            import xml.etree.ElementTree as ET
            # Do NOT call ET.register_namespace — it corrupts namespace declarations on write

            tree = ET.parse(input_path)
            root = tree.getroot()

            keep_set = set(track_indices)

            # Diagnostic: log all media file paths found in XML
            all_paths = [el.text for el in root.iter('pathurl') if el.text]
            log_info(f"filter_xml_tracks: media paths in XML: {all_paths[:10]}")  # first 10

            for audio_section in root.iter('audio'):
                tracks = audio_section.findall('track')
                log_info(f"filter_xml_tracks: found {len(tracks)} audio tracks; keeping {sorted(keep_set)}")
                # Log each track's first clip name for diagnostics
                for i, t in enumerate(tracks):
                    clips = t.findall('.//name')
                    clip_name = clips[0].text if clips else '(unknown)'
                    log_info(f"  track[{i+1}]: first clip='{clip_name}' -> {'KEEP' if (i+1) in keep_set else 'REMOVE'}")
                # Iterate in reverse so removal doesn't shift indices
                for idx, track in reversed(list(enumerate(tracks))):
                    if (idx + 1) not in keep_set:
                        audio_section.remove(track)

            # Write back — preserve exact encoding, no namespace mangling
            tree.write(output_path, encoding="unicode", xml_declaration=False)
            # Prepend UTF-8 declaration manually since encoding='unicode' skips it
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + content)

            log_info(f"Filtered XML written to: {output_path}")
            return True
        except Exception as e:
            log_error(f"filter_xml_tracks error: {e}")
            return False

    def import_xml_as_timeline(self, xml_path):
        """
        Imports an FCP7 XML file into Resolve as a new timeline using
        MediaPool.ImportTimelineFromFile().
        importSourceClips=True tells Resolve to re-link existing media by path.
        Returns the new timeline name (str) or None on failure.
        """
        try:
            if not self.media_pool:
                log_error("import_xml_as_timeline: media_pool not available.")
                return None

            import time as _time
            import_options = {
                "timelineName":      f"BW_Filtered_{int(_time.time())}",
                "importSourceClips": True,   # Critical: must be True to re-link media
            }
            log_info(f"import_xml_as_timeline: calling ImportTimelineFromFile('{xml_path}')")
            new_tl = self.media_pool.ImportTimelineFromFile(xml_path, import_options)

            if not new_tl:
                log_error(f"import_xml_as_timeline: ImportTimelineFromFile returned None for '{xml_path}'.")
                log_error("  Possible causes: XML malformed, media paths wrong, or Resolve API version mismatch.")
                return None

            name = new_tl.GetName()
            log_info(f"import_xml_as_timeline: Imported timeline '{name}' successfully.")

            # Diagnostic: verify track count in imported timeline
            try:
                a_cnt = new_tl.GetTrackCount("audio")
                v_cnt = new_tl.GetTrackCount("video")
                log_info(f"import_xml_as_timeline: result has {v_cnt} video track(s), {a_cnt} audio track(s).")
            except Exception:
                pass

            return name

        except Exception as e:
            log_error(f"import_xml_as_timeline error: {e}")
            return None

    def get_optimal_source_item(self, original_timeline_name):
        """
        AUTO-SOURCING LOGIC:
        Warunek A: Dokładnie 1 nierozcięty klip na osi czasu -> zwraca MediaPoolItem tego klipu.
        Warunek B: Oś pocięta lub wieloklipowa -> zwraca całą oś (Timeline) z Media Pool jako klip.
        """
        if not self.project or not self.media_pool: 
            return None, None

        # 1. Znajdź obiekt osi czasu (Timeline object), aby zliczyć jego zawartość
        target_tl = None
        count = self.project.GetTimelineCount()
        for i in range(1, count + 1):
            tl = self.project.GetTimelineByIndex(i)
            if tl.GetName() == original_timeline_name:
                target_tl = tl
                break
                
        if not target_tl:
            log_error(f"Could not find timeline '{original_timeline_name}'.")
            return None, None

        # 2. Zlicz klipy na wszystkich ścieżkach
        total_v_items = 0
        v_track_count = target_tl.GetTrackCount("video")
        v_clips_all = []
        for i in range(1, v_track_count + 1):
            items = target_tl.GetItemListInTrack("video", i)
            if items: 
                total_v_items += len(items)
                v_clips_all.extend(items)

        total_a_items = 0
        a_track_count = target_tl.GetTrackCount("audio")
        a_clips_all = []
        for i in range(1, a_track_count + 1):
            items = target_tl.GetItemListInTrack("audio", i)
            if items: 
                total_a_items += len(items)
                a_clips_all.extend(items)

        # 3. Logika A/B
        is_single_uncut = False
        source_media_item = None
        context_type = 'video'

        if total_v_items == 1 and total_a_items <= 1:
            v_pool_item = v_clips_all[0].GetMediaPoolItem()
            if total_a_items == 1:
                a_pool_item = a_clips_all[0].GetMediaPoolItem()
                v_path = v_pool_item.GetClipProperty("File Path")
                a_path = a_pool_item.GetClipProperty("File Path")
                
                # Warunek krytyczny: Upewnij się, że wideo i audio pochodzą z tego samego fizycznego pliku
                # Zabezpiecza to przed błędami, gdy użytkownik ręcznie podłożył ścieżkę dźwiękową
                if v_path and a_path and v_path == a_path:
                    source_media_item = v_pool_item
                    is_single_uncut = True
                    context_type = 'video'
            else:
                source_media_item = v_pool_item
                is_single_uncut = True
                context_type = 'video'
                
        elif total_v_items == 0 and total_a_items == 1:
            source_media_item = a_clips_all[0].GetMediaPoolItem()
            is_single_uncut = True
            context_type = 'audio'

        # ZWRÓĆ WYNIK NA PODSTAWIE WARUNKÓW
        if is_single_uncut and source_media_item:
            log_info("Auto-Sourcing: Condition A (Single clip). Using base file.")
            return source_media_item, context_type

        # WARUNEK B (Cały Timeline jako klip)
        log_info("Auto-Sourcing: Condition B (Complex assembly). Using timeline from Media Pool.")
        root_folder = self.media_pool.GetRootFolder()
        timeline_media_item = self.find_timeline_item_recursive(root_folder, original_timeline_name)
        
        context_type = 'audio' if total_v_items == 0 else 'video'
        
        return timeline_media_item, context_type

    # ==========================================
    # TIMELINE GENERATOR FROM OPERATIONS
    # ==========================================

    def generate_timeline_from_ops(self, ops, source_item, new_tl_name, audio_only_mode=False, progress_callback=None):
        if not self.media_pool or not ops: return False
        
        COLOR_MAP = {
            "bad": "Violet", "repeat": "Navy", "typo": "Olive",
            "inaudible": "Chocolate", "silence_mark": "Tan",
            "silence_cut": None, "normal": None 
        }
        
        # [CRITICAL OPTIMIZATION] Lock UI rendering by switching to the Media page
        if self.resolve:
            self.resolve.OpenPage("media")
            
        try:
            log_info(f"Creating timeline: {new_tl_name} (AudioOnly: {audio_only_mode})")
            new_tl = self.media_pool.CreateEmptyTimeline(new_tl_name)
            if not new_tl:
                log_error("Failed to create new timeline.")
                return False
            
            self.project.SetCurrentTimeline(new_tl)
            
            clip_infos = []
            valid_ops = []
            
            for op in ops:
                if op.get('type') == 'silence_cut': continue
                start_f = int(op['s'])
                end_f = int(op['e'])
                if (end_f - start_f) < 2: continue
                
                clip_infos.append({
                    "mediaPoolItem": source_item,
                    "startFrame": start_f,
                    # CRITICAL FIX: Resolve AppendToTimeline uses EXCLUSIVE endFrame
                    # (first frame NOT included in the clip, same as Python slices).
                    # Old code used end_f - 1 (inclusive), which lost 1 frame per clip.
                    # At 55 clips / 25fps that caused ~2.2 seconds of cumulative drift.
                    "endFrame": end_f,
                })
                valid_ops.append(op)

            if not clip_infos:
                log_info("No clips to append.")
                return True

            total_clips = len(clip_infos)
            chunk_size = 50 # Process 50 clips at a time
            
            log_info(f"Starting lazy assembly of {total_clips} clips in chunks of {chunk_size}...")
            
            for i in range(0, total_clips, chunk_size):
                chunk = clip_infos[i:i + chunk_size]
                self.media_pool.AppendToTimeline(chunk)
                
                if progress_callback:
                    current_count = min(i + chunk_size, total_clips)
                    progress_callback(current_count, total_clips)
                    
                # NOTE: time.sleep(0.05) is removed because the UI is frozen on the Media page.

            # Cleanup video if audio_only_mode
            if audio_only_mode:
                video_garbage = new_tl.GetItemListInTrack("video", 1) or []
                if video_garbage:
                    try: new_tl.DeleteClips(video_garbage, False)
                    except: log_error("Failed to delete video garbage clips.")

            # Apply Colors
            video_items = [] if audio_only_mode else (new_tl.GetItemListInTrack("video", 1) or [])
            audio_items = new_tl.GetItemListInTrack("audio", 1) or []
            
            if video_items:
                for i, item in enumerate(video_items):
                    if item and i < len(valid_ops):
                        op_type = str(valid_ops[i]['type'])
                        color = COLOR_MAP.get(op_type)
                        if not color and op_type.startswith("custom_"):
                            color = op_type.split("_")[1]
                        if color: item.SetClipColor(color)
            
            if len(audio_items) == len(valid_ops):
                 for i, item in enumerate(audio_items):
                    if item:
                        op_type = str(valid_ops[i]['type'])
                        color = COLOR_MAP.get(op_type)
                        if not color and op_type.startswith("custom_"):
                            color = op_type.split("_")[1]
                        if color: item.SetClipColor(color)
            else:
                current_rec_head = new_tl.GetStartFrame()
                ops_map = []
                for op in valid_ops:
                    dur = int(op['e']) - int(op['s'])
                    ops_map.append({'op': op, 'start': current_rec_head, 'dur': dur})
                    current_rec_head += dur
                
                for a_item in audio_items:
                    if not a_item: continue
                    a_start = a_item.GetStart()
                    match = next((m for m in ops_map if abs(m['start'] - a_start) <= 2), None)
                    if match:
                        op_type = str(match['op']['type'])
                        color = COLOR_MAP.get(op_type)
                        if not color and op_type.startswith("custom_"):
                            color = op_type.split("_")[1]
                        if color: a_item.SetClipColor(color)

            # Reset Playhead
            try:
                start_frame = new_tl.GetStartFrame()
                new_tl.SetCurrentTimecode(self._frames_to_tc(start_frame))
            except Exception as e:
                log_error(f"Failed to reset playhead: {e}")

            # >>> AGGRESSIVE SWIG/RPC MEMORY CLEANUP <<<
            # We must sever the Python references to Resolve's internal C++ objects.
            # If we don't, the RPC server gets bloated and freezes Resolve on subsequent runs.
            try:
                del video_items
                del audio_items
                del clip_infos
                del valid_ops
                # Delete ops_map if it exists in the local scope
                if 'ops_map' in locals():
                    del ops_map
                del new_tl
            except Exception:
                pass
                
            import gc
            gc.collect()
            # >>> END CLEANUP <<<

            return True

        except Exception as e:
            log_error(f"Generate Timeline Error: {e}")
            import traceback
            log_error(traceback.format_exc())
            return False
            
        finally:
            # ALWAYS return to the Edit page, even if the process failed
            if self.resolve:
                self.resolve.OpenPage("edit")