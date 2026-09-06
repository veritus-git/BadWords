/*
 * Copyright (c) 2026 Szymon Wolarz
 * Licensed under the MIT License.
 *
 * BadWords Linux Native ELF Launcher
 * -------------------------------------------------------------
 * Runs as the main standalone binary on Linux.
 *
 * It dynamically initializes Python inside this process so that:
 *  1. In htop, top, ps, and system monitors the process name is "BadWords" (not "python3")
 *  2. prctl(PR_SET_NAME) sets /proc/self/comm to "BadWords"
 *  3. Virtualenv (venv) packages and paths are accurately loaded
 *  4. Immediate stderr/stdout redirection to badwords_debug.log so errors are never lost
 *  5. Bulletproof fallback to execv if in-process loading cannot be performed
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>
#include <limits.h>
#include <sys/stat.h>
#include <sys/prctl.h>
#include <dirent.h>
#include <errno.h>

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
    // 1. Immediately set thread and process name in Linux kernel
    prctl(PR_SET_NAME, "BadWords", 0, 0, 0);

    // Also overwrite argv[0] in place if space permits
    if (argv && argv[0]) {
        size_t len = strlen(argv[0]);
        if (len >= 8) {
            memset(argv[0], 0, len);
            strncpy(argv[0], "BadWords", len);
        }
    }

    // 2. Resolve real path of this launcher binary (/proc/self/exe)
    char real_exe[MAX_PATH_LEN] = {0};
    ssize_t r = readlink("/proc/self/exe", real_exe, sizeof(real_exe) - 1);
    if (r > 0) {
        real_exe[r] = '\0';
    } else {
        if (realpath(argv[0], real_exe) == NULL) {
            strncpy(real_exe, argv[0], sizeof(real_exe) - 1);
        }
    }

    // Determine install directory (where BadWords binary resides)
    char install_dir[MAX_PATH_LEN] = {0};
    strncpy(install_dir, real_exe, sizeof(install_dir) - 1);
    char *last_slash = strrchr(install_dir, '/');
    if (last_slash) {
        *last_slash = '\0';
    }

    // If install_dir ends with /bin, strip /bin (e.g. ~/.local/share/BadWords/bin -> ~/.local/share/BadWords)
    size_t id_len = strlen(install_dir);
    if (id_len > 4 && strcmp(install_dir + id_len - 4, "/bin") == 0) {
        install_dir[id_len - 4] = '\0';
    }

    char python_lib[MAX_PATH_LEN] = {0};
    char python_bin[MAX_PATH_LEN] = {0};
    char main_py[MAX_PATH_LEN] = {0};

    // Check config file if available
    char cfg_path[MAX_PATH_LEN] = {0};
    snprintf(cfg_path, sizeof(cfg_path), "%s/badwords.cfg", install_dir);
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
            snprintf(install_dir, sizeof(install_dir), "%s/.local/share/BadWords", home);
        } else {
            strncpy(install_dir, "/opt/BadWords", sizeof(install_dir) - 1);
        }
    }

    // 3. Redirect stdout & stderr to badwords_debug.log immediately for diagnostic safety
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
    fprintf(stderr, "\n=== BadWords Linux Native Launcher (PID %d) ===\n", getpid());
    fprintf(stderr, "[LAUNCHER] Executable:   %s\n", real_exe);
    fprintf(stderr, "[LAUNCHER] Install dir:  %s\n", install_dir);

    // 4. Resolve Python binary (check both python3 and python inside venv)
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

    // 5. Resolve Main Python script
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

    // 6. Inspect pyvenv.cfg to detect Python home and version
    char venv_home[MAX_PATH_LEN] = {0};
    char py_version[64] = {0};
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
            } else if (strcmp(k, "version") == 0) {
                strncpy(py_version, v, sizeof(py_version) - 1);
            }
        }
        fclose(fcfg);
        fprintf(stderr, "[LAUNCHER] pyvenv.cfg: home=%s, version=%s\n", venv_home, py_version);
    }

    // 7. Discover libpython if not explicitly provided
    if (python_lib[0] == '\0' || !file_exists(python_lib)) {
        char ver_short[16] = {0};
        if (py_version[0] != '\0') {
            char *dot = strchr(py_version, '.');
            if (dot) {
                char *dot2 = strchr(dot + 1, '.');
                if (dot2) {
                    strncpy(ver_short, py_version, dot2 - py_version);
                } else {
                    strncpy(ver_short, py_version, sizeof(ver_short) - 1);
                }
            }
        }

        const char *search_dirs[] = {
            "/usr/lib/x86_64-linux-gnu",
            "/usr/lib64",
            "/usr/lib",
            "/usr/local/lib",
            NULL
        };

        const char *versions[] = {
            ver_short[0] ? ver_short : "3.12",
            "3.12", "3.11", "3.10", "3.9", "3.13",
            NULL
        };

        for (int d = 0; search_dirs[d] != NULL && python_lib[0] == '\0'; d++) {
            for (int v = 0; versions[v] != NULL && python_lib[0] == '\0'; v++) {
                char cand_so[MAX_PATH_LEN];
                snprintf(cand_so, sizeof(cand_so), "%s/libpython%s.so.1.0", search_dirs[d], versions[v]);
                if (file_exists(cand_so)) {
                    strncpy(python_lib, cand_so, sizeof(python_lib) - 1);
                    break;
                }
                snprintf(cand_so, sizeof(cand_so), "%s/libpython%s.so", search_dirs[d], versions[v]);
                if (file_exists(cand_so)) {
                    strncpy(python_lib, cand_so, sizeof(python_lib) - 1);
                    break;
                }
            }
        }
    }
    fprintf(stderr, "[LAUNCHER] Python library: %s\n", python_lib[0] ? python_lib : "(none)");

    // 8. Detect site-packages directory inside venv/lib/
    char site_pkgs[MAX_PATH_LEN] = {0};
    char venv_lib[MAX_PATH_LEN];
    snprintf(venv_lib, sizeof(venv_lib), "%s/venv/lib", install_dir);
    DIR *dirp = opendir(venv_lib);
    if (dirp) {
        struct dirent *ent;
        while ((ent = readdir(dirp)) != NULL) {
            if (strncmp(ent->d_name, "python", 6) == 0) {
                char cand_sp[MAX_PATH_LEN * 2];
                snprintf(cand_sp, sizeof(cand_sp), "%s/%s/site-packages", venv_lib, ent->d_name);
                if (dir_exists(cand_sp)) {
                    strncpy(site_pkgs, cand_sp, sizeof(site_pkgs) - 1);
                    break;
                }
            }
        }
        closedir(dirp);
    }
    fprintf(stderr, "[LAUNCHER] Site packages:  %s\n", site_pkgs[0] ? site_pkgs : "(none)");

    // 9. Configure Virtual Environment Variables
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

    // 10. Set Working Directory
    char work_dir[MAX_PATH_LEN];
    snprintf(work_dir, sizeof(work_dir), "%s/src", install_dir);
    if (dir_exists(work_dir)) {
        if (chdir(work_dir) != 0) { /* continue */ }
    } else {
        if (chdir(install_dir) != 0) { /* continue */ }
    }

    // 11. Construct command line arguments
    int new_argc = argc + 1;
    char **new_argv = (char **)malloc((new_argc + 1) * sizeof(char *));
    new_argv[0] = (python_bin[0] != '\0') ? python_bin : "python3";
    new_argv[1] = main_py;
    for (int i = 1; i < argc; i++) {
        new_argv[i + 1] = argv[i];
    }
    new_argv[new_argc] = NULL;

    // 12. Strategy A: In-process execution via libpython
    if (python_lib[0] != '\0' && file_exists(python_lib)) {
        fprintf(stderr, "[LAUNCHER] Attempting in-process execution via dlopen(%s)...\n", python_lib);
        void *py_handle = dlopen(python_lib, RTLD_NOW | RTLD_GLOBAL);
        if (py_handle) {
            int (*Py_BytesMain)(int, char **) = (int (*)(int, char **))dlsym(py_handle, "Py_BytesMain");
            if (!Py_BytesMain) {
                Py_BytesMain = (int (*)(int, char **))dlsym(py_handle, "Py_Main");
            }
            if (Py_BytesMain) {
                fprintf(stderr, "[LAUNCHER] Invoking in-process Py_BytesMain (comm=BadWords)...\n");
                prctl(PR_SET_NAME, "BadWords", 0, 0, 0);
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

    // 13. Strategy B: Safe Fallback to execv
    fprintf(stderr, "[LAUNCHER] Falling back to execv(%s)...\n", python_bin);
    prctl(PR_SET_NAME, "BadWords", 0, 0, 0);
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
