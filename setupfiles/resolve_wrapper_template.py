#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
DaVinci Resolve Utility script template for BadWords.
Placeholder __BADWORDS_INSTALL_DIR__ is replaced with the BadWords install path.
"""

import builtins
import os
import re
import subprocess
import sys

for _k in ("resolve", "bmd", "fusion", "fu"):
    if _k in globals() and globals()[_k] is not None:
        setattr(builtins, _k, globals()[_k])
    elif _k in locals() and locals()[_k] is not None:
        setattr(builtins, _k, locals()[_k])

INSTALL_DIR = r"""__BADWORDS_INSTALL_DIR__"""
MAIN_SCRIPT = ""

for _main_cand in (
    os.path.join(INSTALL_DIR, "main.py"),
    os.path.join(INSTALL_DIR, "src", "main.py"),
    os.path.join(os.path.dirname(INSTALL_DIR), "main.py"),
    os.path.join(os.path.dirname(INSTALL_DIR), "src", "main.py"),
):
    if os.path.isfile(_main_cand):
        MAIN_SCRIPT = _main_cand
        break

if not MAIN_SCRIPT:
    MAIN_SCRIPT = os.path.join(INSTALL_DIR, "main.py")

# 1. Discover all site-packages candidates (venv direct paths + libs symlink/junction)
_candidates = [
    os.path.join(INSTALL_DIR, "libs"),
    os.path.join(os.path.dirname(INSTALL_DIR), "libs"),
    os.path.join(INSTALL_DIR, "venv", "Lib", "site-packages"),
    os.path.join(os.path.dirname(INSTALL_DIR), "venv", "Lib", "site-packages"),
]

for _base in (INSTALL_DIR, os.path.dirname(INSTALL_DIR)):
    for _lib_sub in ("lib", "lib64"):
        _v_lib = os.path.join(_base, "venv", _lib_sub)
        if os.path.isdir(_v_lib):
            try:
                for _entry in os.listdir(_v_lib):
                    _sp = os.path.join(_v_lib, _entry, "site-packages")
                    if os.path.isdir(_sp) and _sp not in _candidates:
                        _candidates.append(_sp)
            except Exception:
                pass


def _clean_env():
    """Return an isolated subprocess environment stripped of host/Conda Python variables."""
    env = os.environ.copy()
    env["BADWORDS_EMBEDDED"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    for _var in (
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONSTARTUP",
        "PYTHONEXECUTABLE",
        "__PYVENV_LAUNCHER__",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "CONDA_PYTHON_EXE",
        "CONDA_SHLVL",
        "CONDA_EXE",
    ):
        env.pop(_var, None)

    _bad_tokens = ("resolve", "conda", "miniconda", "anaconda")
    if sys.platform.startswith("linux") and "LD_LIBRARY_PATH" in env:
        clean_paths = [
            p for p in env["LD_LIBRARY_PATH"].split(os.pathsep)
            if p and not any(tok in p.lower() for tok in _bad_tokens)
        ]
        if clean_paths:
            env["LD_LIBRARY_PATH"] = os.pathsep.join(clean_paths)
        else:
            env.pop("LD_LIBRARY_PATH", None)
    elif sys.platform == "darwin":
        for _dyld_var in ("DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH"):
            if _dyld_var in env:
                clean_paths = [
                    p for p in env[_dyld_var].split(os.pathsep)
                    if p and not any(tok in p.lower() for tok in _bad_tokens)
                ]
                if clean_paths:
                    env[_dyld_var] = os.pathsep.join(clean_paths)
                else:
                    env.pop(_dyld_var, None)
    return env


def _launch_external():
    """Launch BadWords in its own isolated external process (never using host/system Python)."""
    clean_env = _clean_env()
    cwd = os.path.dirname(MAIN_SCRIPT) if (MAIN_SCRIPT and os.path.isfile(MAIN_SCRIPT)) else INSTALL_DIR
    if not os.path.isdir(cwd):
        cwd = os.path.dirname(INSTALL_DIR)

    sp_kwargs = {}
    if sys.platform.startswith("win"):
        sp_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    if sys.platform == "darwin":
        for _app_cand in (
            os.path.expanduser("~/Applications/BadWords.app"),
            "/Applications/BadWords.app",
        ):
            if os.path.isdir(_app_cand):
                try:
                    subprocess.Popen(["open", "-n", _app_cand, "--args", "--embedded"], env=clean_env)
                    print("[BadWords] Launched macOS app bundle:", _app_cand)
                    return True
                except Exception:
                    pass

    for cand in (
        os.path.join(INSTALL_DIR, "BadWords"),
        os.path.join(os.path.dirname(INSTALL_DIR), "BadWords"),
        os.path.join(INSTALL_DIR, "BadWords.exe"),
        os.path.join(os.path.dirname(INSTALL_DIR), "BadWords.exe"),
    ):
        if os.path.isfile(cand) and (sys.platform.startswith("win") or os.access(cand, os.X_OK)):
            try:
                subprocess.Popen([cand, "--embedded"], env=clean_env, cwd=cwd, **sp_kwargs)
                print("[BadWords] Launched standalone binary:", cand)
                return True
            except Exception:
                pass

    py_cands = (
        os.path.join(INSTALL_DIR, "venv", "Scripts", "pythonw.exe"),
        os.path.join(INSTALL_DIR, "venv", "Scripts", "python.exe"),
        os.path.join(os.path.dirname(INSTALL_DIR), "venv", "Scripts", "pythonw.exe"),
        os.path.join(os.path.dirname(INSTALL_DIR), "venv", "Scripts", "python.exe"),
        os.path.join(INSTALL_DIR, "venv", "bin", "python3"),
        os.path.join(INSTALL_DIR, "venv", "bin", "python"),
        os.path.join(os.path.dirname(INSTALL_DIR), "venv", "bin", "python3"),
        os.path.join(os.path.dirname(INSTALL_DIR), "venv", "bin", "python"),
    )
    py_bin = next((p for p in py_cands if os.path.isfile(p)), None)
    if py_bin and os.path.isfile(MAIN_SCRIPT):
        subprocess.Popen([py_bin, MAIN_SCRIPT, "--embedded"], env=clean_env, cwd=cwd, **sp_kwargs)
        print("[BadWords] Launched external venv process:", MAIN_SCRIPT)
        return True

    print(
        "[BadWords] BadWords environment not found. Please run the BadWords installer: "
        "https://github.com/veritus-git/BadWords/releases/latest"
    )
    return False


# 2. Detect venv Python version to avoid CPython ABI crashes in host DaVinci Resolve
_venv_ver = None
for _v_base in (INSTALL_DIR, os.path.dirname(INSTALL_DIR)):
    _cfg = os.path.join(_v_base, "venv", "pyvenv.cfg")
    if os.path.isfile(_cfg):
        try:
            with open(_cfg, "r", encoding="utf-8") as _f:
                for _l in _f:
                    if "=" not in _l:
                        continue
                    _key, _val = _l.split("=", 1)
                    _key = _key.strip().lower()
                    if _key in ("version", "version_info"):
                        _p = [int(x) for x in _val.strip().split(".")[:2] if x.isdigit()]
                        if len(_p) == 2:
                            _venv_ver = tuple(_p)
                        break
        except Exception:
            pass
        if _venv_ver:
            break

_host_ver = sys.version_info[:2]
_is_abi_incompatible = (_venv_ver is not None and _venv_ver != _host_ver)

if _is_abi_incompatible:
    print(
        "[BadWords] Host Python ("
        + str(_host_ver[0])
        + "."
        + str(_host_ver[1])
        + ") differs from venv Python ("
        + str(_venv_ver[0])
        + "."
        + str(_venv_ver[1])
        + ")."
    )
    print("[BadWords] Launching BadWords standalone process with Lua Bridge to prevent CPython ABI conflicts...")
    _launch_external()
else:
    # Strip sys.path entries belonging to other Python minor versions (e.g. Conda 3.13)
    _posix_re = re.compile(r"python(\d+)\.(\d+)", re.IGNORECASE)
    _win_re = re.compile(r"[Pp]ython(\d)(\d{1,2})(?:[\\/]|$)")
    _filtered_path = []
    for _entry in sys.path:
        _m = _posix_re.search(_entry) or _win_re.search(_entry)
        if _m and (int(_m.group(1)), int(_m.group(2))) != _host_ver:
            continue
        _filtered_path.append(_entry)
    sys.path[:] = _filtered_path

    for _sp_dir in _candidates:
        if os.path.isdir(_sp_dir):
            if _sp_dir in sys.path:
                sys.path.remove(_sp_dir)
            sys.path.insert(0, _sp_dir)

    for _p in (
        INSTALL_DIR,
        os.path.join(INSTALL_DIR, "src"),
        os.path.dirname(INSTALL_DIR),
        os.path.join(os.path.dirname(INSTALL_DIR), "src"),
    ):
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.append(_p)

    # Windows: process identity & register DLL search paths (no blind ctypes.CDLL loop)
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("veritus.badwords.editor.v4")
        except Exception:
            pass
        if hasattr(os, "add_dll_directory"):
            for _sp_dir in _candidates:
                if os.path.isdir(_sp_dir):
                    for _pkg in ("PySide6", "shiboken6"):
                        _p = os.path.join(_sp_dir, _pkg)
                        if os.path.isdir(_p):
                            try:
                                os.add_dll_directory(_p)
                            except Exception:
                                pass
                    _nv_dir = os.path.join(_sp_dir, "nvidia")
                    if os.path.isdir(_nv_dir):
                        for _nv_pkg in ("cublas", "cudnn", "cuda_nvrtc", "cuda_runtime"):
                            _bin_p = os.path.join(_nv_dir, _nv_pkg, "bin")
                            if os.path.isdir(_bin_p):
                                try:
                                    os.add_dll_directory(_bin_p)
                                    os.environ["PATH"] = _bin_p + os.pathsep + os.environ.get("PATH", "")
                                except Exception:
                                    pass

    # Linux: Preload Qt6 shared libraries into RTLD_GLOBAL if needed
    if sys.platform.startswith("linux"):
        import ctypes
        for _sp_dir in _candidates:
            _qt_lib_dir = os.path.join(_sp_dir, "PySide6", "Qt", "lib")
            if os.path.isdir(_qt_lib_dir):
                _qt_preload = (
                    "libQt6Core.so.6",
                    "libQt6Network.so.6",
                    "libQt6DBus.so.6",
                    "libQt6Gui.so.6",
                    "libQt6Widgets.so.6",
                    "libQt6OpenGL.so.6",
                    "libQt6XcbQpa.so.6",
                )
                for _lib in _qt_preload:
                    _p = os.path.join(_qt_lib_dir, _lib)
                    if os.path.exists(_p):
                        try:
                            ctypes.CDLL(_p, mode=ctypes.RTLD_GLOBAL)
                        except OSError:
                            pass
                break

    if os.path.exists(MAIN_SCRIPT):
        os.environ["BADWORDS_EMBEDDED"] = "1"
        if "--embedded" not in sys.argv:
            sys.argv.append("--embedded")
        try:
            with open(MAIN_SCRIPT, encoding="utf-8") as f:
                code = f.read()
            gv = globals().copy()
            gv["__file__"] = MAIN_SCRIPT
            exec(code, gv)
        except Exception as e:
            print("[BadWords] In-process execution failed:", e)
            print("[BadWords] Falling back to external process launch...")
            _launch_external()
    else:
        print("CRITICAL: script not found at", MAIN_SCRIPT)
