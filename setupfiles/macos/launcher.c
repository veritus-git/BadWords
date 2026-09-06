/*
 * Copyright (c) 2026 Szymon Wolarz
 * Licensed under the MIT License.
 *
 * BadWords macOS Native Mach-O Launcher
 * -------------------------------------------------------------
 * This launcher runs inside BadWords.app/Contents/MacOS/BadWords.
 * Instead of executing an external python binary via execve (which
 * causes macOS WindowServer and Stage Manager to assign the window
 * to Python.app and display the Python rocket icon + "Python" menu),
 * this launcher dynamically loads libpython and invokes Py_BytesMain
 * in-process.
 *
 * This guarantees:
 *  1. Process CFBundleGetMainBundle() is BadWords.app.
 *  2. Application Menu title is "BadWords".
 *  3. Stage Manager and Dock use BadWords.app/Contents/Resources/icon.icns.
 *  4. Spotlight, Cmd+Tab, and Activity Monitor show "BadWords".
 *  5. Graceful fallback to execv if dlopen is unavailable.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>
#include <limits.h>
#include <sys/stat.h>
#include <mach-o/dyld.h>

#define MAX_PATH_LEN 2048

static void trim(char *s) {
    char *p = s;
    int l = strlen(p);
    while (l > 0 && (p[l - 1] == ' ' || p[l - 1] == '\t' || p[l - 1] == '\n' || p[l - 1] == '\r')) {
        p[--l] = '\0';
    }
    while (*p && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) {
        p++;
    }
    if (p != s) {
        memmove(s, p, strlen(p) + 1);
    }
}

static int file_exists(const char *path) {
    struct stat st;
    return (stat(path, &st) == 0 && S_ISREG(st.st_mode));
}

static int dir_exists(const char *path) {
    struct stat st;
    return (stat(path, &st) == 0 && S_ISDIR(st.st_mode));
}

int main(int argc, char *argv[]) {
    char exe_path[MAX_PATH_LEN] = {0};
    uint32_t size = sizeof(exe_path);
    if (_NSGetExecutablePath(exe_path, &size) != 0) {
        strncpy(exe_path, argv[0], sizeof(exe_path) - 1);
    }

    // Resolve realpath of launcher
    char real_exe[MAX_PATH_LEN] = {0};
    if (realpath(exe_path, real_exe) == NULL) {
        strncpy(real_exe, exe_path, sizeof(real_exe) - 1);
    }

    // Find Contents directory
    // real_exe = .../BadWords.app/Contents/MacOS/BadWords
    char contents_dir[MAX_PATH_LEN] = {0};
    strncpy(contents_dir, real_exe, sizeof(contents_dir) - 1);
    char *last_slash = strrchr(contents_dir, '/');
    if (last_slash) {
        *last_slash = '\0'; // strip /BadWords -> .../Contents/MacOS
        last_slash = strrchr(contents_dir, '/');
        if (last_slash) {
            *last_slash = '\0'; // strip /MacOS -> .../Contents
        }
    }

    char install_dir[MAX_PATH_LEN] = {0};
    char python_lib[MAX_PATH_LEN] = {0};
    char python_bin[MAX_PATH_LEN] = {0};
    char main_py[MAX_PATH_LEN] = {0};

    // Read config from Contents/Resources/BadWords.cfg if available
    char cfg_path[MAX_PATH_LEN] = {0};
    snprintf(cfg_path, sizeof(cfg_path), "%s/Resources/BadWords.cfg", contents_dir);

    FILE *f = fopen(cfg_path, "r");
    if (f) {
        char line[1024];
        while (fgets(line, sizeof(line), f)) {
            trim(line);
            if (line[0] == '#' || line[0] == '\0') continue;
            char *eq = strchr(line, '=');
            if (!eq) continue;
            *eq = '\0';
            char *key = line;
            char *val = eq + 1;
            trim(key);
            trim(val);
            if (strcmp(key, "INSTALL_DIR") == 0) {
                strncpy(install_dir, val, sizeof(install_dir) - 1);
            } else if (strcmp(key, "PYTHON_LIB") == 0) {
                strncpy(python_lib, val, sizeof(python_lib) - 1);
            } else if (strcmp(key, "PYTHON_BIN") == 0) {
                strncpy(python_bin, val, sizeof(python_bin) - 1);
            } else if (strcmp(key, "MAIN_PY") == 0) {
                strncpy(main_py, val, sizeof(main_py) - 1);
            }
        }
        fclose(f);
    }

    // Fallbacks if not specified in config
    const char *home = getenv("HOME");
    if (install_dir[0] == '\0') {
        if (home) {
            snprintf(install_dir, sizeof(install_dir), "%s/Library/Application Support/BadWords", home);
        } else {
            strncpy(install_dir, "/Applications/BadWords", sizeof(install_dir) - 1);
        }
    }

    if (python_bin[0] == '\0') {
        snprintf(python_bin, sizeof(python_bin), "%s/venv/bin/python3", install_dir);
        if (!file_exists(python_bin)) {
            snprintf(python_bin, sizeof(python_bin), "%s/venv/bin/python", install_dir);
        }
    }

    if (main_py[0] == '\0') {
        snprintf(main_py, sizeof(main_py), "%s/src/main.py", install_dir);
        if (!file_exists(main_py)) {
            snprintf(main_py, sizeof(main_py), "%s/main.py", install_dir);
        }
    }

    // If python_lib was not configured, attempt auto-discovery
    if (python_lib[0] == '\0' && file_exists(python_bin)) {
        char resolved_bin[MAX_PATH_LEN] = {0};
        if (realpath(python_bin, resolved_bin) != NULL) {
            // Check framework: /Library/Frameworks/Python.framework/Versions/X.Y/bin/python3
            // Lib is: /Library/Frameworks/Python.framework/Versions/X.Y/Python
            char *bin_sub = strstr(resolved_bin, "/bin/python");
            if (bin_sub) {
                char prefix[MAX_PATH_LEN] = {0};
                strncpy(prefix, resolved_bin, bin_sub - resolved_bin);
                char cand[MAX_PATH_LEN];
                snprintf(cand, sizeof(cand), "%s/Python", prefix);
                if (file_exists(cand)) {
                    strncpy(python_lib, cand, sizeof(python_lib) - 1);
                } else {
                    // Try lib/libpython3.*.dylib
                    snprintf(cand, sizeof(cand), "%s/lib/libpython3.12.dylib", prefix);
                    if (file_exists(cand)) strncpy(python_lib, cand, sizeof(python_lib) - 1);
                    else {
                        snprintf(cand, sizeof(cand), "%s/lib/libpython3.11.dylib", prefix);
                        if (file_exists(cand)) strncpy(python_lib, cand, sizeof(python_lib) - 1);
                        else {
                            snprintf(cand, sizeof(cand), "%s/lib/libpython3.10.dylib", prefix);
                            if (file_exists(cand)) strncpy(python_lib, cand, sizeof(python_lib) - 1);
                        }
                    }
                }
            }
        }
    }

    // Secondary search paths for libpython
    if (python_lib[0] == '\0' || !file_exists(python_lib)) {
        const char *cand_libs[] = {
            "/Library/Frameworks/Python.framework/Versions/3.12/Python",
            "/Library/Frameworks/Python.framework/Versions/3.11/Python",
            "/Library/Frameworks/Python.framework/Versions/3.10/Python",
            "/Library/Frameworks/Python.framework/Versions/3.9/Python",
            "/opt/homebrew/opt/python@3.12/Frameworks/Python.framework/Versions/3.12/Python",
            "/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11/Python",
            "/opt/homebrew/opt/python@3.10/Frameworks/Python.framework/Versions/3.10/Python",
            "/usr/local/opt/python@3.12/Frameworks/Python.framework/Versions/3.12/Python",
            "/usr/local/opt/python@3.11/Frameworks/Python.framework/Versions/3.11/Python",
            "/usr/local/opt/python@3.10/Frameworks/Python.framework/Versions/3.10/Python",
            NULL
        };
        for (int i = 0; cand_libs[i] != NULL; i++) {
            if (file_exists(cand_libs[i])) {
                strncpy(python_lib, cand_libs[i], sizeof(python_lib) - 1);
                break;
            }
        }
    }

    // Set environment variables for virtualenv
    char venv_dir[MAX_PATH_LEN];
    snprintf(venv_dir, sizeof(venv_dir), "%s/venv", install_dir);
    if (dir_exists(venv_dir)) {
        setenv("VIRTUAL_ENV", venv_dir, 1);
    }

    // Prepend venv/bin and bin to PATH
    char new_path[4096];
    const char *cur_path = getenv("PATH");
    snprintf(new_path, sizeof(new_path), "%s/venv/bin:%s/bin:%s", install_dir, install_dir, cur_path ? cur_path : "/usr/bin:/bin");
    setenv("PATH", new_path, 1);

    // Set PYTHONPATH
    char py_path[4096];
    const char *cur_pypath = getenv("PYTHONPATH");
    if (cur_pypath && cur_pypath[0] != '\0') {
        snprintf(py_path, sizeof(py_path), "%s/src:%s:%s", install_dir, install_dir, cur_pypath);
    } else {
        snprintf(py_path, sizeof(py_path), "%s/src:%s", install_dir, install_dir);
    }
    setenv("PYTHONPATH", py_path, 1);

    // Working directory
    char work_dir[MAX_PATH_LEN];
    snprintf(work_dir, sizeof(work_dir), "%s/src", install_dir);
    if (dir_exists(work_dir)) {
        chdir(work_dir);
    } else {
        chdir(install_dir);
    }

    // Build argv array
    // [0] = "BadWords"
    // [1] = main_py
    // [2..] = forwarded arguments
    int new_argc = argc + 1;
    char **new_argv = (char **)malloc((new_argc + 1) * sizeof(char *));
    new_argv[0] = "BadWords";
    new_argv[1] = main_py;
    for (int i = 1; i < argc; i++) {
        new_argv[i + 1] = argv[i];
    }
    new_argv[new_argc] = NULL;

    // 1. Attempt in-process execution via libpython
    if (python_lib[0] != '\0' && file_exists(python_lib)) {
        void *py_handle = dlopen(python_lib, RTLD_NOW | RTLD_GLOBAL);
        if (py_handle) {
            int (*Py_BytesMain)(int, char **) = (int (*)(int, char **))dlsym(py_handle, "Py_BytesMain");
            if (Py_BytesMain) {
                return Py_BytesMain(new_argc, new_argv);
            }
        }
    }

    // 2. Safe Fallback: Execute python binary directly if dlopen fails
    if (file_exists(python_bin)) {
        new_argv[0] = python_bin;
        execv(python_bin, new_argv);
    } else {
        execvp("python3", new_argv);
    }

    free(new_argv);
    return 1;
}
