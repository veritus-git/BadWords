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

    def render_audio(self, unique_id, export_path):
        """
        Renders the current timeline audio to a WAV file.
        """
        if not self.project or not self.timeline: return None
        
        target_file = os.path.join(export_path, f"{unique_id}.wav")
        
        # Save current render settings to restore later
        self.project.LoadRenderPreset("Audio Only")
        
        self.project.SetRenderSettings({
            "SelectAllFrames": 1,
            "TargetDir": export_path,
            "CustomName": unique_id,
            "ExportVideo": False,
            "ExportAudio": True,
            "AudioCodec": "wav",
            "AudioBitDepth": 16,
            "AudioSampleRate": 48000
        })
        
        pid = self.project.AddRenderJob()
        self.project.StartRendering(pid)
        
        # Wait loop
        while self.project.IsRenderingInProgress():
            time.sleep(1)
            
        # Check status
        status = self.project.GetRenderJobStatus(pid)
        self.project.DeleteRenderJob(pid)
        
        if status.get("JobStatus") == "Complete":
            return target_file
        else:
            log_error(f"Render failed. Status: {status}")
            return None

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
            log_info("Auto-Sourcing: Warunek A (Jeden klip). Użyto pliku bazowego.")
            return source_media_item, context_type

        # WARUNEK B (Cały Timeline jako klip)
        log_info("Auto-Sourcing: Warunek B (Złożony montaż). Użyto osi czasu z Media Pool.")
        root_folder = self.media_pool.GetRootFolder()
        timeline_media_item = self.find_timeline_item_recursive(root_folder, original_timeline_name)
        
        context_type = 'audio' if total_v_items == 0 else 'video'
        
        return timeline_media_item, context_type

    # ==========================================
    # TIMELINE GENERATOR FROM OPERATIONS
    # ==========================================

    def generate_timeline_from_ops(self, ops, source_item, new_tl_name, audio_only_mode=False, progress_callback=None):
        """
        Creates a new timeline and assembles it based on the operations list.
        Explicitly colors tracks using Index-Based Coloring.
        Includes Lazy-Assemble (chunking) to prevent DaVinci Resolve from freezing.
        
        Args:
            ops: List of cut operations.
            source_item: MediaPoolItem to append.
            new_tl_name: Name for the new timeline.
            audio_only_mode: If True, ensures result has no video track/clips.
            progress_callback: Function to report progress back to the Engine/GUI.
        """
        if not self.media_pool or not ops: return False
        
        # UPDATED COLOR MAP
        COLOR_MAP = {
            "bad": "Violet",
            "repeat": "Navy",
            "typo": "Olive",
            "inaudible": "Chocolate",
            "silence_mark": "Beige",
            "silence_cut": None, 
            "normal": None 
        }
        
        try:
            # 1. Create New Timeline
            log_info(f"Creating timeline: {new_tl_name} (AudioOnly: {audio_only_mode})")
            new_tl = self.media_pool.CreateEmptyTimeline(new_tl_name)
            if not new_tl:
                log_error("Failed to create new timeline.")
                return False
            
            self.project.SetCurrentTimeline(new_tl)
            
            # 2. Prepare Clip Info List for AppendToTimeline
            clip_infos = []
            valid_ops = [] # Ops that actually result in clips
            
            for op in ops:
                op_type = op.get('type')
                if op_type == 'silence_cut': 
                    continue
                    
                start_f = int(op['s'])
                end_f = int(op['e'])
                duration = end_f - start_f
                
                if duration <= 1: continue 
                
                # Create Clip Info for Append
                clip_info = {
                    "mediaPoolItem": source_item,
                    "startFrame": start_f,
                    "endFrame": end_f - 1 
                }
                clip_infos.append(clip_info)
                valid_ops.append(op)

            # 3. Batch Append (LAZY ASSEMBLE CHUNKING)
            if not clip_infos:
                log_info("No clips to append.")
                return True

            total_clips = len(clip_infos)
            chunk_size = 10
            
            log_info(f"Starting lazy assembly of {total_clips} clips in chunks of {chunk_size}...")
            
            for i in range(0, total_clips, chunk_size):
                chunk = clip_infos[i:i + chunk_size]
                self.media_pool.AppendToTimeline(chunk)
                
                if progress_callback:
                    current_count = min(i + chunk_size, total_clips)
                    progress_callback(current_count, total_clips)
                
                # Ułamek sekundy opóźnienia, aby interfejs Resolve'a zarejestrował i wyrenderował zmiany
                time.sleep(0.05) 
            
            # 3.5. CLEANUP FOR AUDIO ONLY MODE
            # If user wanted audio only, but source clip had video (e.g. mp4 file),
            # Resolve appended both Video and Audio tracks. We must delete Video track content.
            if audio_only_mode:
                video_garbage = new_tl.GetItemListInTrack("video", 1) or []
                if video_garbage:
                    log_info("Audio Only Mode: Cleaning up video track.")
                    # In API, deleting items from timeline usually requires list of items
                    # Note: DeleteClips is a method of Timeline object in newer APIs?
                    # Fallback: DeleteTrack not always available safely without impacting Audio.
                    # Best way: Delete the clips themselves.
                    try:
                        new_tl.DeleteClips(video_garbage, False) # False = No Ripple (safe)
                    except:
                        log_error("Failed to delete video garbage clips.")

            # 4. ROBUST INDEX-BASED COLORING
            
            # Get Items (Check existence)
            video_items = []
            if not audio_only_mode:
                video_items = new_tl.GetItemListInTrack("video", 1) or []
            
            audio_items = new_tl.GetItemListInTrack("audio", 1) or []
            
            # Apply to Video (Only if not in audio mode and items exist)
            if video_items:
                for i, item in enumerate(video_items):
                    if item and i < len(valid_ops):
                        op_type = valid_ops[i]['type']
                        color = COLOR_MAP.get(op_type)
                        if color: item.SetClipColor(color)
            
            # Apply to Audio
            # Match coloring logic with video if possible, else use sync
            if len(audio_items) == len(valid_ops):
                 # Perfect match (1:1 with ops)
                 for i, item in enumerate(audio_items):
                    if item:
                        op_type = valid_ops[i]['type']
                        color = COLOR_MAP.get(op_type)
                        if color: item.SetClipColor(color)
            else:
                # Fallback: Color Audio by checking start time match against ops timing
                log_info("Audio item count mismatch. Using time-sync for Audio coloring.")
                current_rec_head = new_tl.GetStartFrame()
                
                # Create a map of Ops timing
                ops_map = []
                for op in valid_ops:
                    dur = int(op['e']) - int(op['s'])
                    ops_map.append({'op': op, 'start': current_rec_head, 'dur': dur})
                    current_rec_head += dur
                
                for a_item in audio_items:
                    if not a_item: continue
                    a_start = a_item.GetStart()
                    # Find op that matches this start time
                    match = next((m for m in ops_map if abs(m['start'] - a_start) <= 2), None)
                    
                    if match:
                        color = COLOR_MAP.get(match['op']['type'])
                        if color: a_item.SetClipColor(color)

            # NEW: Reset Playhead to Start (Home)
            # This ensures the user starts viewing the timeline from the beginning.
            try:
                start_frame = new_tl.GetStartFrame()
                start_tc_str = self._frames_to_tc(start_frame)
                new_tl.SetCurrentTimecode(start_tc_str)
            except Exception as e:
                log_error(f"Failed to reset playhead: {e}")

            return True

        except Exception as e:
            log_error(f"Generate Timeline Error: {e}")
            import traceback
            log_error(traceback.format_exc())
            return False