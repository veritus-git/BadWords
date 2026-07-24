"""
DRT Assembler — Native DaVinci Resolve Timeline Assembly Engine
================================================================
Implements the hybrid .drt assembly pipeline for BadWords:

  1. Export source timeline as .drt (ZIP) via Resolve API
  2. Unpack → parse SeqContainer XML
  3. Apply ops cuts: modify ONLY Start/Duration/In on clips
  4. Repack as .drt → import via Resolve API
  5. Post-import: SetName() + reapply_clip_colors()

WHY .drt OVER FCP7 XML:
  • Preserves 100% of DaVinci-specific data (adjustment clips,
    generators, Fusion comps, color grading, all binary metadata)
  • No format-specific hacks (generatoritem conversion, sourcetrack
    stripping, compound clip skipping)
  • Media relinking is automatic (absolute paths in the .drt)

SAFETY GUARANTEE:
  We NEVER touch binary blobs (FieldsBlob, EffectFiltersBA,
  MediaFrameRate, MediaTimemapBA, etc.).  Only Start, Duration, In,
  and DbId are modified — the minimum needed to reposition clips.
"""

import os
import uuid
import zipfile
import copy
import xml.etree.ElementTree as ET

from osdoc import log_info, log_error


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


def find_seq_container_xml(unpacked_timeline_dir):
    """
    Locate the SeqContainer XML file inside the unpacked timeline dir.
    Returns the absolute path to the XML file.
    """
    seq_dir = os.path.join(unpacked_timeline_dir, "SeqContainer")
    if not os.path.isdir(seq_dir):
        raise FileNotFoundError(
            f"SeqContainer directory not found in {unpacked_timeline_dir}"
        )
    for fname in os.listdir(seq_dir):
        if fname.endswith('.xml'):
            return os.path.join(seq_dir, fname)
    raise FileNotFoundError(f"No XML file found in {seq_dir}")


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
    return c


def apply_ops_to_seq_container(seq_xml_path, ops, base_offset, fps, audio_only_mode=False):
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
        tree = ET.parse(seq_xml_path)
        root = tree.getroot()

        # ── 1. Base offset is now provided by the timeline ───────────────────
        log_info(f"drt_apply_ops: base_offset={base_offset}, ops={len(ops)}, "
                 f"fps={fps}, audio_only={audio_only_mode}")

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

        # ── 4. Write modified XML back ────────────────────────────────────────
        # Preserve XML declaration and comment from original
        tree.write(seq_xml_path, encoding='unicode', xml_declaration=True)

        log_info(f"drt_apply_ops: wrote {seq_xml_path} "
                 f"(base={base_offset}, total_dest={total_dest_frames}f, "
                 f"color_entries={len(color_schedule)})")
        return True, color_schedule

    except Exception as e:
        import traceback
        log_error(f"drt_apply_ops error: {e}\n{traceback.format_exc()}")
        return False, {}


# ══════════════════════════════════════════════════════════════════════════════
# HIGH-LEVEL ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def assemble_via_drt(resolve_handler, original_tl_name, ops,
                     new_tl_name, audio_only_mode=False,
                     temp_dir=None):
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
        log_info(f"drt_assemble: exporting '{original_tl_name}' as .drt...")
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

        export_type = getattr(resolve_handler.resolve, 'EXPORT_DRT', None)
        if export_type is None:
            log_error("drt_assemble: resolve.EXPORT_DRT constant not available.")
            return False, {}, None

        export_ok = target_tl.Export(src_drt_path, export_type)
        if not export_ok or not os.path.exists(src_drt_path):
            log_error("drt_assemble: .drt export failed.")
            return False, {}, None

        log_info(f"drt_assemble: exported .drt ({os.path.getsize(src_drt_path)} bytes)")
        time.sleep(0.05)



        # ── Step 2: Unpack .drt ───────────────────────────────────────────────
        timeline_dir = unpack_drt(src_drt_path, unpack_dir)
        seq_xml = find_seq_container_xml(timeline_dir)
        log_info(f"drt_assemble: SeqContainer at {seq_xml}")

        # ── Step 3: Apply ops cuts ────────────────────────────────────────────
        ok, color_schedule = apply_ops_to_seq_container(
            seq_xml, ops, base_offset, fps, audio_only_mode=audio_only_mode
        )
        if not ok:
            log_error("drt_assemble: apply_ops_to_seq_container failed.")
            return False, {}, None

        # ── Step 4: Repack as .drt ────────────────────────────────────────────
        repack_drt(unpack_dir, cut_drt_path)
        time.sleep(0.05)

        # ── Step 5: Import modified .drt ──────────────────────────────────────
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

        # ── Step 6: Rename (importOptions not valid for .drt) ─────────────────
        actual_name = new_tl.GetName()
        log_info(f"drt_assemble: imported as '{actual_name}', renaming to '{new_tl_name}'...")
        try:
            new_tl.SetName(new_tl_name)
            actual_name = new_tl.GetName()
            log_info(f"drt_assemble: renamed to '{actual_name}'")
        except Exception as rename_err:
            log_error(f"drt_assemble: SetName failed: {rename_err}")
            # Continue with original name — not fatal

        # ── Step 7: Move to BadWords bin ──────────────────────────────────────
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
