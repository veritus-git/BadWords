#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates setupfiles/windows/version.h dynamically from src/config/app_constants.py
Ensures Windows PE VersionInfo resources are never hardcoded.
"""

import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
CONSTANTS_PATH = os.path.join(ROOT_DIR, "src", "config", "app_constants.py")
HEADER_PATH = os.path.join(SCRIPT_DIR, "version.h")


def get_version():
    if os.path.isfile(CONSTANTS_PATH):
        with open(CONSTANTS_PATH, "r", encoding="utf-8") as f:
            m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', f.read())
            if m:
                return m.group(1).strip()
    return "4.0.0"


def main():
    ver = get_version()
    parts = [re.sub(r'\D', '', p) or '0' for p in ver.split('.')]
    while len(parts) < 4:
        parts.append('0')
    parts = parts[:4]
    commas = ",".join(parts)

    content = f"""/* Auto-generated from src/config/app_constants.py - DO NOT EDIT MANUALLY */
#ifndef BW_VERSION_H
#define BW_VERSION_H

#define BW_VERSION_STR "{ver}"
#define BW_VERSION_COMMAS {commas}

#endif /* BW_VERSION_H */
"""
    with open(HEADER_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated {HEADER_PATH} with VERSION={ver} ({commas})")

    # Keep installer/Cargo.toml synchronized with app_constants.py
    cargo_toml = os.path.join(ROOT_DIR, "installer", "Cargo.toml")
    if os.path.isfile(cargo_toml):
        with open(cargo_toml, "r", encoding="utf-8") as f:
            c_text = f.read()
        new_c_text = re.sub(r'(?m)^version\s*=\s*"[^"]+"', f'version = "{ver}"', c_text, count=1)
        if new_c_text != c_text:
            with open(cargo_toml, "w", encoding="utf-8") as f:
                f.write(new_c_text)
            print(f"Synchronized {cargo_toml} to version = \"{ver}\"")


if __name__ == "__main__":
    main()
