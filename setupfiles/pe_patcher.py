#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: pe_patcher.py
ROLE: Windows PE Resource Patcher
DESCRIPTION:
Injects icon resources (RT_ICON & RT_GROUP_ICON) into a Windows PE executable (.exe)
using native Win32 API (kernel32.dll) to ensure Windows Task Manager and Explorer
display the custom BadWords application logo.
"""

import os
import sys
import struct


def patch_exe_icon(exe_path: str, ico_path: str) -> bool:
    """
    Patches the main application icon (ID 1) of a PE binary (.exe) with the given .ico file.
    Works natively on Windows without third-party dependencies via Win32 BeginUpdateResourceW.
    """
    if os.name != 'nt':
        return False

    if not os.path.isfile(exe_path) or not os.path.isfile(ico_path):
        return False

    try:
        with open(ico_path, 'rb') as f:
            ico_data = f.read()

        if len(ico_data) < 6:
            return False

        reserved, ico_type, count = struct.unpack('<HHH', ico_data[:6])
        if ico_type != 1 or count < 1:
            return False

        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32

        # Begin resource update (do not delete existing resources, only replace/add)
        hUpdate = kernel32.BeginUpdateResourceW(str(exe_path), False)
        if not hUpdate:
            return False

        try:
            # Build GRPICONDIR structure (Header + GRPICONDIRENTRY array)
            # GRPICONDIR: idReserved (2), idType (2), idCount (2)
            grp_data = bytearray(struct.pack('<HHH', reserved, ico_type, count))

            RT_ICON = ctypes.c_void_p(3)
            RT_GROUP_ICON = ctypes.c_void_p(14)

            for i in range(count):
                entry_offset = 6 + i * 16
                entry = ico_data[entry_offset : entry_offset + 16]
                w, h, colors, res, planes, bpp, size, offset = struct.unpack('<BBBBHHII', entry)
                icon_id = i + 1

                # GRPICONDIRENTRY: w, h, colors, res, planes, bpp, size, nID
                grp_data.extend(struct.pack('<BBBBHHIH', w, h, colors, res, planes, bpp, size, icon_id))

                # Write individual RT_ICON resource
                img_data = ico_data[offset : offset + size]
                kernel32.UpdateResourceW(
                    hUpdate,
                    RT_ICON,
                    ctypes.c_void_p(icon_id),
                    0,  # Neutral language
                    img_data,
                    len(img_data)
                )

            # Write RT_GROUP_ICON resource (ID 1 = standard application icon)
            kernel32.UpdateResourceW(
                hUpdate,
                RT_GROUP_ICON,
                ctypes.c_void_p(1),
                0,  # Neutral language
                bytes(grp_data),
                len(grp_data)
            )

            # Commit changes
            return bool(kernel32.EndUpdateResourceW(hUpdate, False))

        except Exception:
            kernel32.EndUpdateResourceW(hUpdate, True)
            return False

    except Exception:
        return False


def ensure_badwords_exe(install_dir: str) -> str:
    """
    Creates and patches venv/Scripts/BadWords.exe from pythonw.exe on Windows.
    Returns the path to BadWords.exe if successfully created/existing, or pythonw.exe fallback.
    """
    if os.name != 'nt':
        return ""

    import shutil

    venv_scripts = os.path.join(install_dir, "venv", "Scripts")
    pyw = os.path.join(venv_scripts, "pythonw.exe")
    bw_exe = os.path.join(venv_scripts, "BadWords.exe")

    if not os.path.isfile(pyw):
        return ""

    try:
        if not os.path.isfile(bw_exe) or os.path.getmtime(pyw) > os.path.getmtime(bw_exe):
            shutil.copy2(pyw, bw_exe)

        ico_path = os.path.join(install_dir, "assets", "icons", "icon_default.ico")
        if not os.path.isfile(ico_path):
            ico_path = os.path.join(install_dir, "icons", "icon_default.ico")

        if os.path.isfile(ico_path):
            patch_exe_icon(bw_exe, ico_path)

        return bw_exe if os.path.isfile(bw_exe) else pyw
    except Exception:
        return pyw


if __name__ == '__main__':
    if len(sys.argv) > 2:
        res = patch_exe_icon(sys.argv[1], sys.argv[2])
        print("Patched successfully" if res else "Patch failed")
    elif len(sys.argv) > 1:
        res_exe = ensure_badwords_exe(sys.argv[1])
        print(f"Target executable: {res_exe}")
