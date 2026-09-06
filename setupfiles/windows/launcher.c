/*
 * Copyright (c) 2026 Szymon Wolarz
 * Licensed under the MIT License.
 *
 * BadWords Windows Native GUI Subsystem Launcher
 * -------------------------------------------------------------
 * Runs as the main standalone binary (BadWords.exe) on Windows.
 *
 * It dynamically initializes Python inside this process so that:
 *  1. In Windows Task Manager (Processes & Details) the process is "BadWords.exe"
 *  2. The window and taskbar entry use the embedded BadWords icon
 *  3. Subsystem is WINDOWS GUI - NO console CMD window will ever pop up
 *  4. Virtualenv (venv) packages and paths are accurately loaded
 *  5. Immediate stderr/stdout redirection to badwords_debug.log so errors are never lost
 *  6. Bulletproof fallback to CreateProcessW if in-process loading cannot be performed
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#define MAX_PATH_LEN 4096
#define MAX_ENV_LEN  32768

static int file_exists_w(const wchar_t *path) {
    if (!path || path[0] == L'\0') return 0;
    DWORD attr = GetFileAttributesW(path);
    return (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY));
}

static int dir_exists_w(const wchar_t *path) {
    if (!path || path[0] == L'\0') return 0;
    DWORD attr = GetFileAttributesW(path);
    return (attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY));
}

static void trim_w(wchar_t *s) {
    wchar_t *p = s;
    int l = (int)wcslen(p);
    while (l > 0 && (p[l - 1] == L' ' || p[l - 1] == L'\t' || p[l - 1] == L'\n' || p[l - 1] == L'\r')) {
        p[--l] = L'\0';
    }
    while (*p && (*p == L' ' || *p == L'\t' || *p == L'\n' || *p == L'\r')) {
        p++;
    }
    if (p != s) {
        wmemmove(s, p, wcslen(p) + 1);
    }
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR pCmdLine, int nCmdShow) {
    (void)hInstance; (void)hPrevInstance; (void)pCmdLine; (void)nCmdShow;

    // 1. Resolve executable path (BadWords.exe)
    wchar_t real_exe[MAX_PATH_LEN] = {0};
    GetModuleFileNameW(NULL, real_exe, MAX_PATH_LEN - 1);

    // Determine install directory (where BadWords.exe resides)
    wchar_t install_dir[MAX_PATH_LEN] = {0};
    wcsncpy(install_dir, real_exe, MAX_PATH_LEN - 1);
    wchar_t *last_slash = wcsrchr(install_dir, L'\\');
    if (last_slash) {
        *last_slash = L'\0';
    }

    // If install_dir ends with \bin, strip \bin
    size_t id_len = wcslen(install_dir);
    if (id_len > 4 && _wcsicmp(install_dir + id_len - 4, L"\\bin") == 0) {
        install_dir[id_len - 4] = L'\0';
    }

    // 2. Redirect stdout & stderr to badwords_debug.log immediately for diagnostic safety
    wchar_t log_path[MAX_PATH_LEN];
    _snwprintf(log_path, MAX_PATH_LEN, L"%s\\badwords_debug.log", install_dir);
    FILE *log_fp = _wfsopen(log_path, L"a", _SH_DENYNO);
    if (log_fp) {
        int log_fd = _fileno(log_fp);
        (void)_dup2(log_fd, 1);
        (void)_dup2(log_fd, 2);
        setvbuf(stdout, NULL, _IONBF, 0);
        setvbuf(stderr, NULL, _IONBF, 0);
    }
    fwprintf(stderr, L"\n=== BadWords Windows Native Launcher (PID %lu) ===\n", GetCurrentProcessId());
    fwprintf(stderr, L"[LAUNCHER] Executable:   %s\n", real_exe);
    fwprintf(stderr, L"[LAUNCHER] Install dir:  %s\n", install_dir);

    // 3. Resolve Python binary (prefer pythonw.exe for windowed, python.exe fallback)
    wchar_t python_bin[MAX_PATH_LEN] = {0};
    wchar_t pythonw_bin[MAX_PATH_LEN] = {0};
    _snwprintf(pythonw_bin, MAX_PATH_LEN, L"%s\\venv\\Scripts\\pythonw.exe", install_dir);
    _snwprintf(python_bin, MAX_PATH_LEN, L"%s\\venv\\Scripts\\python.exe", install_dir);

    wchar_t active_py[MAX_PATH_LEN] = {0};
    if (file_exists_w(pythonw_bin)) {
        wcsncpy(active_py, pythonw_bin, MAX_PATH_LEN - 1);
    } else if (file_exists_w(python_bin)) {
        wcsncpy(active_py, python_bin, MAX_PATH_LEN - 1);
    }
    fwprintf(stderr, L"[LAUNCHER] Python target: %s\n", active_py);

    // 4. Resolve Main Python script
    wchar_t main_py[MAX_PATH_LEN] = {0};
    wchar_t cand_main[MAX_PATH_LEN];
    _snwprintf(cand_main, MAX_PATH_LEN, L"%s\\src\\main.py", install_dir);
    if (file_exists_w(cand_main)) {
        wcsncpy(main_py, cand_main, MAX_PATH_LEN - 1);
    } else {
        _snwprintf(cand_main, MAX_PATH_LEN, L"%s\\main.py", install_dir);
        if (file_exists_w(cand_main)) {
            wcsncpy(main_py, cand_main, MAX_PATH_LEN - 1);
        }
    }
    fwprintf(stderr, L"[LAUNCHER] Main script:   %s\n", main_py);

    // 5. Inspect pyvenv.cfg to detect Python home directory
    wchar_t venv_home[MAX_PATH_LEN] = {0};
    wchar_t pyvenv_cfg[MAX_PATH_LEN];
    _snwprintf(pyvenv_cfg, MAX_PATH_LEN, L"%s\\venv\\pyvenv.cfg", install_dir);
    FILE *fcfg = _wfsopen(pyvenv_cfg, L"r", _SH_DENYNO);
    if (fcfg) {
        wchar_t line[512];
        while (fgetws(line, 512, fcfg)) {
            trim_w(line);
            if (line[0] == L'#' || line[0] == L'\0') continue;
            wchar_t *eq = wcschr(line, L'=');
            if (!eq) continue;
            *eq = L'\0';
            wchar_t *k = line; wchar_t *v = eq + 1;
            trim_w(k); trim_w(v);
            if (_wcsicmp(k, L"home") == 0) {
                wcsncpy(venv_home, v, MAX_PATH_LEN - 1);
            }
        }
        fclose(fcfg);
        fwprintf(stderr, L"[LAUNCHER] pyvenv.cfg home: %s\n", venv_home);
    }

    // 6. Discover python3xx.dll
    wchar_t python_dll[MAX_PATH_LEN] = {0};
    const wchar_t *search_dirs[4] = {0};
    int sc = 0;
    wchar_t venv_scripts[MAX_PATH_LEN];
    _snwprintf(venv_scripts, MAX_PATH_LEN, L"%s\\venv\\Scripts", install_dir);
    search_dirs[sc++] = venv_scripts;
    wchar_t venv_root[MAX_PATH_LEN];
    _snwprintf(venv_root, MAX_PATH_LEN, L"%s\\venv", install_dir);
    search_dirs[sc++] = venv_root;
    if (venv_home[0] != L'\0') {
        search_dirs[sc++] = venv_home;
    }

    for (int d = 0; d < sc && python_dll[0] == L'\0'; d++) {
        wchar_t mask[MAX_PATH_LEN];
        _snwprintf(mask, MAX_PATH_LEN, L"%s\\python3*.dll", search_dirs[d]);
        WIN32_FIND_DATAW fd;
        HANDLE hFind = FindFirstFileW(mask, &fd);
        if (hFind != INVALID_HANDLE_VALUE) {
            do {
                if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                    // Skip python3.dll (forwarder) if specific version exists
                    if (_wcsicmp(fd.cFileName, L"python3.dll") != 0) {
                        _snwprintf(python_dll, MAX_PATH_LEN, L"%s\\%s", search_dirs[d], fd.cFileName);
                        break;
                    }
                }
            } while (FindNextFileW(hFind, &fd));
            FindClose(hFind);
        }
    }
    fwprintf(stderr, L"[LAUNCHER] Python DLL:    %s\n", python_dll[0] ? python_dll : L"(none)");

    // 7. Detect site-packages directory
    wchar_t site_pkgs[MAX_PATH_LEN] = {0};
    wchar_t cand_sp[MAX_PATH_LEN];
    _snwprintf(cand_sp, MAX_PATH_LEN, L"%s\\venv\\Lib\\site-packages", install_dir);
    if (dir_exists_w(cand_sp)) {
        wcsncpy(site_pkgs, cand_sp, MAX_PATH_LEN - 1);
    }
    fwprintf(stderr, L"[LAUNCHER] Site packages: %s\n", site_pkgs[0] ? site_pkgs : L"(none)");

    // 8. Configure Virtual Environment Variables
    wchar_t venv_dir[MAX_PATH_LEN];
    _snwprintf(venv_dir, MAX_PATH_LEN, L"%s\\venv", install_dir);
    SetEnvironmentVariableW(L"VIRTUAL_ENV", venv_dir);

    wchar_t cur_path[MAX_ENV_LEN] = {0};
    GetEnvironmentVariableW(L"PATH", cur_path, MAX_ENV_LEN - 1);
    wchar_t new_path[MAX_ENV_LEN];
    _snwprintf(new_path, MAX_ENV_LEN, L"%s\\venv\\Scripts;%s\\bin;%s", install_dir, install_dir, cur_path);
    SetEnvironmentVariableW(L"PATH", new_path);

    wchar_t cur_pypath[MAX_ENV_LEN] = {0};
    GetEnvironmentVariableW(L"PYTHONPATH", cur_pypath, MAX_ENV_LEN - 1);
    wchar_t py_path[MAX_ENV_LEN];
    if (site_pkgs[0] != L'\0') {
        if (cur_pypath[0] != L'\0') {
            _snwprintf(py_path, MAX_ENV_LEN, L"%s\\src;%s;%s;%s", install_dir, install_dir, site_pkgs, cur_pypath);
        } else {
            _snwprintf(py_path, MAX_ENV_LEN, L"%s\\src;%s;%s", install_dir, install_dir, site_pkgs);
        }
    } else {
        if (cur_pypath[0] != L'\0') {
            _snwprintf(py_path, MAX_ENV_LEN, L"%s\\src;%s;%s", install_dir, install_dir, cur_pypath);
        } else {
            _snwprintf(py_path, MAX_ENV_LEN, L"%s\\src;%s", install_dir, install_dir);
        }
    }
    SetEnvironmentVariableW(L"PYTHONPATH", py_path);

    // 9. Set Working Directory
    wchar_t work_dir[MAX_PATH_LEN];
    _snwprintf(work_dir, MAX_PATH_LEN, L"%s\\src", install_dir);
    if (dir_exists_w(work_dir)) {
        SetCurrentDirectoryW(work_dir);
    } else {
        SetCurrentDirectoryW(install_dir);
    }

    // 10. Strategy A: In-Process Execution via python3xx.dll
    if (python_dll[0] != L'\0' && file_exists_w(python_dll)) {
        fwprintf(stderr, L"[LAUNCHER] Attempting in-process execution via LoadLibraryW(%s)...\n", python_dll);
        HMODULE hPy = LoadLibraryW(python_dll);
        if (hPy) {
            int (*Py_BytesMain)(int, char **) = (int (*)(int, char **))GetProcAddress(hPy, "Py_BytesMain");
            if (!Py_BytesMain) {
                Py_BytesMain = (int (*)(int, char **))GetProcAddress(hPy, "Py_Main");
            }
            if (Py_BytesMain) {
                fwprintf(stderr, L"[LAUNCHER] Invoking in-process Py_BytesMain (BadWords.exe)...\n");

                // Convert arguments to UTF-8
                int argc = 0;
                LPWSTR *argvW = CommandLineToArgvW(GetCommandLineW(), &argc);
                int new_argc = 2 + (argc > 1 ? (argc - 1) : 0);
                char **new_argv = (char **)malloc((new_argc + 1) * sizeof(char *));

                // argv[0] = active_py (converted to UTF-8)
                char py_u8[MAX_PATH_LEN];
                WideCharToMultiByte(CP_UTF8, 0, active_py, -1, py_u8, sizeof(py_u8), NULL, NULL);
                new_argv[0] = _strdup(py_u8);

                // argv[1] = main_py (converted to UTF-8)
                char main_u8[MAX_PATH_LEN];
                WideCharToMultiByte(CP_UTF8, 0, main_py, -1, main_u8, sizeof(main_u8), NULL, NULL);
                new_argv[1] = _strdup(main_u8);

                int idx = 2;
                for (int i = 1; i < argc; i++) {
                    int needed = WideCharToMultiByte(CP_UTF8, 0, argvW[i], -1, NULL, 0, NULL, NULL);
                    char *arg_buf = (char *)malloc(needed + 1);
                    WideCharToMultiByte(CP_UTF8, 0, argvW[i], -1, arg_buf, needed + 1, NULL, NULL);
                    new_argv[idx++] = arg_buf;
                }
                new_argv[new_argc] = NULL;
                if (argvW) LocalFree(argvW);

                int ret = Py_BytesMain(new_argc, new_argv);
                fwprintf(stderr, L"[LAUNCHER] In-process execution finished with code %d\n", ret);
                return ret;
            } else {
                fwprintf(stderr, L"[LAUNCHER] GetProcAddress failed to find Py_BytesMain / Py_Main\n");
            }
        } else {
            fwprintf(stderr, L"[LAUNCHER] LoadLibraryW failed (error %lu)\n", GetLastError());
        }
    }

    // 11. Strategy B: Safe Fallback to CreateProcessW (CREATE_NO_WINDOW)
    fwprintf(stderr, L"[LAUNCHER] Falling back to CreateProcessW(%s)...\n", active_py);
    wchar_t cmdline[MAX_ENV_LEN];
    _snwprintf(cmdline, MAX_ENV_LEN, L"\"%s\" \"%s\"", active_py, main_py);

    STARTUPINFOW si;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    PROCESS_INFORMATION pi;
    ZeroMemory(&pi, sizeof(pi));

    BOOL ok = CreateProcessW(
        NULL,
        cmdline,
        NULL,
        NULL,
        FALSE,
        CREATE_NO_WINDOW,
        NULL,
        work_dir,
        &si,
        &pi
    );

    if (ok) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        DWORD exit_code = 0;
        GetExitCodeProcess(pi.hProcess, &exit_code);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        fwprintf(stderr, L"[LAUNCHER] Child process exited with code %lu\n", exit_code);
        return (int)exit_code;
    } else {
        fwprintf(stderr, L"[LAUNCHER] CreateProcessW failed (error %lu)\n", GetLastError());
    }

    return 1;
}
