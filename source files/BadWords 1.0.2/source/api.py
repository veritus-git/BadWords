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

    def get_current_source_item(self):
        if not self.timeline: return None
        
        # Strategy: Get the clip currently under playhead on V1
        current_time = self.timeline.GetCurrentTimecode()
        
        # Note: GetItemListInTrack returns ALL items. We should grab the first one
        # or check logic. For this script, we assume user prepared V1.
        clips = self.timeline.GetItemListInTrack("video", 1)
        if clips:
            return clips[0].GetMediaPoolItem()
        return None

    def create_compound_clip_wrapper(self, original_tl_name):
        if not self.media_pool: return None, None
        
        root_folder = self.media_pool.GetRootFolder()
        original_tl_item = self.find_timeline_item_recursive(root_folder, original_tl_name)
        
        if not original_tl_item:
            log_error(f"Could not find timeline '{original_tl_name}' in Media Pool.")
            return None, None
            
        timestamp = int(time.time())
        nested_tl_name = f"BW_Compound_{original_tl_name}_{timestamp}"
        
        try:
            new_tl = self.media_pool.CreateEmptyTimeline(nested_tl_name)
            
            if new_tl:
                if self.media_pool.AppendToTimeline([original_tl_item]):
                    self.project.SetCurrentTimeline(new_tl)
                    self.resolve.OpenPage("edit")
                    return new_tl, original_tl_item
        except Exception as e:
            log_error(f"Compound creation error: {e}")
            
        return None, None

    # ==========================================
    # NEW: TIMELINE GENERATOR FROM OPERATIONS
    # ==========================================

    def generate_timeline_from_ops(self, ops, source_item, new_tl_name):
        """
        Creates a new timeline and assembles it based on the operations list.
        Explicitly colors both Video (V1) and Audio (A1) tracks using Index-Based Coloring.
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
            log_info(f"Creating timeline: {new_tl_name}")
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

            # 3. Batch Append
            if not clip_infos:
                log_info("No clips to append.")
                return True

            appended_items = self.media_pool.AppendToTimeline(clip_infos)
            
            # 4. ROBUST INDEX-BASED COLORING (Fallback to Time-based if counts mismatch)
            # We assume appended_items usually returns Video Clips.
            
            # Get Video Track Items
            video_items = new_tl.GetItemListInTrack("video", 1) or []
            audio_items = new_tl.GetItemListInTrack("audio", 1) or []
            
            # Apply to Video
            for i, item in enumerate(video_items):
                if i < len(valid_ops):
                    op_type = valid_ops[i]['type']
                    color = COLOR_MAP.get(op_type)
                    if color: item.SetClipColor(color)
            
            # Apply to Audio (Mirror Video structure if possible)
            if len(audio_items) == len(video_items):
                for i, item in enumerate(audio_items):
                    if i < len(valid_ops):
                        op_type = valid_ops[i]['type']
                        color = COLOR_MAP.get(op_type)
                        if color: item.SetClipColor(color)
            else:
                # Fallback: Color Audio by checking start time match against video items
                log_info("Audio/Video count mismatch. Using time-sync for Audio coloring.")
                for a_item in audio_items:
                    a_start = a_item.GetStart()
                    # Find video clip at same start
                    match = next((v for v in video_items if abs(v.GetStart() - a_start) <= 1), None)
                    if match:
                        # Copy color from video clip
                        # Note: GetClipColor might not be available in all API versions for reading
                        # So we better match against valid_ops time map
                        
                        # Re-calculate ops timing map
                        current_rec_head = new_tl.GetStartFrame()
                        found_op = None
                        for op in valid_ops:
                            dur = int(op['e']) - int(op['s'])
                            if abs(current_rec_head - a_start) <= 2:
                                found_op = op
                                break
                            current_rec_head += dur
                        
                        if found_op:
                            color = COLOR_MAP.get(found_op['type'])
                            if color: a_item.SetClipColor(color)

            return True

        except Exception as e:
            log_error(f"Generate Timeline Error: {e}")
            import traceback
            log_error(traceback.format_exc())
            return False