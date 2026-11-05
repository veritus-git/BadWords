#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: assembler.py
ROLE: Core Module
DESCRIPTION:
Handles the final assembly and composition of video/audio files.
"""

import os
import uuid
import zipfile
import copy
import re
import json
import subprocess
import xml.etree.ElementTree as ET

from osdoc import log_info, log_warn, log_error, get_subprocess_kwargs


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

COLOR_MAP = {
    "bad":          "Violet",
    "repeat":       "Navy",
    "typo":         "Olive",
    "inaudible":    "Chocolate",
    "silence_mark": "Tan",
}

# All clip element tags we process for cutting
_CLIP_TAGS = frozenset({
    "Sm2TiVideoClip",
    "Sm2TiAudioClip",
    "Sm2TiGenerator",
})


# ══════════════════════════════════════════════════════════════════════════════
# DRT ASSEMBLY PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def unpack_drt(drt_path, output_dir):
    """
    Unpack a .drt file (ZIP archive) into output_dir.

    Returns the path to the inner timeline directory
    (e.g. output_dir/timeline_name/).
    """
    os.makedirs(output_dir, exist_ok=True)
    with zipfile.ZipFile(drt_path, 'r') as z:
        z.extractall(output_dir)

    # .drt usually contains a single top-level directory
    entries = [e for e in os.listdir(output_dir)
               if os.path.isdir(os.path.join(output_dir, e))]
    if len(entries) == 1:
        return os.path.join(output_dir, entries[0])
    return output_dir


def repack_drt(unpacked_root_dir, output_drt_path):
    """
    Repackage the unpacked directory structure back into a .drt (ZIP) file.
    """
    if os.path.exists(output_drt_path):
        os.remove(output_drt_path)
    with zipfile.ZipFile(output_drt_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(unpacked_root_dir):
            for fname in files:
                full_path = os.path.join(root, fname)
                arcname = os.path.relpath(full_path, unpacked_root_dir)
                z.write(full_path, arcname)
    log_info(f"repack_drt: wrote {output_drt_path}")


def find_seq_container_xml(unpacked_timeline_dir, target_tl_name=None):
    """
    Locate the SeqContainer XML file inside the unpacked timeline dir.
    When multiple SeqContainer XMLs exist (e.g. compound clips, nested sequences),
    identifies the exact SeqContainer for target_tl_name via MpFolder.xml/project.xml.
    """
    seq_dir = os.path.join(unpacked_timeline_dir, "SeqContainer")
    if not os.path.isdir(seq_dir):
        raise FileNotFoundError(
            f"SeqContainer directory not found in {unpacked_timeline_dir}"
        )
    xml_files = [f for f in os.listdir(seq_dir) if f.endswith('.xml')]
    if not xml_files:
        raise FileNotFoundError(f"No XML file found in {seq_dir}")
    if len(xml_files) == 1 or not target_tl_name:
        return os.path.join(seq_dir, xml_files[0])

    import re

    # Search MpFolder.xml and project.xml for target_tl_name
    for root_dir, dirs, files in os.walk(unpacked_timeline_dir):
        for fname in files:
            if fname.endswith('.xml') and root_dir != seq_dir:
                fpath = os.path.join(root_dir, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as xf:
                        content = xf.read()
                    if target_tl_name not in content:
                        continue

                    idx = 0
                    needle = f'<Name>{target_tl_name}</Name>'
                    while True:
                        idx = content.find(needle, idx)
                        if idx == -1:
                            break
                        chunk = content[idx:idx + 5000]
                        # Look for hex-encoded SeqRef: 005300650071005200650066 (SeqRef in utf-16-be)
                        seq_ref_pos = chunk.find('005300650071005200650066')
                        if seq_ref_pos != -1:
                            raw_hex = chunk[seq_ref_pos:seq_ref_pos + 400]
                            try:
                                decoded = bytes.fromhex(raw_hex).decode('utf-16-be', errors='ignore')
                                m = re.search(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', decoded)
                                if m:
                                    cand = os.path.join(seq_dir, f"{m.group(0).lower()}.xml")
                                    if os.path.isfile(cand):
                                        log_info(f"find_seq_container_xml: resolved '{target_tl_name}' via SeqRef -> {cand}")
                                        return cand
                            except Exception:
                                pass

                        # Match via <Sm2Sequence DbId="...">
                        m_seq = re.search(r'<Sm2Sequence[^>]+DbId="([^"]+)"', chunk)
                        if m_seq:
                            seq_id = m_seq.group(1)
                            for xf_name in xml_files:
                                cand_path = os.path.join(seq_dir, xf_name)
                                with open(cand_path, 'r', encoding='utf-8', errors='ignore') as sc:
                                    if seq_id in sc.read():
                                        log_info(f"find_seq_container_xml: resolved '{target_tl_name}' via sequence DbId -> {cand_path}")
                                        return cand_path
                        idx += len(needle)
                except Exception as e:
                    log_error(f"find_seq_container_xml scan error in {fpath}: {e}")

    # Fallback to the largest XML file (the main sequence is virtually always larger than compound clips)
    largest_file = max(xml_files, key=lambda f: os.path.getsize(os.path.join(seq_dir, f)))
    cand_fallback = os.path.join(seq_dir, largest_file)
    log_info(f"find_seq_container_xml: fallback by size -> {cand_fallback}")
    return cand_fallback


# ══════════════════════════════════════════════════════════════════════════════
# CORE CUTTING ENGINE
# ══════════════════════════════════════════════════════════════════════════════



def _get_clip_in(clip_el):
    """Read the <In> value from a clip element. Returns 0 if empty."""
    in_el = clip_el.find('In')
    if in_el is not None and in_el.text and in_el.text.strip():
        try:
            return int(in_el.text)
        except ValueError:
            pass
    return 0


def _set_clip_field(clip_el, tag, value):
    """Set or create a text field on a clip element."""
    el = clip_el.find(tag)
    if el is None:
        el = ET.SubElement(clip_el, tag)
    if value is None or (isinstance(value, int) and value == 0 and tag == 'In'):
        el.text = None  # produces <In/> (empty element)
    else:
        el.text = str(value)


def _op_color(op):
    """Return the Resolve clip color string for an op, or None."""
    c = COLOR_MAP.get(op['type'])
    if not c and str(op['type']).startswith('custom_'):
        parts = op['type'].split('_', 1)
        if len(parts) > 1:
            c = parts[1]
    if c:
        c = c.capitalize()
    return c

def _filter_tracks(track_vec, keep_indices, preserve_order=False):
    """Remove track Elements not in keep_indices (1-based), or clear them if preserve_order is True."""
    if keep_indices is None:
        return
    elements = list(track_vec.findall('Element'))
    for i, el in enumerate(elements):
        if (i + 1) not in keep_indices:
            # If preserve_order is True, or if we are deleting ALL tracks, keep the first one but empty
            if preserve_order or (i == 0 and not keep_indices):
                items_el = el.find('.//Items')
                if items_el is not None:
                    items_el.clear()
            else:
                track_vec.remove(el)


def apply_ops_to_seq_container(seq_xml_path, ops, base_offset, fps, audio_only_mode=False, audio_track_filter=None, video_track_filter=None, preserve_track_order=False):
    """
    Apply BadWords ops cuts to the SeqContainer XML in-place.

    ALGORITHM (mirrors apply_ops_cuts_to_timeline_xml but for .drt format):
      - ops is a sorted list of {'s': int, 'e': int, 'type': str} in 0-based frames.
      - Each clip's <Start> is absolute (base_offset + relative_position).
      - We subtract base_offset to work in 0-based space, apply cuts, then
        write destination positions starting from 0 + base_offset.
      - For each clip that overlaps with kept ops: emit one clip per op-overlap,
        adjusting <Start>, <Duration>, <In> and generating a new DbId.
      - Binary blobs are NEVER touched.

    Args:
        seq_xml_path: path to the SeqContainer/<uuid>.xml file
        ops: sorted list of {'s': int, 'e': int, 'type': str} (0-based frames)
        audio_only_mode: if True, clear video track items

    Returns:
        (success: bool, color_schedule: dict)
        color_schedule maps dest_start_frame → color_string|None
    """
    try:
        raw_bytes = b""
        with open(seq_xml_path, 'rb') as xf:
            raw_bytes = xf.read()

        has_colon_colon = False
        try:
            root = ET.fromstring(raw_bytes)
            tree = ET.ElementTree(root)
        except ET.ParseError as pe:
            log_warn(f"drt_apply_ops: direct XML parse error ({pe}), applying sanitization...")
            try:
                with open('/tmp/badwords_failed_seq.xml', 'wb') as dbg_f:
                    dbg_f.write(raw_bytes)
            except Exception:
                pass

            try:
                text = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text = raw_bytes.decode('latin-1', errors='replace')

            # 1. Strip illegal XML 1.0 control characters (except \t, \n, \r)
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

            # 2. Fix unescaped ampersands that are not valid entities
            text = re.sub(r'&(?!(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);)', '&amp;', text)

            # 3. Fix unescaped less-thans
            text = re.sub(r'<(?![a-zA-Z/_!?])', '&lt;', text)

            # 4. Fix C++ namespace colons in XML tag names (e.g. <ListMgt::LmVersionTable>)
            # XML 1.0 strictly forbids consecutive colons in element tags.
            while '::' in text:
                new_text = re.sub(r'(</?[a-zA-Z0-9_-]+)::([a-zA-Z0-9_-]+)', r'\1_BW_COLONCOLON_\2', text)
                if new_text == text:
                    break
                text = new_text
                has_colon_colon = True

            root = ET.fromstring(text.encode('utf-8'))
            tree = ET.ElementTree(root)
            log_info("drt_apply_ops: XML sanitized and parsed successfully!")

        # ── 1. Base offset is now provided by the timeline ───────────────────
        log_info(f"drt_apply_ops: base_offset={base_offset}, ops={len(ops)}, "
                 f"fps={fps}, audio_only={audio_only_mode}, preserve_order={preserve_track_order}")

        # ── 2. Build sorted ops and cumulative dest offsets ───────────────────
        sorted_ops = sorted(ops, key=lambda x: x['s'])
        dest_offsets = []
        acc = 0
        for op in sorted_ops:
            dest_offsets.append(acc)
            acc += (op['e'] - op['s'])
        total_dest_frames = acc

        color_schedule = {}

        # ── 3. Process each TrackVec ──────────────────────────────────────────
        for track_vec_name in ('VideoTrackVec', 'AudioTrackVec'):
            track_vec = root.find(track_vec_name)
            if track_vec is None:
                continue

            is_video_vec = (track_vec_name == 'VideoTrackVec')

            if is_video_vec and video_track_filter is not None:
                _filter_tracks(track_vec, video_track_filter, preserve_track_order)
            elif (not is_video_vec) and audio_track_filter is not None:
                _filter_tracks(track_vec, audio_track_filter, preserve_track_order)

            # If audio-only mode, clear all video track items
            if audio_only_mode and is_video_vec:
                for track_wrapper in track_vec.findall('Element'):
                    for track_el in track_wrapper:
                        items_el = track_el.find('Items')
                        if items_el is not None:
                            items_el.clear()
                continue

            # Process each track in this vec
            for track_wrapper in track_vec.findall('Element'):
                for track_el in track_wrapper:
                    items_el = track_el.find('Items')
                    if items_el is None:
                        continue

                    # Collect original clip elements
                    original_elements = list(items_el.findall('Element'))
                    # Clear the items — we'll re-add cut versions
                    items_el.clear()

                    for orig_wrapper in original_elements:
                        # Find the actual clip element inside <Element>
                        clip_el = None
                        clip_tag = None
                        for tag in _CLIP_TAGS:
                            clip_el = orig_wrapper.find(tag)
                            if clip_el is not None:
                                clip_tag = tag
                                break

                        if clip_el is None:
                            # Unknown element type — preserve as-is
                            # (safety: don't drop anything we don't understand)
                            items_el.append(orig_wrapper)
                            continue

                        # Read timing
                        start_el = clip_el.find('Start')
                        dur_el = clip_el.find('Duration')
                        if start_el is None or dur_el is None:
                            items_el.append(orig_wrapper)
                            continue

                        try:
                            abs_start = int(start_el.text)
                            duration = int(dur_el.text)
                        except (ValueError, TypeError):
                            items_el.append(orig_wrapper)
                            continue

                        clip_in = _get_clip_in(clip_el)

                        # ── Decode MediaFrameRate to find source scale ────────
                        media_fps = fps
                        mfr_el = clip_el.find('MediaFrameRate')
                        if mfr_el is not None and mfr_el.text:
                            hex_str = mfr_el.text.strip()
                            if len(hex_str) >= 16:
                                try:
                                    import struct
                                    media_fps = struct.unpack('<d', bytes.fromhex(hex_str[:16]))[0]
                                except Exception:
                                    pass
                        
                        source_scale = media_fps / fps if fps > 0 else 1.0

                        # Convert to 0-based
                        rel_start = abs_start - base_offset
                        rel_end = rel_start + duration

                        # ── Find all op-overlaps for this clip ────────────────
                        for i, op in enumerate(sorted_ops):
                            overlap_s = max(rel_start, op['s'])
                            overlap_e = min(rel_end, op['e'])
                            if overlap_e <= overlap_s:
                                continue

                            # Calculate new timing
                            clip_offset = overlap_s - rel_start
                            seg_dur = overlap_e - overlap_s
                            new_dest_rel = dest_offsets[i] + (overlap_s - op['s'])
                            new_abs_start = new_dest_rel + base_offset
                            
                            # Adjust In point using source scale
                            source_in_offset = int(clip_offset * source_scale)
                            new_in = clip_in + source_in_offset

                            # Deep-clone the entire wrapper <Element>
                            new_wrapper = copy.deepcopy(orig_wrapper)
                            new_clip = new_wrapper.find(clip_tag)

                            # Generate new unique DbId
                            new_clip.set('DbId', str(uuid.uuid4()))

                            # Patch timing fields ONLY
                            _set_clip_field(new_clip, 'Start', new_abs_start)
                            _set_clip_field(new_clip, 'Duration', seg_dur)
                            # In: write value if > 0, else leave empty
                            if new_in > 0:
                                _set_clip_field(new_clip, 'In', new_in)
                            else:
                                in_el = new_clip.find('In')
                                if in_el is not None:
                                    in_el.text = None

                            items_el.append(new_wrapper)

                            # Record color schedule
                            color_schedule[new_dest_rel] = _op_color(op)

        # ── 3b. Track Packing (when preserve_track_order is False) ─────────────
        # If preserve_track_order is False: remove all empty tracks (tracks with no clips),
        # so remaining tracks are packed sequentially starting at Track 1.
        if not preserve_track_order:
            for track_vec_name in ('VideoTrackVec', 'AudioTrackVec'):
                track_vec = root.find(track_vec_name)
                if track_vec is None:
                    continue

                if audio_only_mode and track_vec_name == 'VideoTrackVec':
                    # In audio-only mode, ensure exactly 1 empty video track remains
                    v_elements = list(track_vec.findall('Element'))
                    for el in v_elements[1:]:
                        track_vec.remove(el)
                    continue

                elements = list(track_vec.findall('Element'))
                non_empty = []
                for el in elements:
                    items_el = el.find('.//Items')
                    if items_el is not None and len(items_el.findall('Element')) > 0:
                        non_empty.append(el)

                if non_empty:
                    for el in elements:
                        if el not in non_empty:
                            track_vec.remove(el)
                elif len(elements) > 1:
                    # All tracks empty: keep only the first one
                    for el in elements[1:]:
                        track_vec.remove(el)

        # ── 4. Write modified XML back ────────────────────────────────────────
        serialized = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        # Restore C++ namespace tags if replaced
        if has_colon_colon or b'_BW_COLONCOLON_' in serialized:
            serialized = serialized.replace(b'_BW_COLONCOLON_', b'::')

        # Ensure standard double-quote declaration
        if serialized.startswith(b"<?xml version='1.0' encoding='utf-8'?>"):
            serialized = b'<?xml version="1.0" encoding="UTF-8"?>' + serialized[len(b"<?xml version='1.0' encoding='utf-8'?>"):]

        # Preserve original DbAppVer/DbPrjVer comment if present
        m_comment = re.search(rb'(<!--DbAppVer="[^"]*"\s+DbPrjVer="[^"]*"-->)', raw_bytes)
        if m_comment and m_comment.group(1) not in serialized:
            decl_end = serialized.find(b'?>\n')
            if decl_end != -1:
                insert_idx = decl_end + 3
                serialized = serialized[:insert_idx] + m_comment.group(1) + b'\n' + serialized[insert_idx:]

        with open(seq_xml_path, 'wb') as out_f:
            out_f.write(serialized)

        log_info(f"drt_apply_ops: wrote {seq_xml_path} "
                 f"(base={base_offset}, total_dest={total_dest_frames}f, "
                 f"color_entries={len(color_schedule)})")
        return True, color_schedule

    except Exception as e:
        import traceback
        log_error(f"drt_apply_ops error: {e}\n{traceback.format_exc()}")
        return False, {}


# ══════════════════════════════════════════════════════════════════════════════
# MEDIA POOL DUPLICATE CLEANUP
# ══════════════════════════════════════════════════════════════════════════════

def _snapshot_media_pool(media_pool):
    """
    Walk the entire Media Pool and count occurrences of each (file_path, clip_name).
    
    This is used BEFORE .drt import to identify which clips already existed,
    so we can delete the newly-created duplicates afterwards.
    
    We use (file_path, clip_name) as identifiers because Resolve's scripting
    API creates new proxy objects on each GetClipList() call, making Python
    id() unreliable for cross-call comparisons.
    
    Returns a dict of {(file_path, clip_name): count}.
    """
    from collections import Counter
    existing = Counter()
    
    def _walk_folder(folder):
        try:
            clips = folder.GetClipList()
            if clips:
                for clip in clips:
                    try:
                        fp = clip.GetClipProperty("File Path") or ""
                        name = clip.GetName() or ""
                        existing[(fp, name)] += 1
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            for sub in folder.GetSubFolderList():
                _walk_folder(sub)
        except Exception:
            pass
    
    try:
        root = media_pool.GetRootFolder()
        if root:
            _walk_folder(root)
    except Exception as e:
        log_error(f"_snapshot_media_pool error: {e}")
    
    return existing


def _cleanup_duplicate_media(media_pool, pre_import_counts, resolve_handler):
    """
    After .drt import, walk the Media Pool again and compare counts.
    Any (file_path, clip_name) key whose count increased means Resolve
    created duplicates during the .drt import.
    
    CRITICAL: We do NOT delete these clips! The newly imported timeline
    references them internally by database ID. Deleting them would cause
    Media Offline on the assembled timeline.
    
    Instead, we MOVE the surplus copies to BadWords/Resources bin so they
    don't clutter the user's carefully organized Media Pool.
    
    We skip Timeline-type clips (the newly imported timeline is handled separately).
    
    Identification is done via (file_path, clip_name) tuples with occurrence counting.
    """
    from collections import Counter
    
    # Build post-import counts and collect clip references
    post_counts = Counter()
    clip_registry = {}  # key -> list of (clip, folder)
    
    def _walk_folder(folder):
        try:
            clips = folder.GetClipList()
            if clips:
                for clip in clips:
                    try:
                        clip_type = clip.GetClipProperty("Type")
                        if clip_type == "Timeline":
                            continue
                        
                        fp = clip.GetClipProperty("File Path") or ""
                        name = clip.GetName() or ""
                        key = (fp, name)
                        
                        post_counts[key] += 1
                        if key not in clip_registry:
                            clip_registry[key] = []
                        clip_registry[key].append((clip, folder))
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            for sub in folder.GetSubFolderList():
                _walk_folder(sub)
        except Exception:
            pass
    
    try:
        root = media_pool.GetRootFolder()
        if root:
            _walk_folder(root)
    except Exception as e:
        log_error(f"_cleanup_duplicate_media walk error: {e}")
        return
    
    # Find keys where count increased (duplicates created by import)
    to_move = []
    for key, post_count in post_counts.items():
        pre_count = pre_import_counts.get(key, 0)
        surplus = post_count - pre_count
        if surplus > 0:
            # Move the LAST 'surplus' clips for this key (most recently added)
            entries = clip_registry.get(key, [])
            for clip, folder in entries[-surplus:]:
                to_move.append(clip)
    
    if not to_move:
        log_info("drt_cleanup: no duplicate media clips found after import.")
        return
    
    # Move duplicates to BadWords/Resources bin instead of deleting
    resources_bin = resolve_handler.get_badwords_resources_bin()
    if not resources_bin:
        log_error("drt_cleanup: could not get BadWords/Resources bin, skipping cleanup.")
        return
    
    log_info(f"drt_cleanup: moving {len(to_move)} imported source clip(s) to BadWords/Resources...")
    try:
        media_pool.MoveClips(to_move, resources_bin)
        log_info(f"drt_cleanup: moved {len(to_move)} clip(s) to BadWords/Resources.")
    except Exception as move_err:
        log_error(f"drt_cleanup: MoveClips to Resources failed: {move_err}")


# ══════════════════════════════════════════════════════════════════════════════
# HIGH-LEVEL ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def assemble_via_drt(resolve_handler, original_tl_name, ops,
                     new_tl_name, audio_only_mode=False,
                     audio_track_filter=None, video_track_filter=None,
                     preserve_track_order=False,
                     temp_dir=None, status_cb=None):
    """
    Full DRT assembly pipeline — direct vertical slicing.

    1. Export source timeline as .drt
    2. Unpack → apply ops cuts to SeqContainer XML → repack
    3. Import modified .drt
    4. Rename timeline (importOptions not supported for .drt)
    5. Return (success, color_schedule, actual_tl_name)
    """
    import time

    if not temp_dir:
        temp_dir = resolve_handler.os_doc.get_temp_folder() if hasattr(resolve_handler, 'os_doc') else '/tmp'
    os.makedirs(temp_dir, exist_ok=True)

    safe_name = "".join(c for c in new_tl_name if c.isalnum() or c in '_- ')
    safe_name = safe_name.replace(' ', '_')
    src_drt_path = os.path.join(temp_dir, f"bw_src_{safe_name}.drt")
    cut_drt_path = os.path.join(temp_dir, f"bw_cut_{safe_name}.drt")
    unpack_dir = os.path.join(temp_dir, f"bw_unpack_{safe_name}")

    try:
        # ── Step 1: Export source timeline as .drt ────────────────────────────
        # Resolve Free 21.1+ does not support DRT export via API/bridge and would hang/fail.
        # Bypass DRT immediately so we jump straight to XML assembly without delay.
        if hasattr(resolve_handler, 'is_free_21_1_or_newer') and resolve_handler.is_free_21_1_or_newer():
            log_info("drt_assemble: Resolve Free 21.1+ detected — bypassing DRT export directly to XML fallback.")
            return False, {}, None

        log_info(f"drt_assemble: exporting '{original_tl_name}' as .drt...")
        if resolve_handler.backend == 'bridge':
            export_ok, base_offset = resolve_handler.export_timeline_drt(original_tl_name, src_drt_path)
            fps = resolve_handler.fps
            if not export_ok or not os.path.exists(src_drt_path):
                log_error("drt_assemble: .drt export failed (bridge).")
                return False, {}, None
        else:
            target_tl = None
            count = resolve_handler.project.GetTimelineCount()
            for i in range(1, count + 1):
                tl = resolve_handler.project.GetTimelineByIndex(i)
                if tl.GetName() == original_tl_name:
                    target_tl = tl
                    break

            if not target_tl:
                log_error(f"drt_assemble: timeline '{original_tl_name}' not found.")
                return False, {}, None

            # Get critical parameters for math
            base_offset = target_tl.GetStartFrame()
            fps = resolve_handler.fps

            export_type = getattr(resolve_handler.resolve, 'EXPORT_DRT', 1)
            if export_type is None:
                export_type = 1

            export_ok = target_tl.Export(src_drt_path, export_type)
            if not export_ok or not os.path.exists(src_drt_path):
                log_error("drt_assemble: .drt export failed.")
                return False, {}, None

        log_info(f"drt_assemble: exported .drt ({os.path.getsize(src_drt_path)} bytes)")
        time.sleep(0.05)



        # ── Step 2: Unpack .drt ───────────────────────────────────────────────
        timeline_dir = unpack_drt(src_drt_path, unpack_dir)
        seq_xml = find_seq_container_xml(timeline_dir, original_tl_name)
        log_info(f"drt_assemble: SeqContainer at {seq_xml}")

        # ── Step 3: Apply ops cuts ────────────────────────────────────────────
        ok, color_schedule = apply_ops_to_seq_container(
            seq_xml, ops, base_offset, fps, audio_only_mode=audio_only_mode,
            audio_track_filter=audio_track_filter, video_track_filter=video_track_filter,
            preserve_track_order=preserve_track_order
        )
        if not ok:
            log_error("drt_assemble: apply_ops_to_seq_container failed.")
            return False, {}, None

        # ── Step 4: Repack as .drt ────────────────────────────────────────────
        repack_drt(unpack_dir, cut_drt_path)
        time.sleep(0.05)

        if status_cb:
            try:
                status_cb("import")
            except Exception:
                pass

        if resolve_handler.backend == 'bridge':
            log_info("drt_assemble: importing modified .drt via bridge...")
            imp_ok, actual_name = resolve_handler.import_timeline_drt(cut_drt_path, new_tl_name)
            if not imp_ok:
                log_error("drt_assemble: import_timeline_drt (bridge) failed.")
                return False, {}, None
            log_info(f"drt_assemble: SUCCESS (bridge) → '{actual_name}'")
            return True, color_schedule, actual_name

        # ── Step 5: Snapshot Media Pool BEFORE import ─────────────────────────
        # .drt import does NOT support importSourceClips:false, so Resolve will
        # re-import every referenced source file as a new Media Pool clip.
        # We snapshot existing clips beforehand and delete the duplicates after.
        log_info("drt_assemble: snapshotting Media Pool before import...")
        pre_import_clips = _snapshot_media_pool(resolve_handler.media_pool)
        log_info(f"drt_assemble: pre-import snapshot: {len(pre_import_clips)} clip(s)")

        # ── Step 6: Import modified .drt ──────────────────────────────────────
        log_info(f"drt_assemble: importing modified .drt...")

        # Reset to root folder for clean import
        root_folder = resolve_handler.media_pool.GetRootFolder()
        if root_folder:
            resolve_handler.media_pool.SetCurrentFolder(root_folder)

        new_tl = resolve_handler.media_pool.ImportTimelineFromFile(cut_drt_path)
        time.sleep(0.1)

        if not new_tl:
            log_error("drt_assemble: ImportTimelineFromFile returned None.")
            return False, {}, None

        # ── Step 7: Move duplicate media clips to BadWords/Resources ─────────
        # .drt import creates new MediaPoolItems for all referenced source files.
        # We can't delete them (timeline references them by DB ID → Media Offline).
        # Instead, move them to BadWords/Resources to keep the user's bins clean.
        try:
            _cleanup_duplicate_media(resolve_handler.media_pool, pre_import_clips, resolve_handler)
        except Exception as cleanup_err:
            log_error(f"drt_assemble: duplicate cleanup error: {cleanup_err}")

        # ── Step 8: Rename (importOptions not valid for .drt) ─────────────────
        actual_name = new_tl.GetName()
        log_info(f"drt_assemble: imported as '{actual_name}', renaming to '{new_tl_name}'...")
        try:
            new_tl.SetName(new_tl_name)
            actual_name = new_tl.GetName()
            log_info(f"drt_assemble: renamed to '{actual_name}'")
        except Exception as rename_err:
            log_error(f"drt_assemble: SetName failed: {rename_err}")
            # Continue with original name — not fatal
        # ── Step 9: Replaced with safe import retention ───────────────────────
        # Note: Do NOT delete timelines here based on t != new_tl as Python PyRemoteObject
        # instances are distinct wrappers and newly imported DRTs don't have colors populated yet.

        # ── Step 10: Move to BadWords bin ─────────────────────────────────────
        bw_bin = resolve_handler.get_badwords_root_bin()
        if bw_bin:
            try:
                tl_item = resolve_handler.find_timeline_item_recursive(
                    resolve_handler.media_pool.GetRootFolder(), actual_name
                )
                if tl_item:
                    resolve_handler.media_pool.MoveClips([tl_item], bw_bin)
                    log_info(f"drt_assemble: moved '{actual_name}' → BadWords/")
            except Exception as move_err:
                log_error(f"drt_assemble: MoveClips error: {move_err}")

        log_info(f"drt_assemble: SUCCESS → '{actual_name}'")
        return True, color_schedule, actual_name

    except Exception as e:
        import traceback
        log_error(f"drt_assemble: FAILED: {e}\n{traceback.format_exc()}")
        return False, {}, None

    finally:
        # Cleanup temp files
        import shutil
        for p in (src_drt_path, cut_drt_path):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        try:
            if os.path.exists(unpack_dir):
                shutil.rmtree(unpack_dir)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# SEAMLESS / LOSSLESS CUT ASSEMBLY PIPELINE (STANDALONE MEDIA FILES)
# ══════════════════════════════════════════════════════════════════════════════

def assemble_via_seamless_cut(source_file: str, ops: list, output_path: str,
                              fps: float = 24.0, temp_dir: str = None,
                              callback_status = None, callback_progress = None,
                              ffmpeg_cmd: str = "ffmpeg") -> tuple[bool, str]:
    """
    Direct lossless/seamless cut assembly for standalone video and audio files
    (MP4, MOV, MKV, WAV, etc.) using FFmpeg direct stream copy (-c copy) and concat demuxer.
    
    Preserves 100% of original quality, bitrates, codecs and container streams without
    any re-encoding.
    
    Args:
        source_file: Path to input media file.
        ops: Sorted list of kept operations [{'s': start_frame, 'e': end_frame, ...}, ...]
        output_path: Destination path for the cut media file.
        fps: Timeline frame rate (default 24.0).
        temp_dir: Directory for temporary segments.
        callback_status: Callable(str) for progress updates.
        callback_progress: Callable(int 0..100) for progress bar updates.
        ffmpeg_cmd: Path or command for FFmpeg executable.
        
    Returns:
        (success: bool, result_message: str)
    """
    import subprocess
    import shutil
    import time

    def set_status(msg: str):
        if callback_status:
            callback_status(msg)
        else:
            log_info(f"[SeamlessCut] {msg}")

    def set_progress(val: int):
        if callback_progress:
            callback_progress(val)

    if not source_file or not os.path.isfile(source_file):
        log_error(f"assemble_via_seamless_cut: source file does not exist: {source_file}")
        return False, "Source file not found."

    if not ops:
        log_error("assemble_via_seamless_cut: ops list is empty.")
        return False, "No operations to assemble."

    if fps <= 0:
        fps = 24.0

    # 1. Calculate kept time ranges in seconds
    keep_segments = []
    for op in sorted(ops, key=lambda x: x['s']):
        start_s = max(0.0, float(op['s']) / fps)
        end_s = max(0.0, float(op['e']) / fps)
        dur_s = end_s - start_s
        if dur_s > 0.04:  # Minimum 1-frame duration threshold
            keep_segments.append((start_s, dur_s))

    if not keep_segments:
        log_error("assemble_via_seamless_cut: all segments were cut.")
        return False, "All segments were cut out."

    log_info(f"assemble_via_seamless_cut: {len(keep_segments)} segment(s) to stitch into '{output_path}'")
    set_status("Przygotowywanie bezstratnego montażu...")
    set_progress(5)

    # 2. Setup temp directory
    if not temp_dir:
        temp_dir = os.path.join(os.path.dirname(output_path), f".bw_tmp_{int(time.time())}")
    os.makedirs(temp_dir, exist_ok=True)

    _, ext = os.path.splitext(source_file)
    segment_files = []

    try:
        # 3. Extract each segment losslessly via FFmpeg stream copy
        total_segs = len(keep_segments)
        for idx, (start_s, dur_s) in enumerate(keep_segments):
            seg_filename = f"seg_{idx:05d}{ext}"
            seg_path = os.path.join(temp_dir, seg_filename)

            set_status(f"Wycinanie segmentu {idx + 1}/{total_segs}...")
            pct = 10 + int((idx / max(1, total_segs)) * 70)
            set_progress(pct)

            cmd = [
                ffmpeg_cmd, "-y",
                "-ss", f"{start_s:.6f}",
                "-i", source_file,
                "-t", f"{dur_s:.6f}",
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                seg_path
            ]

            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, **get_subprocess_kwargs())
            if res.returncode != 0 or not os.path.exists(seg_path) or os.path.getsize(seg_path) == 0:
                log_error(f"assemble_via_seamless_cut: segment {idx} failed (rc={res.returncode}): {res.stderr[-300:]}")
                return False, f"Failed to cut segment {idx + 1}."

            segment_files.append(seg_path)

        # 4. Write concat demuxer list
        set_status("Łączenie wyciętych segmentów bez rekompresji...")
        set_progress(85)

        concat_list_path = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for seg in segment_files:
                # Escape single quotes for ffmpeg concat demuxer
                safe_path = seg.replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        # 5. Merge all segments via Concat Demuxer with stream copy
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        concat_cmd = [
            ffmpeg_cmd, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            output_path
        ]

        concat_res = subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, **get_subprocess_kwargs())
        if concat_res.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            log_error(f"assemble_via_seamless_cut: concat failed (rc={concat_res.returncode}): {concat_res.stderr[-300:]}")
            return False, "Failed to concatenate segments."

        set_status("Zakończono montaż bezstratny!")
        set_progress(100)
        log_info(f"assemble_via_seamless_cut: SUCCESS -> '{output_path}' ({os.path.getsize(output_path)} bytes)")
        return True, output_path

    except Exception as e:
        import traceback
        log_error(f"assemble_via_seamless_cut: unexpected error: {e}\n{traceback.format_exc()}")
        return False, str(e)

    finally:
        # Clean up temporary segments directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


# ==============================================================================
# STANDALONE TIMELINE EXPORTERS (FCP7 XML, OpenTimelineIO, FCPXML, EDL)
# ==============================================================================

def _path_to_fileurl(path: str) -> str:
    """Converts a local filesystem path to a standard RFC 3986 file://localhost URL."""
    import urllib.parse
    path = path.replace('\\', '/')
    if len(path) >= 2 and path[1] == ':':
        path = '/' + path
    if not path.startswith('/'):
        path = '/' + path
    encoded = urllib.parse.quote(path, safe='/:@')
    return 'file://localhost' + encoded


def _get_fps_params(fps: float) -> tuple[int, str]:
    """
    Returns (timebase: int, is_ntsc: str) for XML timeline specifications.
    Uses strict 0.005 threshold so standard integer frame rates (24, 30, 60)
    remain NTSC="FALSE", while drop-frame/fractional rates (23.976, 29.97, 59.94)
    are mapped to NTSC="TRUE".
    """
    ntsc_map = {
        23.976: (24, "TRUE"),
        29.97:  (30, "TRUE"),
        47.952: (48, "TRUE"),
        59.94:  (60, "TRUE"),
    }
    for target_fps, (tb, ntsc) in ntsc_map.items():
        if abs(fps - target_fps) < 0.005:
            return tb, ntsc
    return int(round(fps)), "FALSE"


def _get_fcpxml_fps_params(fps: float, height: int) -> tuple[str, str, any]:
    """
    Returns (format_name, frame_duration_str, to_time_str_fn) for Apple FCPXML.
    Adheres strictly to the Apple FCPXML DTD standard rational fractions.
    """
    if abs(fps - 23.976) < 0.005:
        name = f"FFVideoFormat{height}p2398"
        frame_dur = "1001/24000s"
        def to_time_str(frames: int) -> str:
            return f"{frames * 1001}/24000s" if frames != 0 else "0s"
        return name, frame_dur, to_time_str
    elif abs(fps - 29.97) < 0.005:
        name = f"FFVideoFormat{height}p2997"
        frame_dur = "1001/30000s"
        def to_time_str(frames: int) -> str:
            return f"{frames * 1001}/30000s" if frames != 0 else "0s"
        return name, frame_dur, to_time_str
    elif abs(fps - 59.94) < 0.005:
        name = f"FFVideoFormat{height}p5994"
        frame_dur = "1001/60000s"
        def to_time_str(frames: int) -> str:
            return f"{frames * 1001}/60000s" if frames != 0 else "0s"
        return name, frame_dur, to_time_str
    else:
        r_fps = int(round(fps)) if fps > 0 else 24
        name = f"FFVideoFormat{height}p{r_fps}"
        frame_dur = f"1/{r_fps}s"
        def to_time_str(frames: int) -> str:
            return f"{frames}/{r_fps}s" if frames != 0 else "0s"
        return name, frame_dur, to_time_str


def _format_timecode_edl(frame, fps: float) -> str:
    """Calculates non-drop frame timecode string HH:MM:SS:FF for EDL."""
    r_fps = int(round(fps)) if fps > 0 else 24
    f_int = int(round(float(frame)))
    ff = f_int % r_fps
    total_s = f_int // r_fps
    ss = total_s % 60
    total_m = total_s // 60
    mm = total_m % 60
    hh = total_m // 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


_MEDIA_TC_CACHE: dict[tuple[str, float], tuple[int, str, float]] = {}


def get_media_start_timecode_info(file_path: str, fps: float) -> tuple[int, str, float]:
    """
    Extracts embedded start timecode metadata from media file (BWF WAV, MP4/MOV, etc.).
    Returns (start_frames, tc_string, start_seconds).
    Caches results to avoid repeated ffprobe calls.
    """
    cache_key = (file_path, round(float(fps), 4))
    if cache_key in _MEDIA_TC_CACHE:
        return _MEDIA_TC_CACHE[cache_key]

    default_res = (0, "00:00:00:00", 0.0)
    if not file_path or not os.path.exists(file_path):
        return default_res

    try:
        kwargs = get_subprocess_kwargs()
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format:stream",
            "-of", "json", file_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8, **kwargs)
        if res.returncode != 0:
            _MEDIA_TC_CACHE[cache_key] = default_res
            return default_res

        data = json.loads(res.stdout)
        fmt = data.get("format", {})
        tags = fmt.get("tags", {})
        streams = data.get("streams", [])

        # 1. BWF WAV time_reference (samples since midnight / start)
        if "time_reference" in tags:
            try:
                tref = int(tags["time_reference"])
                sr = 48000
                for s in streams:
                    if s.get("codec_type") == "audio" and "sample_rate" in s:
                        sr = int(s["sample_rate"])
                        break
                sec = tref / sr
                f = int(round(sec * fps))
                hh = int(sec // 3600)
                mm = int((sec % 3600) // 60)
                ss = int(sec % 60)
                ff = int(round((sec - int(sec)) * fps))
                tc_str = f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"
                val = (f, tc_str, sec)
                _MEDIA_TC_CACHE[cache_key] = val
                return val
            except Exception:
                pass

        # 2. Container or Stream timecode tag (e.g. MOV/MP4 or WAV timecode tag)
        tc_tag = tags.get("timecode")
        if not tc_tag:
            for s in streams:
                stags = s.get("tags", {})
                if "timecode" in stags:
                    tc_tag = stags["timecode"]
                    break

        if tc_tag and isinstance(tc_tag, str):
            parts = [int(p) for p in tc_tag.replace(";", ":").split(":") if p.isdigit()]
            if len(parts) == 4:
                hh, mm, ss, ff = parts
                f = int(round((hh * 3600 + mm * 60 + ss) * fps + ff))
                sec = f / fps
                val = (f, tc_tag, sec)
                _MEDIA_TC_CACHE[cache_key] = val
                return val

        # 3. Container start_time
        st = fmt.get("start_time")
        if st:
            try:
                sec = float(st)
                if sec > 0.001:
                    f = int(round(sec * fps))
                    hh = int(sec // 3600)
                    mm = int((sec % 3600) // 60)
                    ss = int(sec % 60)
                    ff = int(round((sec - int(sec)) * fps))
                    tc_str = f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"
                    val = (f, tc_str, sec)
                    _MEDIA_TC_CACHE[cache_key] = val
                    return val
            except Exception:
                pass

    except Exception:
        pass

    _MEDIA_TC_CACHE[cache_key] = default_res
    return default_res


def build_standalone_fcp7_xml(clips_info: list, ops: list, output_path: str,
                              fps: float = 24.0, width: int = 1920, height: int = 1080,
                              preserve_audio_tracks: bool = True,
                              timeline_name: str = "BadWords Sequence",
                              link_all_tracks: bool = False,
                              link_av_clips: bool = True) -> tuple[bool, str]:
    """
    Builds a frame-accurate Final Cut Pro 7 XML (<xmeml version="5">) for standalone files.
    References only original source files on disk (never proxies).
    Fully supports mixed media: V1 track contains video items where video exists, with empty
    gaps during audio-only segments. A1..An tracks receive multi-channel audio clips.
    """
    try:
        kept_ops = [op for op in ops if op.get("type") != "silence_cut" and (op["e"] - op["s"]) >= 1]
        if not kept_ops:
            return False, "Brak operacji cięcia do wyeksportowania."

        if not clips_info:
            return False, "Brak danych o klipach źródłowych."

        total_dest_frames = sum(op["e"] - op["s"] for op in kept_ops)
        timebase, ntsc_str = _get_fps_params(fps)

        # Precompute frame bounds for each clip
        processed_clips = []
        for c in clips_info:
            start_f = int(round(float(c.get("offset", 0.0)) * fps))
            dur_f = max(1, int(round(float(c.get("duration", 0.0)) * fps)))

            processed_clips.append({
                "path": c["path"],
                "name": os.path.basename(c["path"]),
                "rel_start": start_f,
                "rel_end": start_f + dur_f,
                "src_in": 0,
                "src_out": dur_f,
                "total_frames": dur_f,
                "has_video": bool(c.get("has_video", False)),
                "audio_channels": max(1, int(c.get("audio_channels", 2))),
            })

        audio_exts = {
            ".wav", ".mp3", ".aac", ".aiff", ".aif", ".flac", ".m4a", ".ogg", ".opus"
        }

        # Root XML element
        xmeml = ET.Element("xmeml", version="5")
        seq = ET.SubElement(xmeml, "sequence", id="sequence-1")
        ET.SubElement(seq, "name").text = timeline_name
        ET.SubElement(seq, "duration").text = str(total_dest_frames)

        r_seq = ET.SubElement(seq, "rate")
        ET.SubElement(r_seq, "timebase").text = str(timebase)
        ET.SubElement(r_seq, "ntsc").text = ntsc_str

        media_el = ET.SubElement(seq, "media")

        # ── Video Section ─────────────────────────────────────────────────────
        video_el = ET.SubElement(media_el, "video")
        fmt = ET.SubElement(video_el, "format")
        sc = ET.SubElement(fmt, "samplecharacteristics")
        ET.SubElement(sc, "width").text = str(width)
        ET.SubElement(sc, "height").text = str(height)
        r_sc = ET.SubElement(sc, "rate")
        ET.SubElement(r_sc, "timebase").text = str(timebase)
        ET.SubElement(r_sc, "ntsc").text = ntsc_str

        # File registry
        file_registry: dict[str, str] = {}
        file_id_counter = [0]

        def get_file_id(fp: str) -> str:
            if fp not in file_registry:
                file_id_counter[0] += 1
                file_registry[fp] = f"file-{file_id_counter[0]}"
            return file_registry[fp]

        emitted_full_files: set[str] = set()

        def make_file_elem(parent_el, fp: str):
            fid = get_file_id(fp)
            file_el = ET.SubElement(parent_el, "file", id=fid)
            if fp not in emitted_full_files:
                emitted_full_files.add(fp)
                ET.SubElement(file_el, "name").text = os.path.basename(fp)
                ET.SubElement(file_el, "pathurl").text = _path_to_fileurl(fp)
                r_f = ET.SubElement(file_el, "rate")
                ET.SubElement(r_f, "timebase").text = str(timebase)
                ET.SubElement(r_f, "ntsc").text = ntsc_str

                # Find clip total duration in frames and metadata
                match_dur = 0
                clip_has_vid = False
                clip_ch = 2
                for pc in processed_clips:
                    if pc["path"] == fp:
                        match_dur = max(match_dur, pc["total_frames"])
                        clip_has_vid = pc.get("has_video", False)
                        clip_ch = pc.get("audio_channels", 2)
                if match_dur > 0:
                    ET.SubElement(file_el, "duration").text = str(match_dur)

                # Timecode block inside file element: DaVinci Resolve strictly requires
                # <timecode> matching media embedded timecode to conform and link media online!
                tc_frames, tc_str, _ = get_media_start_timecode_info(fp, float(timebase))
                tc_el = ET.SubElement(file_el, "timecode")
                r_tc = ET.SubElement(tc_el, "rate")
                ET.SubElement(r_tc, "timebase").text = str(timebase)
                ET.SubElement(r_tc, "ntsc").text = ntsc_str
                ET.SubElement(tc_el, "string").text = tc_str
                ET.SubElement(tc_el, "frame").text = str(tc_frames)
                ET.SubElement(tc_el, "displayformat").text = "NDF"

                media_sub = ET.SubElement(file_el, "media")
                if clip_has_vid:
                    v_sub = ET.SubElement(media_sub, "video")
                    sc_v = ET.SubElement(v_sub, "samplecharacteristics")
                    ET.SubElement(sc_v, "width").text = str(width)
                    ET.SubElement(sc_v, "height").text = str(height)
                a_sub = ET.SubElement(media_sub, "audio")
                sc_a = ET.SubElement(a_sub, "samplecharacteristics")
                ET.SubElement(sc_a, "depth").text = "24" if not clip_has_vid else "16"
                ET.SubElement(sc_a, "samplerate").text = "48000"
                ET.SubElement(a_sub, "channelcount").text = str(clip_ch)

        from collections import defaultdict
        links_by_key = defaultdict(list)

        ci_counter_v = [0]
        any_video = any(c["has_video"] for c in processed_clips)
        if any_video:
            v_track = ET.SubElement(video_el, "track")
            dest_pos = 0
            for op_idx, op in enumerate(kept_ops):
                op_dur = op["e"] - op["s"]
                for clip_idx, clip in enumerate(processed_clips):
                    ov_start = max(op["s"], clip["rel_start"])
                    ov_end = min(op["e"], clip["rel_end"])
                    if ov_end > ov_start and clip["has_video"]:
                        offset_in_clip = ov_start - clip["rel_start"]
                        src_in = offset_in_clip
                        seg_dur = ov_end - ov_start
                        src_out = src_in + seg_dur
                        op_offset = ov_start - op["s"]
                        ci_start = dest_pos + op_offset
                        ci_end = ci_start + seg_dur

                        ci_counter_v[0] += 1
                        ci = ET.SubElement(v_track, "clipitem", id=f"clipitem-v1-{ci_counter_v[0]}")
                        ET.SubElement(ci, "name").text = clip["name"]
                        ET.SubElement(ci, "duration").text = str(seg_dur)
                        r_ci = ET.SubElement(ci, "rate")
                        ET.SubElement(r_ci, "timebase").text = str(timebase)
                        ET.SubElement(r_ci, "ntsc").text = ntsc_str
                        ET.SubElement(ci, "start").text = str(ci_start)
                        ET.SubElement(ci, "end").text = str(ci_end)
                        ET.SubElement(ci, "in").text = str(src_in)
                        ET.SubElement(ci, "out").text = str(src_out)
                        make_file_elem(ci, clip["path"])

                        if link_all_tracks or link_av_clips:
                            l_key = op_idx if link_all_tracks else (op_idx, clip_idx)
                            links_by_key[l_key].append({
                                "id": f"clipitem-v1-{ci_counter_v[0]}",
                                "mediatype": "video",
                                "trackindex": 1,
                                "clipindex": ci_counter_v[0],
                                "elem": ci
                            })

                dest_pos += op_dur
        else:
            ET.SubElement(video_el, "track")

        # ── Audio Section ─────────────────────────────────────────────────────
        audio_el = ET.SubElement(media_el, "audio")
        max_ch = max((c["audio_channels"] for c in processed_clips), default=2) if preserve_audio_tracks else 2
        num_audio_tracks = max(1, min(max_ch, 8)) if preserve_audio_tracks else 1

        if preserve_audio_tracks:
            ET.SubElement(audio_el, "numOutputChannels").text = str(num_audio_tracks)
            fmt_a = ET.SubElement(audio_el, "format")
            sc_a = ET.SubElement(fmt_a, "samplecharacteristics")
            ET.SubElement(sc_a, "depth").text = "16"
            ET.SubElement(sc_a, "samplerate").text = "48000"

            outputs_el = ET.SubElement(audio_el, "outputs")
            for o_idx in range(1, num_audio_tracks + 1):
                grp = ET.SubElement(outputs_el, "group")
                ET.SubElement(grp, "index").text = str(o_idx)
                ET.SubElement(grp, "numchannels").text = "1"
                ET.SubElement(grp, "downmix").text = "0"
                ch_el = ET.SubElement(grp, "channel")
                ET.SubElement(ch_el, "index").text = str(o_idx)
        else:
            ET.SubElement(audio_el, "numOutputChannels").text = "2"
            fmt_a = ET.SubElement(audio_el, "format")
            sc_a = ET.SubElement(fmt_a, "samplecharacteristics")
            ET.SubElement(sc_a, "depth").text = "16"
            ET.SubElement(sc_a, "samplerate").text = "48000"

            outputs_el = ET.SubElement(audio_el, "outputs")
            grp1 = ET.SubElement(outputs_el, "group")
            ET.SubElement(grp1, "index").text = "1"
            ET.SubElement(grp1, "numchannels").text = "1"
            ET.SubElement(grp1, "downmix").text = "0"
            ch1 = ET.SubElement(grp1, "channel")
            ET.SubElement(ch1, "index").text = "1"

            grp2 = ET.SubElement(outputs_el, "group")
            ET.SubElement(grp2, "index").text = "2"
            ET.SubElement(grp2, "numchannels").text = "1"
            ET.SubElement(grp2, "downmix").text = "0"
            ch2 = ET.SubElement(grp2, "channel")
            ET.SubElement(ch2, "index").text = "2"

        for t_idx in range(1, num_audio_tracks + 1):
            track_ci_idx = 0
            if preserve_audio_tracks:
                a_track = ET.SubElement(
                    audio_el, "track",
                    currentExplodedTrackIndex=str(t_idx - 1),
                    totalExplodedTrackCount=str(num_audio_tracks),
                    premiereTrackType="Mono"
                )
                ET.SubElement(a_track, "outputchannelindex").text = str(t_idx)
            else:
                a_track = ET.SubElement(audio_el, "track", premiereTrackType="Stereo")

            dest_pos = 0
            for op_idx, op in enumerate(kept_ops):
                op_dur = op["e"] - op["s"]
                for clip_idx, clip in enumerate(processed_clips):
                    ov_start = max(op["s"], clip["rel_start"])
                    ov_end = min(op["e"], clip["rel_end"])
                    if ov_end > ov_start:
                        clip_ch = clip["audio_channels"]
                        src_ch = t_idx if t_idx <= clip_ch else (1 if clip_ch == 1 else ((t_idx - 1) % clip_ch + 1))

                        offset_in_clip = ov_start - clip["rel_start"]
                        src_in = offset_in_clip
                        seg_dur = ov_end - ov_start
                        src_out = src_in + seg_dur
                        op_offset = ov_start - op["s"]
                        ci_start = dest_pos + op_offset
                        ci_end = ci_start + seg_dur

                        track_ci_idx += 1
                        ci_kwargs = {"id": f"clipitem-a{t_idx}-{track_ci_idx}"}
                        if preserve_audio_tracks:
                            ci_kwargs["premiereChannelType"] = "mono"
                        else:
                            ci_kwargs["premiereChannelType"] = "stereo"

                        ci = ET.SubElement(a_track, "clipitem", **ci_kwargs)
                        ET.SubElement(ci, "name").text = clip["name"]
                        ET.SubElement(ci, "duration").text = str(seg_dur)
                        r_ci = ET.SubElement(ci, "rate")
                        ET.SubElement(r_ci, "timebase").text = str(timebase)
                        ET.SubElement(r_ci, "ntsc").text = ntsc_str
                        ET.SubElement(ci, "start").text = str(ci_start)
                        ET.SubElement(ci, "end").text = str(ci_end)
                        ET.SubElement(ci, "in").text = str(src_in)
                        ET.SubElement(ci, "out").text = str(src_out)
                        make_file_elem(ci, clip["path"])

                        if preserve_audio_tracks:
                            # Audio source track mapping for separated mono tracks
                            st = ET.SubElement(ci, "sourcetrack")
                            ET.SubElement(st, "mediatype").text = "audio"
                            ET.SubElement(st, "trackindex").text = str(src_ch)

                            flt = ET.SubElement(ci, "filter")
                            eff = ET.SubElement(flt, "effect")
                            ET.SubElement(eff, "name").text = "Audio Pan"
                            ET.SubElement(eff, "effectid").text = "audiopan"
                            ET.SubElement(eff, "effectcategory").text = "audio"
                            ET.SubElement(eff, "effecttype").text = "audio"
                            ET.SubElement(eff, "mediatype").text = "audio"
                            param = ET.SubElement(eff, "parameter")
                            ET.SubElement(param, "parameterid").text = "pan"
                            ET.SubElement(param, "name").text = "Pan"
                            ET.SubElement(param, "value").text = "0"
                        else:
                            # Single stereo track mode:
                            # If source has >= 2 channels, omit sourcetrack and pan filter so DaVinci Resolve
                            # binds full native stereo (Ch 1 -> Left, Ch 2 -> Right) in Clip Attributes!
                            # If source is genuinely mono (1 channel), map track 1 and pan center so audio plays in both ears.
                            if clip_ch == 1:
                                st = ET.SubElement(ci, "sourcetrack")
                                ET.SubElement(st, "mediatype").text = "audio"
                                ET.SubElement(st, "trackindex").text = "1"

                                flt = ET.SubElement(ci, "filter")
                                eff = ET.SubElement(flt, "effect")
                                ET.SubElement(eff, "name").text = "Audio Pan"
                                ET.SubElement(eff, "effectid").text = "audiopan"
                                ET.SubElement(eff, "effectcategory").text = "audio"
                                ET.SubElement(eff, "effecttype").text = "audio"
                                ET.SubElement(eff, "mediatype").text = "audio"
                                param = ET.SubElement(eff, "parameter")
                                ET.SubElement(param, "parameterid").text = "pan"
                                ET.SubElement(param, "name").text = "Pan"
                                ET.SubElement(param, "value").text = "0"

                        if link_all_tracks or link_av_clips:
                            l_key = op_idx if link_all_tracks else (op_idx, clip_idx)
                            links_by_key[l_key].append({
                                "id": f"clipitem-a{t_idx}-{track_ci_idx}",
                                "mediatype": "audio",
                                "trackindex": t_idx,
                                "clipindex": track_ci_idx,
                                "elem": ci
                            })

                dest_pos += op_dur

        # Build link elements across linked items (video-audio, audio-audio, etc.)
        if link_all_tracks or link_av_clips:
            for seg_key, items in links_by_key.items():
                if len(items) > 1:
                    for item in items:
                        for target in items:
                            link_el = ET.SubElement(item["elem"], "link")
                            ET.SubElement(link_el, "linkclipref").text = target["id"]
                            ET.SubElement(link_el, "mediatype").text = target["mediatype"]
                            ET.SubElement(link_el, "trackindex").text = str(target["trackindex"])
                            ET.SubElement(link_el, "clipindex").text = str(target["clipindex"])

        # Save XML to output path
        raw_xml = ET.tostring(xmeml, encoding="unicode")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(raw_xml)

        log_info(f"build_standalone_fcp7_xml: wrote {output_path} ({len(kept_ops)} cuts, {total_dest_frames} frames)")
        return True, output_path

    except Exception as e:
        import traceback
        log_error(f"build_standalone_fcp7_xml failed: {e}\n{traceback.format_exc()}")
        return False, str(e)


def build_standalone_otio(clips_info: list, ops: list, output_path: str,
                          fps: float = 24.0, width: int = 1920, height: int = 1080,
                          preserve_audio_tracks: bool = True,
                          timeline_name: str = "BadWords Sequence") -> tuple[bool, str]:
    """
    Builds an OpenTimelineIO (.otio) JSON timeline file.
    Fully open-source standard created by Pixar / Academy Software Foundation,
    natively imported by DaVinci Resolve, Premiere, and modern post-production suites.
    Uses clean absolute local file paths, matched track lengths, and complete schema
    fields to guarantee 100% stability and prevent DaVinci Resolve freezes.
    """
    try:
        kept_ops = [op for op in ops if op.get("type") != "silence_cut" and (op["e"] - op["s"]) >= 1]
        if not kept_ops:
            return False, "Brak operacji cięcia do wyeksportowania."

        total_dest_frames = sum(op["e"] - op["s"] for op in kept_ops)

        processed_clips = []
        for c in clips_info:
            start_f = int(round(float(c.get("offset", 0.0)) * fps))
            dur_f = max(1, int(round(float(c.get("duration", 0.0)) * fps)))

            processed_clips.append({
                "path": c["path"],
                "name": os.path.basename(c["path"]),
                "rel_start": start_f,
                "rel_end": start_f + dur_f,
                "src_in": 0,
                "src_out": dur_f,
                "total_frames": dur_f,
                "has_video": bool(c.get("has_video", False)),
                "audio_channels": max(1, int(c.get("audio_channels", 2))),
            })

        # Try using opentimelineio package if available
        try:
            import opentimelineio as otio
            tl = otio.schema.Timeline(
                name=timeline_name,
                global_start_time=otio.opentime.RationalTime(0, fps)
            )

            # Video Track
            any_video = any(c["has_video"] for c in processed_clips)
            if any_video:
                v_track = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
                dest_pos = 0
                curr_v_track_head = 0

                for op in kept_ops:
                    op_dur = op["e"] - op["s"]
                    for clip in processed_clips:
                        ov_start = max(op["s"], clip["rel_start"])
                        ov_end = min(op["e"], clip["rel_end"])
                        if ov_end > ov_start and clip["has_video"]:
                            offset_in_clip = ov_start - clip["rel_start"]
                            src_in = offset_in_clip
                            seg_dur = ov_end - ov_start
                            op_offset = ov_start - op["s"]
                            ci_start = dest_pos + op_offset

                            if ci_start > curr_v_track_head:
                                gap_dur = ci_start - curr_v_track_head
                                v_track.append(otio.schema.Gap(
                                    source_range=otio.opentime.TimeRange(
                                        start_time=otio.opentime.RationalTime(0, fps),
                                        duration=otio.opentime.RationalTime(gap_dur, fps)
                                    )
                                ))
                                curr_v_track_head = ci_start

                            clip_item = otio.schema.Clip(
                                name=clip["name"],
                                source_range=otio.opentime.TimeRange(
                                    start_time=otio.opentime.RationalTime(src_in, fps),
                                    duration=otio.opentime.RationalTime(seg_dur, fps)
                                ),
                                media_reference=otio.schema.ExternalReference(
                                    target_url=clip["path"],
                                    available_range=otio.opentime.TimeRange(
                                        start_time=otio.opentime.RationalTime(0, fps),
                                        duration=otio.opentime.RationalTime(clip["total_frames"], fps)
                                    )
                                )
                            )
                            v_track.append(clip_item)
                            curr_v_track_head = ci_start + seg_dur

                    dest_pos += op_dur

                if curr_v_track_head < total_dest_frames:
                    v_track.append(otio.schema.Gap(
                        source_range=otio.opentime.TimeRange(
                            start_time=otio.opentime.RationalTime(0, fps),
                            duration=otio.opentime.RationalTime(total_dest_frames - curr_v_track_head, fps)
                        )
                    ))

                tl.tracks.append(v_track)

            # Audio Track (single stereo master track A1)
            a_track = otio.schema.Track(name="A1", kind=otio.schema.TrackKind.Audio)
            dest_pos = 0
            curr_a_track_head = 0

            for op in kept_ops:
                op_dur = op["e"] - op["s"]
                for clip in processed_clips:
                    ov_start = max(op["s"], clip["rel_start"])
                    ov_end = min(op["e"], clip["rel_end"])
                    if ov_end > ov_start:
                        offset_in_clip = ov_start - clip["rel_start"]
                        src_in = offset_in_clip
                        seg_dur = ov_end - ov_start
                        op_offset = ov_start - op["s"]
                        ci_start = dest_pos + op_offset

                        if ci_start > curr_a_track_head:
                            gap_dur = ci_start - curr_a_track_head
                            a_track.append(otio.schema.Gap(
                                source_range=otio.opentime.TimeRange(
                                    start_time=otio.opentime.RationalTime(0, fps),
                                    duration=otio.opentime.RationalTime(gap_dur, fps)
                                )
                            ))
                            curr_a_track_head = ci_start

                        clip_item = otio.schema.Clip(
                            name=clip["name"],
                            source_range=otio.opentime.TimeRange(
                                start_time=otio.opentime.RationalTime(src_in, fps),
                                duration=otio.opentime.RationalTime(seg_dur, fps)
                            ),
                            media_reference=otio.schema.ExternalReference(
                                target_url=clip["path"],
                                available_range=otio.opentime.TimeRange(
                                    start_time=otio.opentime.RationalTime(0, fps),
                                    duration=otio.opentime.RationalTime(clip["total_frames"], fps)
                                )
                            )
                        )
                        a_track.append(clip_item)
                        curr_a_track_head = ci_start + seg_dur

                dest_pos += op_dur

            if curr_a_track_head < total_dest_frames:
                a_track.append(otio.schema.Gap(
                    source_range=otio.opentime.TimeRange(
                        start_time=otio.opentime.RationalTime(0, fps),
                        duration=otio.opentime.RationalTime(total_dest_frames - curr_a_track_head, fps)
                    )
                ))

            tl.tracks.append(a_track)

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            otio.adapters.write_to_file(tl, output_path)
            log_info(f"build_standalone_otio: wrote {output_path} via opentimelineio")
            return True, output_path

        except ImportError:
            # Pure Python JSON fallback if opentimelineio package not installed
            import json
            tracks_children = []

            # Video Track
            any_video = any(c["has_video"] for c in processed_clips)
            if any_video:
                v_children = []
                dest_pos = 0
                curr_v_track_head = 0

                for op in kept_ops:
                    op_dur = op["e"] - op["s"]
                    for clip in processed_clips:
                        ov_start = max(op["s"], clip["rel_start"])
                        ov_end = min(op["e"], clip["rel_end"])
                        if ov_end > ov_start and clip["has_video"]:
                            offset_in_clip = ov_start - clip["rel_start"]
                            src_in = offset_in_clip
                            seg_dur = ov_end - ov_start
                            op_offset = ov_start - op["s"]
                            ci_start = dest_pos + op_offset

                            if ci_start > curr_v_track_head:
                                gap_dur = ci_start - curr_v_track_head
                                v_children.append({
                                    "OTIO_SCHEMA": "Gap.1",
                                    "metadata": {},
                                    "name": "Gap",
                                    "source_range": {
                                        "OTIO_SCHEMA": "TimeRange.1",
                                        "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": 0.0},
                                        "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(gap_dur)}
                                    },
                                    "effects": [],
                                    "markers": [],
                                    "enabled": True
                                })
                                curr_v_track_head = ci_start

                            v_children.append({
                                "OTIO_SCHEMA": "Clip.1",
                                "metadata": {},
                                "name": clip["name"],
                                "source_range": {
                                    "OTIO_SCHEMA": "TimeRange.1",
                                    "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(src_in)},
                                    "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(seg_dur)}
                                },
                                "effects": [],
                                "markers": [],
                                "enabled": True,
                                "media_reference": {
                                    "OTIO_SCHEMA": "ExternalReference.1",
                                    "metadata": {},
                                    "name": clip["name"],
                                    "target_url": clip["path"],
                                    "available_range": {
                                        "OTIO_SCHEMA": "TimeRange.1",
                                        "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": 0.0},
                                        "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(clip["total_frames"])}
                                    }
                                }
                            })
                            curr_v_track_head = ci_start + seg_dur

                    dest_pos += op_dur

                if curr_v_track_head < total_dest_frames:
                    v_children.append({
                        "OTIO_SCHEMA": "Gap.1",
                        "metadata": {},
                        "name": "Gap",
                        "source_range": {
                            "OTIO_SCHEMA": "TimeRange.1",
                            "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": 0.0},
                            "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(total_dest_frames - curr_v_track_head)}
                        },
                        "effects": [],
                        "markers": [],
                        "enabled": True
                    })

                tracks_children.append({
                    "OTIO_SCHEMA": "Track.1",
                    "metadata": {},
                    "name": "V1",
                    "kind": "Video",
                    "source_range": None,
                    "effects": [],
                    "markers": [],
                    "enabled": True,
                    "children": v_children
                })

            # Audio Track (single stereo master track A1)
            a_children = []
            dest_pos = 0
            curr_a_track_head = 0

            for op in kept_ops:
                op_dur = op["e"] - op["s"]
                for clip in processed_clips:
                    ov_start = max(op["s"], clip["rel_start"])
                    ov_end = min(op["e"], clip["rel_end"])
                    if ov_end > ov_start:
                        offset_in_clip = ov_start - clip["rel_start"]
                        src_in = offset_in_clip
                        seg_dur = ov_end - ov_start
                        op_offset = ov_start - op["s"]
                        ci_start = dest_pos + op_offset

                        if ci_start > curr_a_track_head:
                            gap_dur = ci_start - curr_a_track_head
                            a_children.append({
                                "OTIO_SCHEMA": "Gap.1",
                                "metadata": {},
                                "name": "Gap",
                                "source_range": {
                                    "OTIO_SCHEMA": "TimeRange.1",
                                    "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": 0.0},
                                    "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(gap_dur)}
                                },
                                "effects": [],
                                "markers": [],
                                "enabled": True
                            })
                            curr_a_track_head = ci_start

                        a_children.append({
                            "OTIO_SCHEMA": "Clip.1",
                            "metadata": {},
                            "name": clip["name"],
                            "source_range": {
                                "OTIO_SCHEMA": "TimeRange.1",
                                "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(src_in)},
                                "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(seg_dur)}
                            },
                            "effects": [],
                            "markers": [],
                            "enabled": True,
                            "media_reference": {
                                "OTIO_SCHEMA": "ExternalReference.1",
                                "metadata": {},
                                "name": clip["name"],
                                "target_url": clip["path"],
                                "available_range": {
                                    "OTIO_SCHEMA": "TimeRange.1",
                                    "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": 0.0},
                                    "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(clip["total_frames"])}
                                }
                            }
                        })
                        curr_a_track_head = ci_start + seg_dur

                dest_pos += op_dur

            if curr_a_track_head < total_dest_frames:
                a_children.append({
                    "OTIO_SCHEMA": "Gap.1",
                    "metadata": {},
                    "name": "Gap",
                    "source_range": {
                        "OTIO_SCHEMA": "TimeRange.1",
                        "start_time": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": 0.0},
                        "duration": {"OTIO_SCHEMA": "RationalTime.1", "rate": fps, "value": float(total_dest_frames - curr_a_track_head)}
                    },
                    "effects": [],
                    "markers": [],
                    "enabled": True
                })

            tracks_children.append({
                "OTIO_SCHEMA": "Track.1",
                "metadata": {},
                "name": "A1",
                "kind": "Audio",
                "source_range": None,
                "effects": [],
                "markers": [],
                "enabled": True,
                "children": a_children
            })

            otio_doc = {
                "OTIO_SCHEMA": "Timeline.1",
                "metadata": {},
                "name": timeline_name,
                "global_start_time": {
                    "OTIO_SCHEMA": "RationalTime.1",
                    "rate": float(fps),
                    "value": 0.0
                },
                "tracks": {
                    "OTIO_SCHEMA": "Stack.1",
                    "metadata": {},
                    "name": "tracks",
                    "source_range": None,
                    "effects": [],
                    "markers": [],
                    "enabled": True,
                    "children": tracks_children
                }
            }

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(otio_doc, f, indent=2)

            log_info(f"build_standalone_otio: wrote {output_path} via json fallback")
            return True, output_path

    except Exception as e:
        import traceback
        log_error(f"build_standalone_otio failed: {e}\n{traceback.format_exc()}")
        return False, str(e)


def build_standalone_fcpxml(clips_info: list, ops: list, output_path: str,
                            fps: float = 24.0, width: int = 1920, height: int = 1080,
                            preserve_audio_tracks: bool = True,
                            timeline_name: str = "BadWords Sequence") -> tuple[bool, str]:
    """
    Builds an Apple Final Cut Pro X XML (.fcpxml).
    Conforms video on V1 and audio on A1/A2 with synchronized offsets and format matching.
    When preserve_audio_tracks is enabled, assigns distinct sub-roles to each audio channel
    (dialogue.dialogue-1 -> A1, dialogue.dialogue-2 -> A2), ensuring clean track separation
    without scattering cut pieces into individual extra tracks.
    """
    try:
        kept_ops = [op for op in ops if op.get("type") != "silence_cut" and (op["e"] - op["s"]) >= 1]
        if not kept_ops:
            return False, "Brak operacji cięcia do wyeksportowania."

        fcpxml = ET.Element("fcpxml", version="1.9")
        resources = ET.SubElement(fcpxml, "resources")
        fmt_name, frame_dur_str, to_time_str = _get_fcpxml_fps_params(fps, height)

        ET.SubElement(resources, "format", id="r1", name=fmt_name,
                      frameDuration=frame_dur_str, width=str(width), height=str(height))

        asset_map = {}
        for idx, c in enumerate(clips_info):
            aid = f"r{idx+2}"
            asset_map[c["path"]] = aid
            dur_s = float(c.get("duration", 0.0))
            dur_frames = max(1, int(round(dur_s * fps)))
            has_vid = bool(c.get("has_video"))
            ch = max(1, int(c.get("audio_channels", 2)))

            tc_frames, tc_str, tc_sec = get_media_start_timecode_info(c["path"], fps)

            asset_attribs = {
                "id": aid,
                "name": os.path.basename(c["path"]),
                "src": _path_to_fileurl(c["path"]),
                "start": to_time_str(tc_frames) if tc_frames > 0 else "0s",
                "duration": to_time_str(dur_frames),
                "hasVideo": "1" if has_vid else "0",
                "hasAudio": "1",
                "audioSources": "1",
                "audioChannels": str(ch),
                "audioRate": "48000"
            }
            if has_vid:
                asset_attribs["format"] = "r1"
            asset_el = ET.SubElement(resources, "asset", **asset_attribs)
            ET.SubElement(asset_el, "media-rep", kind="original-media", src=_path_to_fileurl(c["path"]))

        total_dest_frames = sum(op["e"] - op["s"] for op in kept_ops)
        library = ET.SubElement(fcpxml, "library")
        event = ET.SubElement(library, "event", name="BadWords Event")
        project = ET.SubElement(event, "project", name=timeline_name)
        sequence = ET.SubElement(project, "sequence", format="r1", duration=to_time_str(total_dest_frames))
        spine = ET.SubElement(sequence, "spine")

        # Process ops into spine clips sequentially with accurate offset and format
        dest_pos = 0
        for op in kept_ops:
            op_dur = op["e"] - op["s"]
            for c in clips_info:
                start_f = int(round(float(c.get("offset", 0.0)) * fps))
                dur_f = max(1, int(round(float(c.get("duration", 0.0)) * fps)))
                rel_end = start_f + dur_f

                ov_start = max(op["s"], start_f)
                ov_end = min(op["e"], rel_end)
                if ov_end > ov_start:
                    seg_dur = ov_end - ov_start
                    src_in = ov_start - start_f
                    op_offset = ov_start - op["s"]
                    ci_start = dest_pos + op_offset

                    aid = asset_map.get(c["path"], "r2")
                    has_vid = bool(c.get("has_video"))
                    audio_ch = max(1, int(c.get("audio_channels", 2)))

                    tc_frames, _, _ = get_media_start_timecode_info(c["path"], fps)
                    clip_kwargs = {
                        "ref": aid,
                        "name": os.path.basename(c["path"]),
                        "offset": to_time_str(ci_start),
                        "duration": to_time_str(seg_dur),
                        "start": to_time_str(tc_frames + src_in),
                        "audioRole": "dialogue"
                    }
                    if has_vid:
                        clip_kwargs["format"] = "r1"
                    ET.SubElement(spine, "asset-clip", **clip_kwargs)

            dest_pos += op_dur

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        raw_xml = ET.tostring(fcpxml, encoding="unicode")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n')
            f.write(raw_xml)

        return True, output_path
    except Exception as e:
        return False, str(e)


def build_standalone_edl(clips_info: list, ops: list, output_path: str,
                         fps: float = 24.0, preserve_audio_tracks: bool = True,
                         timeline_name: str = "BadWords Sequence") -> tuple[bool, str]:
    """
    Builds a CMX 3600 Edit Decision List (.edl).
    Uses industry-standard AX reel identifier and clean CMX conformity comments (* FROM CLIP NAME)
    with synchronized track codes (B for Both video+audio, AA for audio-only, V for video-only).
    """
    try:
        kept_ops = [op for op in ops if op.get("type") != "silence_cut" and (op["e"] - op["s"]) >= 1]
        if not kept_ops:
            return False, "Brak operacji cięcia do wyeksportowania."

        is_drop = (abs(fps - 29.97) < 0.005 or abs(fps - 59.94) < 0.005)
        lines = [
            f"TITLE: {timeline_name}",
            f"FCM: {'DROP FRAME' if is_drop else 'NON-DROP FRAME'}",
            f"* TIMEBASE: {fps:g}",
            ""
        ]

        event_idx = 1
        dest_pos = 0

        for op in kept_ops:
            op_dur = op["e"] - op["s"]
            for c in clips_info:
                start_f = int(round(float(c.get("offset", 0.0)) * fps))
                dur_f = max(1, int(round(float(c.get("duration", 0.0)) * fps)))
                rel_end = start_f + dur_f

                ov_start = max(op["s"], start_f)
                ov_end = min(op["e"], rel_end)
                if ov_end > ov_start:
                    seg_dur = ov_end - ov_start
                    src_in = ov_start - start_f
                    src_out = src_in + seg_dur
                    op_offset = ov_start - op["s"]
                    ci_start = dest_pos + op_offset
                    ci_end = ci_start + seg_dur

                    tc_frames, _, _ = get_media_start_timecode_info(c["path"], fps)
                    src_in_tc = _format_timecode_edl(tc_frames + src_in, fps)
                    src_out_tc = _format_timecode_edl(tc_frames + src_out, fps)
                    dst_in_tc = _format_timecode_edl(ci_start, fps)
                    dst_out_tc = _format_timecode_edl(ci_end, fps)

                    clip_name = os.path.basename(c["path"])
                    has_video = bool(c.get("has_video"))
                    audio_ch = max(1, int(c.get("audio_channels", 2)))

                    any_project_video = any(bool(clip.get("has_video")) for clip in clips_info)

                    if has_video:
                        lines.append(f"{event_idx:03d}  AX       {'B':<5} C        {src_in_tc} {src_out_tc} {dst_in_tc} {dst_out_tc}")
                        lines.append(f"* FROM CLIP NAME: {clip_name}")
                        lines.append("")
                        event_idx += 1
                    else:
                        if any_project_video:
                            # In a timeline with video, insert BL (Black) video generator so the video record timeline does not shift
                            lines.append(f"{event_idx:03d}  BL       {'V':<5} C        00:00:00:00 {_format_timecode_edl(seg_dur, fps)} {dst_in_tc} {dst_out_tc}")
                            lines.append(f"* FROM CLIP NAME: BLACK")
                            lines.append("")
                            event_idx += 1
                        trk = "AA" if audio_ch >= 2 else "A"
                        lines.append(f"{event_idx:03d}  AX       {trk:<5} C        {src_in_tc} {src_out_tc} {dst_in_tc} {dst_out_tc}")
                        lines.append(f"* FROM CLIP NAME: {clip_name}")
                        lines.append("")
                        event_idx += 1

            dest_pos += op_dur

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True, output_path
    except Exception as e:
        return False, str(e)



