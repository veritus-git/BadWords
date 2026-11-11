#!/usr/bin/env python3
#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

# --- BADWORDS AUTO-UPDATE (Cross-Platform) ---
# Called by the BadWords GUI when the user clicks "Update Now", or runs background update.
# Implements full clean installation/update matching installer Option 1.
# Detects 3.x -> 4.x migration, displaying an informative one-time dialog directing to GitHub.

import os
import sys
import shutil
import hashlib
import tempfile
import argparse
import subprocess
import json
import urllib.request
import ssl
import webbrowser
import re

def _sp_hidden_kwargs():
    """Returns kwargs to ensure child processes never flash console windows on Windows."""
    kwargs = {}
    if os.name == 'nt':
        kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
        si = subprocess.STARTUPINFO()
        si.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)
        si.wShowWindow = getattr(subprocess, 'SW_HIDE', 0)
        kwargs['startupinfo'] = si
    return kwargs


def load_app_version(install_dir=None):
    """
    Dynamically loads the application version from src/config/app_constants.py
    as the single source of truth across the entire BadWords backend.
    """
    candidates = []
    if install_dir:
        candidates.extend([
            os.path.join(install_dir, "config", "app_constants.py"),
            os.path.join(install_dir, "src", "config", "app_constants.py"),
        ])
    cur = os.path.abspath(__file__)
    cur_dir = os.path.dirname(cur)
    candidates.extend([
        os.path.join(cur_dir, "..", "src", "config", "app_constants.py"),
        os.path.join(cur_dir, "..", "config", "app_constants.py"),
        os.path.join(cur_dir, "config", "app_constants.py"),
        os.path.join(cur_dir, "src", "config", "app_constants.py"),
        os.path.join(os.getcwd(), "src", "config", "app_constants.py"),
        os.path.join(os.getcwd(), "config", "app_constants.py"),
    ])
    for c in candidates:
        if os.path.isfile(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', f.read())
                    if m:
                        return m.group(1).strip()
            except Exception:
                pass
    return "4.0.0"

UPDATER_VERSION = load_app_version()
UPDATER_BUILD   = 2026111002

def is_no_self_upgrade_configured(install_dir: str = None, args_no_self_upgrade: bool = False) -> bool:
    """
    Checks if updater self-upgrade should be disabled.
    Honors:
    - --no-self-upgrade CLI flag
    - BW_NO_SELF_UPGRADE environment variable
    - .no_self_upgrade marker file in install_dir or updater directory
    - settings.json["no_self_upgrade"] == True in install_dir or updater directory
    """
    if args_no_self_upgrade:
        return True
    if os.environ.get("BW_NO_SELF_UPGRADE") == "1":
        return True
    
    probe_dirs = []
    if install_dir and os.path.isdir(install_dir):
        probe_dirs.append(os.path.abspath(install_dir))
    
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    probe_dirs.extend([cur_dir, os.path.dirname(cur_dir), os.getcwd()])

    for d in probe_dirs:
        if not os.path.isdir(d):
            continue
        marker = os.path.join(d, ".no_self_upgrade")
        if os.path.isfile(marker):
            return True
        for st_candidate in (os.path.join(d, "settings.json"), os.path.join(d, "config", "settings.json")):
            if os.path.isfile(st_candidate):
                try:
                    with open(st_candidate, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("no_self_upgrade") is True:
                            return True
                except Exception:
                    pass
    return False

# Auxiliary files required by updater for custom dialogs, assets, or helpers
# pulled on-demand from the latest git tag prior to running the update.
UPDATER_AUXILIARY_FILES = [
    "src/gui/dialogs/v4_migration_dialog.py",
]

def log(msg): print(f"[UPDATE] {msg}")
def info(msg): print(f"[INFO]   {msg}")
def warn(msg): print(f"[WARN]   {msg}")
def err(msg): print(f"[ERROR]  {msg}", file=sys.stderr)

MIGRATION_TEXTS = {
    "pl": {
        "title": f"BadWords {UPDATER_VERSION} – Zaktualizowano pomyślnie",
        "badge": f"Wersja {UPDATER_VERSION} • Nowa era BadWords",
        "heading": f"Zaktualizowano do BadWords {UPDATER_VERSION}!",
        "body": (
            f"Twoja instalacja została pomyślnie zaktualizowana do wersji {UPDATER_VERSION}.\n\n"
            f"Od wersji {UPDATER_VERSION} BadWords stało się nie tylko znacznie szybszym i bardziej zaawansowanym "
            "pluginem dla DaVinci Resolve, ale także w pełni niezależną, samostojącą aplikacją desktopową.\n\n"
            "Zalecamy pobranie i uruchomienie nowego oficjalnego instalatora ze strony GitHub Releases, "
            "aby utworzyć dedykowane skróty na pulpicie, wpis w menu aplikacji oraz zainstalować natywny launcher."
        ),
        "btn_github": "Pobierz nowy instalator (GitHub)",
        "btn_close": "Rozumiem / Zamknij",
    },
    "en": {
        "title": f"BadWords {UPDATER_VERSION} – Update Complete",
        "badge": f"Version {UPDATER_VERSION} • A New Era of BadWords",
        "heading": f"Updated to BadWords {UPDATER_VERSION}!",
        "body": (
            f"Your installation has been successfully updated to version {UPDATER_VERSION}.\n\n"
            f"Starting with version {UPDATER_VERSION}, BadWords is not only an advanced DaVinci Resolve plugin, "
            "but also a full standalone desktop application with dedicated native launchers and system integration.\n\n"
            "We recommend downloading and running the official installer from GitHub Releases "
            "to set up native launchers, desktop shortcuts, and full system integration."
        ),
        "btn_github": "Download New Installer (GitHub)",
        "btn_close": "Got it / Close",
    },
    "de": {
        "title": f"BadWords {UPDATER_VERSION} – Update abgeschlossen",
        "badge": f"Version {UPDATER_VERSION} • Eine neue Ära",
        "heading": f"Auf BadWords {UPDATER_VERSION} aktualisiert!",
        "body": (
            f"Ihre Installation wurde erfolgreich auf Version {UPDATER_VERSION} aktualisiert.\n\n"
            f"Ab Version {UPDATER_VERSION} ist BadWords nicht nur ein DaVinci Resolve-Plugin, "
            "sondern auch eine vollwertige, eigenständige Desktop-Anwendung mit nativen Launchern.\n\n"
            "Wir empfehlen, das offizielle Installationsprogramm von GitHub Releases herunterzuladen, "
            "um Desktop-Verknüpfungen und die Systemintegration einzurichten."
        ),
        "btn_github": "Neuen Installer herunterladen (GitHub)",
        "btn_close": "Verstanden / Schließen",
    },
    "es": {
        "title": f"BadWords {UPDATER_VERSION} – Actualización completada",
        "badge": f"Versión {UPDATER_VERSION} • Nueva era de BadWords",
        "heading": f"¡Actualizado a BadWords {UPDATER_VERSION}!",
        "body": (
            f"Tu instalación se ha actualizado correctamente a la versión {UPDATER_VERSION}.\n\n"
            f"A partir de la versión {UPDATER_VERSION}, BadWords no es solo un complemento para DaVinci Resolve, "
            "sino también una aplicación de escritorio independiente con lanzadores nativos.\n\n"
            "Recomendamos descargar el instalador oficial desde GitHub Releases "
            "para configurar los accesos directos y la integración en el sistema."
        ),
        "btn_github": "Descargar nuevo instalador (GitHub)",
        "btn_close": "Entendido / Cerrar",
    },
    "fr": {
        "title": f"BadWords {UPDATER_VERSION} – Mise à jour terminée",
        "badge": f"Version {UPDATER_VERSION} • Une nouvelle ère",
        "heading": f"Mis à jour vers BadWords {UPDATER_VERSION} !",
        "body": (
            f"Votre installation a été mise à jour avec succès vers la version {UPDATER_VERSION}.\n\n"
            f"À partir de la version {UPDATER_VERSION}, BadWords n'est plus seulement un plugin DaVinci Resolve, "
            "mais aussi une application de bureau autonome avec lanceurs natifs.\n\n"
            "Nous vous recommandons de télécharger le programme d'installation officiel sur GitHub Releases "
            "pour configurer les raccourcis et l'intégration système."
        ),
        "btn_github": "Télécharger le nouvel installateur (GitHub)",
        "btn_close": "Compris / Fermer",
    },
    "it": {
        "title": f"BadWords {UPDATER_VERSION} – Aggiornamento completato",
        "badge": f"Versione {UPDATER_VERSION} • Una nuova era",
        "heading": f"Aggiornato a BadWords {UPDATER_VERSION}!",
        "body": (
            f"La tua installazione è stata aggiornata con successo alla versione {UPDATER_VERSION}.\n\n"
            f"A partire dalla versione {UPDATER_VERSION}, BadWords non è solo un plugin per DaVinci Resolve, "
            "ma anche un'applicazione desktop autonoma completa con launcher nativi.\n\n"
            "Ti consigliamo di scaricare l'installer ufficiale da GitHub Releases "
            "per configurare i collegamenti sul desktop e l'integrazione di sistema."
        ),
        "btn_github": "Scarica nuovo installer (GitHub)",
        "btn_close": "Ho capito / Chiudi",
    },
    "nl": {
        "title": f"BadWords {UPDATER_VERSION} – Update voltooid",
        "badge": f"Versie {UPDATER_VERSION} • Een nieuw tijdperk",
        "heading": f"Bijgewerkt naar BadWords {UPDATER_VERSION}!",
        "body": (
            f"Uw installatie is succesvol bijgewerkt naar versie {UPDATER_VERSION}.\n\n"
            f"Vanaf versie {UPDATER_VERSION} is BadWords niet alleen een DaVinci Resolve-plug-in, "
            "maar ook een volwaardige standalone desktop-applicatie met native launchers.\n\n"
            "We raden aan het officiële installatieprogramma van GitHub Releases te downloaden "
            "om snelkoppelingen en systeemintegratie in te stellen."
        ),
        "btn_github": "Nieuwe installer downloaden (GitHub)",
        "btn_close": "Begrepen / Sluiten",
    },
    "pt": {
        "title": f"BadWords {UPDATER_VERSION} – Atualização concluída",
        "badge": f"Versão {UPDATER_VERSION} • Nova era do BadWords",
        "heading": f"Atualizado para BadWords {UPDATER_VERSION}!",
        "body": (
            f"Sua instalação foi atualizada com sucesso para a versão {UPDATER_VERSION}.\n\n"
            f"A partir de la versión {UPDATER_VERSION}, o BadWords é não apenas um plugin para DaVinci Resolve, "
            "mas também um aplicativo desktop independente com inicializadores nativos.\n\n"
            "Recomendamos baixar o instalador oficial no GitHub Releases "
            "para configurar atalhos na área de trabalho e integração ao sistema."
        ),
        "btn_github": "Baixar novo instalador (GitHub)",
        "btn_close": "Entendi / Fechar",
    },
    "ru": {
        "title": f"BadWords {UPDATER_VERSION} – Обновление завершено",
        "badge": f"Версия {UPDATER_VERSION} • Новая эра BadWords",
        "heading": f"Обновлено до BadWords {UPDATER_VERSION}!",
        "body": (
            f"Ваша установка была успешно обновлена до версии {UPDATER_VERSION}.\n\n"
            f"Начиная с версии {UPDATER_VERSION}, BadWords — это не только плагин для DaVinci Resolve, "
            "но и полноценное автономное приложение с нативными лаунчерами.\n\n"
            "Мы рекомендуем скачать официальный установщик со страницы GitHub Releases, "
            "чтобы настроить ярлыки на рабочем столе и интеграцию с системой."
        ),
        "btn_github": "Скачать новый установщик (GitHub)",
        "btn_close": "Понятно / Закрыть",
    },
    "uk": {
        "title": f"BadWords {UPDATER_VERSION} – Оновлення завершено",
        "badge": f"Версія {UPDATER_VERSION} • Нова ера BadWords",
        "heading": f"Оновлено до BadWords {UPDATER_VERSION}!",
        "body": (
            f"Вашу установку успішно оновлено до версії {UPDATER_VERSION}.\n\n"
            f"Починаючи з версії {UPDATER_VERSION}, BadWords — це не лише плагін для DaVinci Resolve, "
            "але й повноцінний автономний застосунок із нативними лаунчерами.\n\n"
            "Ми рекомендуємо завантажити офіційний інсталятор зі сторінки GitHub Releases, "
            "щоб налаштувати ярлики на робочому столі та інтеграцію із системою."
        ),
        "btn_github": "Завантажити новий інсталятор (GitHub)",
        "btn_close": "Зрозуміло / Закрити",
    },
}

def md5(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

def fetch_json(url, timeout=10):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "BadWords-Updater/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))

def parse_version(tag):
    if not tag:
        return (0, 0, 0)
    tag = str(tag).strip().lstrip('v').lstrip('V')
    try:
        parts = [int(x) for x in tag.split('.') if x.isdigit()]
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])
    except Exception:
        return (0, 0, 0)

def parse_tag_tuple(t):
    """
    Parses a git tag into a comparable tuple (major, minor, patch, clean_priority).
    Clean releases (e.g. '4.0.0') get priority over suffixed tags (e.g. '4.0.0-clean-arch').
    """
    if not t:
        return (0, 0, 0, -10)
    clean = re.sub(r"^[vV]", "", str(t).strip())
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", clean)
    if m:
        maj = int(m.group(1))
        min_ = int(m.group(2))
        patch = int(m.group(3)) if m.group(3) else 0
        has_suffix = 0 if re.match(r"^\d+\.\d+(?:\.\d+)?$", clean) else -1
        return (maj, min_, patch, has_suffix)
    return (0, 0, 0, -10)

def get_latest_release():
    # 1. Try GitHub
    try:
        data = fetch_json("https://api.github.com/repos/veritus-git/BadWords/releases/latest")
        tag = data.get("tag_name", "").strip()
        if tag:
            zip_url = f"https://github.com/veritus-git/BadWords/archive/refs/tags/{tag}.zip"
            return tag, zip_url, "GitHub"
    except Exception as e:
        warn(f"GitHub API failed: {e}")

    # 2. Try GitLab fallback
    try:
        data = fetch_json("https://gitlab.com/api/v4/projects/badwords%2FBadWords/releases")
        if isinstance(data, list) and data:
            tag = data[0].get("tag_name", "").strip()
        elif isinstance(data, dict):
            tag = data.get("tag_name", "").strip()
        
        if tag:
            zip_url = f"https://gitlab.com/badwords/BadWords/-/archive/{tag}/BadWords-{tag}.zip"
            return tag, zip_url, "GitLab"
    except Exception as e:
        warn(f"GitLab API failed: {e}")

    return None, None, None

def get_latest_tag():
    """
    Specifically queries git tags from GitHub API (with GitLab fallback).
    Selects the highest semver tag and returns (tag, zip_url, source_name).
    """
    # 1. GitHub tags
    try:
        data = fetch_json("https://api.github.com/repos/veritus-git/BadWords/tags")
        if isinstance(data, list) and data:
            valid_tags = [t.get("name", "").strip() for t in data if t.get("name")]
            if valid_tags:
                sorted_tags = sorted(valid_tags, key=parse_tag_tuple, reverse=True)
                tag = sorted_tags[0]
                zip_url = f"https://github.com/veritus-git/BadWords/archive/refs/tags/{tag}.zip"
                return tag, zip_url, "GitHub"
    except Exception as e:
        warn(f"GitHub tags API failed: {e}")

    # 2. GitLab tags
    try:
        data = fetch_json("https://gitlab.com/api/v4/projects/badwords%2FBadWords/repository/tags")
        if isinstance(data, list) and data:
            valid_tags = [t.get("name", "").strip() for t in data if t.get("name")]
            if valid_tags:
                sorted_tags = sorted(valid_tags, key=parse_tag_tuple, reverse=True)
                tag = sorted_tags[0]
                zip_url = f"https://gitlab.com/badwords/BadWords/-/archive/{tag}/BadWords-{tag}.zip"
                return tag, zip_url, "GitLab"
    except Exception as e:
        warn(f"GitLab tags API failed: {e}")

    # Fallback to releases if tags API failed
    return get_latest_release()

def fetch_raw_file_from_tag(tag: str, rel_path: str):
    """
    Fetches raw bytes of a file from GitHub or GitLab at the specified git tag.
    """
    rel_clean = rel_path.lstrip("/").replace("\\", "/")
    gh_url = f"https://raw.githubusercontent.com/veritus-git/BadWords/{tag}/{rel_clean}"
    gl_url = f"https://gitlab.com/badwords/BadWords/-/raw/{tag}/{rel_clean}"

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {"User-Agent": "BadWords-Updater/1.0"}

    for url in (gh_url, gl_url):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception:
            continue
    return None

def sync_auxiliary_files(tag: str, install_dir: str):
    """
    Downloads any auxiliary files required by the updater from the latest git tag
    before full repository extraction (e.g. custom migration dialogs).
    """
    if not install_dir or not os.path.isdir(install_dir):
        return

    for rel_path in UPDATER_AUXILIARY_FILES:
        target_path = os.path.join(install_dir, rel_path)
        content = fetch_raw_file_from_tag(tag, rel_path)
        if content:
            try:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "wb") as f:
                    f.write(content)
                info(f"Pulled auxiliary dependency from tag '{tag}': {rel_path}")
            except Exception as e:
                warn(f"Could not write auxiliary file {rel_path}: {e}")

def extract_updater_meta(code_str: str) -> tuple:
    """Extracts (version_tuple, build_int) from an updater.py file content."""
    ver = (0, 0, 0)
    bld = 0
    m_ver = re.search(r'UPDATER_VERSION\s*=\s*(?:load_app_version\(\)|["\']([^"\']+)["\'])', code_str)
    if m_ver and m_ver.group(1):
        ver = parse_version(m_ver.group(1))
    else:
        m_v2 = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', code_str)
        if m_v2:
            ver = parse_version(m_v2.group(1))
    m_bld = re.search(r'UPDATER_BUILD\s*=\s*(\d+)', code_str)
    if m_bld:
        try:
            bld = int(m_bld.group(1))
        except Exception:
            bld = 0
    return ver, bld

def self_upgrade_if_needed(tag: str, install_dir: str = None) -> bool:
    """
    Compares the running updater.py with updater.py from the latest git tag.
    If the remote updater is strictly newer or different, replaces itself, pulls auxiliary files,
    and relaunches into the updated script.
    """
    if os.environ.get("_BW_UPDATER_SELF_UPGRADED") == "1":
        return False

    current_script = os.path.abspath(__file__)
    current_content = b""
    if os.path.isfile(current_script):
        try:
            with open(current_script, "rb") as f:
                current_content = f.read()
        except Exception:
            pass

    remote_code = fetch_raw_file_from_tag(tag, "setupfiles/updater.py")
    if not remote_code or len(remote_code) < 200:
        return False

    # Validate syntax before considering
    try:
        compile(remote_code, "<updater_upgrade>", "exec")
    except Exception as e:
        warn(f"Remote updater from tag '{tag}' failed syntax check: {e}")
        return False

    remote_hash = hashlib.sha256(remote_code).hexdigest()
    local_hash = hashlib.sha256(current_content).hexdigest() if current_content else ""

    if remote_hash == local_hash:
        return False

    # Check version & build metadata to guarantee we never downgrade
    local_text = current_content.decode("utf-8", errors="replace")
    remote_text = remote_code.decode("utf-8", errors="replace")

    local_ver, local_bld = extract_updater_meta(local_text)
    remote_ver, remote_bld = extract_updater_meta(remote_text)

    # If local has a strictly higher build, skip self-upgrade
    if remote_bld > 0 and local_bld > 0 and remote_bld < local_bld:
        return False

    log(f"Newer or updated updater detected on tag '{tag}' (remote build: {remote_bld}, local build: {local_bld}). Self-upgrading...")

    # Overwrite running script
    try:
        with open(current_script, "wb") as f:
            f.write(remote_code)
    except Exception as e:
        warn(f"Could not overwrite running script ({current_script}): {e}")
        return False

    # Also sync into install_dir (both setupfiles/updater.py and root updater.py)
    if install_dir and os.path.isdir(install_dir):
        inst_updater = os.path.join(install_dir, "setupfiles", "updater.py")
        root_updater = os.path.join(install_dir, "updater.py")
        for u_dest in (inst_updater, root_updater):
            if os.path.abspath(u_dest) != current_script:
                try:
                    os.makedirs(os.path.dirname(u_dest), exist_ok=True)
                    with open(u_dest, "wb") as f:
                        f.write(remote_code)
                except Exception:
                    pass

    # Pull auxiliary files required by the new updater
    sync_auxiliary_files(tag, install_dir)

    log("Updater successfully self-upgraded! Relaunching...")
    new_env = os.environ.copy()
    new_env["_BW_UPDATER_SELF_UPGRADED"] = "1"

    if os.name == "nt":
        r = subprocess.run([sys.executable, current_script] + sys.argv[1:], env=new_env, **_sp_hidden_kwargs())
        sys.exit(r.returncode)
    else:
        os.execve(sys.executable, [sys.executable, current_script] + sys.argv[1:], new_env)

    return True

def download(url, dest):
    if shutil.which("curl"):
        r = subprocess.run(["curl", "-fsSL", "--retry", "3", url, "-o", dest], capture_output=True, **_sp_hidden_kwargs())
        if r.returncode == 0 and os.path.isfile(dest):
            return True
    if shutil.which("wget"):
        r = subprocess.run(["wget", "-qO", dest, url], capture_output=True, **_sp_hidden_kwargs())
        if r.returncode == 0 and os.path.isfile(dest):
            return True
    if os.name == "nt":
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Invoke-WebRequest -Uri '{url}' -OutFile '{dest}' -UseBasicParsing"],
            capture_output=True,
            **_sp_hidden_kwargs()
        )
        if r.returncode == 0 and os.path.isfile(dest):
            return True
    
    # Python fallback
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "BadWords-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp, open(dest, 'wb') as out:
            shutil.copyfileobj(resp, out)
        return os.path.isfile(dest)
    except Exception as e:
        err(f"Python download failed: {e}")
        return False

def detect_installed_version(install_dir):
    candidates = [
        os.path.join(install_dir, "config", "app_constants.py"),
        os.path.join(install_dir, "src", "config", "app_constants.py"),
        os.path.join(install_dir, "config.py"),
        os.path.join(install_dir, "src", "config.py"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("VERSION") or line.startswith("APP_VERSION"):
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                val = parts[1].strip().strip('"').strip("'")
                                if val:
                                    return val
            except Exception:
                pass

    for fn in ["settings.json", "user.json", "pref.json"]:
        p = os.path.join(install_dir, fn)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    val = d.get("settings_version") or d.get("version") or d.get("badwords_version")
                    if val:
                        return str(val)
            except Exception:
                pass
    return "3.2.4"

def get_ui_language(install_dir):
    for fn in ["settings.json", "user.json", "pref.json"]:
        p = os.path.join(install_dir, fn)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    lang = d.get("lang") or d.get("gui_lang")
                    if lang and isinstance(lang, str):
                        code = lang.lower().strip()
                        if code in MIGRATION_TEXTS:
                            return code
            except Exception:
                pass
    try:
        import locale
        loc = locale.getdefaultlocale()[0]
        if loc:
            code = loc[:2].lower()
            if code in MIGRATION_TEXTS:
                return code
    except Exception:
        pass
    return "en"

def is_v4_migration_already_notified(install_dir):
    marker = os.path.join(install_dir, ".v4_migration_notified")
    if os.path.isfile(marker):
        return True
    for fn in ["settings.json", "user.json", "pref.json"]:
        p = os.path.join(install_dir, fn)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if d.get("v4_migration_notified") is True:
                        return True
            except Exception:
                pass
    return False

def mark_v4_migration_notified(install_dir):
    try:
        marker = os.path.join(install_dir, ".v4_migration_notified")
        with open(marker, "w", encoding="utf-8") as f:
            f.write("1\n")
    except Exception:
        pass
    for fn in ["settings.json", "user.json"]:
        p = os.path.join(install_dir, fn)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                d["v4_migration_notified"] = True
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(d, f, indent=4)
            except Exception:
                pass

def build_migration_dialog_class():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
    )

    class V4MigrationDialog(QDialog):
        def __init__(self, lang="en", parent=None):
            super().__init__(parent)
            self.user_choice = "close"
            self.lang = lang if lang in MIGRATION_TEXTS else "en"
            t = MIGRATION_TEXTS[self.lang]

            self.setWindowTitle(t["title"])
            self.setFixedWidth(680)
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)

            self.setStyleSheet("""
                QDialog {
                    background-color: #121212;
                    color: #e6e6e6;
                    font-family: 'Segoe UI', 'Ubuntu', 'Helvetica Neue', sans-serif;
                }
                #MainCard {
                    background-color: #181818;
                    border: 1px solid #282828;
                    border-radius: 12px;
                }
                #BadgeLabel {
                    background-color: #0d2e18;
                    color: #39ff7a;
                    border: 1px solid #1a572d;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-size: 9pt;
                    font-weight: bold;
                }
                #HeadingLabel {
                    color: #ffffff;
                    font-size: 13.5pt;
                    font-weight: bold;
                }
                #BodyLabel {
                    color: #cccccc;
                    font-size: 10pt;
                    line-height: 1.5;
                }
                QPushButton {
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 9.5pt;
                    font-weight: bold;
                }
                #PrimaryBtn {
                    background-color: #238636;
                    color: #ffffff;
                    border: 1px solid #2ea043;
                }
                #PrimaryBtn:hover {
                    background-color: #2ea043;
                }
                #SecondaryBtn {
                    background-color: #21262d;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                }
                #SecondaryBtn:hover {
                    background-color: #30363d;
                    color: #ffffff;
                }
                #CloseBtn {
                    background-color: transparent;
                    color: #8b949e;
                    border: none;
                }
                #CloseBtn:hover {
                    color: #ffffff;
                }
            """)

            outer = QVBoxLayout(self)
            outer.setSizeConstraint(QVBoxLayout.SetFixedSize)
            outer.setContentsMargins(20, 20, 20, 20)

            card = QFrame(self)
            card.setObjectName("MainCard")
            card_layout = QVBoxLayout(card)
            card_layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
            card_layout.setContentsMargins(24, 24, 24, 24)
            card_layout.setSpacing(14)

            top_row = QHBoxLayout()
            badge = QLabel(t["badge"])
            badge.setObjectName("BadgeLabel")
            top_row.addWidget(badge)
            top_row.addStretch()

            close_x = QPushButton("✕")
            close_x.setObjectName("CloseBtn")
            close_x.setCursor(Qt.PointingHandCursor)
            close_x.clicked.connect(self._on_close)
            top_row.addWidget(close_x)
            card_layout.addLayout(top_row)

            heading = QLabel(t["heading"])
            heading.setObjectName("HeadingLabel")
            heading.setWordWrap(True)
            card_layout.addWidget(heading)

            body = QLabel(t["body"])
            body.setObjectName("BodyLabel")
            body.setWordWrap(True)
            card_layout.addWidget(body)

            card_layout.addSpacing(6)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(10)
            btn_row.addStretch()

            btn_close = QPushButton(t["btn_close"])
            btn_close.setObjectName("SecondaryBtn")
            btn_close.setCursor(Qt.PointingHandCursor)
            btn_close.clicked.connect(self._on_close)
            btn_row.addWidget(btn_close)

            btn_github = QPushButton(t["btn_github"])
            btn_github.setObjectName("PrimaryBtn")
            btn_github.setCursor(Qt.PointingHandCursor)
            btn_github.clicked.connect(self._on_github)
            btn_row.addWidget(btn_github)

            card_layout.addLayout(btn_row)
            outer.addWidget(card)

        def _on_github(self):
            self.user_choice = "github"
            try:
                webbrowser.open("https://github.com/veritus-git/BadWords/releases/latest")
            except Exception:
                pass
            self.accept()

        def _on_close(self):
            self.user_choice = "close"
            self.reject()

    return V4MigrationDialog

def get_migration_dialog_class(install_dir=None):
    """
    Attempts to load V4MigrationDialog from the pulled auxiliary module.
    Falls back to the self-contained build_migration_dialog_class().
    """
    if install_dir:
        src_path = os.path.join(install_dir, "src")
        if os.path.isdir(src_path) and src_path not in sys.path:
            sys.path.insert(0, src_path)
        try:
            from gui.dialogs.v4_migration_dialog import V4MigrationDialog
            return V4MigrationDialog
        except Exception:
            pass
    return build_migration_dialog_class()

def prompt_v4_migration_notice(install_dir, lang="en"):
    """
    Shows the custom PySide6 window informing the user about BadWords 4.0.0.
    Returns: 'github', 'continue', or 'close' (fallback to 'continue' if no GUI).
    """
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        created_app = False
        if app is None:
            app = QApplication([sys.argv[0]])
            created_app = True

        DialogClass = get_migration_dialog_class(install_dir)
        dlg = DialogClass(lang=lang)
        dlg.exec()
        choice = getattr(dlg, "user_choice", "continue")
        if created_app:
            pass
        return choice
    except Exception as e:
        warn(f"Could not display migration window (headless/no display): {e}")
        return "continue"

def detect_nvidia_gpu():
    if os.name == "nt":
        for p in [r"C:\Windows\System32\nvcuda.dll", r"C:\Windows\System32\nvapi64.dll"]:
            if os.path.isfile(p):
                return True
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "try{$g=Get-WmiObject Win32_VideoController -EA Stop "
                 "| Where-Object {$_.Name -like '*NVIDIA*'} "
                 "| Select-Object -First 1; if($g){'1'}else{'0'}}catch{'0'}"],
                capture_output=True, text=True, timeout=10,
                **_sp_hidden_kwargs()
            )
            return r.stdout.strip() == "1"
        except Exception:
            return False
    else:
        if shutil.which("lspci"):
            try:
                r = subprocess.run(["lspci"], capture_output=True, text=True)
                if "nvidia" in r.stdout.lower():
                    return True
            except Exception:
                pass
        if shutil.which("lshw"):
            try:
                r = subprocess.run(["lshw", "-C", "display"], capture_output=True, text=True)
                if "nvidia" in r.stdout.lower():
                    return True
            except Exception:
                pass
    return False

def get_resolve_script_dirs():
    paths = []
    if os.name == "nt":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            paths.append(os.path.join(appdata, "Blackmagic Design", "DaVinci Resolve", "Support", "Fusion", "Scripts", "Utility"))
            paths.append(os.path.join(appdata, "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts", "Utility"))
        progdata = os.environ.get("PROGRAMDATA", "")
        if progdata:
            paths.append(os.path.join(progdata, "Blackmagic Design", "DaVinci Resolve", "Support", "Fusion", "Scripts", "Utility"))
            paths.append(os.path.join(progdata, "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts", "Utility"))
    elif sys.platform == "darwin":
        home = os.path.expanduser("~")
        paths.append(os.path.join(home, "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts", "Utility"))
        paths.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility")
    else:
        home = os.path.expanduser("~")
        paths.append(os.path.join(home, ".local", "share", "DaVinciResolve", "Fusion", "Scripts", "Utility"))
        paths.append(os.path.join(home, ".var", "app", "com.blackmagicdesign.resolve", "data", "DaVinciResolve", "Fusion", "Scripts", "Utility"))

    unique = []
    for p in paths:
        if p and p not in unique:
            unique.append(p)
    return unique

def deploy_davinci_wrappers(install_dir):
    try:
        sys.path.insert(0, install_dir)
        sys.path.insert(0, os.path.join(install_dir, "setupfiles"))
        from setupfiles.setup import generate_davinci_wrapper
        generate_davinci_wrapper(install_dir)
        info("DaVinci Resolve script wrapper updated via setup module.")
        return
    except Exception as e:
        warn(f"Invoking setup.generate_davinci_wrapper notice: {e}")

    wrapper_content = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BadWords - AI-powered DaVinci Resolve Workflow Plugin
# Generated by BadWords Updater

import sys
import os

INSTALL_DIR = r"{install_dir}"

def _launch_external():
    import subprocess
    venv_py = os.path.join(INSTALL_DIR, "venv", "Scripts", "pythonw.exe") if sys.platform.startswith('win') else os.path.join(INSTALL_DIR, "venv", "bin", "python3")
    if not os.path.isfile(venv_py):
        venv_py = os.path.join(INSTALL_DIR, "venv", "Scripts", "python.exe") if sys.platform.startswith('win') else os.path.join(INSTALL_DIR, "venv", "bin", "python")
    if not os.path.isfile(venv_py):
        venv_py = sys.executable
    main_py = os.path.join(INSTALL_DIR, "main.py")
    if not os.path.isfile(main_py):
        main_py = os.path.join(INSTALL_DIR, "src", "main.py")
    if os.path.isfile(main_py):
        kwargs = {{}}
        if sys.platform.startswith('win'):
            kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
        subprocess.Popen([venv_py, main_py, "--resolve-attached"], cwd=INSTALL_DIR, **kwargs)

_venv_ver = None
_cfg = os.path.join(INSTALL_DIR, "venv", "pyvenv.cfg")
if os.path.isfile(_cfg):
    try:
        with open(_cfg, "r", encoding="utf-8", errors="ignore") as _f:
            for _l in _f:
                if _l.strip().lower().startswith("version"):
                    _v_str = _l.split("=")[-1].strip()
                    _p = [int(x) for x in _v_str.split(".")[:2] if x.isdigit()]
                    if len(_p) == 2:
                        _venv_ver = tuple(_p)
                    break
    except Exception:
        pass

_host_ver = sys.version_info[:2]
if _venv_ver is not None and _venv_ver != _host_ver:
    _launch_external()
    sys.exit(0)

if os.path.isdir(INSTALL_DIR):
    if INSTALL_DIR not in sys.path:
        sys.path.insert(0, INSTALL_DIR)
    libs_dir = os.path.join(INSTALL_DIR, "libs")
    if os.path.isdir(libs_dir) and libs_dir not in sys.path:
        sys.path.insert(0, libs_dir)

    main_script = os.path.join(INSTALL_DIR, "main.py")
    if not os.path.isfile(main_script):
        main_script = os.path.join(INSTALL_DIR, "src", "main.py")

    if os.path.isfile(main_script):
        try:
            with open(main_script, "rb") as f:
                code = compile(f.read(), main_script, "exec")
                globs = globals()
                globs["__file__"] = main_script
                exec(code, globs)
        except Exception:
            _launch_external()
'''
    script_dirs = get_resolve_script_dirs()
    count = 0
    for sd in script_dirs:
        try:
            os.makedirs(sd, exist_ok=True)
            w_path = os.path.join(sd, "BadWords.py")
            with open(w_path, "w", encoding="utf-8") as f:
                f.write(wrapper_content)
            if os.name != "nt":
                os.chmod(w_path, 0o755)
            count += 1
        except Exception as e:
            warn(f"Could not deploy DaVinci wrapper to {sd}: {e}")
    if count > 0:
        info(f"DaVinci Resolve script wrapper updated in {count} locations.")

def ensure_ffmpeg(bin_dir):
    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffmpeg_path = os.path.join(bin_dir, ffmpeg_name)
    if os.path.isfile(ffmpeg_path):
        return True

    sys_ff = shutil.which("ffmpeg")
    if sys_ff and os.path.isfile(sys_ff):
        try:
            shutil.copy2(sys_ff, ffmpeg_path)
            if os.name != "nt":
                os.chmod(ffmpeg_path, 0o755)
            info(f"Copied system FFmpeg from {sys_ff}")
            return True
        except Exception as e:
            warn(f"Failed to copy system FFmpeg: {e}")

    info("Downloading portable FFmpeg...")
    try:
        if os.name == "nt":
            url = "https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-essentials_build.zip"
            zip_tmp = os.path.join(bin_dir, "ff_tmp.zip")
            if download(url, zip_tmp):
                import zipfile
                with zipfile.ZipFile(zip_tmp, 'r') as zf:
                    for m in zf.namelist():
                        if os.path.basename(m) in ("ffmpeg.exe", "ffprobe.exe"):
                            data = zf.read(m)
                            with open(os.path.join(bin_dir, os.path.basename(m)), "wb") as out:
                                out.write(data)
                try: os.remove(zip_tmp)
                except Exception: pass
                return os.path.isfile(ffmpeg_path)
    except Exception as e:
        warn(f"Portable FFmpeg download notice: {e}")
    return False

def refresh_os_launchers_and_shortcuts(install_dir):
    info("Refreshing native launchers and system shortcuts...")
    try:
        sys.path.insert(0, install_dir)
        sys.path.insert(0, os.path.join(install_dir, "setupfiles"))

        if os.name == "nt":
            try:
                from setupfiles.pe_patcher import ensure_badwords_exe
                ensure_badwords_exe(install_dir)
            except Exception as e:
                warn(f"BadWords.exe generation notice: {e}")

        try:
            from setupfiles.setup import _create_os_shortcuts
            _create_os_shortcuts(install_dir, create_desktop=True, create_menu=True)
            info("OS shortcuts refreshed successfully.")
        except Exception as e:
            warn(f"Shortcuts refresh notice: {e}")
    except Exception as e:
        warn(f"Integration refresh notice: {e}")

def main():
    parser = argparse.ArgumentParser(description="BadWords Auto-Updater")
    parser.add_argument("--install-dir", required=False, help="Path to BadWords installation directory")
    parser.add_argument("--version", default="", help="Specific git tag/version to install (e.g. 4.0.0, v4.0.0)")
    parser.add_argument("--test-screenshot", default="", help="Save migration window screenshot to file and exit")
    parser.add_argument("--lang", default="", help="Language override for screenshot or test")
    parser.add_argument("--no-self-upgrade", action="store_true", help="Disable automatic updater self-upgrade")
    args = parser.parse_args()

    # ── Offscreen screenshot test helper ──
    if args.test_screenshot:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([sys.argv[0]])
        lang = args.lang if args.lang in MIGRATION_TEXTS else "pl"
        DialogClass = build_migration_dialog_class()
        dlg = DialogClass(lang=lang)
        dlg.show()
        app.processEvents()
        pix = dlg.grab()
        os.makedirs(os.path.dirname(os.path.abspath(args.test_screenshot)), exist_ok=True)
        ok = pix.save(args.test_screenshot)
        if ok:
            print(f"[TEST] Screenshot saved to: {args.test_screenshot}")
            sys.exit(0)
        else:
            print(f"[ERROR] Failed to save screenshot to: {args.test_screenshot}", file=sys.stderr)
            sys.exit(1)

    if not args.install_dir:
        err("--install-dir is required")
        sys.exit(1)

    install_dir = os.path.abspath(args.install_dir)
    if not os.path.isdir(install_dir) or not (
        os.path.isfile(os.path.join(install_dir, "main.py")) or 
        os.path.isfile(os.path.join(install_dir, "src", "main.py"))
    ):
        err(f"Valid BadWords installation not found at: {install_dir}")
        sys.exit(1)

    info(f"Target installation directory: {install_dir}")

    # 1. Updater self-upgrade check (TAGS, not releases)
    should_self_upgrade = not is_no_self_upgrade_configured(install_dir, getattr(args, 'no_self_upgrade', False))
    if should_self_upgrade:
        info("Checking latest git tag from repository for updater self-upgrade...")
        tag, _, source_repo = get_latest_tag()
        if tag:
            self_upgrade_if_needed(tag, install_dir=install_dir)
            sync_auxiliary_files(tag, install_dir)
    else:
        info("Updater self-upgrade skipped (--no-self-upgrade or developer configuration active).")

    # 2. Check target release for BadWords program update
    if getattr(args, 'version', None) and args.version.strip():
        rel_tag = args.version.strip()
        zip_url = f"https://github.com/veritus-git/BadWords/archive/refs/tags/{rel_tag}.zip"
        source_repo = "GitHub Tag"
        info(f"Target version explicitly requested: {rel_tag}")
    else:
        info("Checking latest release for BadWords update...")
        rel_tag, zip_url, source_repo = get_latest_release()
        if not rel_tag or not zip_url:
            warn("Could not determine latest release from GitHub/GitLab releases, falling back to latest tag...")
            rel_tag, zip_url, source_repo = get_latest_tag()

    if not rel_tag or not zip_url:
        err("Could not determine target version from GitHub or GitLab.")
        sys.exit(1)

    log(f"Target release: {rel_tag} (source: {source_repo})")

    # 3. Check installed version and 3.x -> 4.x transition
    current_ver_str = detect_installed_version(install_dir)
    curr_tuple = parse_version(current_ver_str)
    target_tuple = parse_version(rel_tag)
    info(f"Current version: {current_ver_str} -> Target version: {rel_tag}")

    is_v4_migration = (curr_tuple[0] < 4 and target_tuple[0] >= 4)
    if is_v4_migration:
        info("Detected migration from 3.x to 4.x. Attempting native installer upgrade...")
        tmp_inst_dir = tempfile.mkdtemp(prefix="bw_upd_inst_")
        if os.name == "nt":
            bin_name = "badwords-setup-windows.exe"
        elif sys.platform == "darwin":
            bin_name = "badwords-setup-macos"
        else:
            bin_name = "badwords-setup-linux"

        clean_tag = rel_tag.lstrip("vV")
        installer_candidates = [
            f"https://github.com/veritus-git/BadWords/releases/download/{clean_tag}/{bin_name}",
            f"https://github.com/veritus-git/BadWords/releases/download/v{clean_tag}/{bin_name}",
            f"https://github.com/veritus-git/BadWords/releases/latest/download/{bin_name}",
        ]
        inst_path = os.path.join(tmp_inst_dir, bin_name)
        inst_downloaded = False
        for i_url in installer_candidates:
            info(f"Downloading native installer for seamless migration: {i_url}")
            if download(i_url, inst_path):
                inst_downloaded = True
                break

        if inst_downloaded and os.path.isfile(inst_path):
            if os.name != "nt":
                os.chmod(inst_path, 0o755)
            info(f"Executing native installer in headless mode for {install_dir}...")
            r_inst = subprocess.run([inst_path, "--headless", "--install", install_dir], **_sp_hidden_kwargs())
            if r_inst.returncode == 0:
                log(f"BadWords updated to {rel_tag} successfully via native installer!")
                log("Please restart BadWords (close and relaunch from DaVinci Resolve or Desktop shortcut).")
                shutil.rmtree(tmp_inst_dir, ignore_errors=True)
                sys.exit(0)
            else:
                warn(f"Native installer headless returned code {r_inst.returncode}. Falling back to python source sync...")
        shutil.rmtree(tmp_inst_dir, ignore_errors=True)

    # 3. Download and extract
    tmp_dir = tempfile.mkdtemp(prefix="bw_update_")
    zip_path = os.path.join(tmp_dir, "repo.zip")

    info(f"Downloading source release from {source_repo}...")
    dl_ok = download(zip_url, zip_path)
    if not dl_ok:
        # Try alternate tag formatting (with or without leading 'v') and mirror
        alt_tag = rel_tag[1:] if (rel_tag.startswith("v") or rel_tag.startswith("V")) else f"v{rel_tag}"
        alt_urls = [
            f"https://github.com/veritus-git/BadWords/archive/refs/tags/{alt_tag}.zip",
            f"https://gitlab.com/badwords/BadWords/-/archive/{rel_tag}/BadWords-{rel_tag}.zip",
            f"https://gitlab.com/badwords/BadWords/-/archive/{alt_tag}/BadWords-{alt_tag}.zip",
        ]
        for a_url in alt_urls:
            info(f"Retrying download using candidate URL: {a_url}")
            if download(a_url, zip_path):
                dl_ok = True
                break
    if not dl_ok:
        err("Download failed.")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)

    info("Extracting...")
    import zipfile
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp_dir)
    except Exception as e:
        err(f"Extraction failed: {e}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)

    top_dirs = [d for d in os.listdir(tmp_dir) if os.path.isdir(os.path.join(tmp_dir, d)) and d not in ("__MACOSX",)]
    extracted_root = None
    for r in [tmp_dir] + [os.path.join(tmp_dir, d) for d in top_dirs]:
        if os.path.isdir(os.path.join(r, "src")) and os.path.isfile(os.path.join(r, "src", "main.py")):
            extracted_root = r
            break

    if not extracted_root:
        err("Extraction failed — src/main.py not found in archive.")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)

    source_path = os.path.join(extracted_root, "src")
    assets_path = os.path.join(extracted_root, "assets")
    setupfiles_path = os.path.join(extracted_root, "setupfiles")

    info("Resetting application files to clean state (preserving user data)...")
    protected_names = {
        "settings.json", "user.json", "pref.json", "dev.json", ".python_auto_installed",
        ".v4_migration_notified", ".no_self_upgrade", "models", "saves", "venv", "bin", "libs"
    }
    cur_script = os.path.abspath(__file__)
    if os.path.isdir(install_dir):
        for item in os.listdir(install_dir):
            if item.lower() in {p.lower() for p in protected_names}:
                continue
            full_path = os.path.join(install_dir, item)
            if os.path.abspath(full_path) == cur_script:
                continue
            try:
                if os.path.isdir(full_path) and not os.path.islink(full_path):
                    shutil.rmtree(full_path, ignore_errors=True)
                else:
                    os.remove(full_path)
            except Exception as e:
                log(f"Clean wipe warning: {e}")

    # Clean previous logs on every update so logs start fresh
    for _log_name in ["badwords_debug.log", "badwords.log", "badwords_setup.log", "setup.log"]:
        _lf = os.path.join(install_dir, _log_name)
        if os.path.isfile(_lf):
            try: os.remove(_lf)
            except Exception: pass

    info("Deploying fresh application files...")
    if os.path.isdir(source_path):
        shutil.copytree(source_path, install_dir, dirs_exist_ok=True)
    if os.path.isdir(assets_path):
        dest_assets = os.path.join(install_dir, "assets")
        shutil.copytree(assets_path, dest_assets, dirs_exist_ok=True)
    if os.path.isdir(setupfiles_path):
        dst_setupfiles = os.path.join(install_dir, "setupfiles")
        shutil.copytree(setupfiles_path, dst_setupfiles, dirs_exist_ok=True)
        up_py = os.path.join(setupfiles_path, "updater.py")
        if os.path.isfile(up_py):
            shutil.copy2(up_py, os.path.join(install_dir, "updater.py"))

    log("Application files deployed cleanly.")

    # Stamp .version file and sync app_constants
    clean_tag = rel_tag.lstrip("vV")
    try:
        with open(os.path.join(install_dir, ".version"), "w", encoding="utf-8") as f:
            f.write(f"{clean_tag}\n")
    except Exception as e:
        warn(f"Could not stamp .version file: {e}")

    # Remove stale bytecode caches
    info("Cleaning stale bytecode caches...")
    for root, dirs, files in os.walk(install_dir):
        if "venv" in root:
            continue
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)
        for f in files:
            if f.endswith(".pyc") or f.endswith(".pyo"):
                try: os.remove(os.path.join(root, f))
                except Exception: pass

    # Clean legacy v3 root files
    legacy_v3_files = [
        "BadWords_Launcher.py", "transcribe.py", "timeline.py", "silence.py",
        "audio.py", "BadWords.lua", "Badwords.py", "BadWords (Linux).py",
        "BadWords (Mac).py", "BadWords (macOS).py", "BadWords (Windows).py",
        "config.py", "gui.py", "interface.py", "whisper_net.py"
    ]
    for leg in legacy_v3_files:
        leg_p = os.path.join(install_dir, leg)
        if os.path.isfile(leg_p):
            try: os.remove(leg_p)
            except Exception: pass

    # 4. Pip upgrades & venv integrity check
    venv_dir = os.path.join(install_dir, "venv")
    if os.name == "nt":
        venv_py = os.path.join(venv_dir, "Scripts", "python.exe")
        venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        venv_py = os.path.join(venv_dir, "bin", "python3")
        if not os.path.isfile(venv_py):
            venv_py = os.path.join(venv_dir, "bin", "python")
        venv_pip = os.path.join(venv_dir, "bin", "pip")

    if os.path.isfile(venv_pip):
        info("Upgrading pip, setuptools & wheel...")
        subprocess.run([venv_pip, "install", "--upgrade", "pip", "setuptools", "wheel", "--quiet"], capture_output=True, **_sp_hidden_kwargs())

        info("Checking for legacy PyTorch installation...")
        torch_check = subprocess.run([venv_pip, "show", "torch"], capture_output=True, **_sp_hidden_kwargs())
        if torch_check.returncode == 0:
            info("Uninstalling legacy PyTorch to save disk space...")
            subprocess.run([venv_pip, "uninstall", "-y", "torch", "torchaudio"], capture_output=True, **_sp_hidden_kwargs())

        info("Upgrading core dependencies (faster-whisper, pypdf, PySide6)...")
        # av<19: PyAV 19 removed av.open(metadata_errors=...), which faster-whisper <= 1.2.1 still passes
        r = subprocess.run([venv_pip, "install", "--upgrade", "faster-whisper", "av<19", "pypdf", "PySide6"],
                           capture_output=True, text=True, **_sp_hidden_kwargs())
        for line in r.stdout.splitlines():
            if "Requirement already" not in line:
                info(line)
        if r.stderr:
            for line in r.stderr.splitlines():
                if "WARNING" in line or "ERROR" in line:
                    warn(line)

        # Hardware acceleration packages (NVIDIA CUDA 12)
        if detect_nvidia_gpu():
            info("NVIDIA GPU detected. Installing/upgrading CUDA 12 packages...")
            subprocess.run([venv_pip, "install", "--upgrade", "nvidia-cublas-cu12", "nvidia-cudnn-cu12"], capture_output=True, **_sp_hidden_kwargs())
            info("CUDA 12 acceleration libraries ready.")

        # Apple Silicon GPU engine (mlx-whisper), without PyTorch (only its model converter needs torch)
        import platform
        if sys.platform == "darwin" and platform.machine() == "arm64":
            info("Apple Silicon detected. Installing/upgrading the Apple GPU engine (MLX)...")
            r1 = subprocess.run([venv_pip, "install", "--upgrade", "--no-deps", "mlx-whisper"], capture_output=True, **_sp_hidden_kwargs())
            r2 = subprocess.run([venv_pip, "install", "--upgrade", "mlx", "numba", "scipy", "tiktoken",
                                 "more-itertools", "tqdm", "huggingface_hub"], capture_output=True, **_sp_hidden_kwargs())
            if r1.returncode == 0 and r2.returncode == 0:
                info("Apple GPU engine ready.")
            else:
                warn("Apple GPU engine could not be installed. Transcription will use the CPU.")

        # Verify environment integrity
        info("Verifying Python packages integrity...")
        test_cmd = [venv_py, "-c", "import PySide6, faster_whisper, pypdf; print('OK')"]
        verify_res = subprocess.run(test_cmd, capture_output=True, text=True, **_sp_hidden_kwargs())
        if verify_res.returncode != 0:
            warn(f"Integrity check notice: {verify_res.stderr.strip() if verify_res.stderr else 'missing modules'}. Running automatic repair...")
            subprocess.run([venv_pip, "install", "--upgrade", "--force-reinstall", "faster-whisper", "av<19", "pypdf", "PySide6"],
                           capture_output=True, **_sp_hidden_kwargs())
            info("Auto-repair completed.")

        log("Python packages verified and ready.")
    else:
        warn("venv pip not found — skipping package upgrade.")

    # 5. FFmpeg
    bin_dir = os.path.join(install_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    ensure_ffmpeg(bin_dir)

    # 6. Refresh libs link
    info("Refreshing libs symlink...")
    libs_link = os.path.join(install_dir, "libs")
    lib_root = os.path.join(venv_dir, "Lib" if os.name == "nt" else "lib")
    site_pkgs = None
    if os.path.isdir(lib_root):
        for root, dirs, _ in os.walk(lib_root):
            if "site-packages" in dirs:
                site_pkgs = os.path.join(root, "site-packages")
                break

    if site_pkgs:
        if os.path.islink(libs_link) or os.path.isdir(libs_link):
            try: os.remove(libs_link)
            except Exception: shutil.rmtree(libs_link, ignore_errors=True)

        if os.name == "nt":
            subprocess.run(f'mklink /J "{libs_link}" "{site_pkgs}"', shell=True, capture_output=True, **_sp_hidden_kwargs())
        else:
            try: os.symlink(site_pkgs, libs_link, target_is_directory=True)
            except Exception: pass

    # 7. Update DaVinci Resolve wrappers
    deploy_davinci_wrappers(install_dir)

    # 8. Refresh OS launchers and shortcuts
    refresh_os_launchers_and_shortcuts(install_dir)

    # Cleanup
    shutil.rmtree(tmp_dir, ignore_errors=True)
    log(f"BadWords updated to {tag} successfully!")
    log("Please restart BadWords (close and relaunch from DaVinci Resolve or Desktop shortcut).")

    # 9. Milestone notice for 3.x -> 4.x migration (post-update)
    if is_v4_migration and not is_v4_migration_already_notified(install_dir):
        user_lang = args.lang or get_ui_language(install_dir)
        info(f"Migration from 3.x to 4.x complete. Displaying milestone notice ({user_lang})...")
        prompt_v4_migration_notice(install_dir, lang=user_lang)
        mark_v4_migration_notified(install_dir)


if __name__ == "__main__":
    main()
