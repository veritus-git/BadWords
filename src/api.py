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
import threading

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

    def render_audio(self, unique_id, export_path, timeline_name=None, track_indices=None, end_frame_override=None, progress_callback=None):
        """
        Renders audio from the specified timeline to a WAV file.

        Args:
            unique_id (str): Unique file name prefix.
            export_path (str): Directory to write the WAV file to.
            timeline_name (str|None): Name of the timeline to render. If None,
                uses the currently active timeline.
            track_indices (list[int]|None): 1-based list of audio track indices
                to include. If None or empty, all tracks are rendered.
            end_frame_override (int|None): If set, render only up to this RELATIVE
                frame (0-based from timeline start). Used to skip silent tail from
                longer unused tracks. The timeline's original range is restored after.

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

        # ── 3. Configure render range and execute ─────────────────────────────
        render_ok = False
        mark_range_set = False
        # These are captured inside the try block and accessed in finally for restore
        _tl_start_for_restore = None
        _tl_end_for_restore   = None

        try:
            self.project.LoadRenderPreset("Audio Only")

            tl_start = render_timeline.GetStartFrame()
            tl_end   = render_timeline.GetEndFrame()
            _tl_start_for_restore = tl_start
            _tl_end_for_restore   = tl_end

            if end_frame_override is not None:
                # Convert relative frame to absolute (add TL timecode start offset)
                abs_end_frame = tl_start + end_frame_override
                abs_end_frame = min(abs_end_frame, tl_end)
                log_info(f"render_audio: limiting render to frame {abs_end_frame} "
                         f"(relative {end_frame_override}, tl_start={tl_start})")

                self.project.SetRenderSettings({
                    "SelectAllFrames": 0,
                    "MarkIn":          tl_start,
                    "MarkOut":         abs_end_frame,
                    "TargetDir":       export_path,
                    "CustomName":      unique_id,
                    "ExportVideo":     False,
                    "ExportAudio":     True,
                    "AudioCodec":      "wav",
                    "AudioBitDepth":   16,
                    "AudioSampleRate": 48000,
                })
                mark_range_set = True
            else:
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

            # ── Unified render-status polling loop ────────────────────────────
            # GetRenderJobStatus is unreliable for live audio render progress.
            # It blocks the API thread and doesn't update fast enough.
            # We revert to standard robust polling.
            time.sleep(0.5)
            
            while self.project.IsRenderingInProgress():
                time.sleep(1.0)
                
            status = self.project.GetRenderJobStatus(pid)
            self.project.DeleteRenderJob(pid)

            render_ok = status.get("JobStatus") in ("Complete", "Completed") if isinstance(status, dict) else False
            if not render_ok:
                # Some Resolve versions omit JobStatus in the dict—treat non-empty as success
                if isinstance(status, dict) and status and "JobStatus" not in status:
                    render_ok = True
                else:
                    log_error(f"Render failed. Status: {status}")

        except Exception as e:
            log_error(f"Render error: {e}")
            render_ok = False

        finally:
            # ── Step A: Restore render range ──────────────────────────────────
            # SetRenderSettings may trigger a Deliver page switch internally.
            # We do this FIRST before OpenPage so it doesn't undo our page switch.
            if mark_range_set:
                try:
                    _rs = _tl_start_for_restore
                    _re = _tl_end_for_restore
                    if _rs is None or _re is None:
                        _rs = render_timeline.GetStartFrame()
                        _re = render_timeline.GetEndFrame()
                    self.project.SetRenderSettings({
                        "SelectAllFrames": 1,
                        "MarkIn":          _rs,
                        "MarkOut":         _re,
                    })
                    log_info(f"render_audio: restored full render range (MarkIn={_rs}, MarkOut={_re}).")
                except Exception as rr_err:
                    log_error(f"render_audio: could not restore render range: {rr_err}")
                    try:
                        self.project.SetRenderSettings({"SelectAllFrames": 1})
                    except Exception:
                        pass

            # ── Step B: Return to Edit page ──────────────────────────────────
            # Must happen AFTER SetRenderSettings (Step A) but BEFORE unmute (Step C).
            # SetTrackEnable only works correctly while on the Edit page.
            if self.resolve:
                try:
                    self.resolve.OpenPage("edit")
                    time.sleep(1.0)  # wait for Edit page to be fully active
                except Exception:
                    pass

            # ── Step C: Restore muted tracks ─────────────────────────────────
            # Now on Edit page — track enable/disable is reliable here.
            if mute_state_backup and working_set_name:
                try:
                    _set = getattr(render_timeline, working_set_name)
                    if callable(_set):
                        for idx in mute_state_backup:
                            _set("audio", idx, True)
                        log_info(f"render_audio: unmuted tracks {mute_state_backup}.")
                except Exception as restore_err:
                    log_error(f"Track restore via {working_set_name} failed: {restore_err}")

            # ── Step D: Restore original timeline ──────────────────────────────
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
        Calculates the next suffix index for the new Edit timeline.
        """
        base_name = re.sub(r" BadWords Edit \d+$", "", original_name)
        
        idx = 1
        count_map = self.project.GetTimelineCount()
        for i in range(1, count_map + 1):
            tl = self.project.GetTimelineByIndex(i)
            name = tl.GetName()
            if name.startswith(f"{base_name} BadWords Edit "):
                try:
                    curr_idx = int(name.split(" BadWords Edit ")[-1])
                    if curr_idx >= idx: idx = curr_idx + 1
                except: pass
        
        return base_name, idx

    def get_selected_tracks_end_seconds(self, timeline_name, track_indices):
        """
        Returns the end time (in seconds, from position 0) of the last clip on the
        specified audio track indices within the named timeline.

        CRITICAL: DaVinci Resolve's GetStart() returns ABSOLUTE timeline frame positions
        (e.g. if the timeline starts at 01:00:00:00 @ 60fps, GetStartFrame() = 216000).
        GetStart() on a clip that starts at the first frame of the TL would return 216000,
        NOT 0. We must subtract GetStartFrame() to get a 0-based position that matches
        the WAV file timestamps from Whisper.
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
                log_error(f"get_selected_tracks_end_seconds: timeline '{timeline_name}' not found.")
                return None

            fps = self.fps
            if not fps or fps == 0:
                return None

            # The offset to subtract — timeline start timecode in frames
            tl_start_frame = target_tl.GetStartFrame()
            log_info(f"get_selected_tracks_end_seconds: tl_start_frame={tl_start_frame}, fps={fps}")

            max_rel_frame = 0  # relative to timeline start = 0
            for idx in track_indices:
                items = target_tl.GetItemListInTrack("audio", idx)
                if not items:
                    log_info(f"  track A{idx}: no items.")
                    continue
                for item in items:
                    abs_end = item.GetStart() + item.GetDuration()
                    rel_end = abs_end - tl_start_frame  # 0-based
                    log_info(f"  track A{idx}: abs_end={abs_end}, rel_end={rel_end} ({rel_end/fps:.2f}s)")
                    if rel_end > max_rel_frame:
                        max_rel_frame = rel_end

            if max_rel_frame == 0:
                log_error(f"get_selected_tracks_end_seconds: no clips found on tracks {track_indices}.")
                return None

            end_seconds = max_rel_frame / fps
            log_info(f"get_selected_tracks_end_seconds: selected tracks end at {end_seconds:.3f}s (rel frame {max_rel_frame}).")
            return end_seconds

        except Exception as e:
            log_error(f"get_selected_tracks_end_seconds error: {e}")
            return None

    def get_direct_audio_info(self, timeline_name, track_indices=None):
        """
        Uses Resolve's scripting API (_build_source_clip_map) to inspect the
        audio clips on the given timeline WITHOUT requiring an XML export.

        ELIGIBILITY RULES:
          • All clips on selected tracks must share the SAME source file path.
          • No clip may have a non-1.0 speed (GetProperty('Clip Speed') / GetLeftOffset).
          • No clip may have audio FX applied (GetProperty('Audio FX') non-empty).
          • The source file must physically exist on disk.

        Returns a dict on success, or None (fall back to Resolve render).
        """
        if not self.project or not self.timeline:
            return None

        # -- locate the target timeline --
        target_tl = None
        try:
            count = self.project.GetTimelineCount()
            for i in range(1, count + 1):
                tl = self.project.GetTimelineByIndex(i)
                if tl and tl.GetName() == timeline_name:
                    target_tl = tl
                    break
        except Exception as e:
            log_error(f"get_direct_audio_info: could not locate timeline: {e}")
            return None

        if not target_tl:
            log_info(f"get_direct_audio_info: timeline '{timeline_name}' not found.")
            return None

        try:
            fps = self.fps
            try:
                fps = float(target_tl.GetSetting("timelineFrameRate")) or fps
            except Exception:
                pass

            a_track_count = target_tl.GetTrackCount("audio")
            if a_track_count == 0:
                return None

            # Which audio tracks to inspect
            if track_indices:
                check_tracks = [i for i in track_indices if 1 <= i <= a_track_count]
            else:
                check_tracks = list(range(1, a_track_count + 1))

            if not check_tracks:
                return None

            tl_start_frame = int(target_tl.GetStartFrame())
            source_paths   = set()
            collected_clips = []  # {src_in_f, src_out_f, tl_start_f, file_path}

            for ai in check_tracks:
                raw_items = target_tl.GetItemListInTrack("audio", ai)
                if not raw_items:
                    continue

                for item in raw_items:
                    try:
                        # -- Speed check --
                        # GetProperty returns a string; '100.00' means normal speed.
                        try:
                            speed_str = item.GetProperty("Clip Speed") or ""
                            speed_val = float(speed_str.replace("%", "").strip() or "100")
                            if abs(speed_val - 100.0) > 0.5:
                                log_info(f"get_direct_audio_info: clip on A{ai} has speed {speed_val}% — render required.")
                                return None
                        except (ValueError, AttributeError):
                            pass  # property unavailable — assume normal speed

                        # -- Audio FX check --
                        try:
                            fx = item.GetProperty("Audio FX") or ""
                            if str(fx).strip() not in ("", "0", "None", "false"):
                                log_info(f"get_direct_audio_info: clip on A{ai} has Audio FX '{fx}' — render required.")
                                return None
                        except Exception:
                            pass  # property unavailable — assume no FX

                        # -- Media pool item / file path --
                        pool_item = item.GetMediaPoolItem()
                        if not pool_item:
                            log_info(f"get_direct_audio_info: clip on A{ai} has no pool item — render required.")
                            return None

                        fp = pool_item.GetClipProperty("File Path") or ""
                        if not fp:
                            log_info(f"get_direct_audio_info: clip on A{ai} has no file path — render required.")
                            return None

                        if not os.path.exists(fp):
                            log_info(f"get_direct_audio_info: source not on disk: '{fp}' — render required.")
                            return None

                        source_paths.add(fp)

                        # -- Clip geometry (all in frames) --
                        abs_start   = int(item.GetStart())
                        duration    = int(item.GetDuration())
                        src_in_f    = int(item.GetLeftOffset())  # offset from media head

                        collected_clips.append({
                            "src_in_f":   src_in_f,
                            "src_out_f":  src_in_f + duration,
                            "tl_start_f": abs_start - tl_start_frame,  # 0-based
                            "file_path":  fp,
                        })

                    except Exception as ci_err:
                        log_error(f"get_direct_audio_info: skipping clip on A{ai}: {ci_err}")
                        return None  # conservative: any error → render

            if not collected_clips:
                log_info("get_direct_audio_info: no clips found.")
                return None

            if len(source_paths) != 1:
                log_info(f"get_direct_audio_info: {len(source_paths)} source files — render required.")
                return None

            source_file = next(iter(source_paths))

            # Sort by timeline position
            collected_clips.sort(key=lambda c: c["tl_start_f"])

            # Convert frame counts to seconds for FFmpeg
            clips_seconds = [
                {
                    "src_in_s":   c["src_in_f"]  / fps,
                    "duration_s": (c["src_out_f"] - c["src_in_f"]) / fps,
                }
                for c in collected_clips
            ]

            mode = "single_uncut" if len(clips_seconds) == 1 else "single_source_multicopy"
            log_info(f"get_direct_audio_info: mode={mode}, clips={len(clips_seconds)}, fps={fps}, source='{source_file}'")
            return {
                "mode":        mode,
                "source_file": source_file,
                "clips":       clips_seconds,
                "fps":         fps,
            }

        except Exception as e:
            log_error(f"get_direct_audio_info: unexpected error: {e}")
            return None


    def timeline_exists(self, timeline_name):
        """Returns True if a timeline with the given name exists in the current project."""
        try:
            count = self.project.GetTimelineCount()
            for i in range(1, count + 1):
                if self.project.GetTimelineByIndex(i).GetName() == timeline_name:
                    return True
            return False
        except Exception:
            return False

    def get_next_xml_index(self, source_tl_name):
        """
        Calculates the next suffix index for BadWords Filtered timelines.
        Format: '{source_tl_name} BadWords Filtered N'
        """
        base_name = re.sub(r" BadWords (Filtered|Edit) \d+$", "", source_tl_name)
        idx = 1
        count_map = self.project.GetTimelineCount()
        for i in range(1, count_map + 1):
            name = self.project.GetTimelineByIndex(i).GetName()
            if name.startswith(f"{base_name} BadWords Filtered "):
                try:
                    curr_idx = int(name.split(" BadWords Filtered ")[-1])
                    if curr_idx >= idx: idx = curr_idx + 1
                except: pass
        return base_name, idx

    # ── BadWords Bin Management ──────────────────────────────────────────────
    # All files produced by BadWords land here. Structure:
    #   Master/
    #     BadWords/
    #       Edits/       ← final output timelines ("BadWords Edit N")
    #       Resources/   ← everything else (filtered TLs, temp imports, etc.)

    def _get_or_create_folder(self, parent_folder, name):
        """Returns existing subfolder by name, or creates it."""
        try:
            for sub in parent_folder.GetSubFolderList():
                if sub.GetName() == name:
                    return sub
            return self.media_pool.AddSubFolder(parent_folder, name)
        except Exception as e:
            log_error(f"_get_or_create_folder('{name}') error: {e}")
            return None

    def get_badwords_root_bin(self):
        """Returns (or creates) the top-level 'BadWords' bin under Master."""
        try:
            root = self.media_pool.GetRootFolder()
            return self._get_or_create_folder(root, "BadWords")
        except Exception as e:
            log_error(f"get_badwords_root_bin error: {e}")
            return None

    def get_badwords_edits_bin(self):
        """Returns (or creates) BadWords/Edits — for final assembled timelines."""
        bw = self.get_badwords_root_bin()
        if not bw: return None
        return self._get_or_create_folder(bw, "Edits")

    def get_badwords_resources_bin(self):
        """Returns (or creates) BadWords/Resources — for all intermediate files."""
        bw = self.get_badwords_root_bin()
        if not bw: return None
        return self._get_or_create_folder(bw, "Resources")

    def move_to_badwords_bin(self, item_name, bin_type="resources"):
        """
        Moves a Media Pool item by name to the appropriate BadWords bin.
        bin_type: 'edits' or 'resources'
        """
        try:
            target_bin = self.get_badwords_edits_bin() if bin_type == "edits" else self.get_badwords_resources_bin()
            if not target_bin:
                return
            item = self.find_timeline_item_recursive(self.media_pool.GetRootFolder(), item_name)
            if item:
                self.media_pool.MoveClips([item], target_bin)
                log_info(f"Moved '{item_name}' to BadWords/{bin_type.capitalize()}.")
        except Exception as e:
            log_error(f"move_to_badwords_bin('{item_name}') error: {e}")

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
        Video clips are trimmed to end at the max end frame of the kept audio tracks.
        Returns True on success, False otherwise.
        """
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(input_path)
            root = tree.getroot()

            keep_set = set(track_indices)

            # Diagnostic: log media paths
            all_paths = [el.text for el in root.iter('pathurl') if el.text]
            log_info(f"filter_xml_tracks: media paths in XML: {all_paths[:10]}")

            # ── Step 1: Filter audio tracks, collect kept elements ─────────────
            kept_track_elements = []
            for audio_section in root.iter('audio'):
                tracks = audio_section.findall('track')
                log_info(f"filter_xml_tracks: found {len(tracks)} audio tracks; keeping {sorted(keep_set)}")
                for i, t in enumerate(tracks):
                    clips = t.findall('.//name')
                    clip_name = clips[0].text if clips else '(unknown)'
                    log_info(f"  track[{i+1}]: '{clip_name}' -> {'KEEP' if (i+1) in keep_set else 'REMOVE'}")
                for idx, track in reversed(list(enumerate(tracks))):
                    if (idx + 1) not in keep_set:
                        audio_section.remove(track)
                    else:
                        kept_track_elements.append(track)

            # ── Step 2: Find max end frame of kept audio tracks ───────────────
            max_end_frame = None
            for track in kept_track_elements:
                for clipitem in track.findall('.//clipitem'):
                    end_el = clipitem.find('end')
                    if end_el is not None and end_el.text:
                        try:
                            end_f = int(end_el.text)
                            if max_end_frame is None or end_f > max_end_frame:
                                max_end_frame = end_f
                        except ValueError:
                            pass

            if max_end_frame is not None:
                log_info(f"filter_xml_tracks: audio ends at frame {max_end_frame}. Trimming video and duration.")

                # ── Step 3: Trim video clips to max_end_frame ─────────────────
                # This is the real fix for timeline length — video clips set the TL length.
                for video_section in root.iter('video'):
                    for track in video_section.findall('track'):
                        clips_to_remove = []
                        for clipitem in track.findall('clipitem'):
                            start_el = clipitem.find('start')
                            end_el   = clipitem.find('end')
                            if start_el is None or end_el is None:
                                continue
                            try:
                                clip_start = int(start_el.text)
                                clip_end   = int(end_el.text)
                            except ValueError:
                                continue

                            if clip_start >= max_end_frame:
                                # Entirely after the audio — remove
                                clips_to_remove.append(clipitem)
                            elif clip_end > max_end_frame:
                                # Partially overlapping — trim to exact audio end
                                end_el.text = str(max_end_frame)
                                # Also adjust the source out-point to match the cut
                                source_out = clipitem.find('out')
                                if source_out is not None:
                                    try:
                                        source_in  = int(clipitem.find('in').text) if clipitem.find('in') is not None else 0
                                        new_dur    = max_end_frame - clip_start
                                        source_out.text = str(source_in + new_dur)
                                    except Exception:
                                        pass

                        for ci in clips_to_remove:
                            track.remove(ci)

                # ── Step 4: Patch sequence <duration> ────────────────────────
                for seq in root.iter('sequence'):
                    dur_el = seq.find('duration')
                    if dur_el is not None:
                        dur_el.text = str(max_end_frame)
                    out_el = seq.find('out')
                    if out_el is not None:
                        out_el.text = str(max_end_frame)
                    break

            # ── Step 5: Write output ──────────────────────────────────────────
            tree.write(output_path, encoding="unicode", xml_declaration=False)
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + content)

            log_info(f"Filtered XML written to: {output_path}")
            return True
        except Exception as e:
            log_error(f"filter_xml_tracks error: {e}")
            return False

    def import_xml_as_timeline(self, xml_path, source_tl_name):
        """
        Imports a filtered FCP7 XML into Resolve as a new named timeline.
        - Timeline is named: '{source_tl_name} BadWords Filtered N'
        - Timeline is moved to BadWords/Resources.
        - importSourceClips=True re-links existing media by file path.
        Returns the new timeline name (str) or None on failure.
        """
        try:
            if not self.media_pool:
                log_error("import_xml_as_timeline: media_pool not available.")
                return None

            base_name, xml_idx = self.get_next_xml_index(source_tl_name)
            xml_tl_name = f"{base_name} BadWords Filtered {xml_idx}"

            # Set current folder to Resources BEFORE importing so any source clips
            # that Resolve creates as part of the import (duplicates of existing media)
            # land in BadWords/Resources instead of Master or wherever was active.
            _resources_bin = self.get_badwords_resources_bin()
            if _resources_bin:
                try:
                    self.media_pool.SetCurrentFolder(_resources_bin)
                except Exception:
                    pass

            import_options = {
                "timelineName":      xml_tl_name,
                # importSourceClips=True: required to re-link media when importing
                # from XML. Without this, clips may appear as offline.
                # The current folder is set to BadWords/Resources above so any
                # newly created/duplicated source clips land there, not in Master.
                "importSourceClips": True,
            }
            log_info(f"import_xml_as_timeline: importing as '{xml_tl_name}' from '{xml_path}'")
            new_tl = self.media_pool.ImportTimelineFromFile(xml_path, import_options)

            if not new_tl:
                log_error(f"import_xml_as_timeline: ImportTimelineFromFile returned None for '{xml_path}'.")
                log_error("  Possible causes: XML malformed, media paths wrong, or Resolve API version mismatch.")
                return None

            name = new_tl.GetName()
            log_info(f"import_xml_as_timeline: Imported timeline '{name}' successfully.")

            # Diagnostic
            try:
                a_cnt = new_tl.GetTrackCount("audio")
                v_cnt = new_tl.GetTrackCount("video")
                log_info(f"import_xml_as_timeline: result has {v_cnt} video track(s), {a_cnt} audio track(s).")
            except Exception:
                pass

            # Move to BadWords/Resources
            self.move_to_badwords_bin(name, "resources")

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
    # XML ASSEMBLY PIPELINE (PRIMARY PATH)
    # ==========================================

    def _path_to_fileurl(self, path):
        """
        Converts a filesystem path to a valid file:// URL for FCP7 XML.
        Handles Windows drive letters and Linux/macOS absolute paths.
        Spaces and special chars are percent-encoded (RFC 3986).
        """
        import urllib.parse
        # Normalise separators
        path = path.replace('\\', '/')
        # Windows: "C:/..." → "/C:/..."
        if len(path) >= 2 and path[1] == ':':
            path = '/' + path
        # Quote everything except safe URL characters (slashes, colon for drive)
        encoded = urllib.parse.quote(path, safe='/:@')
        return 'file://' + encoded

    def _get_fps_params(self, fps):
        """
        Returns (timebase_int, is_ntsc) for FCP7 XML <rate> elements.

        FCP7 XML encodes FPS as an integer <timebase> + boolean <ntsc>.
        NTSC fractional rates (23.976, 29.97, 59.94 etc.) must set ntsc=TRUE
        so Resolve reconstructs the exact rational rate (e.g. 24000/1001).

        24fps, 30fps, 48fps, 60fps are CLEAN integer rates — ntsc=FALSE.
        """
        # NTSC rates: map the rounded integer (as Resolve reports it) to the
        # exact fractional value. ONLY the fractional variants are NTSC.
        # 24/30/48/60 are clean rates and must NOT appear in this map.
        NTSC_MAP = {
            23: 23.976,   # 23.976 rounds to 23 in some APIs, or to 24
            29: 29.97,    # 29.97 rounds to 30
            47: 47.952,   # 47.952 rounds to 48
            59: 59.94,    # 59.94 rounds to 60
        }
        rounded = int(round(fps))
        # Primary detection: if actual fps differs from its nearest integer by >0.01
        # it is definitively a fractional (NTSC) rate.
        if abs(fps - rounded) > 0.01:
            return rounded, True
        # Secondary: catch values like 23.976 or 29.97 that some Resolve versions
        # report with higher floating-point precision.
        for tb, ntsc_rate in NTSC_MAP.items():
            if abs(fps - ntsc_rate) < 0.02:
                return tb, True
        # Clean integer rate (24, 30, 48, 60, etc.)
        return rounded, False

    def _build_source_clip_map(self, timeline, track_type, track_idx, tl_start_frame=0):
        """
        Returns an ordered list of clip dicts for one track on the given timeline.
        Each dict:
          abs_start  – raw frame from item.GetStart() (may be timecode-absolute or 0-based)
          abs_end    – abs_start + duration
          rel_start  – 0-based position from TL start  = abs_start - tl_start_frame
          rel_end    – rel_start + duration
          src_in     – source media in-point (frames from media file beginning)
          src_out    – source media out-point (exclusive)
          file_path  – absolute filesystem path to the media file
        Clips are sorted by rel_start ascending.
        Using rel_start/rel_end in op_to_clipitems guarantees correct mapping
        regardless of whether GetStart() uses timecode-absolute or 0-based space.
        """
        clips = []
        try:
            items = timeline.GetItemListInTrack(track_type, track_idx)
            if not items:
                return clips
            for item in items:
                try:
                    pool_item = item.GetMediaPoolItem()
                    if not pool_item:
                        continue
                    fp          = pool_item.GetClipProperty("File Path") or ""
                    abs_start   = int(item.GetStart())
                    duration    = int(item.GetDuration())
                    src_in      = int(item.GetLeftOffset())  # frames from media head to in-point
                    rel_start   = abs_start - tl_start_frame
                    # CRITICAL: total source file duration prevents Freeze Time in FCP7 XML.
                    # When src_in > 0 and <file><duration> < src_out, Resolve freezes the clip.
                    try:
                        total_frames = int(pool_item.GetClipProperty("Frames") or 0)
                    except Exception:
                        total_frames = 0
                    if total_frames <= 0:
                        # Fallback: at minimum must be >= src_in + duration
                        total_frames = src_in + duration
                    clips.append({
                        "abs_start":    abs_start,
                        "abs_end":      abs_start + duration,
                        "rel_start":    rel_start,              # KEY: 0-based from TL start
                        "rel_end":      rel_start + duration,   # KEY: 0-based from TL start
                        "src_in":       src_in,
                        "src_out":      src_in + duration,
                        "file_path":    fp,
                        "total_frames": total_frames,           # KEY: full source file length
                    })
                except Exception as ci_err:
                    log_error(f"_build_source_clip_map: skipping clip: {ci_err}")
            clips.sort(key=lambda c: c["rel_start"])
        except Exception as e:
            log_error(f"_build_source_clip_map({track_type}, {track_idx}): {e}")
        return clips

    def build_edit_xml_from_ops(self, ops, source_tl_name, new_tl_name,
                                 track_indices, audio_only_mode, output_path,
                                 preserve_track_order=False):
        """
        Constructs a complete FCP7 XML file ready to be imported as a new
        DaVinci Resolve timeline.

        Returns: (success: bool, color_schedule: dict)
          color_schedule maps dest_start_frame → color_string (or None for normal clips).
          This schedule covers EVERY clipitem (including multi-clip-source splits),
          enabling reapply_clip_colors() to verify/correct colors with 100% coverage.
        """
        import xml.etree.ElementTree as ET

        # Resolve clip colors — same map used in XML and in API verification pass
        COLOR_MAP = {
            "bad":          "Violet",
            "repeat":       "Navy",
            "typo":         "Olive",
            "inaudible":    "Chocolate",
            "silence_mark": "Tan",
        }

        try:
            # ── 1. Find source timeline ───────────────────────────────────────
            target_tl = None
            count = self.project.GetTimelineCount()
            for i in range(1, count + 1):
                tl = self.project.GetTimelineByIndex(i)
                if tl.GetName() == source_tl_name:
                    target_tl = tl
                    break
            if not target_tl:
                log_error(f"build_edit_xml_from_ops: timeline '{source_tl_name}' not found.")
                return False, {}

            # ── 2. FPS & rate params ──────────────────────────────────────────
            try:
                raw_fps = float(target_tl.GetSetting("timelineFrameRate"))
            except Exception:
                raw_fps = self.fps or 24.0
            timebase, is_ntsc = self._get_fps_params(raw_fps)
            ntsc_str = "TRUE" if is_ntsc else "FALSE"
            log_info(f"build_edit_xml_from_ops: fps={raw_fps} → timebase={timebase}, ntsc={ntsc_str}")

            tl_start_frame = int(target_tl.GetStartFrame())

            # ── 3. Determine which audio tracks to include ────────────────────
            a_track_count = target_tl.GetTrackCount("audio")
            v_track_count = target_tl.GetTrackCount("video")

            if track_indices:
                audio_tracks_src = sorted(set(i for i in track_indices
                                              if 1 <= i <= a_track_count))
            else:
                audio_tracks_src = list(range(1, a_track_count + 1))

            # Build clip maps — pass tl_start_frame so clips store rel_start/rel_end
            # Video: always ALL video tracks (user decision)
            video_clip_maps = {}
            if not audio_only_mode:
                for vi in range(1, v_track_count + 1):
                    clips = self._build_source_clip_map(target_tl, "video", vi, tl_start_frame)
                    if clips:
                        video_clip_maps[vi] = clips

            # Audio: only selected tracks
            audio_clip_maps = {}
            for ai in audio_tracks_src:
                clips = self._build_source_clip_map(target_tl, "audio", ai, tl_start_frame)
                if clips:
                    audio_clip_maps[ai] = clips

            log_info(f"build_edit_xml_from_ops: {len(video_clip_maps)} video track(s), "
                     f"{len(audio_clip_maps)} audio track(s), tl_start={tl_start_frame}")

            # ── 4. Filter ops ─────────────────────────────────────────────────
            # IMPORTANT: `ops` (clean_ops from engine) is ALREADY filtered by
            # calculate_timeline_structure() which respects do_auto_del, do_silence_cut etc.
            # The ONLY thing we skip here is 'silence_cut' — a cut-point marker with
            # zero payload that AppendToTimeline also never placed on the timeline.
            # We do NOT touch 'bad' here — if auto_del was ON, they’re already gone.
            # If auto_del was OFF, red clips MUST appear in the output (Violet color).
            kept_ops = [op for op in ops
                        if op["type"] != "silence_cut" and (op["e"] - op["s"]) >= 2]

            if not kept_ops:
                log_error("build_edit_xml_from_ops: no ops to assemble after filtering.")
                return False, {}


            # ── 5. Helper: map one op range onto source clips ─────────────────
            def op_to_clipitems(op, clip_map):
                """
                Maps one op (in 0-based frames, same space as ops list) onto the
                source clips using their rel_start/rel_end fields (also 0-based).
                Returns a list of segment dicts for clips that overlap the op.
                Correctly handles multi-clip source timelines with any number of
                sequential or non-sequential clips.
                """
                result = []
                for clip in clip_map:
                    # All in 0-based space — no tl_start_frame addition needed
                    overlap_start = max(op["s"], clip["rel_start"])
                    overlap_end   = min(op["e"], clip["rel_end"])
                    if overlap_end <= overlap_start:
                        continue
                    offset  = overlap_start - clip["rel_start"]
                    src_in  = clip["src_in"] + offset
                    dur     = overlap_end - overlap_start
                    src_out = src_in + dur
                    # op_offset: how many frames into the op this segment starts.
                    # CRITICAL for correct dest_pos placement when a clip boundary
                    # falls inside an op (prevents zakładka / timeline desync).
                    op_offset = overlap_start - op["s"]
                    result.append({
                        "src_in":    src_in,
                        "src_out":   src_out,
                        "duration":  dur,
                        "file_path": clip["file_path"],
                        "op_offset": op_offset,
                    })
                return result

            # ── 6. Build XML tree ─────────────────────────────────────────────
            # Collect unique file paths for the <file> registry
            file_registry = {}  # path → xml id string
            file_id_counter = [0]

            def get_file_id(path):
                if path not in file_registry:
                    file_id_counter[0] += 1
                    file_registry[path] = f"file-{file_id_counter[0]}"
                return file_registry[path]

            # Build file_total_frames map: path → max known total frames
            # Used in <file> elements to prevent Freeze Time when src_in > 0
            file_total_frames = {}
            for cm_dict in list(video_clip_maps.values()) + list(audio_clip_maps.values()):
                for clip in cm_dict:
                    fp = clip["file_path"]
                    tf = clip.get("total_frames", 0)
                    if tf > file_total_frames.get(fp, 0):
                        file_total_frames[fp] = tf

            # color_schedule: dest_start_frame → color_string|None
            # Every clipitem (including multi-clip splits) gets an entry.
            # This is the source of truth for reapply_clip_colors().
            color_schedule = {}

            # Pre-walk all ops to register files in order
            for op in kept_ops:
                for vm in video_clip_maps.values():
                    for seg in op_to_clipitems(op, vm):
                        get_file_id(seg["file_path"])
                for am in audio_clip_maps.values():
                    for seg in op_to_clipitems(op, am):
                        get_file_id(seg["file_path"])

            def make_rate_elem(parent, ntsc=ntsc_str, tb=timebase):
                r = ET.SubElement(parent, "rate")
                ET.SubElement(r, "timebase").text = str(tb)
                ET.SubElement(r, "ntsc").text = ntsc
                return r

            def make_file_elem(parent, path, emit_full):
                """
                Emits <file id="file-N"> with full content (first time),
                or a self-closing reference <file id="file-N"/> (subsequent).
                Includes <duration> = total source frames to prevent Freeze Time
                when src_in > 0 (trimmed clips).
                """
                fid = get_file_id(path)
                file_el = ET.SubElement(parent, "file", id=fid)
                if emit_full:
                    ET.SubElement(file_el, "name").text = path.split("/")[-1].split("\\")[-1]
                    ET.SubElement(file_el, "pathurl").text = self._path_to_fileurl(path)
                    make_rate_elem(file_el)
                    # Full source file duration — MUST be >= max(src_out) for all clips
                    # using this file, otherwise Resolve shows Freeze Time.
                    tf = file_total_frames.get(path, 0)
                    if tf > 0:
                        ET.SubElement(file_el, "duration").text = str(tf)
                # else: empty element = reference only

            def make_clipitem(parent, ci_id, dest_start, dest_end,
                              src_in, src_out, duration, file_path,
                              color=None, sourcetrack_type=None, sourcetrack_idx=None):
                ci = ET.SubElement(parent, "clipitem", id=ci_id)
                ET.SubElement(ci, "name").text = file_path.split("/")[-1].split("\\")[-1]
                ET.SubElement(ci, "duration").text = str(duration)
                make_rate_elem(ci)
                ET.SubElement(ci, "start").text   = str(dest_start)
                ET.SubElement(ci, "end").text     = str(dest_end)
                ET.SubElement(ci, "in").text      = str(src_in)
                ET.SubElement(ci, "out").text     = str(src_out)
                # First emission of a file path includes full definition; subsequent refs only
                first_emit = file_path not in getattr(make_clipitem, "_emitted_files", set())
                if not hasattr(make_clipitem, "_emitted_files"):
                    make_clipitem._emitted_files = set()
                make_file_elem(ci, file_path, emit_full=first_emit)
                make_clipitem._emitted_files.add(file_path)
                # PRIMARY color embed — Resolve honours <logginginfo><clipcolor> on import
                # reapply_clip_colors() will verify and correct these after import
                if color:
                    li = ET.SubElement(ci, "logginginfo")
                    ET.SubElement(li, "clipcolor").text = color
                # Audio sourcetrack sub-element
                if sourcetrack_type:
                    st = ET.SubElement(ci, "sourcetrack")
                    ET.SubElement(st, "mediatype").text = sourcetrack_type
                    if sourcetrack_idx is not None:
                        ET.SubElement(st, "trackindex").text = str(sourcetrack_idx)
                # Record in color_schedule for reapply verification
                color_schedule[dest_start] = color
                return ci

            # Reset statics
            if hasattr(make_clipitem, "_emitted_files"):
                del make_clipitem._emitted_files

            # Root
            xmeml = ET.Element("xmeml", version="5")
            seq   = ET.SubElement(xmeml, "sequence", id="sequence-1")
            ET.SubElement(seq, "name").text = new_tl_name

            # Calculate total destination frames
            total_dest_frames = sum(op["e"] - op["s"] for op in kept_ops)
            ET.SubElement(seq, "duration").text = str(total_dest_frames)
            make_rate_elem(seq)

            media = ET.SubElement(seq, "media")

            # ── VIDEO section ─────────────────────────────────────────
            video_el = ET.SubElement(media, "video")

            # Format
            fmt = ET.SubElement(video_el, "format")
            sc  = ET.SubElement(fmt, "samplecharacteristics")
            try:
                w = int(target_tl.GetSetting("timelineResolutionWidth")  or 1920)
                h = int(target_tl.GetSetting("timelineResolutionHeight") or 1080)
            except Exception:
                w, h = 1920, 1080
            ET.SubElement(sc, "width").text  = str(w)
            ET.SubElement(sc, "height").text = str(h)
            make_rate_elem(sc)

            if not audio_only_mode and video_clip_maps:
                ci_counter = [0]
                for vi_src, vclips in sorted(video_clip_maps.items()):
                    v_track_el = ET.SubElement(video_el, "track")
                    dest_pos = 0
                    for op in kept_ops:
                        op_dur = op["e"] - op["s"]
                        color  = COLOR_MAP.get(op["type"])
                        if not color and str(op["type"]).startswith("custom_"):
                            color = op["type"].split("_")[1]
                        segs = op_to_clipitems(op, vclips)
                        for seg in segs:
                            # dest_start accounts for where in the op this segment begins
                            # (op_offset > 0 when a clip boundary falls inside the op)
                            ci_dest_start = dest_pos + seg["op_offset"]
                            ci_counter[0] += 1
                            make_clipitem(
                                v_track_el,
                                ci_id      = f"clipitem-v{vi_src}-{ci_counter[0]}",
                                dest_start = ci_dest_start,
                                dest_end   = ci_dest_start + seg["duration"],
                                src_in     = seg["src_in"],
                                src_out    = seg["src_out"],
                                duration   = seg["duration"],
                                file_path  = seg["file_path"],
                                color      = color,
                            )
                        # ALWAYS advance by full op duration — keeps all tracks in sync
                        dest_pos += op_dur
            else:
                # Empty video track placeholder (required by FCP7 XML schema)
                ET.SubElement(video_el, "track")

            # ── AUDIO section ─────────────────────────────────────────
            audio_el = ET.SubElement(media, "audio")

            if audio_clip_maps:
                ci_counter_a = [0]
                sorted_src_tracks = sorted(audio_clip_maps.keys())

                if preserve_track_order:
                    # Emit one <track> per position from 1 to max selected source track.
                    # Non-selected positions get an empty <track> element (gap placeholder).
                    # sourcetrack_idx uses out_idx (sequential channel of source file),
                    # NOT ai_src — because trackindex refers to the source FILE's audio
                    # channel, not the source timeline track number.
                    max_src_track  = sorted_src_tracks[-1]
                    track_positions = range(1, max_src_track + 1)
                else:
                    # Pack tracks sequentially: A1→1, A4→2, etc.
                    track_positions = range(1, len(sorted_src_tracks) + 1)

                for track_pos in track_positions:
                    a_track_el = ET.SubElement(audio_el, "track")

                    if preserve_track_order:
                        ai_src = track_pos
                    else:
                        ai_src = sorted_src_tracks[track_pos - 1]

                    if ai_src not in audio_clip_maps:
                        # Gap placeholder — empty track, no clipitems
                        continue

                    aclips  = audio_clip_maps[ai_src]
                    # out_idx = sequential rank among selected tracks (1-based).
                    # This is the SOURCE FILE's channel index — NOT the TL track number.
                    out_idx = sorted_src_tracks.index(ai_src) + 1

                    dest_pos = 0
                    for op in kept_ops:
                        op_dur = op["e"] - op["s"]
                        color  = COLOR_MAP.get(op["type"])
                        if not color and str(op["type"]).startswith("custom_"):
                            color = op["type"].split("_")[1]
                        segs = op_to_clipitems(op, aclips)
                        for seg in segs:
                            ci_dest_start = dest_pos + seg["op_offset"]
                            ci_counter_a[0] += 1
                            make_clipitem(
                                a_track_el,
                                ci_id            = f"clipitem-a{ai_src}-{ci_counter_a[0]}",
                                dest_start       = ci_dest_start,
                                dest_end         = ci_dest_start + seg["duration"],
                                src_in           = seg["src_in"],
                                src_out          = seg["src_out"],
                                duration         = seg["duration"],
                                file_path        = seg["file_path"],
                                color            = color,
                                sourcetrack_type = "audio",
                                sourcetrack_idx  = out_idx,
                            )
                        # ALWAYS advance by full op duration — keeps all tracks in sync
                        dest_pos += op_dur
            else:
                ET.SubElement(audio_el, "track")

            # ── 7. Write XML with proper declaration ──────────────────
            tree = ET.ElementTree(xmeml)
            raw_bytes = ET.tostring(xmeml, encoding="unicode", xml_declaration=False)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(raw_bytes)

            log_info(f"build_edit_xml_from_ops: wrote {output_path} "
                     f"({len(kept_ops)} ops, {total_dest_frames} frames, "
                     f"{len(color_schedule)} colored clipitems)")
            return True, color_schedule

        except Exception as e:
            import traceback
            log_error(f"build_edit_xml_from_ops error: {e}\n{traceback.format_exc()}")
            return False, {}

    def reapply_clip_colors(self, tl_name, color_schedule):
        """
        POST-IMPORT COLOR VERIFICATION & CORRECTION.

        Receives the color_schedule built during XML generation — a dict of
        {dest_start_frame: color_string|None} covering EVERY clipitem in the
        imported timeline (including multi-clip-source splits).

        Strategy:
          1. For each clip on every track, look up its GetStart() in color_schedule.
          2. If expected color is None (normal clip) — don’t touch it.
          3. If expected color is set:
             - GetClipColor() to check current color.
             - If already correct: count as OK (XML did its job).
             - If wrong/missing: SetClipColor() to correct it.
          4. Log summary: X correct from XML, Y corrected via API.
        """
        if not color_schedule:
            log_info("reapply_clip_colors: empty schedule, skipping.")
            return

        try:
            target_tl = None
            count = self.project.GetTimelineCount()
            for i in range(1, count + 1):
                tl = self.project.GetTimelineByIndex(i)
                if tl and tl.GetName() == tl_name:
                    target_tl = tl
                    break
            if not target_tl:
                log_error(f"reapply_clip_colors: timeline '{tl_name}' not found.")
                return

            tl_start = int(target_tl.GetStartFrame())
            # The schedule was built with dest_start=0 as sequence frame 0;
            # after import, frame 0 of the sequence maps to tl_start of the new TL.
            # Build an adjusted lookup: (tl_start + schedule_key) → color
            # But also keep original keys in case TL start is 0.
            def sched_color(item_start):
                """Returns expected color for a clip at item_start, or False if not found."""
                c = color_schedule.get(item_start)
                if c is not None or item_start in color_schedule:
                    return c  # None means 'normal' (no color)
                # Try offset by tl_start in case XML=0-based but TL has timecode offset
                adjusted = item_start - tl_start
                if adjusted in color_schedule:
                    return color_schedule[adjusted]
                return False  # not found

            corrected = 0
            ok_count  = 0
            missed    = 0

            def verify_track(track_type, track_count):
                nonlocal corrected, ok_count, missed
                for ti in range(1, track_count + 1):
                    try:
                        items = target_tl.GetItemListInTrack(track_type, ti) or []
                        for item in items:
                            if not item:
                                continue
                            item_start     = int(item.GetStart())
                            item_dur       = int(item.GetDuration()) if hasattr(item, 'GetDuration') else -1
                            expected_color = sched_color(item_start)
                            if expected_color is False:
                                # ── DIAGNOSTIC: log unknown clips so we can trace ghost clips ──
                                try:
                                    pool_item = item.GetMediaPoolItem()
                                    fp = (pool_item.GetClipProperty("File Path") or "??") if pool_item else "<no pool item>"
                                except Exception:
                                    fp = "<err>"
                                log_error(
                                    f"reapply_clip_colors: UNKNOWN CLIP on {track_type}{ti} "
                                    f"| start={item_start} (adj={item_start - tl_start}) "
                                    f"| dur={item_dur}f "
                                    f"| file={fp} "
                                    f"| schedule_keys={sorted(color_schedule.keys())[:10]}..."
                                )
                                missed += 1
                                continue
                            if not expected_color:
                                # Normal clip — no color expected, skip
                                ok_count += 1
                                continue
                            # Check what color is currently set
                            try:
                                actual_color = item.GetClipColor() or ""
                            except Exception:
                                actual_color = ""
                            if actual_color.lower() == expected_color.lower():
                                ok_count += 1  # XML set it correctly
                            else:
                                item.SetClipColor(expected_color)
                                corrected += 1
                    except Exception as te:
                        log_error(f"reapply_clip_colors verify {track_type}{ti}: {te}")

            v_count = target_tl.GetTrackCount("video")
            a_count = target_tl.GetTrackCount("audio")
            verify_track("video", v_count)
            verify_track("audio", a_count)

            log_info(f"reapply_clip_colors: '{tl_name}' — "
                     f"{ok_count} ok from XML, {corrected} corrected via API"
                     + (f", {missed} unmatched (normal)" if missed else "."))

        except Exception as e:
            log_error(f"reapply_clip_colors error: {e}")

    # ==========================================
    # LEGACY FALLBACK: APPEND TO TIMELINE
    # !! ABSOLUTE LAST RESORT — used only when XML import fails !!
    # Do NOT call this directly; engine.py calls it only as an emergency fallback.
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

            # Ensure new timeline lands in BadWords/Edits — pre-select that folder
            edits_bin = self.get_badwords_edits_bin()
            if edits_bin:
                self.media_pool.SetCurrentFolder(edits_bin)

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