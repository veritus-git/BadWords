/*
 * Copyright (c) 2026 Szymon Wolarz
 * Licensed under the MIT License.
 *
 * BadWords macOS Native Mach-O Launcher
 * -------------------------------------------------------------
 * Runs inside BadWords.app/Contents/MacOS/BadWords.
 *
 * It dynamically initializes Python inside this process so that:
 *  1. CFBundleGetMainBundle() remains BadWords.app (PID belongs to BadWords.app)
 *  2. macOS Menu bar title is "BadWords" (not "Python")
 *  3. Stage Manager & Dock display BadWords icon (not the Python rocket)
 *  4. Virtualenv (venv) packages (PySide6, etc.) and paths are accurately loaded
 *  5. Immediate stderr/stdout redirection to badwords_debug.log so errors are never lost
 *  6. Bulletproof fallback to execv if in-process loading cannot be performed
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>
#include <limits.h>
#include <sys/stat.h>
#include <dirent.h>
#include <errno.h>

#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

#define MAX_PATH_LEN 4096
#define MAX_ENV_LEN  16384

static void trim(char *s) {
    char *p = s;
    int l = (int)strlen(p);
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
    if (!path || path[0] == '\0') return 0;
    struct stat st;
    return (stat(path, &st) == 0 && S_ISREG(st.st_mode));
}

static int dir_exists(const char *path) {
    if (!path || path[0] == '\0') return 0;
    struct stat st;
    return (stat(path, &st) == 0 && S_ISDIR(st.st_mode));
}

int main(int argc, char *argv[]) {
    char exe_path[MAX_PATH_LEN] = {0};
#ifdef __APPLE__
    uint32_t size = sizeof(exe_path);
    if (_NSGetExecutablePath(exe_path, &size) != 0) {
        strncpy(exe_path, argv[0], sizeof(exe_path) - 1);
    }
#else
    strncpy(exe_path, argv[0], sizeof(exe_path) - 1);
#endif

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

    // 1. Read config from Contents/Resources/BadWords.cfg if available
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

    // 2. Redirect stdout & stderr to badwords_debug.log immediately for diagnostic safety
    char log_path[MAX_PATH_LEN];
    snprintf(log_path, sizeof(log_path), "%s/badwords_debug.log", install_dir);
    FILE *log_fp = fopen(log_path, "a");
    if (log_fp) {
        int log_fd = fileno(log_fp);
        dup2(log_fd, STDOUT_FILENO);
        dup2(log_fd, STDERR_FILENO);
        setvbuf(stdout, NULL, _IONBF, 0);
        setvbuf(stderr, NULL, _IONBF, 0);
    }
    fprintf(stderr, "\n=== BadWords macOS Native Launcher (PID %d) ===\n", getpid());
    fprintf(stderr, "[LAUNCHER] Contents dir: %s\n", contents_dir);
    fprintf(stderr, "[LAUNCHER] Install dir:  %s\n", install_dir);

    // 3. Resolve Python binary (check both python3 and python inside venv)
    if (python_bin[0] == '\0' || !file_exists(python_bin)) {
        char cand[MAX_PATH_LEN];
        snprintf(cand, sizeof(cand), "%s/venv/bin/python3", install_dir);
        if (file_exists(cand)) {
            strncpy(python_bin, cand, sizeof(python_bin) - 1);
        } else {
            snprintf(cand, sizeof(cand), "%s/venv/bin/python", install_dir);
            if (file_exists(cand)) {
                strncpy(python_bin, cand, sizeof(python_bin) - 1);
            }
        }
    }
    fprintf(stderr, "[LAUNCHER] Python binary: %s\n", python_bin);

    // 4. Resolve Main Python script
    if (main_py[0] == '\0' || !file_exists(main_py)) {
        char cand[MAX_PATH_LEN];
        snprintf(cand, sizeof(cand), "%s/src/main.py", install_dir);
        if (file_exists(cand)) {
            strncpy(main_py, cand, sizeof(main_py) - 1);
        } else {
            snprintf(cand, sizeof(cand), "%s/main.py", install_dir);
            if (file_exists(cand)) {
                strncpy(main_py, cand, sizeof(main_py) - 1);
            }
        }
    }
    fprintf(stderr, "[LAUNCHER] Main script:   %s\n", main_py);

    // 5. Inspect pyvenv.cfg to detect Python home and library path
    char venv_home[MAX_PATH_LEN] = {0};
    char pyvenv_cfg[MAX_PATH_LEN];
    snprintf(pyvenv_cfg, sizeof(pyvenv_cfg), "%s/venv/pyvenv.cfg", install_dir);
    FILE *fcfg = fopen(pyvenv_cfg, "r");
    if (fcfg) {
        char line[512];
        while (fgets(line, sizeof(line), fcfg)) {
            trim(line);
            if (line[0] == '#' || line[0] == '\0') continue;
            char *eq = strchr(line, '=');
            if (!eq) continue;
            *eq = '\0';
            char *k = line; char *v = eq + 1;
            trim(k); trim(v);
            if (strcmp(k, "home") == 0) {
                strncpy(venv_home, v, sizeof(venv_home) - 1);
            }
        }
        fclose(fcfg);
        fprintf(stderr, "[LAUNCHER] Base Python home from pyvenv.cfg: %s\n", venv_home);
    }

    // 6. Discover libpython if not explicitly provided
    if (python_lib[0] == '\0' || !file_exists(python_lib)) {
        // Option A: Check framework from venv_home (.../Versions/X.Y/bin -> .../Versions/X.Y/Python)
        if (venv_home[0] != '\0') {
            char base_prefix[MAX_PATH_LEN] = {0};
            strncpy(base_prefix, venv_home, sizeof(base_prefix) - 1);
            char *bin_sub = strstr(base_prefix, "/bin");
            if (bin_sub) {
                *bin_sub = '\0';
            }
            char cand[MAX_PATH_LEN];
            snprintf(cand, sizeof(cand), "%s/Python", base_prefix);
            if (file_exists(cand)) {
                strncpy(python_lib, cand, sizeof(python_lib) - 1);
            } else {
                snprintf(cand, sizeof(cand), "%s/lib/libpython3.12.dylib", base_prefix);
                if (file_exists(cand)) strncpy(python_lib, cand, sizeof(python_lib) - 1);
                else {
                    snprintf(cand, sizeof(cand), "%s/lib/libpython3.11.dylib", base_prefix);
                    if (file_exists(cand)) strncpy(python_lib, cand, sizeof(python_lib) - 1);
                    else {
                        snprintf(cand, sizeof(cand), "%s/lib/libpython3.10.dylib", base_prefix);
                        if (file_exists(cand)) strncpy(python_lib, cand, sizeof(python_lib) - 1);
                    }
                }
            }
        }

        // Option B: Check realpath of python_bin
        if ((python_lib[0] == '\0' || !file_exists(python_lib)) && file_exists(python_bin)) {
            char resolved_bin[MAX_PATH_LEN] = {0};
            if (realpath(python_bin, resolved_bin) != NULL) {
                char *bin_sub = strstr(resolved_bin, "/bin/python");
                if (bin_sub) {
                    char prefix[MAX_PATH_LEN] = {0};
                    strncpy(prefix, resolved_bin, bin_sub - resolved_bin);
                    char cand[MAX_PATH_LEN];
                    snprintf(cand, sizeof(cand), "%s/Python", prefix);
                    if (file_exists(cand)) {
                        strncpy(python_lib, cand, sizeof(python_lib) - 1);
                    }
                }
            }
        }

        // Option C: Standard system framework & Homebrew paths
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
    }
    fprintf(stderr, "[LAUNCHER] Python library: %s\n", python_lib[0] ? python_lib : "(none)");

    // 7. Detect site-packages directory inside venv/lib/
    char site_pkgs[MAX_PATH_LEN] = {0};
    char venv_lib[MAX_PATH_LEN];
    snprintf(venv_lib, sizeof(venv_lib), "%s/venv/lib", install_dir);
    DIR *d = opendir(venv_lib);
    if (d) {
        struct dirent *ent;
        while ((ent = readdir(d)) != NULL) {
            if (strncmp(ent->d_name, "python", 6) == 0) {
                char cand_sp[MAX_PATH_LEN];
                snprintf(cand_sp, sizeof(cand_sp), "%s/%s/site-packages", venv_lib, ent->d_name);
                if (dir_exists(cand_sp)) {
                    strncpy(site_pkgs, cand_sp, sizeof(site_pkgs) - 1);
                    break;
                }
            }
        }
        closedir(d);
    }
    fprintf(stderr, "[LAUNCHER] Site packages:  %s\n", site_pkgs[0] ? site_pkgs : "(none)");

    // 8. Configure Virtual Environment Variables
    char venv_dir[MAX_PATH_LEN];
    snprintf(venv_dir, sizeof(venv_dir), "%s/venv", install_dir);
    if (dir_exists(venv_dir)) {
        setenv("VIRTUAL_ENV", venv_dir, 1);
    }

    char new_path[MAX_ENV_LEN];
    const char *cur_path = getenv("PATH");
    snprintf(new_path, sizeof(new_path), "%s/venv/bin:%s/bin:%s", install_dir, install_dir, cur_path ? cur_path : "/usr/bin:/bin");
    setenv("PATH", new_path, 1);

    char py_path[MAX_ENV_LEN];
    const char *cur_pypath = getenv("PYTHONPATH");
    if (site_pkgs[0] != '\0') {
        if (cur_pypath && cur_pypath[0] != '\0') {
            snprintf(py_path, sizeof(py_path), "%s/src:%s:%s:%s", install_dir, install_dir, site_pkgs, cur_pypath);
        } else {
            snprintf(py_path, sizeof(py_path), "%s/src:%s:%s", install_dir, install_dir, site_pkgs);
        }
    } else {
        if (cur_pypath && cur_pypath[0] != '\0') {
            snprintf(py_path, sizeof(py_path), "%s/src:%s:%s", install_dir, install_dir, cur_pypath);
        } else {
            snprintf(py_path, sizeof(py_path), "%s/src:%s", install_dir, install_dir);
        }
    }
    setenv("PYTHONPATH", py_path, 1);

    // 9. Set Working Directory
    char work_dir[MAX_PATH_LEN];
    snprintf(work_dir, sizeof(work_dir), "%s/src", install_dir);
    if (dir_exists(work_dir)) {
        chdir(work_dir);
    } else {
        chdir(install_dir);
    }

    // 10. Construct command line arguments
    // argv[0] MUST be python_bin so Python's initialization finds pyvenv.cfg and sets sys.prefix
    // argv[1] MUST be main_py
    // Filter out macOS LaunchServices -psn_... parameter
    int new_argc = 2;
    for (int i = 1; i < argc; i++) {
        if (strncmp(argv[i], "-psn_", 5) == 0) continue;
        new_argc++;
    }

    char **new_argv = (char **)malloc((new_argc + 1) * sizeof(char *));
    new_argv[0] = (python_bin[0] != '\0') ? python_bin : "python3";
    new_argv[1] = main_py;
    int cur_idx = 2;
    for (int i = 1; i < argc; i++) {
        if (strncmp(argv[i], "-psn_", 5) == 0) continue;
        new_argv[cur_idx++] = argv[i];
    }
    new_argv[new_argc] = NULL;

    // 11. Strategy A: In-process execution via libpython
    if (python_lib[0] != '\0' && file_exists(python_lib)) {
        fprintf(stderr, "[LAUNCHER] Attempting in-process execution via dlopen(%s)...\n", python_lib);
        void *py_handle = dlopen(python_lib, RTLD_NOW | RTLD_GLOBAL);
        if (py_handle) {
            int (*Py_BytesMain)(int, char **) = (int (*)(int, char **))dlsym(py_handle, "Py_BytesMain");
            if (!Py_BytesMain) {
                Py_BytesMain = (int (*)(int, char **))dlsym(py_handle, "Py_Main");
            }
            if (Py_BytesMain) {
                fprintf(stderr, "[LAUNCHER] Invoking in-process Py_BytesMain...\n");
                int ret = Py_BytesMain(new_argc, new_argv);
                fprintf(stderr, "[LAUNCHER] In-process execution finished with code %d\n", ret);
                free(new_argv);
                return ret;
            } else {
                fprintf(stderr, "[LAUNCHER] dlsym could not find Py_BytesMain/Py_Main: %s\n", dlerror());
            }
        } else {
            fprintf(stderr, "[LAUNCHER] dlopen failed: %s\n", dlerror());
        }
    }

    // 12. Strategy B: Safe Fallback to execv
    fprintf(stderr, "[LAUNCHER] Falling back to execv(%s)...\n", python_bin);
    if (file_exists(python_bin)) {
        execv(python_bin, new_argv);
        fprintf(stderr, "[LAUNCHER] execv failed: %s (errno %d)\n", strerror(errno), errno);
    }

    fprintf(stderr, "[LAUNCHER] Falling back to execvp('python3')...\n");
    execvp("python3", new_argv);
    fprintf(stderr, "[LAUNCHER] execvp failed: %s (errno %d)\n", strerror(errno), errno);

    free(new_argv);
    return 1;
}
