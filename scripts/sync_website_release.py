#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
Syncs website/ static HTML, changelog, download binary sizes, JSON-LD, and sitemap.xml
with the latest release metadata from src/config/app_constants.py and src/config/release_notes.json
(and optionally GitHub Releases API for live binary sizes).
"""

import argparse
import datetime
import glob
import json
import os
import re
import urllib.request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WEBSITE_DIR = os.path.join(REPO_ROOT, "website")
APP_CONSTANTS = os.path.join(REPO_ROOT, "src", "config", "app_constants.py")
RELEASE_NOTES = os.path.join(REPO_ROOT, "src", "config", "release_notes.json")
GITHUB_API_LATEST = "https://api.github.com/repos/veritus-git/BadWords/releases/latest"


def read_app_version() -> str:
    txt = open(APP_CONSTANTS, "r", encoding="utf-8").read()
    m = re.search(r'^_DEFAULT_VERSION\s*=\s*"([^"]+)"', txt, re.M)
    if not m:
        raise RuntimeError("Could not locate _DEFAULT_VERSION in src/config/app_constants.py")
    return m.group(1).lstrip("vV").strip()


def read_release_notes() -> list:
    if not os.path.isfile(RELEASE_NOTES):
        return []
    data = json.load(open(RELEASE_NOTES, "r", encoding="utf-8"))
    changes = data.get("changes") or []
    return [sanitize_ascii_dashes(str(c).strip()) for c in changes if str(c).strip()]


def sanitize_ascii_dashes(text: str) -> str:
    return text.replace("\u2014", "-").replace("\u2013", "-")


def fetch_github_release(tag: str = "") -> dict:
    url = (
        f"https://api.github.com/repos/veritus-git/BadWords/releases/tags/{tag}"
        if tag
        else GITHUB_API_LATEST
    )
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "BadWords-Website-Sync",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def extract_asset_sizes_mb(release_json: dict) -> dict:
    sizes = {}
    for asset in release_json.get("assets") or []:
        name = asset.get("name", "")
        size_b = asset.get("size", 0)
        if size_b > 0:
            sizes[name] = f"{size_b / (1024 * 1024):.1f} MB"
    return sizes


def escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def update_changelog_html(version: str, iso_date: str, changes: list):
    path = os.path.join(WEBSITE_DIR, "changelog", "index.html")
    html = open(path, "r", encoding="utf-8").read()
    major = version.split(".")[0] if version else "4"

    # Skip injection if this exact version already has an article card
    if f'data-release-version="{version}"' in html or f">{f'v{version} '}" in html or f"v{version} -" in html:
        return False

    # Downgrade previous top card accent to standard card
    html = html.replace('class="card card-lg card-accent"', 'class="card card-lg"')

    bullets_html = "\n".join(
        f'            <li><span class="bullet-dot"></span><span>{escape_html(c)}</span></li>'
        for c in (changes[:5] or ["Maintenance, stability, and quality improvements."])
    )
    new_card = (
        f'        <article class="card card-lg card-accent" data-release-major="{major}" data-release-version="{version}">\n'
        f'          <div class="flex flex-wrap items-center justify-between gap-2">\n'
        f'            <h2 class="h3-card" style="font-size:1.35rem;">v{version} - Release Update</h2>\n'
        f'            <span class="mono-meta text-emerald">{iso_date}</span>\n'
        f'          </div>\n'
        f'          <ul class="bullet-list">\n'
        f'{bullets_html}\n'
        f'          </ul>\n'
        f'        </article>\n\n'
    )

    marker = '<div id="changelogList" class="mx-auto"'
    idx = html.find(marker)
    if idx == -1:
        raise RuntimeError("Could not find #changelogList in changelog/index.html")
    insert_at = html.find(">", idx) + 1
    html = html[:insert_at] + "\n" + new_card + html[insert_at:]
    open(path, "w", encoding="utf-8").write(html)
    return True


def make_short_summary(changes: list, max_len: int = 175) -> str:
    if not changes:
        return "stability, performance, and workflow improvements."
    first = changes[0].strip()
    # Prefer concise lead before semicolon/period if present
    for sep in (";", "."):
        if sep in first:
            cand = first.split(sep, 1)[0].strip()
            if 24 <= len(cand) <= max_len:
                return cand + "."
    if len(first) <= max_len:
        return first if first.endswith(".") else first + "."
    trimmed = first[: max_len - 3].rsplit(" ", 1)[0].rstrip(",;:")
    return trimmed + "..."


def sync_all(version: str, iso_date: str, fetch_sizes: bool, bump_cache: str):
    changes = read_release_notes()
    dot_date = datetime.date.fromisoformat(iso_date).strftime("%d.%m.%Y")
    rel_json = fetch_github_release(f"v{version}") if fetch_sizes else {}
    if fetch_sizes and not rel_json:
        rel_json = fetch_github_release(version)
    if fetch_sizes and not rel_json:
        rel_json = fetch_github_release()
    sizes = extract_asset_sizes_mb(rel_json)

    # 1. Update HTML version strings, dates, binary sizes, and cache-busters
    old_ver_re = re.compile(r"\b4\.\d+\.\d+\b")
    for path in sorted(glob.glob(os.path.join(WEBSITE_DIR, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(path, WEBSITE_DIR)
        html = open(path, "r", encoding="utf-8").read()

        if rel == os.path.join("changelog", "index.html"):
            # Only update header/footer/meta references on changelog, keep historical cards intact
            head, sep, tail = html.partition('<div id="changelogList"')
            head = old_ver_re.sub(version, head)
            if sep:
                footer_idx = tail.find("<footer")
                if footer_idx != -1:
                    tail = tail[:footer_idx] + old_ver_re.sub(version, tail[footer_idx:])
                html = head + sep + tail
            else:
                html = head
        else:
            html = old_ver_re.sub(version, html)

        # Keep data-bw-version in sync
        html = re.sub(r'data-bw-version="[^"]*"', f'data-bw-version="{version}"', html)

        # Update Current Release date & summary on index.html
        if rel == "index.html":
            html = re.sub(
                r'(data-bw-release-date>)\d{2}\.\d{2}\.\d{4}(</span>)',
                rf"\g<1>{dot_date}\g<2>",
                html,
            )
            if changes:
                short_summary = escape_html(make_short_summary(changes))
                html = re.sub(
                    r'(<span data-bw-release-summary>)(.*?)(</span>)',
                    rf"\g<1>{short_summary}\g<3>",
                    html,
                    flags=re.S,
                )

        # Update download asset sizes when available from GitHub Release
        asset_targets = {
            "badwords-setup-windows.exe": ("windows", ""),
            "badwords-setup-macos": ("mac", " Universal"),
            "badwords-setup-linux": ("linux", " x64"),
        }
        for asset_name, (os_key, suffix) in asset_targets.items():
            if asset_name in sizes:
                html = re.sub(
                    rf'(data-bw-size="{os_key}"[^>]*>)[^<]*(</span>)',
                    rf"\g<1>v{version} - {sizes[asset_name]}{suffix}\g<2>",
                    html,
                )

        if bump_cache:
            html = re.sub(r'(\.css|\.js)(\?v=[^"\']+)?', rf"\1?v={bump_cache}", html)

        html = sanitize_ascii_dashes(html)
        assert "\u2014" not in html and "\u2013" not in html, f"Long dash in {rel}"
        open(path, "w", encoding="utf-8").write(html)

    # 2. Prepend changelog entry if new version
    added_cl = update_changelog_html(version, iso_date, changes)

    # 3. Update sitemap.xml lastmod dates
    sm_path = os.path.join(WEBSITE_DIR, "sitemap.xml")
    if os.path.isfile(sm_path):
        sm = open(sm_path, "r", encoding="utf-8").read()
        sm = re.sub(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", f"<lastmod>{iso_date}</lastmod>", sm)
        open(sm_path, "w", encoding="utf-8").write(sm)

    print(
        f"Synced website to v{version} ({iso_date}) | changelog_added={added_cl} | sizes={sizes or 'unchanged'}"
    )


def main():
    parser = argparse.ArgumentParser(description="Sync BadWords website with release metadata.")
    parser.add_argument("--version", default="", help="Override version (defaults to src/config/app_constants.py)")
    parser.add_argument("--date", default=datetime.date.today().isoformat(), help="Release ISO date YYYY-MM-DD")
    parser.add_argument("--fetch-sizes", action="store_true", help="Fetch installer binary sizes from GitHub API")
    parser.add_argument("--bump-cache", default="", help="Optional CSS/JS ?v= cache token")
    args = parser.parse_args()

    ver = args.version.lstrip("vV").strip() if args.version else read_app_version()
    sync_all(ver, args.date, args.fetch_sizes, args.bump_cache)


if __name__ == "__main__":
    main()
