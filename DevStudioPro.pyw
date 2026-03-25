#!/usr/bin/env python3
"""
DevStudio Pro — IDE Python  +  Builder Mods Minecraft
=====================================================
• Éditeur multi-onglets (Python / Java / Groovy-Gradle / JSON / YAML…)
• Numéros de ligne, repli class/def, surbrillance ligne courante
• Explorateur de fichiers avec menu contextuel
• Terminal intégré avec logs colorés

── Mode 🐍 Python ──────────────────────────────────────────────
  • Exécution directe, arguments CLI
  • Injection automatique des dépendances pip dans le code
  • Build EXE via PyInstaller (canal dev / stable)
  • Serveur de MàJ local (HTTP)
  • Promotion dev → stable + push GitHub + Release

── Mode ⛏ Minecraft ──────────────────────────────────────────
  • Choix du loader : Forge / NeoForge / Fabric / Quilt
  • Choix de la version MC (per-loader)
  • JDK auto-téléchargé dans <projet>/.jdk/ sans droits admin (Java 8/17/21)
  • Compilation gradlew build + logs temps réel
  • Clean, ouverture build/libs/

── Onglet 🐙 GitHub (commun) ──────────────────────────────────
  • git status / add / commit / push
  • Création de tag + Release GitHub (API)
  • Attach automatique du .jar (mods) ou .exe (Python)

── Onglet 🎮 Instances Minecraft ──────────────────────────────
  • Création d'instances isolées (Vanilla/Forge/NeoForge/Fabric/Quilt)
  • Installation automatique : client MC + librairies + assets + loader
  • JDK auto-téléchargé si absent (Java 8/17/21 selon la version)
  • Mode OFFLINE total — aucun compte Mojang requis
  • Copie automatique du mod compilé dans chaque instance
  • Lancement solo (singleplayer) en mode hors-ligne
  • Serveur local dédié (LAN/multijoueur) — online-mode=false
  • Réutilisation des assets d'une install .minecraft existante
"""

# ── Bootstrap : installation automatique de PyQt6 ───────────────────────────
import sys as _b_sys, subprocess as _b_sub, importlib.util as _b_ilu
if not getattr(_b_sys, "frozen", False):
    def _b_ensure(pkg, import_as=None):
        name = import_as or pkg.replace("-","_").replace(".","_")
        if _b_ilu.find_spec(name) is None:
            print(f"[DevStudio Pro] Installation de {pkg}...", flush=True)
            _b_sub.check_call([_b_sys.executable, "-m", "pip", "install", "--upgrade", pkg])
    _b_ensure("PyQt6")
    del _b_ensure
del _b_sub, _b_ilu

# ── Logger de démarrage ───────────────────────────────────────────────────────
import os as _os, sys as _sys_boot, platform as _platform_boot, traceback as _tb
from pathlib import Path as _Path
from datetime import datetime as _dt

def _get_log_dir() -> _Path:
    s = _platform_boot.system()
    home = _Path.home()
    if s == "Windows":
        return _Path(_os.environ.get("USERPROFILE", str(home))) / "AppData" / "Roaming" / "FFS" / "DevStudio" / "logs"
    elif s == "Darwin":
        return home / "Library" / "Application Support" / "FFS" / "DevStudio" / "logs"
    else:
        xdg = _Path(_os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share")))
        return xdg / "FFS" / "DevStudio" / "logs"

_log_dir = _get_log_dir(); _log_dir.mkdir(parents=True, exist_ok=True)
_session_ts = _dt.now().strftime("%Y-%m-%d_%H-%M-%S")
_log_path   = _log_dir / f"{_session_ts}.log"
_startup_log = open(_log_path, "w", encoding="utf-8", buffering=1)
_startup_log.write(
    f"DevStudio Pro — session {_dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    f"Python : {_sys_boot.executable}\nOS : {_platform_boot.system()} {_platform_boot.release()}\n"
    + "="*60 + "\n"
)

class _TeeStream:
    def __init__(self, orig, log):
        self._orig = orig; self._log = log
    def write(self, msg):
        try: self._orig and self._orig.write(msg)
        except: pass
        try: self._log.write(msg); self._log.flush()
        except: pass
    def flush(self):
        try: self._orig and self._orig.flush()
        except: pass
    def fileno(self):
        if self._orig:
            try: return self._orig.fileno()
            except: pass
        raise OSError("no fileno")

_sys_boot.stderr = _TeeStream(_sys_boot.stderr, _startup_log)
def _global_excepthook(t, v, tb):
    msg = "".join(_tb.format_exception(t, v, tb))
    _startup_log.write(f"[CRASH] {msg}\n"); _startup_log.flush()
    _sys_boot.__excepthook__(t, v, tb)
_sys_boot.excepthook = _global_excepthook

# ── Imports ───────────────────────────────────────────────────────────────────
import sys, os, re, json, ast as _ast, subprocess, threading, time
import platform, urllib.request, urllib.error, zipfile, tarfile, shutil, queue as _queue
from pathlib import Path
from typing import Optional
from datetime import datetime

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore  import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt6.QtGui   import (QColor, QFont, QTextCharFormat, QSyntaxHighlighter,
                            QPainter, QFontMetrics, QTextCursor, QPalette,
                            QKeySequence, QAction, QFontMetricsF)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QTabWidget,
    QPlainTextEdit, QTreeView, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QGroupBox, QToolBar, QStatusBar, QFileDialog,
    QMessageBox, QInputDialog, QLineEdit, QComboBox, QCheckBox,
    QTextEdit, QMenu, QSpinBox, QDialog, QDialogButtonBox, QProgressBar,
    QScrollArea, QFrame,
)
try:
    from PyQt6.QtWidgets import QFileSystemModel
except ImportError:
    from PyQt6.QtGui import QFileSystemModel  # type: ignore

IS_WIN = platform.system() == "Windows"
JAVA_EXE = "java.exe" if IS_WIN else "java"

# ════════════════════════════════════════════════════════════════
#  MINECRAFT : LOADERS / VERSIONS / JDK
# ════════════════════════════════════════════════════════════════

MC_LOADERS: dict[str, dict[str, dict]] = {
    "Forge": {
        "1.7.10": {"java": 8},  "1.12.2": {"java": 8},
        "1.16.5": {"java": 8},  "1.18.2": {"java": 17},
        "1.19.2": {"java": 17}, "1.19.4": {"java": 17},
        "1.20.1": {"java": 17}, "1.20.4": {"java": 17},
    },
    "NeoForge": {
        "1.20.4": {"java": 17}, "1.21.1": {"java": 21},
        "1.21.4": {"java": 21},
    },
    "Fabric": {
        "1.20.1": {"java": 17}, "1.20.6": {"java": 21},
        "1.21.1": {"java": 21}, "1.21.4": {"java": 21},
    },
    "Quilt": {
        "1.20.1": {"java": 17}, "1.21.1": {"java": 21},
    },
}

_T8  = "jdk8u402-b06"
_T17 = "jdk-17.0.10%2B7"
_T21 = "jdk-21.0.2%2B13"
_A8  = f"https://github.com/adoptium/temurin8-binaries/releases/download/{_T8}"
_A17 = f"https://github.com/adoptium/temurin17-binaries/releases/download/{_T17}"
_A21 = f"https://github.com/adoptium/temurin21-binaries/releases/download/{_T21}"

JDK_URLS: dict[int, dict[tuple, str]] = {
    8: {
        ("Windows","AMD64"):  f"{_A8}/OpenJDK8U-jdk_x64_windows_hotspot_8u402b06.zip",
        ("Windows","x86_64"): f"{_A8}/OpenJDK8U-jdk_x64_windows_hotspot_8u402b06.zip",
        ("Linux","x86_64"):   f"{_A8}/OpenJDK8U-jdk_x64_linux_hotspot_8u402b06.tar.gz",
        ("Darwin","x86_64"):  f"{_A8}/OpenJDK8U-jdk_x64_mac_hotspot_8u402b06.tar.gz",
        ("Darwin","arm64"):   f"{_A8}/OpenJDK8U-jdk_aarch64_mac_hotspot_8u402b06.tar.gz",
    },
    17: {
        ("Windows","AMD64"):  f"{_A17}/OpenJDK17U-jdk_x64_windows_hotspot_17.0.10_7.zip",
        ("Windows","x86_64"): f"{_A17}/OpenJDK17U-jdk_x64_windows_hotspot_17.0.10_7.zip",
        ("Linux","x86_64"):   f"{_A17}/OpenJDK17U-jdk_x64_linux_hotspot_17.0.10_7.tar.gz",
        ("Darwin","x86_64"):  f"{_A17}/OpenJDK17U-jdk_x64_mac_hotspot_17.0.10_7.tar.gz",
        ("Darwin","arm64"):   f"{_A17}/OpenJDK17U-jdk_aarch64_mac_hotspot_17.0.10_7.tar.gz",
    },
    21: {
        ("Windows","AMD64"):  f"{_A21}/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip",
        ("Windows","x86_64"): f"{_A21}/OpenJDK21U-jdk_x64_windows_hotspot_21.0.2_13.zip",
        ("Linux","x86_64"):   f"{_A21}/OpenJDK21U-jdk_x64_linux_hotspot_21.0.2_13.tar.gz",
        ("Darwin","x86_64"):  f"{_A21}/OpenJDK21U-jdk_x64_mac_hotspot_21.0.2_13.tar.gz",
        ("Darwin","arm64"):   f"{_A21}/OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.2_13.tar.gz",
    },
}

def get_app_dir() -> Path:
    """
    Dossier applicatif DevStudio Pro — même logique que le run.bat/run.sh.
      Windows : %USERPROFILE%\\AppData\\Roaming\\FFS\\DevStudio
      macOS   : ~/Library/Application Support/FFS/DevStudio
      Linux   : $XDG_DATA_HOME/FFS/DevStudio  (~/.local/share/FFS/DevStudio)
    """
    home = Path.home()
    s = platform.system()
    if s == "Windows":
        return Path(os.environ.get("USERPROFILE", str(home))) / "AppData" / "Roaming" / "FFS" / "DevStudio"
    elif s == "Darwin":
        return home / "Library" / "Application Support" / "FFS" / "DevStudio"
    else:
        xdg = Path(os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share")))
        return xdg / "FFS" / "DevStudio"

def get_jdk_dir() -> Path:
    """Dossier partagé des JDK : <app_dir>/jdk/jdk<ver>/"""
    return get_app_dir() / "jdk"

def get_mdk_dir() -> Path:
    """Dossier des MDK téléchargés : <app_dir>/mdk/<loader>/<mc_version>/"""
    return get_app_dir() / "mdk"

def get_jdk_url(java_ver: int) -> Optional[str]:
    return JDK_URLS.get(java_ver, {}).get((platform.system(), platform.machine()))

def _scan_jdk_dir(base: Path) -> Optional[Path]:
    """Retourne le JAVA_HOME si un JDK est extrait dans `base`."""
    if not base.exists():
        return None
    for item in sorted(base.iterdir()):
        if not item.is_dir(): continue
        for cand in [item / "bin" / JAVA_EXE,
                     item / "Contents" / "Home" / "bin" / JAVA_EXE]:
            if cand.exists():
                return cand.parent.parent
    return None

def find_app_jdk(java_ver: int) -> Optional[Path]:
    """Cherche un JDK dans le dossier partagé de l'application."""
    return _scan_jdk_dir(get_jdk_dir() / f"jdk{java_ver}")

def find_local_jdk(project_path: Path, java_ver: int) -> Optional[Path]:
    """
    Cherche un JDK dans l'ordre :
      1. Dossier app  : <app_dir>/jdk/jdk<ver>/
      2. Dossier projet (héritage ancienne version) : <projet>/.jdk/jdk<ver>/
    """
    jdk = find_app_jdk(java_ver)
    if jdk:
        return jdk
    # Fallback : ancien emplacement projet (rétro-compat)
    return _scan_jdk_dir(project_path / ".jdk" / f"jdk{java_ver}")

def detect_system_java(java_ver: int) -> Optional[Path]:
    """Vérifie si le java système est de la bonne version majeure."""
    try:
        r = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
        out = r.stderr + r.stdout
        if f'"{java_ver}.' in out or f'"{java_ver}"' in out or f' {java_ver}.' in out:
            jb = shutil.which("java")
            return Path(jb).parent.parent if jb else None
    except Exception:
        pass
    return None

# ════════════════════════════════════════════════════════════════
#  THÈME SOMBRE (Catppuccin Mocha)
# ════════════════════════════════════════════════════════════════

DARK = {
    "bg":        "#1e1e2e", "bg2":    "#181825", "bg3":      "#313244",
    "border":    "#45475a", "text":   "#cdd6f4", "text_dim": "#6c7086",
    "accent":    "#89b4fa", "accent2":"#cba6f7", "green":    "#a6e3a1",
    "yellow":    "#f9e2af", "red":    "#f38ba8", "orange":   "#fab387",
    "teal":      "#94e2d5", "pink":   "#f5c2e7",
    "editor_bg": "#1e1e2e", "gutter_bg":"#181825", "gutter_fg":"#45475a",
    "sel":       "#313244", "line_hi":"#262637",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background:{DARK['bg']}; color:{DARK['text']};
    font-family:'Segoe UI','SF Pro Display','Ubuntu',sans-serif; font-size:13px;
}}
QSplitter::handle {{ background:{DARK['border']}; width:1px; height:1px; }}
QTabWidget::pane {{ border:1px solid {DARK['border']}; background:{DARK['bg']}; }}
QTabBar::tab {{
    background:{DARK['bg2']}; color:{DARK['text_dim']};
    padding:6px 16px; border:none; border-right:1px solid {DARK['border']};
}}
QTabBar::tab:selected {{ background:{DARK['bg']}; color:{DARK['text']}; border-top:2px solid {DARK['accent']}; }}
QTabBar::tab:hover {{ background:{DARK['bg3']}; color:{DARK['text']}; }}
QPlainTextEdit, QTextEdit {{
    background:{DARK['editor_bg']}; color:{DARK['text']}; border:none;
    selection-background-color:{DARK['sel']};
    font-family:'Cascadia Code','JetBrains Mono','Fira Code','Consolas',monospace; font-size:13px;
}}
QTreeView {{
    background:{DARK['bg2']}; color:{DARK['text']}; border:none; font-size:12px;
}}
QTreeView::item:selected {{ background:{DARK['accent']}; color:{DARK['bg']}; }}
QTreeView::item:hover {{ background:{DARK['bg3']}; }}
QPushButton {{
    background:{DARK['bg3']}; color:{DARK['text']};
    border:1px solid {DARK['border']}; border-radius:4px; padding:5px 12px;
}}
QPushButton:hover {{ background:{DARK['accent']}; color:{DARK['bg']}; border-color:{DARK['accent']}; }}
QPushButton:pressed {{ background:{DARK['accent2']}; }}
QPushButton:disabled {{ color:{DARK['text_dim']}; background:{DARK['bg2']}; }}
QPushButton#run_btn {{ background:{DARK['green']}; color:{DARK['bg']}; font-weight:bold; border:none; }}
QPushButton#run_btn:hover {{ background:#b9f0b3; }}
QPushButton#stop_btn {{ background:{DARK['red']}; color:{DARK['bg']}; font-weight:bold; border:none; }}
QPushButton#build_btn {{ background:{DARK['teal']}; color:{DARK['bg']}; font-weight:bold; border:none; }}
QPushButton#build_btn:hover {{ background:#adf5eb; }}
QPushButton#promote_btn {{
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {DARK['accent']},stop:1 {DARK['accent2']});
    color:{DARK['bg']}; font-weight:bold; border:none; border-radius:4px; padding:7px 16px;
}}
QPushButton#gh_btn {{
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #333,stop:1 #555);
    color:#fff; font-weight:bold; border:none; border-radius:4px; padding:6px 14px;
}}
QPushButton#gh_btn:hover {{ background:#555; }}
QGroupBox {{
    border:1px solid {DARK['border']}; border-radius:4px;
    margin-top:8px; padding-top:8px; font-size:11px; color:{DARK['text_dim']};
}}
QGroupBox::title {{ subcontrol-origin:margin; left:8px; padding:0 4px; }}
QLineEdit, QSpinBox, QComboBox {{
    background:{DARK['bg2']}; color:{DARK['text']};
    border:1px solid {DARK['border']}; border-radius:3px; padding:4px 8px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color:{DARK['accent']}; }}
QComboBox::drop-down {{ border:none; }}
QComboBox QAbstractItemView {{ background:{DARK['bg2']}; color:{DARK['text']}; border:1px solid {DARK['border']}; }}
QScrollBar:vertical {{ background:{DARK['bg2']}; width:8px; border:none; }}
QScrollBar::handle:vertical {{ background:{DARK['border']}; border-radius:4px; min-height:30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0px; }}
QScrollBar:horizontal {{ background:{DARK['bg2']}; height:8px; border:none; }}
QScrollBar::handle:horizontal {{ background:{DARK['border']}; border-radius:4px; min-width:30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0px; }}
QToolBar {{ background:{DARK['bg2']}; border-bottom:1px solid {DARK['border']}; spacing:4px; padding:3px; }}
QStatusBar {{ background:{DARK['bg2']}; border-top:1px solid {DARK['border']}; font-size:11px; }}
QMenu {{ background:{DARK['bg2']}; color:{DARK['text']}; border:1px solid {DARK['border']}; }}
QMenu::item:selected {{ background:{DARK['accent']}; color:{DARK['bg']}; }}
QCheckBox {{ color:{DARK['text']}; spacing:6px; }}
QLabel#section_title {{ color:{DARK['accent']}; font-weight:bold; font-size:11px; letter-spacing:1px; }}
QLabel#jdk_ok {{ color:{DARK['green']}; font-size:11px; }}
QLabel#jdk_warn {{ color:{DARK['yellow']}; font-size:11px; }}
QProgressBar {{
    border:1px solid {DARK['border']}; border-radius:3px;
    background:{DARK['bg2']}; color:{DARK['text']}; text-align:center;
}}
QProgressBar::chunk {{ background:{DARK['accent']}; border-radius:2px; }}
"""

# ════════════════════════════════════════════════════════════════
#  MOTEUR D'INJECTION DE DÉPENDANCES (Python)
# ════════════════════════════════════════════════════════════════

_DS_GUARD_START = "# ── DevStudio:deps:start ──"
_DS_GUARD_END   = "# ── DevStudio:deps:end ──"

_STDLIB = frozenset({
    "__future__","_thread","abc","aifc","argparse","array","ast","asynchat","asyncio",
    "asyncore","atexit","base64","bdb","binascii","bisect","builtins","bz2","calendar",
    "cgi","chunk","cmath","cmd","code","codecs","codeop","colorsys","compileall",
    "concurrent","configparser","contextlib","contextvars","copy","copyreg","cProfile",
    "csv","ctypes","curses","dataclasses","datetime","dbm","decimal","difflib","dis",
    "doctest","email","encodings","enum","errno","faulthandler","fcntl","filecmp",
    "fileinput","fnmatch","fractions","ftplib","functools","gc","getopt","getpass",
    "gettext","glob","grp","gzip","hashlib","heapq","hmac","html","http","idlelib",
    "imaplib","imghdr","imp","importlib","inspect","io","ipaddress","itertools","json",
    "keyword","linecache","locale","logging","lzma","mailbox","math","mimetypes","mmap",
    "modulefinder","multiprocessing","netrc","numbers","operator","optparse","os",
    "pathlib","pdb","pickle","pickletools","pkgutil","platform","plistlib","poplib",
    "posix","posixpath","pprint","profile","pstats","pty","pwd","py_compile","pyclbr",
    "pydoc","queue","quopri","random","re","readline","reprlib","resource","rlcompleter",
    "runpy","sched","secrets","select","selectors","shelve","shlex","shutil","signal",
    "site","smtplib","sndhdr","socket","socketserver","sqlite3","ssl","stat","statistics",
    "string","stringprep","struct","subprocess","sunau","symtable","sys","sysconfig",
    "syslog","tabnanny","tarfile","telnetlib","tempfile","termios","test","textwrap",
    "threading","time","timeit","tkinter","token","tokenize","tomllib","trace","traceback",
    "tracemalloc","tty","turtle","types","typing","unicodedata","unittest","urllib","uuid",
    "venv","warnings","wave","weakref","webbrowser","winreg","winsound","wsgiref","xdrlib",
    "xml","xmlrpc","zipapp","zipfile","zipimport","zlib","zoneinfo",
    "_collections_abc","_io","_weakrefset","abc","builtins","PyQt6",
})

_IMPORT_TO_PIP: dict[str, str] = {
    "cv2":"opencv-python","PIL":"Pillow","skimage":"scikit-image","sklearn":"scikit-learn",
    "numpy":"numpy","np":"numpy","pandas":"pandas","pd":"pandas","scipy":"scipy",
    "matplotlib":"matplotlib","plt":"matplotlib","seaborn":"seaborn","plotly":"plotly",
    "tensorflow":"tensorflow","tf":"tensorflow","keras":"keras","torch":"torch",
    "torchvision":"torchvision","transformers":"transformers","openai":"openai",
    "anthropic":"anthropic","langchain":"langchain","requests":"requests","httpx":"httpx",
    "aiohttp":"aiohttp","flask":"flask","Flask":"flask","fastapi":"fastapi",
    "django":"Django","starlette":"starlette","uvicorn":"uvicorn",
    "websockets":"websockets","bs4":"beautifulsoup4","lxml":"lxml","scrapy":"Scrapy",
    "paramiko":"paramiko","pydantic":"pydantic","dotenv":"python-dotenv",
    "pygame":"pygame","pyglet":"pyglet","pydub":"pydub","sounddevice":"sounddevice",
    "mutagen":"mutagen","yt_dlp":"yt-dlp","sqlalchemy":"SQLAlchemy","alembic":"alembic",
    "pymongo":"pymongo","redis":"redis","psycopg2":"psycopg2-binary","pymysql":"PyMySQL",
    "click":"click","rich":"rich","typer":"typer","tqdm":"tqdm","colorama":"colorama",
    "tabulate":"tabulate","prompt_toolkit":"prompt-toolkit","yaml":"PyYAML","toml":"toml",
    "dateutil":"python-dateutil","arrow":"arrow","attrs":"attrs","marshmallow":"marshmallow",
    "cryptography":"cryptography","Crypto":"pycryptodome","jwt":"PyJWT","bcrypt":"bcrypt",
    "pytest":"pytest","faker":"Faker","boto3":"boto3","stripe":"stripe","twilio":"twilio",
    "musicbrainzngs":"musicbrainzngs","spacy":"spacy","nltk":"nltk","numba":"numba",
    "dask":"dask","polars":"polars","pyarrow":"pyarrow","h5py":"h5py","sympy":"sympy",
    "networkx":"networkx","win32api":"pywin32","win32con":"pywin32","pythoncom":"pywin32",
    "pynput":"pynput","pyautogui":"pyautogui","keyboard":"keyboard","mouse":"mouse",
}

_DS_GUARD_TEMPLATE = """{start}
import sys as _ds_sys, subprocess as _ds_sub
if not getattr(_ds_sys, "frozen", False):
    import importlib.util as _ds_ilu
    def _ds_ensure(*_pkgs):
        for _p in _pkgs:
            _mod = _p.split("[")[0].replace("-","_").replace(".","_")
            _remap = {{"opencv-python":"cv2","Pillow":"PIL","scikit-learn":"sklearn",
                       "PyYAML":"yaml","beautifulsoup4":"bs4","yt-dlp":"yt_dlp",
                       "SQLAlchemy":"sqlalchemy","pywin32":"win32api"}}
            _ok = any(_ds_ilu.find_spec(_c) is not None
                      for _c in ([_remap[_p], _mod] if _p in _remap else [_mod]))
            if not _ok:
                print(f"[DevStudio Pro] Installation de {{_p}}...", flush=True)
                _ds_sub.check_call([_ds_sys.executable,"-m","pip","install","--upgrade",_p],
                                   stdout=_ds_sub.DEVNULL, stderr=_ds_sub.PIPE)
            else:
                _ds_sub.run([_ds_sys.executable,"-m","pip","install","--upgrade","--quiet",_p],
                            stdout=_ds_sub.DEVNULL, stderr=_ds_sub.DEVNULL)
    _ds_ensure({packages})
    del _ds_ensure, _ds_ilu
del _ds_sys, _ds_sub
{end}
"""

def _top_level_module(name: str) -> str:
    return name.split(".")[0] if name else ""

def scan_third_party_imports(code: str) -> list[str]:
    try:
        tree = _ast.parse(code)
    except SyntaxError:
        found = set()
        for m in re.finditer(r'^(?:import|from)\s+([\w.]+)', code, re.MULTILINE):
            mod = _top_level_module(m.group(1))
            if mod and mod not in _STDLIB and not mod.startswith("_"):
                found.add(_IMPORT_TO_PIP.get(mod, mod))
        return sorted(found)

    mods: set[str] = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for a in node.names: mods.add(_top_level_module(a.name))
        elif isinstance(node, _ast.ImportFrom):
            if node.module: mods.add(_top_level_module(node.module))

    result = set()
    for mod in mods:
        if (not mod or mod.startswith("_") or mod in _STDLIB or
                mod.lower() in {"__main__","config","utils","helpers","settings","constants","models","views"}):
            continue
        result.add(_IMPORT_TO_PIP.get(mod, mod))
    return sorted(result)

def build_deps_block(packages: list[str]) -> str:
    if not packages: return ""
    pkg_args = ", ".join(f'"{p}"' for p in packages)
    return _DS_GUARD_TEMPLATE.format(start=_DS_GUARD_START, end=_DS_GUARD_END, packages=pkg_args)

def inject_deps_into_code(code: str, packages: list[str]) -> tuple[str, bool]:
    def _remove(c):
        si = c.find(_DS_GUARD_START); ei = c.find(_DS_GUARD_END)
        if si == -1 or ei == -1: return c
        ei += len(_DS_GUARD_END)
        if ei < len(c) and c[ei] == "\n": ei += 1
        return c[:si] + c[ei:]
    def _insert(c, block):
        lines = c.splitlines(keepends=True); insert = 0; i = 0
        while i < len(lines) and i < 3:
            s = lines[i].lstrip()
            if s.startswith("#!") or re.match(r"#.*coding", s):
                i += 1; insert = i
            else: break
        rest = "".join(lines[i:])
        try:
            tree2 = _ast.parse(rest)
            if (tree2.body and isinstance(tree2.body[0], _ast.Expr)
                    and isinstance(tree2.body[0].value, _ast.Constant)
                    and isinstance(tree2.body[0].value.value, str)):
                insert = i + tree2.body[0].end_lineno
        except: pass
        lines.insert(insert, block + ("\n" if not block.endswith("\n") else ""))
        return "".join(lines)
    if not packages:
        if _DS_GUARD_START in code:
            return _remove(code), True
        return code, False
    new_block = build_deps_block(packages)
    if _DS_GUARD_START in code:
        old = code; code = _insert(_remove(code), new_block)
        return code, code != old
    return _insert(code, new_block), True

# ════════════════════════════════════════════════════════════════
#  COLORATIONS SYNTAXIQUES
# ════════════════════════════════════════════════════════════════

def _fmt(color: str, bold=False, italic=False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:   f.setFontWeight(QFont.Weight.Bold)
    if italic: f.setFontItalic(True)
    return f

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        kw = _fmt(DARK["accent"], bold=True)
        builtin = _fmt(DARK["accent2"])
        self._rules = [
            (re.compile(r'\b(False|None|True|and|as|assert|async|await|break|class|'
                        r'continue|def|del|elif|else|except|finally|for|from|global|'
                        r'if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|'
                        r'try|while|with|yield)\b'), kw),
            (re.compile(r'\b(abs|all|any|bin|bool|bytes|callable|chr|dict|dir|divmod|'
                        r'enumerate|eval|exec|filter|float|format|frozenset|getattr|'
                        r'globals|hasattr|hash|help|hex|id|input|int|isinstance|issubclass|'
                        r'iter|len|list|locals|map|max|min|next|object|oct|open|ord|pow|'
                        r'print|property|range|repr|reversed|round|set|setattr|slice|'
                        r'sorted|staticmethod|str|sum|super|tuple|type|vars|zip)\b'), builtin),
            (re.compile(r'@\w+'), _fmt(DARK["yellow"])),
            (re.compile(r'\b\d+\.?\d*([eE][+-]?\d+)?[jJ]?\b'), _fmt(DARK["orange"])),
            (re.compile(r'\b0x[0-9a-fA-F]+\b'), _fmt(DARK["orange"])),
            (re.compile(r'f"[^"\\]*(?:\\.[^"\\]*)*"'), _fmt(DARK["green"])),
            (re.compile(r"f'[^'\\]*(?:\\.[^'\\]*)*'"), _fmt(DARK["green"])),
            (re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), _fmt(DARK["green"])),
            (re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), _fmt(DARK["green"])),
            (re.compile(r'#[^\n]*'), _fmt(DARK["text_dim"], italic=True)),
            (re.compile(r'\b(self|cls)\b'), _fmt(DARK["orange"])),
            (re.compile(r'\b(def|class)\s+(\w+)'), None),
        ]
        self._fn_fmt    = _fmt(DARK["accent2"], bold=True)
        self._class_fmt = _fmt(DARK["yellow"],  bold=True)

    def highlightBlock(self, text: str):
        # Triple-quotes en premier — deux états distincts (1=double, 2=simple)
        ml_ranges: list[tuple[int,int]] = []
        ml_green = _fmt(DARK["green"])
        self.setCurrentBlockState(0)
        for delim, sid in [('"""', 1), ("'''", 2)]:
            self._hl_ml(text, delim, sid, ml_green, ml_ranges)

        def _in_ml(pos: int, length: int) -> bool:
            e = pos + length
            return any(s <= pos and e <= en for s, en in ml_ranges)

        for pattern, fmt in self._rules:
            if fmt is None:
                for m in pattern.finditer(text):
                    if not _in_ml(m.start(2), len(m.group(2))):
                        kw_name = m.group(1)
                        self.setFormat(m.start(2), len(m.group(2)),
                                       self._class_fmt if kw_name == "class" else self._fn_fmt)
            else:
                for m in pattern.finditer(text):
                    if not _in_ml(m.start(), m.end()-m.start()):
                        self.setFormat(m.start(), m.end()-m.start(), fmt)

    def _hl_ml(self, text, delim, state_id, fmt, ranges_out=None):
        prev = self.previousBlockState()
        in_this = (prev == state_id)
        if in_this:
            start = 0; add = 0
        else:
            # Si on est dans l'AUTRE délimiteur, ne pas toucher l'état
            if prev in (1, 2):
                return
            start = text.find(delim)
            add   = len(delim)
        if start == -1:
            # Pas dans ce bloc et pas trouvé sur cette ligne : ne pas reset l'état
            # (évite d'écraser l'état positionné par l'autre délimiteur)
            return
        while start >= 0:
            end = text.find(delim, start + add)
            if end == -1:
                self.setCurrentBlockState(state_id)
                length = len(text) - start
                self.setFormat(start, length, fmt)
                if ranges_out is not None: ranges_out.append((start, start + length))
                break
            else:
                self.setCurrentBlockState(0)
                length = end - start + len(delim)
                self.setFormat(start, length, fmt)
                if ranges_out is not None: ranges_out.append((start, start + length))
                start = text.find(delim, end + len(delim))
                add   = len(delim)



class JavaHighlighter(QSyntaxHighlighter):
    _KEYWORDS = (
        "abstract assert boolean break byte case catch char class const continue default "
        "do double else enum extends final finally float for goto if implements import "
        "instanceof int interface long native new package private protected public return "
        "short static strictfp super switch synchronized this throw throws transient try "
        "void volatile while true false null var record sealed permits"
    ).split()

    def __init__(self, doc):
        super().__init__(doc)
        kw = _fmt(DARK["accent"], bold=True)
        self._rules = []
        for w in self._KEYWORDS:
            self._rules.append((re.compile(r'\b'+w+r'\b'), kw))
        self._rules += [
            (re.compile(r'@\w+'),                            _fmt(DARK["yellow"])),
            (re.compile(r'"(?:[^"\\]|\\.)*"'),               _fmt(DARK["green"])),
            (re.compile(r"'(?:[^'\\]|\\.)*'"),               _fmt(DARK["green"])),
            (re.compile(r'\b\d+\.?\d*[fFdDlL]?\b'),         _fmt(DARK["orange"])),
            (re.compile(r'//[^\n]*'),                        _fmt(DARK["text_dim"], italic=True)),
            (re.compile(r'\b([A-Z][a-zA-Z0-9_]*)\b'),       _fmt(DARK["teal"])),
        ]
        self._ml_fmt   = _fmt(DARK["text_dim"], italic=True)
        self._ml_start = re.compile(r'/\*')
        self._ml_end   = re.compile(r'\*/')

    def highlightBlock(self, text):
        for pat, fmt in self._rules:
            for m in pat.finditer(text):
                self.setFormat(m.start(), len(m.group()), fmt)
        # Block comments
        self.setCurrentBlockState(0)
        start = 0 if self.previousBlockState() == 1 else -1
        if start == -1:
            m = self._ml_start.search(text); start = m.start() if m else -1
        while start >= 0:
            em = self._ml_end.search(text, start)
            if em:
                self.setFormat(start, em.end()-start, self._ml_fmt)
                m2 = self._ml_start.search(text, em.end())
                start = m2.start() if m2 else -1
            else:
                self.setFormat(start, len(text)-start, self._ml_fmt)
                self.setCurrentBlockState(1); break


class GroovyHighlighter(JavaHighlighter):
    _EXTRA = ["def","in","it","as","trait","var","closure","println","apply","dependencies",
               "implementation","testImplementation","repositories","maven","plugins","id"]
    def __init__(self, doc):
        super().__init__(doc)
        gkw = _fmt(DARK["pink"], bold=True)
        for w in self._EXTRA:
            self._rules.insert(0, (re.compile(r'\b'+w+r'\b'), gkw))


HIGHLIGHTERS = {
    ".py":     PythonHighlighter,
    ".pyw":    PythonHighlighter,
    ".java":   JavaHighlighter,
    ".gradle": GroovyHighlighter,
    ".groovy": GroovyHighlighter,
}

# ════════════════════════════════════════════════════════════════
#  GOUTTIÈRE (numéros de ligne + repli)
# ════════════════════════════════════════════════════════════════

GUTTER_W = 56

class GutterArea(QWidget):
    fold_clicked = pyqtSignal(int)
    def __init__(self, editor):
        super().__init__(editor); self.editor = editor
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def sizeHint(self): return QtCore.QSize(GUTTER_W, 0)
    def paintEvent(self, event): self.editor._paint_gutter(event)
    def mousePressEvent(self, event):
        y = event.pos().y(); block = self.editor.firstVisibleBlock()
        offset = self.editor.contentOffset()
        while block.isValid():
            geom = self.editor.blockBoundingGeometry(block).translated(offset)
            if geom.top() <= y <= geom.bottom():
                self.fold_clicked.emit(block.blockNumber()); return
            if geom.top() > y: break
            block = block.next()

# ════════════════════════════════════════════════════════════════
#  ÉDITEUR DE CODE
# ════════════════════════════════════════════════════════════════

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filepath: Optional[Path] = None
        self._modified = False
        self._folded: set = set()
        self._foldable: set = set()
        self._highlighter = None

        font = QFont(); font.setPointSize(12); font.setFixedPitch(True)
        font.setFamilies(["Cascadia Code","JetBrains Mono","Fira Code","Consolas","Courier New"])
        self.setFont(font)
        self.setTabStopDistance(QFontMetrics(font).horizontalAdvance(' ') * 4)

        self._gutter = GutterArea(self)
        self._gutter.fold_clicked.connect(self._toggle_fold)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.document().contentsChanged.connect(self._on_contents_changed)
        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._update_gutter_area)
        self._update_gutter_width(); self._highlight_current_line()

    def _gutter_width(self):
        digits = max(3, len(str(self.blockCount())))
        return GUTTER_W + self.fontMetrics().horizontalAdvance('9') * (digits - 3)
    def _update_gutter_width(self): self.setViewportMargins(self._gutter_width(), 0, 0, 0)
    def _update_gutter_area(self, rect, dy):
        if dy: self._gutter.scroll(0, dy)
        else:  self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()): self._update_gutter_width()
    def resizeEvent(self, e):
        super().resizeEvent(e); cr = self.contentsRect()
        self._gutter.setGeometry(QtCore.QRect(cr.left(), cr.top(), self._gutter_width(), cr.height()))

    def _paint_gutter(self, event):
        p = QPainter(self._gutter); p.fillRect(event.rect(), QColor(DARK["gutter_bg"]))
        block  = self.firstVisibleBlock(); num = block.blockNumber()
        top    = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        line_h = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                color = DARK["accent"] if num == self.textCursor().blockNumber() else DARK["gutter_fg"]
                p.setPen(QColor(color))
                p.drawText(18, int(top), self._gutter.width()-20, line_h, Qt.AlignmentFlag.AlignRight, str(num+1))
                if num in self._foldable:
                    p.setPen(QColor(DARK["accent"]))
                    p.drawText(2, int(top), 14, line_h, Qt.AlignmentFlag.AlignHCenter,
                               "▶" if num in self._folded else "▼")
            block  = block.next(); top = bottom
            bottom = top + self.blockBoundingRect(block).height(); num += 1

    def _scan_foldable(self):
        self._foldable.clear(); doc = self.document()
        rx = re.compile(r'^[ \t]*(class|def)\s+\w+')
        b  = doc.begin()
        while b.isValid():
            if rx.match(b.text()): self._foldable.add(b.blockNumber())
            b = b.next()

    def _on_contents_changed(self):
        self._modified = True; self._scan_foldable(); self._gutter.update()

    def _get_fold_range(self, start_block):
        indent = len(start_block.text()) - len(start_block.text().lstrip())
        blocks = []; b = start_block.next()
        while b.isValid():
            t = b.text()
            if t.strip() == "": blocks.append(b); b = b.next(); continue
            if len(t) - len(t.lstrip()) <= indent: break
            blocks.append(b); b = b.next()
        return blocks

    def _toggle_fold(self, block_num):
        if block_num not in self._foldable: return
        block = self.document().findBlockByNumber(block_num)
        body  = self._get_fold_range(block)
        if not body: return
        if block_num in self._folded:
            for b in body: b.setVisible(True)
            self._folded.discard(block_num)
        else:
            for b in body: b.setVisible(False)
            self._folded.add(block_num)
        self.document().markContentsDirty(block.position(), self.document().characterCount())
        self._gutter.update(); self.viewport().update()

    def _highlight_current_line(self):
        extra = []
        if not self.isReadOnly():
            try:   sel = QTextEdit.ExtraSelection()
            except: return
            sel.format.setBackground(QColor(DARK["line_hi"]))
            sel.format.setProperty(QtGui.QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor(); sel.cursor.clearSelection()
            extra.append(sel)
        self.setExtraSelections(extra)

    def load_file(self, path: Path):
        try:
            self.setPlainText(path.read_text(encoding="utf-8", errors="replace"))
            self._filepath = path; self._modified = False; self._scan_foldable()
            # Appliquer le bon highlighter
            ext = path.suffix.lower()
            cls = HIGHLIGHTERS.get(ext)
            if cls: self._highlighter = cls(self.document())
            else:   self._highlighter = None
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir : {e}")

    def save_file(self, path: Path = None) -> bool:
        p = path or self._filepath
        if not p: return False
        try:
            p.write_text(self.toPlainText(), encoding="utf-8")
            self._filepath = p; self._modified = False; return True
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder : {e}"); return False

# ════════════════════════════════════════════════════════════════
#  WORKER D'EXÉCUTION (subprocess asynchrone)
# ════════════════════════════════════════════════════════════════

class RunWorker(QThread):
    output      = pyqtSignal(str)
    error       = pyqtSignal(str)
    started_pid = pyqtSignal(int)
    finished_rc = pyqtSignal(int)

    def __init__(self, cmd: list, cwd: str = None, env: dict = None):
        super().__init__()
        self.cmd = cmd; self.cwd = cwd; self.env = env
        self._proc = None; self._stopping = False

    def run(self):
        try:
            self._proc = subprocess.Popen(
                self.cmd, cwd=self.cwd, env=self.env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.PIPE, bufsize=0,
            )
            self.started_pid.emit(self._proc.pid)
            q = _queue.Queue(); SENTINEL = object()
            def _reader(stream, tag):
                try:
                    for raw in stream:
                        line = raw.rstrip(b"\n").rstrip(b"\r")
                        try: text = line.decode("utf-8")
                        except: text = line.decode("cp1252", errors="replace")
                        q.put((tag, text))
                except Exception as e:
                    q.put(("err", f"[run] Erreur lecture : {e}"))
                finally: q.put(SENTINEL)
            t_out = threading.Thread(target=_reader, args=(self._proc.stdout, "out"), daemon=True)
            t_err = threading.Thread(target=_reader, args=(self._proc.stderr, "err"), daemon=True)
            t_out.start(); t_err.start()
            sentinels = 0
            while sentinels < 2:
                try: item = q.get(timeout=0.05)
                except _queue.Empty: continue
                if item is SENTINEL: sentinels += 1; continue
                tag, text = item
                (self.output if tag == "out" else self.error).emit(text)
            t_out.join(); t_err.join(); rc = self._proc.wait()
            self.finished_rc.emit(rc)
        except FileNotFoundError:
            self.error.emit(f"[run] Commande introuvable : {self.cmd[0]}")
            self.finished_rc.emit(-1)
        except Exception as e:
            self.error.emit(f"[run] Erreur inattendue : {e}"); self.finished_rc.emit(-1)

    def kill(self):
        self._stopping = True
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.kill() if IS_WIN else self._proc.terminate()
                time.sleep(0.4)
                if self._proc.poll() is None: self._proc.kill()
            except: pass

# ════════════════════════════════════════════════════════════════
#  PANNEAU TERMINAL
# ════════════════════════════════════════════════════════════════

class OutputPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(2)
        bar = QHBoxLayout()
        title = QLabel("TERMINAL"); title.setObjectName("section_title"); bar.addWidget(title)
        bar.addStretch()
        self._log_label = QLabel(""); self._log_label.setStyleSheet(f"color:{DARK['text_dim']};font-size:10px;")
        bar.addWidget(self._log_label)
        clr = QPushButton("✕ Effacer"); clr.setFixedHeight(22); clr.clicked.connect(self.clear)
        bar.addWidget(clr); lay.addLayout(bar)
        self.output = QPlainTextEdit(); self.output.setReadOnly(True); self.output.setMaximumBlockCount(5000)
        font = QFont(); font.setFamilies(["Cascadia Code","Consolas","Courier New"]); font.setPointSize(11)
        self.output.setFont(font); lay.addWidget(self.output)
        self._fmt = {
            "normal": self._mfmt(DARK["text"]),   "err":  self._mfmt(DARK["red"]),
            "info":   self._mfmt(DARK["accent"]), "ok":   self._mfmt(DARK["green"]),
            "warn":   self._mfmt(DARK["yellow"]), "task": self._mfmt(DARK["teal"]),
        }
        self._log_file = None; self._log_path = None; self._init_log_file()

    @staticmethod
    def _mfmt(color): f = QTextCharFormat(); f.setForeground(QColor(color)); return f

    def _init_log_file(self):
        try:
            self._log_file = _startup_log; self._log_path = _log_path
            self._log_label.setText(f"📄 {_log_path.name}")
            self._log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] [INFO] Interface prête\n")
        except Exception as e:
            self._log_label.setText(f"⚠ log désactivé ({e})")

    def _log(self, level, text):
        if self._log_file:
            ts = datetime.now().strftime("%H:%M:%S.%f")[:12]
            try: self._log_file.write(f"[{ts}] [{level:4s}] {text}\n")
            except: pass

    def _append(self, text, fmt_key):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + "\n", self._fmt.get(fmt_key, self._fmt["normal"]))
        self.output.setTextCursor(cursor); self.output.ensureCursorVisible()

    def write(self, text):      self._append(text, "normal"); self._log("OUT",  text)
    def write_err(self, text):  self._append(text, "err");    self._log("ERR",  text)
    def write_info(self, text): self._append(text, "info");   self._log("INFO", text)
    def write_ok(self, text):   self._append(text, "ok");     self._log("OK",   text)
    def write_warn(self, text): self._append(text, "warn");   self._log("WARN", text)
    def write_task(self, text): self._append(text, "task");   self._log("TASK", text)
    def clear(self): self.output.clear()
    def close_log(self):
        if self._log_file:
            try:
                self._log_file.write("="*60+f"\nFin : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self._log_file.close()
            except: pass
            self._log_file = None

# ════════════════════════════════════════════════════════════════
#  GESTIONNAIRE JDK (téléchargement)
# ════════════════════════════════════════════════════════════════

class JDKDownloadThread(QThread):
    progress = pyqtSignal(int, int)
    log      = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url: str, dest: Path):
        super().__init__(); self.url = url; self.dest = dest

    def run(self):
        try:
            self.dest.mkdir(parents=True, exist_ok=True)
            name = self.url.split("/")[-1].split("?")[0]
            archive = self.dest / name
            self.log.emit(f"⬇ Téléchargement de {name} …")
            def hook(count, bs, total): self.progress.emit(count*bs, total)
            urllib.request.urlretrieve(self.url, archive, hook)
            self.log.emit("📦 Extraction …")
            if name.endswith(".zip"):
                with zipfile.ZipFile(archive) as zf: zf.extractall(self.dest)
            else:
                with tarfile.open(archive, "r:gz") as tf: tf.extractall(self.dest)
            archive.unlink(missing_ok=True)
            for item in sorted(self.dest.iterdir()):
                if not item.is_dir(): continue
                for cand in [item/"bin"/JAVA_EXE, item/"Contents"/"Home"/"bin"/JAVA_EXE]:
                    if cand.exists():
                        self.log.emit(f"✅ JDK installé dans {item.name}")
                        self.finished.emit(True, str(cand.parent.parent)); return
            self.finished.emit(False, "Binaire java introuvable après extraction.")
        except Exception as e:
            self.finished.emit(False, str(e))


class JDKDownloadDialog(QDialog):
    def __init__(self, java_ver: int, parent=None):
        super().__init__(parent)
        self.java_ver = java_ver
        self.jdk_home: Optional[Path] = None
        dest_dir = get_jdk_dir() / f"jdk{java_ver}"
        self.setWindowTitle(f"Télécharger JDK {java_ver}"); self.setMinimumWidth(500); self.setModal(True)
        lay = QVBoxLayout(self)
        self.lbl = QLabel(
            f"JDK {java_ver} introuvable localement.\n"
            f"Voulez-vous le télécharger automatiquement ?\n\n"
            f"Destination : {dest_dir}\n"
            f"(partagé entre tous les projets, téléchargement unique)"
        ); self.lbl.setWordWrap(True); lay.addWidget(self.lbl)
        self.bar = QProgressBar(); self.bar.setVisible(False); lay.addWidget(self.bar)
        self.log_view = QPlainTextEdit(); self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(80); self.log_view.setVisible(False); lay.addWidget(self.log_view)
        row = QHBoxLayout()
        self.dl_btn = QPushButton(f"⬇  Télécharger JDK {java_ver}")
        self.cancel = QPushButton("Annuler")
        row.addWidget(self.dl_btn); row.addWidget(self.cancel); lay.addLayout(row)
        self.dl_btn.clicked.connect(self._start); self.cancel.clicked.connect(self.reject)
        if not get_jdk_url(java_ver):
            self.lbl.setText(f"Plateforme non supportée : {platform.system()} {platform.machine()}")
            self.dl_btn.setEnabled(False)

    def _start(self):
        self.dl_btn.setEnabled(False); self.cancel.setEnabled(False)
        self.bar.setVisible(True); self.log_view.setVisible(True); self.bar.setRange(0, 0)
        url  = get_jdk_url(self.java_ver)
        dest = get_jdk_dir() / f"jdk{self.java_ver}"
        self._thread = JDKDownloadThread(url, dest)
        self._thread.progress.connect(self._on_progress)
        self._thread.log.connect(self.log_view.appendPlainText)
        self._thread.finished.connect(self._on_done); self._thread.start()

    def _on_progress(self, dl, total):
        if total > 0:
            self.bar.setRange(0, total); self.bar.setValue(dl)
            self.lbl.setText(f"Téléchargement : {dl/1e6:.1f} / {total/1e6:.1f} Mo")

    def _on_done(self, ok, val):
        if ok:
            self.jdk_home = Path(val); self.lbl.setText(f"✅ JDK {self.java_ver} installé !")
            self.cancel.setText("Fermer"); self.cancel.setEnabled(True)
            self.cancel.clicked.disconnect(); self.cancel.clicked.connect(self.accept)
        else:
            self.lbl.setText(f"❌ Erreur : {val}"); self.dl_btn.setEnabled(True); self.cancel.setEnabled(True)

# ════════════════════════════════════════════════════════════════
#  PANNEAU PYTHON BUILD (serveur + déploiement)
# ════════════════════════════════════════════════════════════════

class PythonBuildPanel(QWidget):
    def __init__(self, project_root: Path, output: OutputPanel, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.output       = output
        self._worker: Optional[RunWorker] = None

        lay = QVBoxLayout(self); lay.setContentsMargins(4,4,4,4); lay.setSpacing(4)

        # ── Auto-injection ──────────────────────────────────────
        deps_bar = QWidget()
        deps_bar.setStyleSheet(f"background:{DARK['bg2']};border-radius:4px;")
        db = QHBoxLayout(deps_bar); db.setContentsMargins(8,4,8,4)
        self.auto_deps_chk = QCheckBox("🔍 Auto-injection des dépendances pip à la sauvegarde")
        self.auto_deps_chk.setChecked(True)
        db.addWidget(self.auto_deps_chk); db.addStretch()
        self.deps_status = QLabel("")
        self.deps_status.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;")
        db.addWidget(self.deps_status); lay.addWidget(deps_bar)

        # ── Configuration du projet ─────────────────────────────
        cfg = QGroupBox("Configuration du build")
        cfg_l = QVBoxLayout(cfg); cfg_l.setContentsMargins(8,4,8,8); cfg_l.setSpacing(4)

        def _row(lbl, w):
            r = QHBoxLayout(); r.addWidget(QLabel(lbl)); r.addWidget(w); cfg_l.addLayout(r)

        self.app_name_edit = QLineEdit(); self.app_name_edit.setPlaceholderText("ex: MonApp")
        self.entry_edit    = QLineEdit(); self.entry_edit.setPlaceholderText("ex: main.py  ou  app.pyw")
        self.version_edit  = QLineEdit(); self.version_edit.setText("1.0.0")
        self.gh_repo_edit  = QLineEdit(); self.gh_repo_edit.setPlaceholderText("ex: moncompte/monapp")

        _row("Nom de l'app :",   self.app_name_edit)
        _row("Point d'entrée :", self.entry_edit)
        _row("Version :",         self.version_edit)
        _row("GitHub repo :",     self.gh_repo_edit)
        lay.addWidget(cfg)

        # ── Build / Déploiement ─────────────────────────────────
        deploy = QGroupBox("Build EXE + Déploiement")
        dep_l  = QVBoxLayout(deploy); dep_l.setContentsMargins(8,4,8,8); dep_l.setSpacing(6)
        notes_row = QHBoxLayout(); notes_row.addWidget(QLabel("Notes de version :"))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("ex: Correctif v1.2.3 …")
        notes_row.addWidget(self.notes_edit); dep_l.addLayout(notes_row)
        btn_row = QHBoxLayout()
        self.build_dev_btn = QPushButton("🔧 Build DEV"); self.build_dev_btn.setObjectName("build_btn")
        self.build_dev_btn.clicked.connect(lambda: self._run_build("dev"))
        self.promote_btn   = QPushButton("🚀 Promouvoir DEV → STABLE"); self.promote_btn.setObjectName("promote_btn")
        self.promote_btn.clicked.connect(self._promote)
        btn_row.addWidget(self.build_dev_btn); btn_row.addWidget(self.promote_btn); dep_l.addLayout(btn_row)
        self.py_progress = QProgressBar(); self.py_progress.setTextVisible(False)
        self.py_progress.setFixedHeight(4); self.py_progress.hide(); dep_l.addWidget(self.py_progress)
        lay.addWidget(deploy); lay.addStretch()

    # ── Helpers ──────────────────────────────────────────────────
    def _app_name(self) -> str: return self.app_name_edit.text().strip() or "App"
    def _entry(self)    -> str: return self.entry_edit.text().strip()    or "main.py"
    def _version(self)  -> str: return self.version_edit.text().strip()  or "1.0.0"
    def _gh_repo(self)  -> str: return self.gh_repo_edit.text().strip()
    def _dist_dir(self, channel: str) -> Path: return self.project_root / "dist" / channel

    # ── Génération des fichiers auxiliaires ──────────────────────
    def _write_version_json(self, channel: str):
        vf = self.project_root / "version.json"
        existing = {}
        if vf.exists():
            try: existing = json.loads(vf.read_text(encoding="utf-8"))
            except: pass
        existing[channel] = {"version": self._version(), "app_name": self._app_name(),
                              "github_repo": self._gh_repo(), "notes": self.notes_edit.text().strip()}
        vf.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        self.output.write_info(f"[build] version.json mis à jour ({channel} = {self._version()})")

    def _write_version_info_py(self):
        vi = self.project_root / "version_info.py"
        vi.write_text(
            "# Généré par DevStudio Pro — mis à jour à chaque build\n"
            f'VERSION     = "{self._version()}"\n'
            f'APP_NAME    = "{self._app_name()}"\n'
            f'GITHUB_REPO = "{self._gh_repo()}"\n',
            encoding="utf-8"
        )
        self.output.write_ok("[build] version_info.py généré ✓")

    def _write_updater(self):
        """Génère _updater.py — embarqué dans l'exe, vérifie les MàJ au démarrage."""
        updater_path = self.project_root / "_updater.py"
        lines = [
            "#!/usr/bin/env python3",
            '"""',
            "_updater.py — Vérification automatique des mises à jour.",
            "Généré par DevStudio Pro.  Appelez check_and_update() au démarrage.",
            '"""',
            "import sys, os, json, threading, subprocess, platform, tempfile",
            "from pathlib import Path",
            "",
            "try:",
            "    import version_info as _vi",
            "    CURRENT_VER  = _vi.VERSION",
            "    GITHUB_REPO  = _vi.GITHUB_REPO",
            "except ImportError:",
            '    CURRENT_VER = "0.0.0"',
            '    GITHUB_REPO = ""',
            "",
            "def _parse(v):",
            "    try: return tuple(int(x) for x in v.lstrip('v').split('.'))",
            "    except: return (0,)",
            "",
            "def _get_latest():",
            "    import urllib.request",
            "    if not GITHUB_REPO: return None",
            "    try:",
            "        url = f'https://api.github.com/repos/{GITHUB_REPO}/releases/latest'",
            "        req = urllib.request.Request(url, headers={'User-Agent': 'DevStudioUpdater/1.0'})",
            "        with urllib.request.urlopen(req, timeout=5) as r:",
            "            return json.loads(r.read())",
            "    except Exception:",
            "        return None",
            "",
            "def _download_and_replace(asset_url):",
            "    import urllib.request",
            "    suffix = '.exe' if platform.system() == 'Windows' else ''",
            "    exe = sys.executable if getattr(sys, 'frozen', False) else None",
            "    if not exe: return",
            "    tmp = Path(tempfile.mktemp(suffix=suffix))",
            "    try:",
            "        with urllib.request.urlopen(asset_url, timeout=60) as r, open(tmp, 'wb') as f:",
            "            f.write(r.read())",
            "        helper = Path(exe).parent / ('_upd.bat' if platform.system() == 'Windows' else '_upd.sh')",
            "        if platform.system() == 'Windows':",
            "            helper.write_text(",
            "                '@echo off\\ntimeout /t 2 /nobreak >nul\\n'",
            "                f'move /Y \"{tmp}\" \"{exe}\"\\nstart \"\" \"{exe}\"\\ndel \"%~f0\"\\n',",
            "                encoding='utf-8'",
            "            )",
            "            subprocess.Popen(['cmd', '/C', str(helper)], creationflags=0x08000000)",
            "        else:",
            "            helper.write_text(",
            "                f'#!/bin/bash\\nsleep 2\\nmv -f \"{tmp}\" \"{exe}\"\\n'",
            "                f'chmod +x \"{exe}\"\\n\"{exe}\" &\\nrm -- \"$0\"\\n',",
            "                encoding='utf-8'",
            "            )",
            "            helper.chmod(0o755)",
            "            subprocess.Popen(['bash', str(helper)])",
            "        sys.exit(0)",
            "    except Exception as e:",
            "        print(f'[updater] Erreur MàJ : {e}', file=sys.stderr)",
            "",
            "def check_and_update(silent=True, channel='stable'):",
            '    """Vérifie les MàJ sur GitHub. Appeler au démarrage (non bloquant)."""',
            "    def _check():",
            "        data = _get_latest()",
            "        if not data: return",
            "        if channel == 'stable' and data.get('prerelease'): return",
            "        latest_ver = data.get('tag_name','').lstrip('v')",
            "        if not latest_ver: return",
            "        if _parse(latest_ver) <= _parse(CURRENT_VER):",
            "            if not silent: print(f'[updater] Déjà à jour ({CURRENT_VER})')",
            "            return",
            "        print(f'[updater] Nouvelle version : {latest_ver} (actuelle : {CURRENT_VER})')",
            "        os_name = platform.system().lower()",
            "        assets  = data.get('assets', [])",
            "        asset   = next(",
            "            (a for a in assets if os_name in a['name'].lower()",
            "             or (os_name == 'windows' and a['name'].endswith('.exe'))),",
            "            assets[0] if assets else None",
            "        )",
            "        if asset: _download_and_replace(asset['browser_download_url'])",
            "    threading.Thread(target=_check, daemon=True).start()",
        ]
        updater_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.output.write_ok("[build] _updater.py généré ✓")

    def _write_installers(self, channel: str):
        name = self._app_name(); gh = self._gh_repo()
        exe_win = f"{name}.exe"; exe_lin = name

        bat = self.project_root / f"install_{channel}.bat"
        bat.write_text(
            f"@echo off\nsetlocal\ntitle Installation de {name}\n"
            f"set \"INSTALL_DIR=%USERPROFILE%\\AppData\\Local\\{name}\"\n"
            f"mkdir \"%INSTALL_DIR%\" 2>nul\n"
            f"echo Telechargement de {name} ({channel})...\n"
            f"powershell -Command \"(New-Object Net.WebClient).DownloadFile("
            f"'https://github.com/{gh}/releases/latest/download/{exe_win}'"
            f",'%INSTALL_DIR%\\{exe_win}')\"\n"
            f"if errorlevel 1 (echo Erreur de telechargement & pause & exit /b 1)\n"
            f"echo Installation terminee dans : %INSTALL_DIR%\npause\nendlocal\n",
            encoding="utf-8"
        )
        sh = self.project_root / f"install_{channel}.sh"
        sh.write_text(
            f"#!/usr/bin/env bash\nset -e\n"
            f'INSTALL_DIR="$HOME/.local/bin"\nmkdir -p "$INSTALL_DIR"\n'
            f'echo "Téléchargement de {name} ({channel})..."\n'
            f'curl -fsSL "https://github.com/{gh}/releases/latest/download/{exe_lin}"'
            f' -o "$INSTALL_DIR/{exe_lin}"\nchmod +x "$INSTALL_DIR/{exe_lin}"\n'
            f'echo "✅ Installé dans $INSTALL_DIR/{exe_lin}"\n',
            encoding="utf-8"
        )
        self.output.write_ok(f"[build] install_{channel}.bat / .sh générés ✓")

    # ── Build PyInstaller ─────────────────────────────────────────
    def _write_installer_generator(self):
        """Genere installer.pyw pour distribution."""
        out_path = self.project_root / "installer.pyw"
        app = self._app_name()
        ver = self._version()
        gh  = self._gh_repo()
        # Ecrire le code de l'installeur dans une liste de lignes pour eviter
        # tout probleme d'echappement de guillemets imbriques
        code_lines = []
        code_lines.append("#!/usr/bin/env python3")
        code_lines.append("import sys, os, json, shutil, subprocess, platform, threading")
        code_lines.append("import urllib.request")
        code_lines.append("from pathlib import Path")
        code_lines.append("APP_NAME    = " + repr(app))
        code_lines.append("VERSION     = " + repr(ver))
        code_lines.append("GITHUB_REPO = " + repr(gh))
        code_lines.append("RELEASE_URL = " + repr("https://api.github.com/repos/" + gh + "/releases/latest"))
        code_lines.append("INSTALL_WIN  = Path.home() / 'AppData' / 'Local' / APP_NAME")
        code_lines.append("INSTALL_UNIX = Path.home() / '.local' / APP_NAME")
        code_lines.append("INSTALL_DIR  = INSTALL_WIN if platform.system() == 'Windows' else INSTALL_UNIX")
        code_lines.append("MODULES = {")
        code_lines.append("    'python':    {'label': 'Python IDE',          'default': True},")
        code_lines.append("    'java_mc':   {'label': 'Minecraft Java Build', 'default': True},")
        code_lines.append("    'instances': {'label': 'Instances Minecraft',  'default': True},")
        code_lines.append("    'github':    {'label': 'GitHub',               'default': True},")
        code_lines.append("}")
        code_lines.append("try:")
        code_lines.append("    from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,")
        code_lines.append("        QLabel, QCheckBox, QPushButton, QProgressBar, QPlainTextEdit)")
        code_lines.append("    from PyQt6.QtCore import Qt")
        code_lines.append("except ImportError:")
        code_lines.append("    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyQt6', '-q'])")
        code_lines.append("    from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,")
        code_lines.append("        QLabel, QCheckBox, QPushButton, QProgressBar, QPlainTextEdit)")
        code_lines.append("    from PyQt6.QtCore import Qt")
        code_lines.append("class Installer(QWidget):")
        code_lines.append("    def __init__(self):")
        code_lines.append("        super().__init__()")
        code_lines.append("        self.setWindowTitle('Installer ' + APP_NAME + ' ' + VERSION)")
        code_lines.append("        self.setMinimumWidth(460)")
        code_lines.append("        lay = QVBoxLayout(self)")
        code_lines.append("        lay.addWidget(QLabel('<h2>' + APP_NAME + ' ' + VERSION + '</h2>'))")
        code_lines.append("        self._checks = {}")
        code_lines.append("        for key, info in MODULES.items():")
        code_lines.append("            chk = QCheckBox(info['label'])")
        code_lines.append("            chk.setChecked(info['default'])")
        code_lines.append("            self._checks[key] = chk")
        code_lines.append("            lay.addWidget(chk)")
        code_lines.append("        self._log = QPlainTextEdit()")
        code_lines.append("        self._log.setReadOnly(True)")
        code_lines.append("        self._log.setMaximumHeight(130)")
        code_lines.append("        lay.addWidget(self._log)")
        code_lines.append("        self._bar = QProgressBar()")
        code_lines.append("        self._bar.setRange(0, 0)")
        code_lines.append("        self._bar.hide()")
        code_lines.append("        lay.addWidget(self._bar)")
        code_lines.append("        btn = QPushButton('Installer')")
        code_lines.append("        btn.clicked.connect(self._start)")
        code_lines.append("        lay.addWidget(btn)")
        code_lines.append("    def _log_msg(self, msg):")
        code_lines.append("        self._log.appendPlainText(str(msg))")
        code_lines.append("    def _start(self):")
        code_lines.append("        selected = [k for k, c in self._checks.items() if c.isChecked()]")
        code_lines.append("        self._bar.show()")
        code_lines.append("        def _do():")
        code_lines.append("            try:")
        code_lines.append("                INSTALL_DIR.mkdir(parents=True, exist_ok=True)")
        code_lines.append("                if GITHUB_REPO:")
        code_lines.append("                    try:")
        code_lines.append("                        req = urllib.request.Request(")
        code_lines.append("                            RELEASE_URL, headers={'User-Agent': 'Installer/1.0'})")
        code_lines.append("                        with urllib.request.urlopen(req, timeout=8) as r:")
        code_lines.append("                            data = json.loads(r.read())")
        code_lines.append("                        os_n = platform.system().lower()")
        code_lines.append("                        assets = data.get('assets', [])")
        code_lines.append("                        asset = next(")
        code_lines.append("                            (a for a in assets")
        code_lines.append("                             if os_n in a['name'].lower()")
        code_lines.append("                             or (os_n == 'windows' and a['name'].endswith('.exe'))),")
        code_lines.append("                            assets[0] if assets else None)")
        code_lines.append("                        if asset:")
        code_lines.append("                            exe = APP_NAME + ('.exe' if platform.system() == 'Windows' else '')")
        code_lines.append("                            dest = INSTALL_DIR / exe")
        code_lines.append("                            self._log_msg('Telechargement...')")
        code_lines.append("                            urllib.request.urlretrieve(asset['browser_download_url'], dest)")
        code_lines.append("                            if platform.system() != 'Windows':")
        code_lines.append("                                os.chmod(dest, 0o755)")
        code_lines.append("                            self._log_msg('Installe dans ' + str(INSTALL_DIR))")
        code_lines.append("                            with open(INSTALL_DIR / 'modules.json', 'w') as f:")
        code_lines.append("                                json.dump({'enabled': selected}, f)")
        code_lines.append("                    except Exception as e:")
        code_lines.append("                        self._log_msg('Hors-ligne ou erreur : ' + str(e))")
        code_lines.append("                self._log_msg('Installation terminee !')")
        code_lines.append("            except Exception as e:")
        code_lines.append("                self._log_msg('Erreur : ' + str(e))")
        code_lines.append("        threading.Thread(target=_do, daemon=True).start()")
        code_lines.append("if __name__ == '__main__':")
        code_lines.append("    _a = QApplication(sys.argv)")
        code_lines.append("    _w = Installer()")
        code_lines.append("    _w.show()")
        code_lines.append("    sys.exit(_a.exec())")
        out_path.write_text("\n".join(code_lines) + "\n", encoding="utf-8")
        self.output.write_ok("[build] installer.pyw genere")


    def _ensure_pyinstaller(self) -> bool:
        import importlib.util
        if importlib.util.find_spec("PyInstaller") is not None: return True
        self.output.write_info("[build] Installation de PyInstaller …")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "PyInstaller", "--quiet"],
                           capture_output=True, text=True)
        if r.returncode == 0: self.output.write_ok("[build] PyInstaller installé ✓"); return True
        self.output.write_err(f"[build] Échec PyInstaller :\n{r.stderr}"); return False

    def _run_build(self, channel: str):
        if not self.project_root:
            QMessageBox.warning(self, "Pas de projet", "Ouvrez d'abord un projet Python."); return
        if self._worker and self._worker.isRunning(): return
        app_name = self._app_name(); entry = self._entry()
        entry_path = self.project_root / entry
        if not entry_path.exists():
            QMessageBox.warning(self, "Point d'entrée introuvable",
                f"'{entry}' n'existe pas dans le projet."); return
        if not self._ensure_pyinstaller(): return

        self._write_version_info_py()
        self._write_updater()
        self._write_version_json(channel)
        self._write_installers(channel)
        self._write_installer_generator()

        dist_dir = self._dist_dir(channel)
        dist_dir.mkdir(parents=True, exist_ok=True)

        # ── Supprimer l'ancien .spec pour forcer la régénération ─────────────
        # PyInstaller utilise le .spec existant et ignore --specpath s'il le trouve.
        for spec in [self.project_root / "build" / f"{app_name}.spec",
                     self.project_root / f"{app_name}.spec"]:
            if spec.exists():
                try: spec.unlink(); self.output.write_info(f"[build] Ancien .spec supprimé : {spec.name}")
                except: pass

        # Dossiers de travail
        work_dir = self.project_root / "build" / "pyinstaller" / channel
        work_dir.mkdir(parents=True, exist_ok=True)
        spec_dir = work_dir  # spec écrit ici, loin du projet

        # ── Stratégie --add-data ───────────────────────────────────────────────
        # Règle : NE PAS utiliser --add-data pour les fichiers .py
        #   → PyInstaller les détecte automatiquement via l'analyse des imports.
        #   → Seuls les fichiers de DONNÉES non-Python ont besoin de --add-data.
        # Utiliser des chemins ABSOLUS pour éviter toute ambiguïté de résolution.
        extra = []

        # version.json = donnée non-Python → --add-data requis
        vj = self.project_root / "version.json"
        if vj.exists():
            extra += ["--add-data", f"{vj.resolve()}{os.pathsep}."]

        # S'assurer que les modules du projet sont trouvables
        # --paths ajoute le dossier au PYTHONPATH de PyInstaller
        extra += ["--paths", str(self.project_root)]

        # Modules Python secondaires du projet → --hidden-import
        # (pour les imports dynamiques que l'analyse statique manquerait)
        SKIP = {entry, "version_info.py", "_updater.py"}
        for f in self.project_root.glob("*.py"):
            if f.name not in SKIP and not f.name.startswith("_"):
                mod = f.stem
                extra += ["--hidden-import", mod]

        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--name",      app_name,
            "--distpath",  str(dist_dir),
            "--workpath",  str(work_dir / "work"),
            "--specpath",  str(spec_dir),
            "--noconfirm",
            "--clean",
        ] + extra + [str(entry_path.resolve())]

        self.output.write_info("═"*55)
        self.output.write_info(f"🐍 Build {channel.upper()} — {app_name} v{self._version()}")
        self.output.write_info(f"   Entrée : {entry}  →  {dist_dir / app_name}")
        self.output.write_info("═"*55)
        self.py_progress.setRange(0,0); self.py_progress.show()
        self.build_dev_btn.setEnabled(False); self.promote_btn.setEnabled(False)
        self._worker = RunWorker(cmd, cwd=str(self.project_root))
        self._worker.output.connect(self._on_build_line)
        self._worker.error.connect(self._on_build_line)
        self._worker.finished_rc.connect(lambda rc: self._on_build_done(rc, channel))
        self._worker.start()

    def _on_build_line(self, line: str):
        lo = line.lower()
        if "error" in lo or "traceback" in lo: self.output.write_err(line)
        elif "warn" in lo:                      self.output.write_warn(line)
        else:                                   self.output.write(line)

    def _on_build_done(self, rc: int, channel: str):
        self.py_progress.hide(); self.build_dev_btn.setEnabled(True); self.promote_btn.setEnabled(True)
        exe = self._dist_dir(channel) / (self._app_name() + (".exe" if IS_WIN else ""))
        if rc == 0:
            self.output.write_info("═"*55)
            self.output.write_ok(f"✅ BUILD {channel.upper()} RÉUSSI → {exe}")
            self.output.write_info("═"*55)
            d = str(self._dist_dir(channel))
            if IS_WIN: os.startfile(d)
            elif platform.system() == "Darwin": subprocess.run(["open", d])
            else: subprocess.run(["xdg-open", d])
        else:
            self.output.write_err(f"❌ BUILD {channel.upper()} ÉCHOUÉ (code {rc})")

    # ── Promotion DEV → STABLE ────────────────────────────────────
    def _promote(self):
        app_name = self._app_name()
        exe_name = app_name + (".exe" if IS_WIN else "")
        dev_exe  = self._dist_dir("dev") / exe_name
        if not dev_exe.exists():
            QMessageBox.warning(self, "Pas de build DEV",
                f"Effectuez d'abord un Build DEV.\n(cherché : {dev_exe})"); return
        r = QMessageBox.question(self, "Confirmer la promotion",
            f"Promouvoir {app_name} v{self._version()} DEV → STABLE ?\n\n"
            "  • Copie dist/dev/ → dist/stable/\n"
            "  • Met à jour version.json (stable)\n"
            "  • Crée un tag Git et pousse sur GitHub",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes: return

        stable_dir = self._dist_dir("stable"); stable_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dev_exe, stable_dir / exe_name)
        self.output.write_ok(f"[promote] Copié → dist/stable/{exe_name}")
        self._write_version_json("stable")

        tag = f"v{self._version()}"
        try:
            subprocess.run(["git", "add", "-A"],                cwd=str(self.project_root), capture_output=True)
            subprocess.run(["git", "commit", "-m", f"release {tag}"], cwd=str(self.project_root), capture_output=True)
            subprocess.run(["git", "tag", tag],                 cwd=str(self.project_root), capture_output=True)
            subprocess.run(["git", "push", "origin", "HEAD", "--tags"], cwd=str(self.project_root), capture_output=True)
            self.output.write_ok(f"[promote] Tag {tag} poussé ✓")
        except Exception as e:
            self.output.write_warn(f"[promote] Git non disponible : {e}")

        self.output.write_ok("[promote] ✅ Promotion terminée !")
        self.output.write_info("[promote] → Onglet 🐙 GitHub pour créer la Release et joindre l'exe")

    def set_project_root(self, root: Path):
        self.project_root = root
        vf = root / "version.json"
        if vf.exists():
            try:
                data = json.loads(vf.read_text(encoding="utf-8"))
                for ch in ("stable", "dev"):
                    if ch in data:
                        d = data[ch]
                        if not self.app_name_edit.text() and d.get("app_name"):
                            self.app_name_edit.setText(d["app_name"])
                        if d.get("version"):     self.version_edit.setText(d["version"])
                        if d.get("github_repo"): self.gh_repo_edit.setText(d["github_repo"])
                        break
            except: pass
        if not self.entry_edit.text():
            for c in ["main.py","app.py","run.py","main.pyw","app.pyw"]:
                if (root / c).exists(): self.entry_edit.setText(c); break

    def stop_server(self): pass



# ════════════════════════════════════════════════════════════════
#  PANNEAU MINECRAFT BUILD
# ════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════
#  MDK DOWNLOAD THREAD + DIALOG "NOUVEAU PROJET MOD"
# ════════════════════════════════════════════════════════════════

class MDKDownloadThread(QThread):
    """
    Télécharge et extrait le MDK pour un loader/version donné.
    Cache dans get_mdk_dir() / <loader> / <mc_version> / mdk.zip
    """
    log      = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(bool, str)   # ok, mdk_dir ou message d'erreur

    # Forge : version récupérée depuis Maven avant le téléchargement
    FORGE_META = "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml"
    FORGE_MDK  = "https://maven.minecraftforge.net/net/minecraftforge/forge/{v}/forge-{v}-mdk.zip"

    # NeoForge MDK template (branche main, toujours à jour)
    NEOFORGE_MDK = "https://github.com/neoforged/MDK/archive/refs/heads/main.zip"

    # Fabric example mod (branche = version MC, ex "1.20.1")
    FABRIC_MDK = "https://github.com/FabricMC/fabric-example-mod/archive/refs/heads/{branch}.zip"
    FABRIC_MDK_FALLBACK = "https://github.com/FabricMC/fabric-example-mod/archive/refs/heads/main.zip"

    # Quilt template
    QUILT_MDK = "https://github.com/QuiltMC/quilt-example-mod/archive/refs/heads/main.zip"

    def __init__(self, loader: str, mc_version: str):
        super().__init__()
        self.loader     = loader
        self.mc_version = mc_version

    def run(self):
        try:    self._run()
        except Exception as e:
            import traceback as _tb
            self.log.emit(f"❌ {e}")
            self.log.emit(_tb.format_exc())
            self.finished.emit(False, str(e))

    def _dl_to(self, url: str, dest: Path, label: str = ""):
        """Télécharge url → dest avec progression. Retourne False si 404/403."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "DevStudioPro/2.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                total = int(r.headers.get("Content-Length", 0))
                done  = 0
                with open(dest, "wb") as f:
                    while chunk := r.read(65536):
                        f.write(chunk)
                        done += len(chunk)
                        if total: self.progress.emit(done, total)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} pour {url}")
        return True

    def _run(self):
        loader = self.loader; ver = self.mc_version
        cache  = get_mdk_dir() / loader / ver
        cache.mkdir(parents=True, exist_ok=True)
        zip_path = cache / "mdk.zip"

        # ── Forge ─────────────────────────────────────────────────────────
        if loader == "Forge":
            if not zip_path.exists():
                self.log.emit(f"🔍 Recherche version Forge pour {ver} …")
                req = urllib.request.Request(self.FORGE_META, headers={"User-Agent":"DevStudioPro/2.0"})
                with urllib.request.urlopen(req, timeout=20) as r: xml = r.read().decode()
                all_ver = re.findall(r'<version>([^<]+)</version>', xml)
                prefix  = f"{ver}-"
                matching = [v for v in all_ver if v.startswith(prefix)]
                if not matching:
                    self.finished.emit(False, f"Aucune version Forge pour {ver}"); return
                def _forge_build(v):
                    try: return tuple(int(x) for x in v.split("-",1)[1].split("."))
                    except: return (0,)
                forge_ver = sorted(matching, key=_forge_build)[-1]
                url = self.FORGE_MDK.format(v=forge_ver)
                self.log.emit(f"⬇ Forge MDK {forge_ver} …")
                self._dl_to(url, zip_path)
            else:
                self.log.emit(f"♻ MDK Forge {ver} déjà en cache.")

        # ── NeoForge ──────────────────────────────────────────────────────
        elif loader == "NeoForge":
            if not zip_path.exists():
                self.log.emit("⬇ NeoForge MDK (template GitHub) …")
                self._dl_to(self.NEOFORGE_MDK, zip_path)
            else:
                self.log.emit("♻ MDK NeoForge déjà en cache.")

        # ── Fabric / Quilt ────────────────────────────────────────────────
        elif loader in ("Fabric", "Quilt"):
            if not zip_path.exists():
                if loader == "Quilt":
                    url = self.QUILT_MDK
                else:
                    # Essaie la branche = version MC, sinon main
                    branch = ver  # ex "1.20.1"
                    url    = self.FABRIC_MDK.format(branch=branch)
                self.log.emit(f"⬇ {loader} MDK …")
                try:
                    self._dl_to(url, zip_path)
                except RuntimeError:
                    if loader == "Fabric":
                        self.log.emit("⬇ Branche main (fallback) …")
                        self._dl_to(self.FABRIC_MDK_FALLBACK, zip_path)
                    else: raise
            else:
                self.log.emit(f"♻ MDK {loader} déjà en cache.")

        else:
            self.finished.emit(False, f"Loader '{loader}' non supporté pour le MDK"); return

        self.finished.emit(True, str(cache))


class NewModProjectDialog(QDialog):
    """
    Dialog de création d'un nouveau projet mod.
    Télécharge le MDK, l'extrait dans un dossier choisi,
    et pré-configure build.gradle avec le nom/mod-id saisi.
    """
    def __init__(self, loader: str, mc_version: str, parent=None):
        super().__init__(parent)
        self.loader     = loader
        self.mc_version = mc_version
        self.result_path: Optional[Path] = None
        self.setWindowTitle(f"Nouveau projet {loader} {mc_version}")
        self.setMinimumWidth(520); self.setModal(True)
        lay = QVBoxLayout(self)

        # ── Infos du mod ──────────────────────────────────────────────
        info = QGroupBox("Informations du mod")
        il   = QVBoxLayout(info); il.setSpacing(4)
        def _row(lbl, w):
            r = QHBoxLayout(); r.addWidget(QLabel(lbl)); r.addWidget(w); il.addLayout(r)
        self.mod_name_edit = QLineEdit(); self.mod_name_edit.setPlaceholderText("ex: SuperMod")
        self.mod_id_edit   = QLineEdit(); self.mod_id_edit.setPlaceholderText("ex: supermod  (minuscules, sans espaces)")
        self.mod_ver_edit  = QLineEdit(); self.mod_ver_edit.setText("1.0.0")
        self.author_edit   = QLineEdit(); self.author_edit.setPlaceholderText("ex: mimiguaip")
        _row("Nom du mod :",   self.mod_name_edit)
        _row("Mod ID :",       self.mod_id_edit)
        _row("Version :",      self.mod_ver_edit)
        _row("Auteur :",       self.author_edit)
        lay.addWidget(info)

        # ── Dossier de destination ────────────────────────────────────
        dest = QGroupBox("Dossier de destination")
        dl   = QHBoxLayout(dest)
        self.dest_edit = QLineEdit(); self.dest_edit.setPlaceholderText("Choisir un dossier…")
        browse = QPushButton("📂"); browse.setFixedWidth(30); browse.clicked.connect(self._browse)
        dl.addWidget(self.dest_edit); dl.addWidget(browse)
        lay.addWidget(dest)

        # ── Log + progression ─────────────────────────────────────────
        self.log_view = QPlainTextEdit(); self.log_view.setReadOnly(True); self.log_view.setMaximumHeight(90)
        lay.addWidget(self.log_view)
        self.bar = QProgressBar(); self.bar.setFixedHeight(4); self.bar.hide(); lay.addWidget(self.bar)

        # ── Boutons ───────────────────────────────────────────────────
        row = QHBoxLayout()
        self.create_btn = QPushButton("🚀 Créer le projet"); self.create_btn.setObjectName("build_btn")
        self.create_btn.clicked.connect(self._start)
        self.cancel_btn = QPushButton("Annuler"); self.cancel_btn.clicked.connect(self.reject)
        row.addWidget(self.create_btn); row.addWidget(self.cancel_btn)
        lay.addLayout(row)

        # Auto-générer le mod_id depuis le nom
        self.mod_name_edit.textChanged.connect(lambda t: self.mod_id_edit.setText(
            re.sub(r'[^a-z0-9_]', '', t.lower().replace(' ', '_'))[:64]
        ))

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Dossier parent du projet", str(Path.home()))
        if d: self.dest_edit.setText(d)

    def _log(self, msg):
        self.log_view.appendPlainText(msg)

    def _start(self):
        dest_parent = self.dest_edit.text().strip()
        mod_name    = self.mod_name_edit.text().strip()
        mod_id      = self.mod_id_edit.text().strip()
        if not dest_parent:
            QMessageBox.warning(self, "Dossier manquant", "Choisissez un dossier de destination."); return
        if not mod_name or not mod_id:
            QMessageBox.warning(self, "Informations manquantes", "Renseignez le nom et l'ID du mod."); return
        if not re.match(r'^[a-z0-9_]+$', mod_id):
            QMessageBox.warning(self, "Mod ID invalide", "Le mod ID ne peut contenir que des lettres minuscules, chiffres et _"); return

        self.create_btn.setEnabled(False); self.cancel_btn.setEnabled(False)
        self.bar.setRange(0,0); self.bar.show()
        self._log(f"Téléchargement du MDK {self.loader} {self.mc_version} …")

        self._dl_thread = MDKDownloadThread(self.loader, self.mc_version)
        self._dl_thread.log.connect(self._log)
        self._dl_thread.progress.connect(lambda d,t: (self.bar.setRange(0,t), self.bar.setValue(d)) if t > 0 else None)
        self._dl_thread.finished.connect(lambda ok, val: self._on_dl_done(ok, val, Path(dest_parent), mod_name, mod_id))
        self._dl_thread.start()

    def _on_dl_done(self, ok: bool, val: str, dest_parent: Path, mod_name: str, mod_id: str):
        self.bar.hide()
        if not ok:
            self._log(f"❌ Erreur : {val}"); self.create_btn.setEnabled(True); self.cancel_btn.setEnabled(True); return

        mdk_cache = Path(val)   # get_mdk_dir() / loader / mc_version
        zip_path  = mdk_cache / "mdk.zip"
        proj_dir  = dest_parent / mod_id

        self._log(f"📦 Extraction dans {proj_dir} …")
        try:
            if proj_dir.exists(): shutil.rmtree(proj_dir)
            proj_dir.mkdir(parents=True)

            with zipfile.ZipFile(zip_path) as zf:
                # La plupart des MDK ont un dossier racine dans le zip (ex "forge-1.20.1-47.4.17-mdk/")
                # On détecte ce préfixe et on l'enlève à l'extraction
                members = zf.namelist()
                # Trouver le préfixe commun (dossier racine du zip)
                first = members[0] if members else ""
                prefix = first.split("/")[0] + "/" if "/" in first else ""
                if prefix and all(m.startswith(prefix) for m in members):
                    # Extraction sans le dossier racine
                    for member in members:
                        rel = member[len(prefix):]
                        if not rel: continue
                        target = proj_dir / rel
                        if member.endswith("/"):
                            target.mkdir(parents=True, exist_ok=True)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(zf.read(member))
                else:
                    zf.extractall(proj_dir)

            # ── Personnalisation du projet ────────────────────────────
            self._log("⚙ Configuration du projet …")
            mod_ver  = self.mod_ver_edit.text().strip() or "1.0.0"
            author   = self.author_edit.text().strip() or "DevStudioPro"
            mc_ver   = self.mc_version
            self._patch_project(proj_dir, mod_name, mod_id, mod_ver, author, mc_ver)

            self._log(f"✅ Projet créé dans {proj_dir}")
            self.result_path = proj_dir
            self.cancel_btn.setText("Ouvrir le projet"); self.cancel_btn.setEnabled(True)
            self.cancel_btn.clicked.disconnect(); self.cancel_btn.clicked.connect(self.accept)

        except Exception as e:
            import traceback as _tb
            self._log(f"❌ {e}\n{_tb.format_exc()}")
            self.create_btn.setEnabled(True); self.cancel_btn.setEnabled(True)

    def _patch_project(self, proj: Path, mod_name: str, mod_id: str,
                        mod_ver: str, author: str, mc_ver: str):
        """Remplace les placeholders du MDK par les valeurs du projet."""
        replacements = {
            # Forge / NeoForge patterns communs dans build.gradle
            "examplemod":          mod_id,
            "MODID":               mod_id,
            "modid":               mod_id,
            "ExampleMod":          mod_name,
            "Example Mod":         mod_name,
            "1.0.0":               mod_ver,
            "exampleplayer":       author.lower(),
            "Your Name":           author,
            "com.example":         f"com.{author.lower().replace(' ','_')}",
        }

        # Fichiers à patcher
        for pattern in ["build.gradle", "gradle.properties", "settings.gradle",
                         "**/mods.toml", "**/fabric.mod.json", "**/quilt.mod.json",
                         "**/*.java"]:
            for f in proj.glob(pattern):
                if f.is_file():
                    try:
                        text = f.read_text(encoding="utf-8", errors="replace")
                        orig = text
                        for old, new in replacements.items():
                            text = text.replace(old, new)
                        if text != orig:
                            f.write_text(text, encoding="utf-8")
                    except Exception:
                        pass

        # Renommer le dossier source principal si examplemod → mod_id
        for candidate in list(proj.rglob("examplemod")):
            if candidate.is_dir():
                try: candidate.rename(candidate.parent / mod_id)
                except Exception: pass

        # Renommer ExampleMod.java → <ModName>.java
        for candidate in list(proj.rglob("ExampleMod.java")):
            try: candidate.rename(candidate.parent / f"{mod_name.replace(' ','')}.java")
            except Exception: pass



def inject_gradle_wrapper(project_path: Path, loader: str, mc_version: str,
                          output_fn=None) -> bool:
    """
    Copie les fichiers Gradle wrapper manquants depuis le MDK en cache.
    Fichiers copiés uniquement s'ils sont absents dans le projet :
      - gradlew  /  gradlew.bat
      - gradle/wrapper/gradle-wrapper.jar
      - gradle/wrapper/gradle-wrapper.properties
    Retourne True si au moins un fichier a été copié.
    """
    WRAPPER_FILES = [
        "gradlew", "gradlew.bat",
        "gradle/wrapper/gradle-wrapper.jar",
        "gradle/wrapper/gradle-wrapper.properties",
    ]

    def _log(msg):
        if output_fn: output_fn(msg)

    # Cherche le MDK en cache
    mdk_zip = get_mdk_dir() / loader / mc_version / "mdk.zip"
    if not mdk_zip.exists():
        _log(f"[wrapper] MDK {loader} {mc_version} non en cache — téléchargement ignoré")
        return False

    copied = False
    try:
        with zipfile.ZipFile(mdk_zip) as zf:
            members = zf.namelist()
            # Détecter le préfixe racine du zip (ex: "forge-1.20.1-47.4.17-mdk/")
            first = members[0] if members else ""
            prefix = (first.split("/")[0] + "/") if "/" in first and all(
                m.startswith(first.split("/")[0] + "/") for m in members
            ) else ""

            for rel_path in WRAPPER_FILES:
                dest = project_path / rel_path
                if dest.exists():
                    continue  # déjà présent, on ne touche pas
                zip_path = prefix + rel_path
                if zip_path not in members:
                    # Essai sans préfixe
                    zip_path = rel_path
                if zip_path not in members:
                    _log(f"[wrapper] ⚠ {rel_path} introuvable dans le MDK")
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(zip_path))
                if not IS_WIN and rel_path in ("gradlew",):
                    dest.chmod(0o755)
                _log(f"[wrapper] ✓ {rel_path} injecté depuis le MDK")
                copied = True
    except Exception as e:
        _log(f"[wrapper] ❌ Erreur injection : {e}")
        return False

    return copied

class MinecraftBuildPanel(QWidget):
    def __init__(self, output: OutputPanel, settings: QSettings, parent=None):
        super().__init__(parent)
        self.output   = output
        self.settings = settings
        self.project_path: Optional[Path] = None
        self.java_home: Optional[Path] = None
        self._worker: Optional[RunWorker] = None
        self._inst_panel_ref = None  # set by MainWindow after build_ui

        lay = QVBoxLayout(self); lay.setContentsMargins(4,4,4,4); lay.setSpacing(6)

        # ── Loader + Version ────────────────────────────────────
        cfg = QGroupBox("Configuration du mod")
        cfg_l = QVBoxLayout(cfg); cfg_l.setContentsMargins(8,4,8,8); cfg_l.setSpacing(6)

        # ── Étape 1 : créer TOUS les widgets avant de brancher TOUT signal ──
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Loader :"))
        self.loader_combo = QComboBox()
        self.loader_combo.addItems(list(MC_LOADERS.keys()))
        row1.addWidget(self.loader_combo); row1.addSpacing(16)
        row1.addWidget(QLabel("Version MC :"))
        self.ver_combo = QComboBox(); row1.addWidget(self.ver_combo); row1.addStretch()
        cfg_l.addLayout(row1)

        # JDK status — créé AVANT toute connexion de signal
        jdk_row = QHBoxLayout()
        self.jdk_lbl = QLabel("☕ JDK : non détecté ⚠")
        self.jdk_lbl.setStyleSheet(f"color:{DARK['yellow']};font-size:11px;")
        jdk_row.addWidget(self.jdk_lbl)
        self.jdk_dl_btn = QPushButton("⬇ Télécharger JDK")
        self.jdk_dl_btn.setFixedHeight(24)
        self.jdk_dl_btn.setVisible(False)
        self.jdk_dl_btn.clicked.connect(self._download_jdk)
        jdk_row.addWidget(self.jdk_dl_btn); jdk_row.addStretch()
        cfg_l.addLayout(jdk_row)

        # MDK status
        mdk_row = QHBoxLayout()
        self.mdk_lbl = QLabel("📦 MDK : non vérifié")
        self.mdk_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;")
        mdk_row.addWidget(self.mdk_lbl)
        self.mdk_dl_btn = QPushButton("⬇ Télécharger MDK")
        self.mdk_dl_btn.setFixedHeight(24)
        self.mdk_dl_btn.clicked.connect(self._download_mdk)
        mdk_row.addWidget(self.mdk_dl_btn); mdk_row.addStretch()
        cfg_l.addLayout(mdk_row)
        lay.addWidget(cfg)

        # ── Boutons ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.new_proj_btn = QPushButton("✨ Nouveau projet")
        self.new_proj_btn.setToolTip("Créer un nouveau projet mod depuis le MDK")
        self.new_proj_btn.clicked.connect(self._new_project)
        self.build_btn = QPushButton("🔨 Build"); self.build_btn.setObjectName("build_btn")
        self.build_btn.clicked.connect(self._start_build)
        self.clean_btn = QPushButton("🧹 Clean"); self.clean_btn.clicked.connect(self._clean)
        self.open_btn  = QPushButton("📦 build/libs/"); self.open_btn.clicked.connect(self._open_output)
        self.open_btn.setEnabled(False)
        btn_row.addWidget(self.new_proj_btn); btn_row.addWidget(self.build_btn)
        btn_row.addWidget(self.clean_btn); btn_row.addWidget(self.open_btn)
        btn_row.addStretch(); lay.addLayout(btn_row)

        self.mc_progress = QProgressBar()
        self.mc_progress.setRange(0, 0); self.mc_progress.setFixedHeight(4); self.mc_progress.hide()
        lay.addWidget(self.mc_progress)

        # Notes de version
        notes_row = QHBoxLayout(); notes_row.addWidget(QLabel("Notes release :"))
        self.notes_edit = QLineEdit(); self.notes_edit.setPlaceholderText("ex: Ajout de la détection de fly …")
        notes_row.addWidget(self.notes_edit); lay.addLayout(notes_row)
        lay.addStretch()

        # ── Étape 2 : brancher les signaux maintenant que tout existe ──
        self.loader_combo.currentTextChanged.connect(self._on_loader_change)
        self.ver_combo.currentTextChanged.connect(self._on_version_change)

        # ── Étape 3 : restaurer les préférences enregistrées ──
        saved_loader = self.settings.value("mc_loader", "Forge")
        saved_ver    = self.settings.value("mc_version", "")
        # Peupler ver_combo SANS déclencher les signaux, puis appel unique à la fin
        self.loader_combo.blockSignals(True); self.ver_combo.blockSignals(True)
        idx_l = self.loader_combo.findText(saved_loader)
        if idx_l >= 0: self.loader_combo.setCurrentIndex(idx_l)
        self.ver_combo.addItems(list(MC_LOADERS.get(self.loader_combo.currentText(), {}).keys()))
        idx_v = self.ver_combo.findText(saved_ver)
        if idx_v >= 0: self.ver_combo.setCurrentIndex(idx_v)
        self.loader_combo.blockSignals(False); self.ver_combo.blockSignals(False)
        # Appel unique et sûr : jdk_lbl + jdk_dl_btn existent déjà
        self._on_version_change(self.ver_combo.currentText())

    def _on_loader_change(self, loader):
        self.ver_combo.blockSignals(True); self.ver_combo.clear()
        self.ver_combo.addItems(list(MC_LOADERS.get(loader, {}).keys()))
        self.ver_combo.blockSignals(False); self._on_version_change(self.ver_combo.currentText())

    def _on_version_change(self, ver):
        if not ver: return
        loader = self.loader_combo.currentText()
        self.settings.setValue("mc_loader", loader); self.settings.setValue("mc_version", ver)
        java_ver = MC_LOADERS.get(loader, {}).get(ver, {}).get("java", 17)
        self._check_jdk(java_ver)
        self._check_mdk(loader, ver)

    def _check_mdk(self, loader: str, ver: str):
        """Vérifie si le MDK est en cache et met à jour le label."""
        mdk_zip = get_mdk_dir() / loader / ver / "mdk.zip"
        if mdk_zip.exists():
            size_mb = mdk_zip.stat().st_size / 1e6
            self.mdk_lbl.setText(f"📦 MDK {loader} {ver} ✓  ({size_mb:.1f} Mo)")
            self.mdk_lbl.setStyleSheet(f"color:{DARK['green']};font-size:11px;")
            self.mdk_dl_btn.setText("🔄 Re-télécharger")
        else:
            self.mdk_lbl.setText(f"📦 MDK {loader} {ver} : non téléchargé")
            self.mdk_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;")
            self.mdk_dl_btn.setText("⬇ Télécharger MDK")

    def _download_mdk(self):
        """Lance le téléchargement du MDK en arrière-plan."""
        loader = self.loader_combo.currentText()
        ver    = self.ver_combo.currentText()
        self.mdk_dl_btn.setEnabled(False)
        self.mdk_lbl.setText(f"📦 Téléchargement MDK {loader} {ver} …")
        self.mdk_lbl.setStyleSheet(f"color:{DARK['yellow']};font-size:11px;")

        self._mdk_thread = MDKDownloadThread(loader, ver)
        self._mdk_thread.log.connect(self.output.write_info)
        self._mdk_thread.finished.connect(lambda ok, val: self._on_mdk_done(ok, val, loader, ver))
        self._mdk_thread.start()

    def _on_mdk_done(self, ok: bool, val: str, loader: str, ver: str):
        self.mdk_dl_btn.setEnabled(True)
        if ok:
            self._check_mdk(loader, ver)
            self.output.write_ok(f"[mdk] ✅ MDK {loader} {ver} téléchargé dans {val}")
        else:
            self.mdk_lbl.setText(f"📦 MDK : erreur ⚠")
            self.mdk_lbl.setStyleSheet(f"color:{DARK['red']};font-size:11px;")
            self.output.write_err(f"[mdk] ❌ {val}")

    def _new_project(self):
        """Ouvre le dialog de création de nouveau projet mod."""
        loader = self.loader_combo.currentText()
        ver    = self.ver_combo.currentText()
        dlg    = NewModProjectDialog(loader, ver, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_path:
            # Ouvrir le projet dans DevStudio
            parent_win = self.window()
            if hasattr(parent_win, "_load_project"):
                parent_win._load_project(dlg.result_path)
                self.output.write_ok(f"[mdk] Projet ouvert : {dlg.result_path}")

    def _required_java(self) -> int:
        loader = self.loader_combo.currentText(); ver = self.ver_combo.currentText()
        return MC_LOADERS.get(loader, {}).get(ver, {}).get("java", 17)

    def _check_jdk(self, java_ver: int):
        self.java_home = None
        # 1. JDK dans le dossier app (partagé, priorité)
        jdk = find_app_jdk(java_ver)
        if jdk:
            self.java_home = jdk
            self.jdk_lbl.setText(f"☕ JDK {java_ver} (app) ✓")
            self.jdk_lbl.setStyleSheet(f"color:{DARK['green']};")
            self.jdk_dl_btn.setVisible(False); return
        # 2. JDK dans le projet (rétro-compat)
        if self.project_path:
            jdk = _scan_jdk_dir(self.project_path / ".jdk" / f"jdk{java_ver}")
            if jdk:
                self.java_home = jdk
                self.jdk_lbl.setText(f"☕ JDK {java_ver} (projet) ✓")
                self.jdk_lbl.setStyleSheet(f"color:{DARK['green']};")
                self.jdk_dl_btn.setVisible(False); return
        # 3. JDK système
        jdk = detect_system_java(java_ver)
        if jdk:
            self.java_home = jdk
            self.jdk_lbl.setText(f"☕ JDK {java_ver} (système) ✓")
            self.jdk_lbl.setStyleSheet(f"color:{DARK['green']};")
            self.jdk_dl_btn.setVisible(False); return
        # 4. Pas trouvé
        self.jdk_lbl.setText(f"☕ JDK {java_ver} introuvable ⚠")
        self.jdk_lbl.setStyleSheet(f"color:{DARK['yellow']};")
        self.jdk_dl_btn.setVisible(True)

    def _download_jdk(self):
        java_ver = self._required_java()
        dlg = JDKDownloadDialog(java_ver, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.jdk_home:
            self.java_home = dlg.jdk_home
            self.jdk_lbl.setText(f"☕ JDK {java_ver} (app) ✓")
            self.jdk_lbl.setStyleSheet(f"color:{DARK['green']};")
            self.jdk_dl_btn.setVisible(False)

    def set_project(self, path: Path):
        self.project_path = path
        self._on_version_change(self.ver_combo.currentText())

    def _start_build(self):
        if not self.project_path: QMessageBox.warning(self, "Pas de projet", "Ouvrez un projet."); return
        if self._worker and self._worker.isRunning(): return

        loader = self.loader_combo.currentText()
        ver    = self.ver_combo.currentText()

        # ── Injecter les fichiers Gradle wrapper depuis le MDK si manquants ──
        gradlew = self.project_path / ("gradlew.bat" if IS_WIN else "gradlew")
        if not gradlew.exists():
            self.output.write_info("[wrapper] gradlew absent — tentative d'injection depuis le MDK …")
            ok = inject_gradle_wrapper(
                self.project_path, loader, ver,
                output_fn=self.output.write_info
            )
            if ok:
                self.output.write_ok("[wrapper] ✅ Fichiers Gradle wrapper injectés.")
            else:
                # MDK pas encore en cache → proposer de le télécharger
                rep = QMessageBox.question(
                    self, "MDK requis",
                    f"gradlew introuvable et le MDK {loader} {ver} n'est pas en cache.\n\n"
                    "Voulez-vous télécharger le MDK maintenant ?\n"
                    "(Ceci permet d'injecter gradlew dans votre projet)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if rep == QMessageBox.StandardButton.Yes:
                    self._download_mdk()
                else:
                    self.output.write_err("❌ gradlew introuvable — Build annulé.")
                return

        # Vérifier de nouveau après injection
        gradlew = self.project_path / ("gradlew.bat" if IS_WIN else "gradlew")
        if not gradlew.exists():
            self.output.write_err("❌ gradlew toujours introuvable après injection.")
            return
        if not IS_WIN: gradlew.chmod(0o755)

        env = os.environ.copy()
        if self.java_home:
            env["JAVA_HOME"] = str(self.java_home)
            env["PATH"] = str(self.java_home/"bin") + os.pathsep + env.get("PATH","")

        self.output.write_info("═"*55)
        self.output.write_info(f"⛏ Build {loader} {ver} — {self.project_path.name}")
        self.output.write_info(f"   Java home : {self.java_home or '(système)'}")
        self.output.write_info("═"*55)

        self.build_btn.setEnabled(False); self.mc_progress.show()
        self._worker = RunWorker([str(gradlew), "build", "--no-daemon"], cwd=str(self.project_path), env=env)
        self._worker.output.connect(self._on_gradle_line)
        self._worker.error.connect(self._on_gradle_line)
        self._worker.finished_rc.connect(self._on_build_done); self._worker.start()

    def _on_gradle_line(self, line):
        lo = line.lower()
        if "build successful" in lo:                     self.output.write_ok(line)
        elif "build failed" in lo or ": error:" in lo:  self.output.write_err(line)
        elif "warning:" in lo or "warn" in lo:           self.output.write_warn(line)
        elif line.startswith("> task") or line.startswith("> configure"): self.output.write_task(line)
        else:                                             self.output.write(line)

    def _on_build_done(self, rc):
        self.build_btn.setEnabled(True); self.mc_progress.hide()
        if rc == 0:
            self.output.write_info("═"*55); self.output.write_ok("✅ BUILD SUCCESSFUL"); self.output.write_info("═"*55)
            self.open_btn.setEnabled(True)
            # Notify instance panel for auto-copy
            if self.project_path and hasattr(self, "_inst_panel_ref") and self._inst_panel_ref:
                self._inst_panel_ref.notify_build_done(self.project_path)
        else:
            self.output.write_info("═"*55); self.output.write_err("❌ BUILD FAILED"); self.output.write_info("═"*55)

    def _clean(self):
        if not self.project_path: return
        bd = self.project_path / "build"
        if bd.exists(): shutil.rmtree(bd); self.output.write_info("🧹 build/ supprimé"); self.open_btn.setEnabled(False)
        else: self.output.write_info("build/ déjà vide")

    def _open_output(self):
        if not self.project_path: return
        libs = self.project_path / "build" / "libs"
        if libs.exists():
            if IS_WIN:                     os.startfile(str(libs))
            elif platform.system()=="Darwin": subprocess.run(["open", str(libs)])
            else:                              subprocess.run(["xdg-open", str(libs)])
        else:
            QMessageBox.warning(self, "Pas encore compilé", "build/libs/ n'existe pas.")

# ════════════════════════════════════════════════════════════════
#  PANNEAU GITHUB
# ════════════════════════════════════════════════════════════════


class GitHubPanel(QWidget):
    """
    Panneau GitHub — workflow basé sur un dossier de sync par projet.
    Le dossier <projet>/.devstudio/github/ est le clone git local.
    Seuls les fichiers spécifiés dans .devstudio/github_files.txt y sont copiés.
    """
    def __init__(self, output: OutputPanel, settings: QSettings, parent=None):
        super().__init__(parent)
        self.output       = output
        self.settings     = settings
        self.project_path: Optional[Path] = None
        self._worker: Optional[RunWorker] = None

        lay = QVBoxLayout(self); lay.setContentsMargins(4,4,4,4); lay.setSpacing(5)

        # ── Auth ─────────────────────────────────────────────────
        auth = QGroupBox("Authentification GitHub")
        al = QHBoxLayout(auth); al.setContentsMargins(8,4,8,4)
        al.addWidget(QLabel("Token :"))
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("ghp_xxxx…")
        self.token_edit.setText(self.settings.value("github_token", ""))
        self.token_edit.editingFinished.connect(
            lambda: self.settings.setValue("github_token", self.token_edit.text().strip()))
        al.addWidget(self.token_edit)
        al.addWidget(QLabel("Branche :"))
        self.branch_edit = QLineEdit(); self.branch_edit.setFixedWidth(80)
        self.branch_edit.setText(self.settings.value("github_branch", "main"))
        self.branch_edit.editingFinished.connect(
            lambda: self.settings.setValue("github_branch", self.branch_edit.text().strip()))
        al.addWidget(self.branch_edit); lay.addWidget(auth)

        # ── Dépôt ────────────────────────────────────────────────
        repo_grp = QGroupBox("Dépôt GitHub")
        rl = QVBoxLayout(repo_grp); rl.setContentsMargins(8,4,8,8); rl.setSpacing(4)
        rr = QHBoxLayout(); rr.addWidget(QLabel("URL remote :"))
        self.remote_edit = QLineEdit()
        self.remote_edit.setPlaceholderText("https://github.com/user/repo.git")
        self.remote_edit.setText(self.settings.value("github_remote", ""))
        self.remote_edit.editingFinished.connect(
            lambda: self.settings.setValue("github_remote", self.remote_edit.text().strip()))
        rr.addWidget(self.remote_edit); rl.addLayout(rr)

        # Dossier de sync
        sf = QHBoxLayout(); sf.addWidget(QLabel("Sync folder :"))
        self.sync_edit = QLineEdit()
        self.sync_edit.setPlaceholderText(".devstudio/github  (dossier clone git)")
        self.sync_edit.setToolTip(
            "Dossier git clone dans votre projet.\n"
            "Seuls les fichiers listés dans .devstudio/github_files.txt seront copiés ici.\n"
            "Laissez vide pour utiliser le défaut (.devstudio/github)")
        sf.addWidget(self.sync_edit)
        rl.addLayout(sf)

        self.sync_info = QLabel("📁 Dossier de sync : non configuré")
        self.sync_info.setStyleSheet(f"color:{DARK['text_dim']};font-size:10px;")
        rl.addWidget(self.sync_info)

        init_row = QHBoxLayout()
        self.clone_btn  = QPushButton("⬇ Cloner / Connecter le dépôt")
        self.clone_btn.setObjectName("promote_btn")
        self.clone_btn.setToolTip("Clone le dépôt distant dans le sync folder,\nou connecte un dépôt existant.")
        self.clone_btn.clicked.connect(self._clone_or_connect)
        self.pull_btn   = QPushButton("🔄 Pull (MàJ depuis GitHub)")
        self.pull_btn.clicked.connect(self._pull)
        init_row.addWidget(self.clone_btn); init_row.addWidget(self.pull_btn)
        rl.addLayout(init_row); lay.addWidget(repo_grp)

        # ── Fichiers à publier ────────────────────────────────────
        files_grp = QGroupBox("Fichiers à publier")
        fl = QVBoxLayout(files_grp); fl.setContentsMargins(8,4,8,8); fl.setSpacing(4)
        fl.addWidget(QLabel(
            "Listez les fichiers/dossiers à inclure dans le dépôt\n"
            "(un par ligne, chemins relatifs au projet, supports glob ex: src/**)"
        ).setStyleSheet if False else
        self._small_lbl(
            "Un fichier/dossier par ligne — chemins relatifs au projet (glob supporté, ex: src/**)"))
        self.files_edit = QPlainTextEdit()
        self.files_edit.setFixedHeight(80)
        self.files_edit.setPlaceholderText(
            "DevStudioPro.pyw\nrun.bat\nrun.sh\nREADME.md\nLICENSE\n.gitignore")
        self.files_edit.setFont(QFont("Consolas", 10))
        fl.addWidget(self.files_edit)
        edit_files_btn = QPushButton("📄 Éditer .devstudio/github_files.txt")
        edit_files_btn.clicked.connect(self._open_files_config)
        fl.addWidget(edit_files_btn)
        lay.addWidget(files_grp)

        # ── Commit + Push ─────────────────────────────────────────
        commit_grp = QGroupBox("Commit + Push")
        cl = QVBoxLayout(commit_grp); cl.setContentsMargins(8,4,8,8); cl.setSpacing(4)
        self.git_status_lbl = QLabel("État : –")
        self.git_status_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;")
        cl.addWidget(self.git_status_lbl)
        mr = QHBoxLayout(); mr.addWidget(QLabel("Message :"))
        self.commit_edit = QLineEdit()
        self.commit_edit.setPlaceholderText("feat: description du commit")
        mr.addWidget(self.commit_edit); cl.addLayout(mr)
        br = QHBoxLayout()
        self.status_btn = QPushButton("🔄 Statut"); self.status_btn.clicked.connect(self._git_status)
        self.sync_push_btn = QPushButton("⬆ Synchroniser + Push")
        self.sync_push_btn.setObjectName("gh_btn")
        self.sync_push_btn.setToolTip(
            "1. Copie les fichiers listés → sync folder\n"
            "2. git add + commit\n"
            "3. git push")
        self.sync_push_btn.clicked.connect(self._sync_and_push)
        br.addWidget(self.status_btn); br.addWidget(self.sync_push_btn)
        cl.addLayout(br); lay.addWidget(commit_grp)

        # ── Release ───────────────────────────────────────────────
        rel_grp = QGroupBox("Release GitHub")
        rrel = QVBoxLayout(rel_grp); rrel.setContentsMargins(8,4,8,8); rrel.setSpacing(4)
        tr = QHBoxLayout(); tr.addWidget(QLabel("Tag :"))
        self.tag_edit = QLineEdit(); self.tag_edit.setPlaceholderText("v1.0.0"); self.tag_edit.setFixedWidth(90)
        tr.addWidget(self.tag_edit); tr.addWidget(QLabel("Nom :"))
        self.rel_name_edit = QLineEdit(); self.rel_name_edit.setPlaceholderText("Version 1.0.0")
        tr.addWidget(self.rel_name_edit); rrel.addLayout(tr)
        nr = QHBoxLayout(); nr.addWidget(QLabel("Notes :"))
        self.rel_notes = QLineEdit(); self.rel_notes.setPlaceholderText("Description de la release …")
        nr.addWidget(self.rel_notes); rrel.addLayout(nr)
        ar = QHBoxLayout(); ar.addWidget(QLabel("Fichier :"))
        self.asset_path_edit = QLineEdit(); self.asset_path_edit.setPlaceholderText("(optionnel) .jar ou .exe")
        ar.addWidget(self.asset_path_edit)
        bb = QPushButton("📂"); bb.setFixedWidth(28); bb.clicked.connect(self._browse_asset)
        ar.addWidget(bb); rrel.addLayout(ar)
        self.prerelease_chk = QCheckBox("Pré-release"); rrel.addWidget(self.prerelease_chk)
        self.create_rel_btn = QPushButton("🚀 Créer la Release")
        self.create_rel_btn.setObjectName("promote_btn"); self.create_rel_btn.clicked.connect(self._create_release)
        rrel.addWidget(self.create_rel_btn); lay.addWidget(rel_grp)

        self.gh_progress = QProgressBar(); self.gh_progress.setRange(0,0)
        self.gh_progress.setFixedHeight(4); self.gh_progress.hide()
        lay.addWidget(self.gh_progress); lay.addStretch()

    @staticmethod
    def _small_lbl(txt):
        l = QLabel(txt); l.setStyleSheet(f"color:{DARK['text_dim']};font-size:10px;"); return l

    # ── Dossier de sync ───────────────────────────────────────────

    def _sync_dir(self) -> Path:
        """Retourne le chemin absolu du dossier de sync (clone git)."""
        custom = self.sync_edit.text().strip()
        if custom:
            p = Path(custom)
            if not p.is_absolute() and self.project_path:
                p = self.project_path / p
            return p
        if self.project_path:
            return self.project_path / ".devstudio" / "github"
        return Path.cwd() / ".devstudio" / "github"

    def _files_config(self) -> Path:
        if self.project_path:
            return self.project_path / ".devstudio" / "github_files.txt"
        return Path(".devstudio/github_files.txt")

    def _load_files_list(self) -> list[str]:
        fc = self._files_config()
        if fc.exists():
            lines = [l.strip() for l in fc.read_text(encoding="utf-8").splitlines()]
            return [l for l in lines if l and not l.startswith("#")]
        return []

    def _save_files_list(self, lines: list[str]):
        fc = self._files_config(); fc.parent.mkdir(parents=True, exist_ok=True)
        fc.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _open_files_config(self):
        fc = self._files_config(); fc.parent.mkdir(parents=True, exist_ok=True)
        if not fc.exists():
            current = self.files_edit.toPlainText().strip()
            fc.write_text(current or "# Ajoutez ici les fichiers à publier\n", encoding="utf-8")
        # Ouvrir dans l'éditeur de DevStudio
        parent_win = self.window()
        if hasattr(parent_win, "_open_file"):
            parent_win._open_file(fc)

    def _update_sync_info(self):
        sd = self._sync_dir()
        git_ok = (sd / ".git").exists()
        if git_ok:
            self.sync_info.setText(f"✅ Sync folder : {sd}")
            self.sync_info.setStyleSheet(f"color:{DARK['green']};font-size:10px;")
        else:
            self.sync_info.setText(f"📁 Sync folder : {sd}  (pas encore initialisé)")
            self.sync_info.setStyleSheet(f"color:{DARK['text_dim']};font-size:10px;")

    # ── Git helpers ───────────────────────────────────────────────

    def _git(self, args: list, cwd: Path = None) -> tuple[int, str]:
        d = cwd or self._sync_dir()
        try:
            r = subprocess.run(["git"] + args, cwd=str(d),
                               capture_output=True, text=True, timeout=60,
                               encoding="utf-8", errors="replace")
            out = (r.stdout + r.stderr).strip()
            return r.returncode, out
        except FileNotFoundError:
            return -1, "git introuvable dans le PATH"
        except Exception as e:
            return -1, str(e)

    def _inject_token_in_url(self, url: str, token: str) -> str:
        """Injecte le token dans l'URL https://github.com/… pour l'auth sans SSH."""
        if token and "github.com" in url and url.startswith("https://"):
            url = url.replace("https://", f"https://oauth2:{token}@", 1)
        return url

    # ── Clone / Connexion ─────────────────────────────────────────

    def _clone_or_connect(self):
        remote = self.remote_edit.text().strip()
        if not remote:
            QMessageBox.warning(self, "Remote manquant", "Entrez l'URL du dépôt GitHub."); return
        token  = self.token_edit.text().strip()
        branch = self.branch_edit.text().strip() or "main"
        sd = self._sync_dir(); sd.mkdir(parents=True, exist_ok=True)

        self.clone_btn.setEnabled(False)
        self.gh_progress.show()
        auth_url = self._inject_token_in_url(remote, token)

        def _do():
            if (sd / ".git").exists():
                # Dépôt déjà initialisé → juste mettre à jour le remote
                self._git(["remote", "set-url", "origin", auth_url])
                rc, out = self._git(["fetch", "origin"])
                if rc == 0:
                    self.output.write_ok(f"[git] ✅ Dépôt déjà connecté, remote mis à jour.")
                else:
                    self.output.write_err(f"[git] Fetch : {out}")
            else:
                # Cloner dans le dossier de sync
                self.output.write_info(f"[git] Clone {remote} → {sd} …")
                rc, out = self._git(["clone", auth_url, ".", "--branch", branch,
                                     "--no-single-branch"], cwd=sd)
                if rc != 0:
                    # Le dépôt est peut-être vide ou la branche n'existe pas
                    self.output.write_warn(f"[git] Clone standard échoué ({out}), init vide …")
                    self._git(["init"], cwd=sd)
                    self._git(["remote", "add", "origin", auth_url], cwd=sd)
                    self._git(["fetch", "origin"], cwd=sd)
                    rc2, _ = self._git(["checkout", "-b", branch], cwd=sd)
                    self.output.write_ok("[git] ✅ Dépôt initialisé (vide).")
                else:
                    self.output.write_ok(f"[git] ✅ Clone réussi → {sd}")

            # Configurer user si nécessaire
            rc_e, val_e = self._git(["config", "user.email"])
            if not val_e.strip():
                self._git(["config", "user.email", "devstudio@local"])
                self._git(["config", "user.name",  "DevStudio Pro"])

            QTimer.singleShot(0, lambda: (
                self.gh_progress.hide(),
                self.clone_btn.setEnabled(True),
                self._update_sync_info(),
                self._git_status()
            ))

        threading.Thread(target=_do, daemon=True).start()

    def _pull(self):
        sd = self._sync_dir()
        if not (sd / ".git").exists():
            QMessageBox.warning(self, "Pas de dépôt", "Clonez d'abord le dépôt."); return
        token  = self.token_edit.text().strip()
        remote = self.remote_edit.text().strip()
        if remote:
            auth_url = self._inject_token_in_url(remote, token)
            self._git(["remote", "set-url", "origin", auth_url])
        branch = self.branch_edit.text().strip() or "main"
        self.gh_progress.show()
        def _do():
            rc, out = self._git(["pull", "origin", branch, "--rebase"])
            QTimer.singleShot(0, lambda: (
                self.gh_progress.hide(),
                self.output.write_ok(f"[git] Pull : {out}") if rc == 0
                    else self.output.write_err(f"[git] Pull échoué : {out}"),
                self._git_status()
            ))
        threading.Thread(target=_do, daemon=True).start()

    # ── Sync files ────────────────────────────────────────────────

    def _sync_files_to_repo(self) -> int:
        """
        Copie les fichiers listés dans github_files.txt du projet vers le sync folder.
        Retourne le nombre de fichiers copiés/mis à jour.
        """
        if not self.project_path: return 0
        sd = self._sync_dir()
        # Sauvegarder d'abord depuis le widget si non vide
        txt = self.files_edit.toPlainText().strip()
        if txt:
            self._save_files_list([l.strip() for l in txt.splitlines() if l.strip()])
        file_patterns = self._load_files_list()
        if not file_patterns:
            # Défaut : fichiers typiques
            file_patterns = [
                "*.py", "*.pyw", "*.md", "*.txt", "LICENSE", ".gitignore",
                "run.bat", "run.sh", "assets/**"
            ]
        import glob as _glob
        copied = 0
        for pat in file_patterns:
            matches = list(self.project_path.glob(pat))
            if not matches:
                # Essai chemin direct
                direct = self.project_path / pat
                if direct.exists(): matches = [direct]
            for src in matches:
                if ".devstudio" in src.parts: continue
                try:
                    rel = src.relative_to(self.project_path)
                    dst = sd / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if src.is_file():
                        # Copier seulement si contenu différent
                        if not dst.exists() or dst.read_bytes() != src.read_bytes():
                            shutil.copy2(src, dst)
                            copied += 1
                except Exception:
                    pass
        return copied

    # ── Status + Commit + Push ────────────────────────────────────

    def _git_status(self):
        sd = self._sync_dir()
        if not (sd / ".git").exists():
            self.git_status_lbl.setText("État : dépôt non initialisé")
            return
        rc, out = self._git(["status", "--short"])
        if rc == 0:
            lines = [l for l in out.splitlines() if l.strip()]
            self.git_status_lbl.setText(
                f"État : {len(lines)} fichier(s) modifié(s)" if lines else "État : dépôt propre ✓")
            if lines: self.output.write_info(f"[git] status :\n{out}")

    def _sync_and_push(self):
        sd = self._sync_dir()
        if not (sd / ".git").exists():
            QMessageBox.warning(self, "Pas de dépôt",
                "Clonez d'abord le dépôt via 'Cloner / Connecter'."); return
        msg = self.commit_edit.text().strip()
        if not msg:
            QMessageBox.warning(self, "Message vide", "Entrez un message de commit."); return
        token  = self.token_edit.text().strip()
        remote = self.remote_edit.text().strip()
        branch = self.branch_edit.text().strip() or "main"

        self.sync_push_btn.setEnabled(False)
        self.gh_progress.show()

        def _do():
            # 1. Injecter token dans remote
            if remote:
                auth_url = self._inject_token_in_url(remote, token)
                self._git(["remote", "set-url", "origin", auth_url])

            # 2. Synchroniser les fichiers
            n = self._sync_files_to_repo()
            self.output.write_info(f"[git] {n} fichier(s) synchronisé(s) → {self._sync_dir()}")

            # 3. git add -A
            self._git(["add", "-A"])

            # 4. git commit
            rc_c, out_c = self._git(["commit", "-m", msg])
            if rc_c == 0:
                self.output.write_ok(f"[git] ✅ Commit : {msg}")
            else:
                if "nothing to commit" in out_c:
                    self.output.write_info("[git] Rien à commiter (aucun changement détecté).")
                else:
                    self.output.write_err(f"[git] Commit échoué : {out_c}")

            # 5. git push
            self.output.write_info(f"[git] Push vers origin/{branch} …")
            rc_p, out_p = self._git(["push", "-u", "origin", f"HEAD:{branch}"])
            if rc_p == 0:
                self.output.write_ok(f"[git] ✅ Push réussi → {remote or 'origin'}/{branch}")
            else:
                self.output.write_err(f"[git] ❌ Push échoué : {out_p}")
                self.output.write_warn(
                    "[git] Causes possibles : token invalide, pas les droits d'écriture,\n"
                    "       ou le dépôt a des commits que vous n'avez pas en local (faites un Pull d'abord).")

            QTimer.singleShot(0, lambda: (
                self.gh_progress.hide(),
                self.sync_push_btn.setEnabled(True),
                self.commit_edit.clear(),
                self._git_status()
            ))

        threading.Thread(target=_do, daemon=True).start()

    # ── Release ───────────────────────────────────────────────────

    def _browse_asset(self):
        p, _ = QFileDialog.getOpenFileName(self, "Choisir le fichier joint",
            str(self.project_path or Path.home()),
            "Fichiers (*.jar *.exe *.zip *.tar.gz);;Tous (*.*)")
        if p: self.asset_path_edit.setText(p)

    def _parse_remote(self) -> Optional[tuple[str,str]]:
        url = self.remote_edit.text().strip()
        if not url:
            rc, url = self._git(["remote", "get-url", "origin"])
            if rc != 0: return None
        m = re.search(r'github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$', url)
        return (m.group(1), m.group(2)) if m else None

    def _create_release(self):
        token = self.token_edit.text().strip()
        if not token:
            QMessageBox.warning(self, "Token manquant", "Entrez votre token GitHub."); return
        tag = self.tag_edit.text().strip()
        if not tag:
            QMessageBox.warning(self, "Tag manquant", "Entrez un tag ex: v1.0.0"); return
        info = self._parse_remote()
        if not info:
            QMessageBox.warning(self, "Remote introuvable",
                "Impossible de détecter owner/repo depuis l'URL remote."); return
        owner, repo = info
        name  = self.rel_name_edit.text().strip() or tag
        notes = self.rel_notes.text().strip()
        pre   = self.prerelease_chk.isChecked()
        asset = self.asset_path_edit.text().strip()
        branch = self.branch_edit.text().strip() or "main"

        # Push le tag
        self._git(["tag", "-f", tag])
        self._git(["push", "origin", f"HEAD:{branch}", "--tags", "--force"])

        self.gh_progress.show()
        self.output.write_info(f"[github] Création de la release {tag} ({owner}/{repo}) …")

        def _do():
            import urllib.request as _ur, urllib.error as _ue, json as _j, urllib.parse as _up
            hdrs = {"Authorization": f"token {token}", "Content-Type": "application/json",
                    "User-Agent": "DevStudioPro"}
            try:
                # Vérifier si la release existe
                rel_data = None
                try:
                    req = _ur.Request(
                        f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}",
                        headers=hdrs)
                    with _ur.urlopen(req, timeout=10) as r:
                        rel_data = _j.loads(r.read())
                    self.output.write_info(f"[github] Release {tag} existante — réutilisation.")
                except _ue.HTTPError as e:
                    if e.code != 404: raise

                if rel_data is None:
                    payload = _j.dumps({
                        "tag_name": tag, "name": name,
                        "body": notes, "prerelease": pre,
                        "target_commitish": branch
                    }).encode()
                    req = _ur.Request(
                        f"https://api.github.com/repos/{owner}/{repo}/releases",
                        data=payload, headers=hdrs, method="POST")
                    with _ur.urlopen(req, timeout=20) as r:
                        rel_data = _j.loads(r.read())
                    self.output.write_ok(f"[github] ✅ Release créée : {rel_data['html_url']}")

                upload_url = rel_data["upload_url"].split("{")[0]

                if asset and Path(asset).exists():
                    ap = Path(asset)
                    safe = _up.quote(ap.name, safe="")
                    self.output.write_info(f"[github] Upload de {ap.name} …")
                    with open(ap, "rb") as f: data = f.read()
                    ureq = _ur.Request(f"{upload_url}?name={safe}", data=data,
                                       headers={**hdrs, "Content-Type": "application/octet-stream"},
                                       method="POST")
                    with _ur.urlopen(ureq, timeout=120) as r2:
                        up = _j.loads(r2.read())
                        self.output.write_ok(f"[github] ✅ Asset : {up.get('browser_download_url','')}")

            except _ue.HTTPError as e:
                self.output.write_err(f"[github] ❌ HTTP {e.code} : {e.read().decode()[:300]}")
            except Exception as e:
                self.output.write_err(f"[github] ❌ {e}")
            finally:
                QTimer.singleShot(0, self.gh_progress.hide)

        threading.Thread(target=_do, daemon=True).start()

    # ── set_project ───────────────────────────────────────────────

    def set_project(self, path: Path):
        self.project_path = path
        # Charger les fichiers de config existants
        fc = self._files_config()
        if fc.exists():
            self.files_edit.setPlainText(fc.read_text(encoding="utf-8"))
        else:
            # Remplir avec des valeurs par défaut sensées
            self.files_edit.setPlainText(
                "DevStudioPro.pyw\nrun.bat\nrun.sh\nREADME.md\nLICENSE\n.gitignore\nassets/")
        # Détecter remote existant dans le sync folder
        sd = self._sync_dir()
        if (sd / ".git").exists():
            rc, url = self._git(["remote", "get-url", "origin"])
            if rc == 0 and url and not self.remote_edit.text():
                clean = re.sub(r'oauth2:[^@]+@', '', url)
                self.remote_edit.setText(clean)
                self.settings.setValue("github_remote", clean)
        self._update_sync_info()
        self._git_status()



# ════════════════════════════════════════════════════════════════
#  INSTANCES MINECRAFT — helpers
# ════════════════════════════════════════════════════════════════

def get_mc_base() -> Path:
    """Dossier global DevStudio Pro pour les installations MC — sous le dossier app."""
    return get_app_dir() / "mc"

def get_server_jar(mc_version: str) -> Path:
    """Chemin global du server.jar vanilla (partagé entre toutes les instances)."""
    return get_mc_base() / "server_jars" / mc_version / "server.jar"

def is_vanilla_installed(mc_version: str) -> bool:
    """True si le client vanilla de cette version est déjà dans le dossier global."""
    base = get_mc_base()
    return (base / "versions" / mc_version / f"{mc_version}.jar").exists() and \
           (base / "versions" / mc_version / f"{mc_version}.json").exists()



def get_system_mc() -> Optional[Path]:
    """Renvoie le dossier .minecraft système s'il existe (réutilisation des assets)."""
    home = Path.home()
    if IS_WIN:   p = Path(os.environ.get("APPDATA","")) / ".minecraft"
    elif platform.system() == "Darwin": p = home/"Library"/"Application Support"/"minecraft"
    else:        p = home / ".minecraft"
    return p if p.exists() else None


class MCInstance:
    def __init__(self, name, mc_version="1.20.1", loader="Forge", username="Player",
                 ram_mb=2048, jvm_extra="", auto_mod=True, installed=False):
        self.name = name; self.mc_version = mc_version; self.loader = loader
        self.username = username; self.ram_mb = ram_mb; self.jvm_extra = jvm_extra
        self.auto_mod = auto_mod; self.installed = installed

    @property
    def instance_dir(self) -> Path: return get_mc_base() / "instances" / self.name
    @property
    def game_dir(self)     -> Path: return self.instance_dir / "game"
    @property
    def mods_dir(self)     -> Path: return self.game_dir / "mods"

    def to_dict(self) -> dict: return {k: v for k, v in vars(self).items()}

    @classmethod
    def from_dict(cls, d: dict) -> "MCInstance":
        o = cls(d.get("name","unnamed")); [setattr(o, k, v) for k, v in d.items()]; return o

    def save(self):
        self.instance_dir.mkdir(parents=True, exist_ok=True)
        (self.instance_dir/"instance.json").write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, p: Path) -> "MCInstance":
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))


# ── Utilitaire : construction de la commande de lancement ────────────────────

def _eval_rules(rules: list) -> bool:
    result = False
    for rule in rules:
        action = rule.get("action") == "allow"
        os_rule = rule.get("os"); feat = rule.get("features")
        if feat: continue
        if os_rule:
            names = {"Windows":"windows","Darwin":"osx","Linux":"linux"}
            if os_rule.get("name") == names.get(platform.system()): result = action
        else: result = action
    return result

def build_launch_cmd(ver_json: dict, game_dir: Path, base: Path,
                     java_home: Optional[Path], ram_mb: int,
                     username: str, jvm_extra: str = "") -> list:
    mc_ver  = ver_json["id"]
    lib_dir = base / "libraries"
    ver_dir = base / "versions" / mc_ver
    natives = ver_dir / "natives"; natives.mkdir(parents=True, exist_ok=True)
    cp_sep  = ";" if IS_WIN else ":"

    # Classpath
    cp_parts = []
    for lib in ver_json.get("libraries", []):
        art = lib.get("downloads", {}).get("artifact")
        if art:
            p = lib_dir / art["path"]
            if p.exists(): cp_parts.append(str(p))
    client_jar = ver_dir / f"{mc_ver}.jar"
    if not client_jar.exists():
        v2 = base/"versions"/ver_json.get("inheritsFrom", mc_ver)/f"{ver_json.get('inheritsFrom', mc_ver)}.jar"
        if v2.exists(): client_jar = v2
    if client_jar.exists(): cp_parts.append(str(client_jar))
    classpath = cp_sep.join(cp_parts)

    # Assets dir (check reuse file)
    assets_root = base / "assets"
    reuse = assets_root / "_reuse_path"
    if reuse.exists():
        rp = Path(reuse.read_text().strip())
        if rp.exists(): assets_root = rp
    asset_id = ver_json.get("assetIndex", {}).get("id", mc_ver)

    # Offline UUID (MD5 based)
    import hashlib
    ba = bytearray(hashlib.md5(f"OfflinePlayer:{username}".encode()).digest())
    ba[6] = (ba[6] & 0x0f) | 0x30; ba[8] = (ba[8] & 0x3f) | 0x80
    uid = f"{ba[0:4].hex()}-{ba[4:6].hex()}-{ba[6:8].hex()}-{ba[8:10].hex()}-{ba[10:16].hex()}"

    vmap = {
        "${auth_player_name}": username,   "${version_name}": mc_ver,
        "${game_directory}":   str(game_dir), "${assets_root}": str(assets_root),
        "${assets_index_name}": asset_id,  "${game_assets}": str(assets_root),
        "${auth_uuid}": uid,               "${auth_access_token}": "0",
        "${user_type}": "legacy",          "${version_type}": "release",
        "${resolution_width}": "854",      "${resolution_height}": "480",
        "${launcher_name}": "DevStudioPro","${launcher_version}": "2.0",
        "${auth_session}": "token:0:"+uid, "${user_properties}": "{}",
        "${natives_directory}": str(natives), "${classpath}": classpath,
        "${library_directory}": str(lib_dir), "${classpath_separator}": cp_sep,
        # Args Forge/modern — remplacés par des valeurs offline vides
        "${clientid}": "",    "${auth_xuid}": "",
        "${clientId}": "",    "${auth_xuid}": "",
    }
    def _r(a: str) -> str:
        for k, v in vmap.items(): a = a.replace(k, v)
        return a

    java_bin = str(java_home/"bin"/JAVA_EXE) if java_home else "java"
    jvm_args = [f"-Xmx{ram_mb}m", "-Xms512m", f"-Djava.library.path={natives}", "-Dfile.encoding=UTF-8"]
    if jvm_extra: jvm_args += jvm_extra.split()

    if "arguments" in ver_json:
        for arg in ver_json["arguments"].get("jvm", []):
            if isinstance(arg, str): jvm_args.append(_r(arg))
            elif isinstance(arg, dict) and _eval_rules(arg.get("rules",[])):
                v = arg.get("value",[])
                jvm_args += [_r(v)] if isinstance(v, str) else [_r(x) for x in v]
    jvm_args += ["-cp", classpath]

    game_args = []
    if "arguments" in ver_json:
        # Parcours par paires pour supprimer --flag <valeur_vide>
        raw = []
        for arg in ver_json["arguments"].get("game", []):
            if isinstance(arg, str): raw.append(_r(arg))
        # Filtrer : si un flag est suivi d'une valeur vide, on saute les deux
        i = 0
        while i < len(raw):
            if raw[i].startswith("--") and i+1 < len(raw) and raw[i+1] == "":
                i += 2  # sauter flag + valeur vide
            elif raw[i] == "":
                i += 1  # sauter valeur vide orpheline
            else:
                game_args.append(raw[i]); i += 1
    elif "minecraftArguments" in ver_json:
        game_args = [_r(a) for a in ver_json["minecraftArguments"].split()]

    # Force offline args (remplace si déjà présents)
    for flag, val in [("--username", username),("--uuid", uid),("--accessToken","0"),("--userType","legacy")]:
        if flag in game_args:
            idx = game_args.index(flag)
            if idx + 1 < len(game_args): game_args[idx+1] = val
        else:
            game_args += [flag, val]

    return [java_bin] + jvm_args + [ver_json.get("mainClass","net.minecraft.client.main.Main")] + game_args


# ════════════════════════════════════════════════════════════════
#  THREADS DE TÉLÉCHARGEMENT / INSTALLATION
# ════════════════════════════════════════════════════════════════

class MCDownloadThread(QThread):
    """Télécharge le client Vanilla MC : version JSON, client.jar, libs, assets, natives.
    Tous les fichiers sont dans get_mc_base() — partagés entre toutes les instances."""
    progress = pyqtSignal(str, int, int)
    log      = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    MC_MANIFEST = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"

    def __init__(self, mc_version: str, base: Path):
        super().__init__(); self.mc_version = mc_version; self.base = base; self._stop = False

    def run(self):
        try:    self._run()
        except Exception as e: self.finished.emit(False, str(e))

    def _dl(self, url, dest: Path):
        if dest.exists(): return
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "DevStudioPro/2.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            f.write(r.read())

    def _run(self):
        base = self.base; ver = self.mc_version

        # ── Manifeste : ne re-télécharge que si le client n'est pas déjà installé ──
        mf_path = base / "version_manifest.json"
        if not is_vanilla_installed(ver) or not mf_path.exists():
            self.log.emit("📋 Manifeste Mojang …")
            self._dl(self.MC_MANIFEST, mf_path)
        else:
            self.log.emit(f"♻ Vanilla {ver} déjà installé — vérification rapide …")
            if not mf_path.exists():
                self._dl(self.MC_MANIFEST, mf_path)

        mf = json.loads(mf_path.read_text())
        ver_url = next((v["url"] for v in mf["versions"] if v["id"] == ver), None)
        if not ver_url: self.finished.emit(False, f"Version {ver} introuvable dans le manifeste."); return

        ver_dir = base / "versions" / ver; ver_dir.mkdir(parents=True, exist_ok=True)
        ver_jf  = ver_dir / f"{ver}.json"
        self._dl(ver_url, ver_jf)
        ver_json = json.loads(ver_jf.read_text())
        self.log.emit(f"✓ Version JSON {ver}")

        # client.jar
        client_jar = ver_dir / f"{ver}.jar"
        if not client_jar.exists():
            self.log.emit(f"⬇ client.jar …")
            self._dl(ver_json["downloads"]["client"]["url"], client_jar)
        self.log.emit(f"✓ client.jar")

        # server.jar global (pour les serveurs d'instances)
        srv_jar_global = get_server_jar(ver)
        if not srv_jar_global.exists() and "server" in ver_json.get("downloads", {}):
            srv_jar_global.parent.mkdir(parents=True, exist_ok=True)
            self.log.emit(f"⬇ server.jar (global) …")
            try: self._dl(ver_json["downloads"]["server"]["url"], srv_jar_global)
            except Exception as e: self.log.emit(f"  ⚠ server.jar non téléchargé : {e}")

        # Bibliothèques
        lib_dir = base / "libraries"; libs = ver_json.get("libraries", [])
        done = 0
        for lib in libs:
            if self._stop: break
            if not self._lib_ok(lib): continue
            art = lib.get("downloads", {}).get("artifact")
            if art:
                p = lib_dir / art["path"]
                if not p.exists():
                    p.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        req = urllib.request.Request(art["url"], headers={"User-Agent":"DevStudioPro/2.0"})
                        with urllib.request.urlopen(req, timeout=30) as r, open(p, "wb") as f:
                            f.write(r.read())
                    except Exception as e: self.log.emit(f"  ⚠ {lib.get('name','?')}: {e}")
            done += 1; self.progress.emit("Bibliothèques", done, len(libs))
        self.log.emit(f"✓ Bibliothèques ({done})")

        self._assets(ver_json, base); self._natives(ver_json, base, ver)
        self.finished.emit(True, "Vanilla installé.")

    def _lib_ok(self, lib: dict) -> bool:
        rules = lib.get("rules")
        if not rules: return True
        allow = False
        for rule in rules:
            action = rule.get("action") == "allow"; os_r = rule.get("os")
            if os_r:
                names = {"Windows":"windows","Darwin":"osx","Linux":"linux"}
                if os_r.get("name") == names.get(platform.system()): allow = action
            else: allow = action
        return allow

    def _assets(self, ver_json: dict, base: Path):
        ai   = ver_json.get("assetIndex", {})
        aid  = ai.get("id",""); assets = base/"assets"
        idx_path = assets/"indexes"/f"{aid}.json"
        if not idx_path.exists():
            self.log.emit(f"⬇ Index assets {aid} …")
            idx_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(ai["url"], idx_path)
        idx = json.loads(idx_path.read_text()); objects = idx.get("objects",{})

        sys_mc = get_system_mc()
        if sys_mc and (sys_mc/"assets"/"indexes"/f"{aid}.json").exists():
            self.log.emit(f"♻ Assets réutilisés depuis {sys_mc.name}")
            (assets/"_reuse_path").write_text(str(sys_mc/"assets"), encoding="utf-8"); return

        if idx.get("virtual") or idx.get("map_to_resources"):
            res_dir = assets/"virtual"/aid; total = len(objects); done = 0
            self.log.emit(f"⬇ Assets legacy …")
            for name, obj in objects.items():
                if self._stop: break
                h = obj["hash"]; dest = res_dir/name
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try: urllib.request.urlretrieve(f"https://resources.download.minecraft.net/{h[:2]}/{h}", dest)
                    except: pass
                done += 1; self.progress.emit("Assets", done, total)
        else:
            total = len(objects); done = 0; self.log.emit(f"⬇ Assets ({total}) …")
            for _, obj in objects.items():
                if self._stop: break
                h = obj["hash"]; dest = assets/"objects"/h[:2]/h
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try: urllib.request.urlretrieve(f"https://resources.download.minecraft.net/{h[:2]}/{h}", dest)
                    except: pass
                done += 1
                if done % 100 == 0: self.progress.emit("Assets", done, total)
        self.log.emit("✓ Assets")

    def _natives(self, ver_json: dict, base: Path, ver: str):
        nat_dir = base/"versions"/ver/"natives"; nat_dir.mkdir(parents=True, exist_ok=True)
        lib_dir = base/"libraries"
        nat_keys = {"Windows":"natives-windows","Darwin":"natives-osx","Linux":"natives-linux"}
        nat_key  = nat_keys.get(platform.system(),"")
        for lib in ver_json.get("libraries",[]):
            if not self._lib_ok(lib): continue
            cls = lib.get("downloads",{}).get("classifiers",{})
            if nat_key not in cls: continue
            ni = cls[nat_key]; p = lib_dir/ni["path"]
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                try: urllib.request.urlretrieve(ni["url"], p)
                except: continue
            try:
                with zipfile.ZipFile(p) as zf:
                    for n in zf.namelist():
                        if not n.startswith("META-INF") and not n.endswith("/"): zf.extract(n, nat_dir)
            except: pass
        self.log.emit("✓ Natives")

    def cancel(self): self._stop = True


class ForgeInstallThread(QThread):
    log      = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    # Maven metadata (pas de 403, liste exhaustive de toutes les versions)
    META_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml"
    INSTALLER_URL = "https://maven.minecraftforge.net/net/minecraftforge/forge/{v}/forge-{v}-installer.jar"

    def __init__(self, mc_version: str, base: Path, java_home: Optional[Path]):
        super().__init__(); self.mc_version = mc_version; self.base = base; self.java_home = java_home

    def run(self):
        try:    self._run()
        except Exception as e: self.finished.emit(False, str(e))

    def _run(self):
        self.log.emit(f"🔍 Forge pour {self.mc_version} — interrogation Maven …")

        # ── Récupérer la liste des versions depuis le Maven metadata ──────────
        req = urllib.request.Request(
            self.META_URL,
            headers={"User-Agent": "DevStudioPro/2.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                xml = r.read().decode()
        except urllib.error.HTTPError as e:
            self.finished.emit(False, f"Impossible d'accéder au Maven Forge : HTTP {e.code}"); return
        except Exception as e:
            self.finished.emit(False, f"Erreur réseau Maven : {e}"); return

        # Toutes les versions au format "1.20.1-47.3.12"
        all_versions = re.findall(r'<version>([^<]+)</version>', xml)

        # Garder uniquement celles qui correspondent à notre MC version
        prefix = f"{self.mc_version}-"
        matching = [v for v in all_versions if v.startswith(prefix)]
        if not matching:
            self.finished.emit(False, f"Aucune version Forge trouvée pour {self.mc_version}"); return

        # Trier par numéro de build (le dernier segment après le dernier tiret)
        def _forge_build(v: str) -> tuple:
            try: return tuple(int(x) for x in v.split("-", 1)[1].split("."))
            except: return (0,)

        matching.sort(key=_forge_build)
        forge_ver = matching[-1]   # version la plus récente
        self.log.emit(f"📦 Forge {forge_ver}  ({len(matching)} versions disponibles)")

        # ── Télécharger l'installeur ──────────────────────────────────────────
        inst_path = self.base / "forge_installers" / f"forge-{forge_ver}-installer.jar"
        inst_path.parent.mkdir(parents=True, exist_ok=True)

        if not inst_path.exists():
            url = self.INSTALLER_URL.format(v=forge_ver)
            self.log.emit(f"⬇ Téléchargement installeur …")
            try:
                req2 = urllib.request.Request(url, headers={"User-Agent": "DevStudioPro/2.0"})
                with urllib.request.urlopen(req2, timeout=120) as r, open(inst_path, "wb") as f:
                    f.write(r.read())
            except urllib.error.HTTPError as e:
                self.finished.emit(False, f"Installeur introuvable (HTTP {e.code}) — URL : {url}"); return
            except Exception as e:
                self.finished.emit(False, f"Téléchargement échoué : {e}"); return
        else:
            self.log.emit(f"✓ Installeur déjà présent ({inst_path.name})")

        # ── Forge exige un launcher_profiles.json dans le dossier cible ─────
        profiles_path = self.base / "launcher_profiles.json"
        if not profiles_path.exists():
            self.log.emit("📝 Création de launcher_profiles.json (requis par Forge) …")
            profiles_path.write_text(json.dumps({
                "profiles": {
                    "DevStudioPro": {
                        "name": "DevStudioPro",
                        "type": "custom",
                        "lastVersionId": self.mc_version,
                    }
                },
                "selectedProfile": "DevStudioPro",
                "clientToken": "DevStudioPro",
                "authenticationDatabase": {},
                "settings": {"enableAdvanced": False, "profileSorting": "ByLastPlayed"},
                "launcherVersion": {"format": 21, "name": "2.0.0", "profilesFormat": 2}
            }, indent=2), encoding="utf-8")

        # ── Lancer l'installeur ───────────────────────────────────────────────
        java_bin = str(self.java_home / "bin" / JAVA_EXE) if self.java_home else "java"
        self.log.emit(f"⚙ Installation Forge (peut prendre plusieurs minutes) …")
        proc = subprocess.Popen(
            [java_bin, "-jar", str(inst_path), "--installClient", str(self.base)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace"
        )
        for line in proc.stdout:
            s = line.rstrip()
            if s: self.log.emit(f"  {s}")
        proc.wait()
        if proc.returncode != 0:
            self.finished.emit(False, f"Forge installer terminé avec le code {proc.returncode}"); return
        self.finished.emit(True, f"Forge {forge_ver} installé avec succès.")


class NeoForgeInstallThread(QThread):
    log      = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    META = "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
    MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge/{v}/neoforge-{v}-installer.jar"

    def __init__(self, mc_version: str, base: Path, java_home: Optional[Path]):
        super().__init__(); self.mc_version = mc_version; self.base = base; self.java_home = java_home

    def run(self):
        try:    self._run()
        except Exception as e: self.finished.emit(False, str(e))

    def _run(self):
        self.log.emit(f"🔍 NeoForge pour {self.mc_version} …")
        req = urllib.request.Request(self.META, headers={"User-Agent": "DevStudioPro/2.0"})
        with urllib.request.urlopen(req, timeout=15) as r: xml = r.read().decode()
        versions = re.findall(r'<version>([^<]+)</version>', xml)
        prefix   = ".".join(self.mc_version.split(".")[1:])
        matching = [v for v in versions if v.startswith(prefix+".")]
        if not matching: self.finished.emit(False, f"Aucune version NeoForge pour {self.mc_version}"); return
        neo_ver = matching[-1]; self.log.emit(f"📦 NeoForge {neo_ver}")

        inst_path = self.base/"neoforge_installers"/f"neoforge-{neo_ver}-installer.jar"
        inst_path.parent.mkdir(parents=True, exist_ok=True)
        if not inst_path.exists():
            self.log.emit("⬇ Installeur NeoForge …")
            req2 = urllib.request.Request(self.MAVEN.format(v=neo_ver), headers={"User-Agent": "DevStudioPro/2.0"})
            with urllib.request.urlopen(req2, timeout=120) as r, open(inst_path, "wb") as f:
                f.write(r.read())

        java_bin = str(self.java_home/"bin"/JAVA_EXE) if self.java_home else "java"

        # NeoForge exige aussi launcher_profiles.json
        profiles_path = self.base / "launcher_profiles.json"
        if not profiles_path.exists():
            self.log.emit("📝 Création de launcher_profiles.json …")
            profiles_path.write_text(json.dumps({
                "profiles": {"DevStudioPro": {"name": "DevStudioPro", "type": "custom",
                              "lastVersionId": self.mc_version}},
                "selectedProfile": "DevStudioPro", "clientToken": "DevStudioPro",
                "authenticationDatabase": {},
                "launcherVersion": {"format": 21, "name": "2.0.0", "profilesFormat": 2}
            }, indent=2), encoding="utf-8")

        self.log.emit("⚙ Installation …")
        proc = subprocess.Popen(
            [java_bin, "-jar", str(inst_path), "--installClient", str(self.base)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace"
        )
        for line in proc.stdout:
            if line.strip(): self.log.emit(f"  {line.rstrip()}")
        proc.wait()
        if proc.returncode != 0: self.finished.emit(False, f"NeoForge installer code {proc.returncode}"); return
        self.finished.emit(True, f"NeoForge {neo_ver} installé.")


class FabricSetupThread(QThread):
    log      = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    META = "https://meta.fabricmc.net/v2"

    def __init__(self, mc_version: str, base: Path, java_home: Optional[Path]):
        super().__init__(); self.mc_version = mc_version; self.base = base; self.java_home = java_home

    def run(self):
        try:    self._run()
        except Exception as e: self.finished.emit(False, str(e))

    def _run(self):
        self.log.emit(f"🔍 Fabric pour {self.mc_version} …")
        req = urllib.request.Request(
            f"{self.META}/versions/loader/{self.mc_version}?limit=5",
            headers={"User-Agent": "DevStudioPro/2.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            loaders = json.loads(r.read())
        stable = next((l for l in loaders if l["loader"]["stable"]), loaders[0] if loaders else None)
        if not stable: self.finished.emit(False, f"Aucun loader Fabric pour {self.mc_version}"); return
        loader_ver = stable["loader"]["version"]; self.log.emit(f"📦 Fabric {loader_ver}")

        profile_url  = f"{self.META}/versions/loader/{self.mc_version}/{loader_ver}/profile/json"
        profile_name = f"fabric-loader-{loader_ver}-{self.mc_version}"
        profile_dir  = self.base/"versions"/profile_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_path = profile_dir/f"{profile_name}.json"

        self.log.emit("⬇ Profil Fabric …")
        req2 = urllib.request.Request(profile_url, headers={"User-Agent": "DevStudioPro/2.0"})
        with urllib.request.urlopen(req2, timeout=15) as r:
            data = r.read()
        profile_path.write_bytes(data)
        profile = json.loads(data)

        lib_dir = self.base/"libraries"; total = len(profile.get("libraries",[])); done = 0
        self.log.emit(f"⬇ Bibliothèques Fabric ({total}) …")
        for lib in profile.get("libraries",[]):
            art = lib.get("downloads",{}).get("artifact")
            if not art: continue
            dest = lib_dir/art["path"]
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                try: urllib.request.urlretrieve(art["url"], dest)
                except Exception as e: self.log.emit(f"  ⚠ {e}")
            done += 1
        self.finished.emit(True, f"Fabric {loader_ver} installé.")


# ════════════════════════════════════════════════════════════════
#  DIALOG CRÉATION D'INSTANCE
# ════════════════════════════════════════════════════════════════

class CreateInstanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle instance Minecraft"); self.setMinimumWidth(430); self.setModal(True)
        lay = QVBoxLayout(self)
        form = QGroupBox("Configuration de l'instance"); fl = QVBoxLayout(form); fl.setSpacing(5)

        def row(lbl, w): r = QHBoxLayout(); r.addWidget(QLabel(lbl)); r.addWidget(w); fl.addLayout(r)

        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("ex: Forge1.20.1_dev")
        row("Nom :", self.name_edit)

        self.loader_combo = QComboBox(); self.loader_combo.addItems(["Vanilla","Forge","NeoForge","Fabric","Quilt"])
        self.loader_combo.setCurrentText("Forge")
        self.loader_combo.currentTextChanged.connect(self._on_loader)
        row("Loader :", self.loader_combo)

        self.ver_combo = QComboBox(); row("Version MC :", self.ver_combo)
        self.user_edit = QLineEdit(); self.user_edit.setText("Player"); row("Pseudo offline :", self.user_edit)
        self.ram_spin  = QSpinBox(); self.ram_spin.setRange(512,16384); self.ram_spin.setValue(2048); self.ram_spin.setSingleStep(512)
        row("RAM (Mo) :", self.ram_spin)
        self.automod_chk = QCheckBox("Copier automatiquement le mod compilé dans cette instance")
        self.automod_chk.setChecked(True); fl.addWidget(self.automod_chk)
        lay.addWidget(form)

        self._info = QLabel("💡 Le JDK requis sera téléchargé automatiquement si nécessaire.")
        self._info.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;"); lay.addWidget(self._info)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); lay.addWidget(btns)
        self._on_loader("Forge")

    def _on_loader(self, loader):
        self.ver_combo.clear()
        if loader == "Vanilla":
            self.ver_combo.addItems(["1.21.4","1.21.1","1.20.6","1.20.1","1.19.4","1.18.2","1.16.5","1.12.2","1.8.9","1.7.10"])
        else:
            self.ver_combo.addItems(list(MC_LOADERS.get(loader, {}).keys()))

    def get_instance(self) -> Optional[MCInstance]:
        name = self.name_edit.text().strip()
        if not name: return None
        return MCInstance(name=name, mc_version=self.ver_combo.currentText(),
                          loader=self.loader_combo.currentText(),
                          username=self.user_edit.text().strip() or "Player",
                          ram_mb=self.ram_spin.value(), auto_mod=self.automod_chk.isChecked())


# ════════════════════════════════════════════════════════════════
#  SERVER INSTALL THREAD  (QThread → signaux → thread principal)
# ════════════════════════════════════════════════════════════════

class ServerInstallThread(QThread):
    """
    Installe le serveur Minecraft dans un QThread dédié.
    Toutes les sorties passent par des signaux Qt → aucun accès widget hors thread principal.
    """
    log_out      = pyqtSignal(str)   # texte normal (stdout du sous-process)
    log_info     = pyqtSignal(str)   # texte bleu info
    log_err      = pyqtSignal(str)   # texte rouge erreur
    log_ok       = pyqtSignal(str)   # texte vert succès
    finished_ok  = pyqtSignal()      # installation réussie
    finished_err = pyqtSignal(str)   # installation échouée, arg = message

    def __init__(self, inst: "MCInstance", srv_dir: Path, srv_port: int, base: Path):
        super().__init__()
        self.inst     = inst
        self.srv_dir  = srv_dir
        self.srv_port = srv_port   # valeur capturée AVANT le thread
        self.base     = base

    def run(self):
        try:
            self._run()
        except Exception as e:
            import traceback as _tb
            self.log_err.emit(f"[server] ❌ Exception : {e}")
            self.log_err.emit(_tb.format_exc())
            self.finished_err.emit(str(e))

    def _run_proc(self, cmd: list, cwd: Path) -> int:
        """Lance une commande, émet chaque ligne via log_out, retourne le code de retour."""
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            cwd=str(cwd)
        )
        for line in proc.stdout:
            s = line.rstrip()
            if s:
                self.log_out.emit(s)
        proc.wait()
        return proc.returncode

    def _run(self):
        inst     = self.inst
        srv_dir  = self.srv_dir
        base     = self.base
        ver      = inst.mc_version

        # ── Java ──────────────────────────────────────────────────────────────
        java_home = self._find_java()
        java_bin  = str(java_home / "bin" / JAVA_EXE) if java_home else "java"

        try:
            r = subprocess.run([java_bin, "-version"], capture_output=True, timeout=10)
            if r.returncode != 0: raise RuntimeError()
        except Exception:
            self.log_err.emit(f"[server] ❌ Java introuvable : {java_bin}")
            self.log_err.emit("[server]    Installez d'abord le JDK requis.")
            self.finished_err.emit("Java introuvable")
            return

        # ── Forge ─────────────────────────────────────────────────────────────
        if inst.loader == "Forge":
            installers = sorted(
                (base / "forge_installers").glob(f"forge-{ver}-*.jar")
            ) if (base / "forge_installers").exists() else []
            if not installers:
                self.log_err.emit("[server] ❌ Installeur Forge introuvable — installez d'abord le client.")
                self.finished_err.emit("Installeur Forge introuvable"); return
            installer = installers[-1]
            self.log_info.emit(f"[server] ⚙ Forge --installServer …  ({installer.name})")
            # Forge 1.17+ : installe dans cwd, PAS d'argument chemin
            rc = self._run_proc([java_bin, "-jar", str(installer), "--installServer"], cwd=srv_dir)
            if rc != 0:
                # Fallback : ancienne syntaxe (<1.17)
                self.log_info.emit(f"[server] Code {rc} — essai syntaxe ancienne …")
                rc = self._run_proc([java_bin, "-jar", str(installer),
                                     "--installServer", str(srv_dir)], cwd=srv_dir)
            if rc != 0:
                self.log_err.emit(f"[server] ❌ Forge installServer code {rc}")
                self.finished_err.emit(f"Forge installServer code {rc}"); return

        # ── NeoForge ──────────────────────────────────────────────────────────
        elif inst.loader == "NeoForge":
            installers = sorted(
                (base / "neoforge_installers").glob("neoforge-*.jar")
            ) if (base / "neoforge_installers").exists() else []
            if not installers:
                self.log_err.emit("[server] ❌ Installeur NeoForge introuvable.")
                self.finished_err.emit("Installeur NeoForge introuvable"); return
            installer = installers[-1]
            (srv_dir / "launcher_profiles.json").write_text(json.dumps({
                "profiles": {"DevStudioPro": {"name":"DevStudioPro","type":"custom","lastVersionId":ver}},
                "selectedProfile":"DevStudioPro","clientToken":"DevStudioPro",
                "authenticationDatabase":{},
                "launcherVersion":{"format":21,"name":"2.0.0","profilesFormat":2}
            }, indent=2), encoding="utf-8")
            self.log_info.emit("[server] ⚙ NeoForge --installServer …")
            rc = self._run_proc([java_bin, "-jar", str(installer), "--installServer"], cwd=srv_dir)
            if rc != 0:
                self.log_err.emit(f"[server] ❌ NeoForge installServer code {rc}")
                self.finished_err.emit(f"NeoForge installServer code {rc}"); return

        # ── Fabric / Quilt ────────────────────────────────────────────────────
        elif inst.loader in ("Fabric", "Quilt"):
            inst_path = base / "fabric_installer.jar"
            if not inst_path.exists():
                self.log_info.emit("[server] ⬇ Fabric installer …")
                url = "https://maven.fabricmc.net/net/fabricmc/fabric-installer/1.0.1/fabric-installer-1.0.1.jar"
                req = urllib.request.Request(url, headers={"User-Agent": "DevStudioPro/2.0"})
                with urllib.request.urlopen(req, timeout=60) as r, open(inst_path, "wb") as f:
                    f.write(r.read())
            self.log_info.emit("[server] ⚙ Fabric server install …")
            rc = self._run_proc([java_bin, "-jar", str(inst_path), "server",
                                  "-mcversion", ver, "-dir", str(srv_dir),
                                  "-downloadMinecraft"], cwd=srv_dir)
            if rc != 0:
                self.log_err.emit(f"[server] ❌ Fabric installer code {rc}")
                self.finished_err.emit(f"Fabric installer code {rc}"); return

        # ── Vanilla ───────────────────────────────────────────────────────────
        else:
            srv_jar_global = get_server_jar(ver)
            srv_jar_local  = srv_dir / "server.jar"
            if not srv_jar_local.exists():
                if srv_jar_global.exists():
                    self.log_info.emit("[server] ♻ Copie server.jar depuis le cache …")
                    shutil.copy2(srv_jar_global, srv_jar_local)
                else:
                    ver_jf = base / "versions" / ver / f"{ver}.json"
                    if not ver_jf.exists():
                        self.log_err.emit("[server] ❌ Version JSON introuvable — installez d'abord le client.")
                        self.finished_err.emit("Version JSON introuvable"); return
                    ver_json = json.loads(ver_jf.read_text())
                    if "server" not in ver_json.get("downloads", {}):
                        self.log_err.emit(f"[server] ❌ Pas de server.jar disponible pour {ver}")
                        self.finished_err.emit("Pas de server.jar"); return
                    self.log_info.emit("[server] ⬇ server.jar …")
                    srv_jar_global.parent.mkdir(parents=True, exist_ok=True)
                    req = urllib.request.Request(
                        ver_json["downloads"]["server"]["url"],
                        headers={"User-Agent": "DevStudioPro/2.0"})
                    with urllib.request.urlopen(req, timeout=120) as r, \
                         open(srv_jar_global, "wb") as f:
                        f.write(r.read())
                    shutil.copy2(srv_jar_global, srv_jar_local)

        # ── Finalisation ──────────────────────────────────────────────────────
        (srv_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")

        props = srv_dir / "server.properties"
        if not props.exists():
            props.write_text(
                f"server-port={self.srv_port}\n"   # variable locale, pas widget ✓
                "online-mode=false\n"
                "motd=DevStudio Pro — Serveur local\n"
                "max-players=4\n"
                "view-distance=8\n"
                "spawn-protection=0\n"
                "enable-command-block=true\n",
                encoding="utf-8"
            )

        # Copie des mods client → server/mods
        if inst.loader not in ("Vanilla",) and inst.mods_dir.exists():
            srv_mods = srv_dir / "mods"
            srv_mods.mkdir(exist_ok=True)
            for jar in inst.mods_dir.glob("*.jar"):
                dest = srv_mods / jar.name
                if not dest.exists():
                    shutil.copy2(jar, dest)
                    self.log_info.emit(f"[server] + mod : {jar.name}")

        self.finished_ok.emit()

    def _find_java(self) -> Optional[Path]:
        java_ver = MC_LOADERS.get(self.inst.loader, {}).get(self.inst.mc_version, {}).get("java", 17) \
                   if self.inst.loader != "Vanilla" else 17
        jdk = find_app_jdk(java_ver)
        if jdk: return jdk
        if hasattr(self, "project_path") and self.project_path:
            jdk = _scan_jdk_dir(self.project_path / ".jdk" / f"jdk{java_ver}")
            if jdk: return jdk
        return detect_system_java(java_ver)


# ════════════════════════════════════════════════════════════════
#  PANNEAU INSTANCES MINECRAFT
# ════════════════════════════════════════════════════════════════

class InstancePanel(QWidget):
    def __init__(self, output: OutputPanel, settings: QSettings, parent=None):
        super().__init__(parent)
        self.output = output; self.settings = settings
        self.project_path: Optional[Path]   = None
        self.java_homes: dict[int, Path]     = {}
        self._instances: list[MCInstance]    = []
        self._dl_thread  = None
        self._game_proc: Optional[subprocess.Popen] = None
        self._srv_proc:  Optional[subprocess.Popen] = None
        self._build_ui(); self._load_instances()

    # ── UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self); root.setContentsMargins(2,2,2,2); root.setSpacing(4)

        # ── Colonne gauche : liste d'instances ───────────────────
        left = QWidget(); left.setFixedWidth(210)
        ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0); ll.setSpacing(2)
        hdr = QLabel("INSTANCES"); hdr.setObjectName("section_title"); ll.addWidget(hdr)

        self.inst_list = QtWidgets.QListWidget()
        self.inst_list.setStyleSheet(f"background:{DARK['bg2']};border:none;font-size:12px;")
        self.inst_list.currentRowChanged.connect(self._on_select)
        ll.addWidget(self.inst_list)

        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("＋"); self.new_btn.setFixedSize(28,24); self.new_btn.setToolTip("Nouvelle instance")
        self.del_btn = QPushButton("✕"); self.del_btn.setFixedSize(28,24); self.del_btn.setToolTip("Supprimer")
        self.dup_btn = QPushButton("⧉"); self.dup_btn.setFixedSize(28,24); self.dup_btn.setToolTip("Dupliquer")
        self.new_btn.clicked.connect(self._create_instance)
        self.del_btn.clicked.connect(self._delete_instance)
        self.dup_btn.clicked.connect(self._duplicate_instance)
        for b in [self.new_btn, self.dup_btn, self.del_btn]: btn_row.addWidget(b)
        btn_row.addStretch(); ll.addLayout(btn_row)

        # info sous la liste
        sys_mc = get_system_mc()
        mc_info = QLabel(f"♻ Assets : {sys_mc.name}" if sys_mc else "⬇ Assets : téléchargement requis")
        mc_info.setStyleSheet(f"color:{DARK['text_dim']};font-size:10px;font-style:italic;"); ll.addWidget(mc_info)
        root.addWidget(left)

        # ── Colonne droite : détails ─────────────────────────────
        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(0,0,0,0); rl.setSpacing(2)
        self.detail_tabs = QTabWidget()

        # ── Tab Config ───────────────────────────────────────────
        cfg_w = QWidget(); cfg_l = QVBoxLayout(cfg_w); cfg_l.setContentsMargins(6,4,6,4); cfg_l.setSpacing(3)
        self.inst_name_lbl = QLabel("Sélectionnez ou créez une instance")
        self.inst_name_lbl.setObjectName("section_title"); cfg_l.addWidget(self.inst_name_lbl)

        g = QWidget(); gl = QVBoxLayout(g); gl.setSpacing(2); gl.setContentsMargins(0,0,0,0)
        def _r(lbl, w): r=QHBoxLayout(); r.addWidget(QLabel(lbl)); r.addWidget(w); gl.addLayout(r)
        self.cfg_loader  = QLabel("–"); self.cfg_version = QLabel("–")
        self.cfg_user    = QLineEdit(); self.cfg_user.setPlaceholderText("Player")
        self.cfg_ram     = QSpinBox();  self.cfg_ram.setRange(512,16384); self.cfg_ram.setSingleStep(512)
        self.cfg_jvm     = QLineEdit(); self.cfg_jvm.setPlaceholderText("-XX:+UseG1GC …")
        self.cfg_automod = QCheckBox("Copier mod automatiquement après build")
        _r("Loader :",   self.cfg_loader);  _r("Version :", self.cfg_version)
        _r("Pseudo :",   self.cfg_user);    _r("RAM (Mo) :", self.cfg_ram)
        _r("JVM extra :", self.cfg_jvm);    gl.addWidget(self.cfg_automod)
        cfg_l.addWidget(g)
        save_btn = QPushButton("💾 Enregistrer"); save_btn.clicked.connect(self._save_config); cfg_l.addWidget(save_btn)
        cfg_l.addStretch(); self.detail_tabs.addTab(cfg_w, "⚙ Config")

        # ── Tab Mods ─────────────────────────────────────────────
        mod_w = QWidget(); mod_l = QVBoxLayout(mod_w); mod_l.setContentsMargins(6,4,6,4); mod_l.setSpacing(3)
        mod_l.addWidget(QLabel("Mods installés :").setStyleSheet if False else QLabel("Mods dans cette instance :"))
        self.mod_list = QtWidgets.QListWidget()
        self.mod_list.setStyleSheet(f"background:{DARK['bg2']};border:none;font-size:11px;")
        mod_l.addWidget(self.mod_list)
        mb = QHBoxLayout()
        for lbl, tip, fn in [
            ("📦 Projet", "Copier build/libs/ → mods/", self._copy_mod_from_project),
            ("➕ .jar",   "Ajouter un fichier JAR",      self._add_jar),
            ("✕ Retirer", "Retirer le mod sélectionné",  self._remove_mod),
            ("📁 Ouvrir", "Ouvrir le dossier mods/",     self._open_mods_dir),
        ]:
            b = QPushButton(lbl); b.setToolTip(tip); b.clicked.connect(fn); mb.addWidget(b)
        mod_l.addLayout(mb); self.detail_tabs.addTab(mod_w, "🧩 Mods")

        # ── Tab Actions (install + launch + server) ───────────────
        act_w = QWidget(); act_l = QVBoxLayout(act_w); act_l.setContentsMargins(6,4,6,4); act_l.setSpacing(4)

        # Install
        ins_grp = QGroupBox("Installation MC + Loader")
        ins_gl  = QVBoxLayout(ins_grp); ins_gl.setSpacing(3)
        self.inst_status_lbl = QLabel("Non installé")
        self.inst_status_lbl.setStyleSheet(f"color:{DARK['yellow']};font-size:11px;"); ins_gl.addWidget(self.inst_status_lbl)
        self.install_btn = QPushButton("⬇  Installer / Mettre à jour")
        self.install_btn.clicked.connect(self._install_instance); ins_gl.addWidget(self.install_btn)
        self.inst_progress = QProgressBar(); self.inst_progress.setFixedHeight(4); self.inst_progress.hide()
        ins_gl.addWidget(self.inst_progress); act_l.addWidget(ins_grp)

        # Launch solo
        launch_grp = QGroupBox("Jouer en solo (mode OFFLINE — aucun compte requis)")
        lg = QVBoxLayout(launch_grp); lg.setSpacing(3)
        solo_row = QHBoxLayout()
        self.launch_btn = QPushButton("▶  Lancer Minecraft"); self.launch_btn.setObjectName("build_btn")
        self.launch_btn.clicked.connect(self._launch_solo)
        self.stop_game_btn = QPushButton("■  Arrêter le jeu"); self.stop_game_btn.setEnabled(False)
        self.stop_game_btn.clicked.connect(self._stop_game)
        solo_row.addWidget(self.launch_btn); solo_row.addWidget(self.stop_game_btn); lg.addLayout(solo_row)
        self.game_status_lbl = QLabel("⬤ Jeu arrêté")
        self.game_status_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;"); lg.addWidget(self.game_status_lbl)
        act_l.addWidget(launch_grp)

        # Server
        srv_grp = QGroupBox("Serveur local dédié (LAN / multijoueur offline)")
        sg = QVBoxLayout(srv_grp); sg.setSpacing(3)
        sg.addWidget(QLabel("  → Adresse de connexion : localhost:25565").setStyleSheet if False else
                     self._lbl("Connexion : localhost:25565  |  online-mode=false"))
        sp_row = QHBoxLayout(); sp_row.addWidget(QLabel("Port :"))
        self.srv_port = QSpinBox(); self.srv_port.setRange(1024,65535); self.srv_port.setValue(25565)
        sp_row.addWidget(self.srv_port); sp_row.addWidget(QLabel("RAM :"))
        self.srv_ram  = QSpinBox(); self.srv_ram.setRange(512,8192); self.srv_ram.setValue(1024); self.srv_ram.setSingleStep(512)
        self.srv_ram_unit = QLabel("Mo"); sp_row.addWidget(self.srv_ram); sp_row.addWidget(self.srv_ram_unit)
        sp_row.addStretch(); sg.addLayout(sp_row)
        srv_btn = QHBoxLayout()
        self.inst_srv_btn = QPushButton("⬇  Installer serveur"); self.inst_srv_btn.clicked.connect(self._install_server)
        self.start_srv_btn = QPushButton("🖥  Démarrer"); self.start_srv_btn.setObjectName("run_btn"); self.start_srv_btn.clicked.connect(self._start_server)
        self.stop_srv_btn  = QPushButton("■  Arrêter"); self.stop_srv_btn.setEnabled(False); self.stop_srv_btn.clicked.connect(self._stop_server)
        for b in [self.inst_srv_btn, self.start_srv_btn, self.stop_srv_btn]: srv_btn.addWidget(b)
        sg.addLayout(srv_btn)
        self.srv_status_lbl = QLabel("⬤ Serveur arrêté")
        self.srv_status_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;"); sg.addWidget(self.srv_status_lbl)

        # ── Terminal serveur (envoi de commandes) ─────────────────────────
        cmd_row = QHBoxLayout()
        self.srv_cmd_edit = QLineEdit()
        self.srv_cmd_edit.setPlaceholderText("Commande serveur  (ex: /op mimiguaip, /say Bonjour, /stop)")
        self.srv_cmd_edit.setEnabled(False)
        self.srv_cmd_edit.returnPressed.connect(self._send_srv_cmd)
        self.srv_cmd_btn = QPushButton("⏎ Envoyer")
        self.srv_cmd_btn.setFixedWidth(90)
        self.srv_cmd_btn.setEnabled(False)
        self.srv_cmd_btn.clicked.connect(self._send_srv_cmd)
        cmd_row.addWidget(self.srv_cmd_edit); cmd_row.addWidget(self.srv_cmd_btn)
        sg.addLayout(cmd_row)
        act_l.addWidget(srv_grp); act_l.addStretch()
        self.detail_tabs.addTab(act_w, "🚀 Actions")

        rl.addWidget(self.detail_tabs); root.addWidget(right)

    @staticmethod
    def _lbl(txt: str) -> QLabel:
        l = QLabel(txt); l.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;"); return l

    # ── Instance list ─────────────────────────────────────────────

    def _load_instances(self):
        base = get_mc_base()/"instances"
        self._instances = []
        if base.exists():
            for p in sorted(base.iterdir()):
                cfg = p/"instance.json"
                if cfg.exists():
                    try: self._instances.append(MCInstance.load(cfg))
                    except: pass
        self._refresh_list()

    def _refresh_list(self):
        self.inst_list.clear()
        for inst in self._instances:
            self.inst_list.addItem(("✅ " if inst.installed else "⬜ ") + inst.name)

    def _current(self) -> Optional[MCInstance]:
        i = self.inst_list.currentRow()
        return self._instances[i] if 0 <= i < len(self._instances) else None

    def _on_select(self, idx):
        inst = self._instances[idx] if 0 <= idx < len(self._instances) else None
        if not inst: return
        self.inst_name_lbl.setText(f"📦  {inst.name}")
        self.cfg_loader.setText(inst.loader); self.cfg_version.setText(inst.mc_version)
        self.cfg_user.setText(inst.username); self.cfg_ram.setValue(inst.ram_mb)
        self.cfg_jvm.setText(inst.jvm_extra); self.cfg_automod.setChecked(inst.auto_mod)
        ok = inst.installed
        self.inst_status_lbl.setText("✅ Installé" if ok else "⬜ Non installé")
        self.inst_status_lbl.setStyleSheet(f"color:{'#a6e3a1' if ok else DARK['yellow']};font-size:11px;")
        self._refresh_mods(inst)

    def _save_config(self):
        inst = self._current()
        if not inst: return
        inst.username = self.cfg_user.text().strip() or "Player"
        inst.ram_mb   = self.cfg_ram.value(); inst.jvm_extra = self.cfg_jvm.text().strip()
        inst.auto_mod = self.cfg_automod.isChecked(); inst.save()
        self.output.write_ok(f"[instance] Config '{inst.name}' sauvegardée.")

    def _create_instance(self):
        dlg = CreateInstanceDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        inst = dlg.get_instance()
        if not inst: return
        if any(i.name == inst.name for i in self._instances):
            QMessageBox.warning(self, "Nom déjà utilisé", f"Une instance '{inst.name}' existe déjà."); return
        inst.save(); self._instances.append(inst); self._refresh_list()
        self.inst_list.setCurrentRow(len(self._instances)-1)
        self.output.write_ok(f"[instance] '{inst.name}' créée.")

    def _delete_instance(self):
        inst = self._current()
        if not inst: return
        r = QMessageBox.question(self, "Supprimer", f"Supprimer '{inst.name}' et tous ses fichiers ?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes: return
        if inst.instance_dir.exists(): shutil.rmtree(inst.instance_dir, ignore_errors=True)
        self._instances.remove(inst); self._refresh_list()

    def _duplicate_instance(self):
        inst = self._current()
        if not inst: return
        name, ok = QInputDialog.getText(self, "Dupliquer", "Nom de la copie :", text=inst.name+"_copy")
        if not ok or not name: return
        new = MCInstance.from_dict({**inst.to_dict(), "name": name, "installed": False})
        new.save(); self._instances.append(new); self._refresh_list()

    # ── Mods ──────────────────────────────────────────────────────

    def _refresh_mods(self, inst: MCInstance):
        self.mod_list.clear()
        if inst.mods_dir.exists():
            for jar in sorted(inst.mods_dir.glob("*.jar")): self.mod_list.addItem(jar.name)

    def _copy_mod_from_project(self):
        inst = self._current()
        if not inst: return
        if not self.project_path: QMessageBox.warning(self, "Pas de projet", "Ouvrez un projet Minecraft."); return
        libs = self.project_path/"build"/"libs"
        if not libs.exists(): QMessageBox.warning(self, "Pas de build", "Compilez d'abord le mod."); return
        jars = [j for j in libs.glob("*.jar") if "sources" not in j.name and "javadoc" not in j.name]
        if not jars: QMessageBox.warning(self, "Aucun JAR", "Aucun .jar dans build/libs/."); return
        inst.mods_dir.mkdir(parents=True, exist_ok=True)
        for jar in jars:
            shutil.copy2(jar, inst.mods_dir/jar.name); self.output.write_ok(f"[mods] {jar.name} → {inst.name}/mods/")
        self._refresh_mods(inst)

    def _add_jar(self):
        inst = self._current()
        if not inst: return
        p, _ = QFileDialog.getOpenFileName(self, "Ajouter un mod", str(Path.home()), "JAR (*.jar);;Tous (*.*)")
        if not p: return
        inst.mods_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, inst.mods_dir/Path(p).name); self._refresh_mods(inst)

    def _remove_mod(self):
        inst = self._current()
        if not inst: return
        item = self.mod_list.currentItem()
        if not item: return
        jar = inst.mods_dir/item.text()
        if jar.exists(): jar.unlink(); self._refresh_mods(inst)

    def _open_mods_dir(self):
        inst = self._current()
        if not inst: return
        inst.mods_dir.mkdir(parents=True, exist_ok=True)
        d = str(inst.mods_dir)
        if IS_WIN: os.startfile(d)
        elif platform.system()=="Darwin": subprocess.run(["open", d])
        else: subprocess.run(["xdg-open", d])

    def notify_build_done(self, project_path: Path):
        """Appelé après un build réussi — copie auto dans les instances configurées."""
        libs = project_path/"build"/"libs"
        if not libs.exists(): return
        jars = [j for j in libs.glob("*.jar") if "sources" not in j.name and "javadoc" not in j.name]
        for inst in self._instances:
            if inst.auto_mod and inst.installed:
                inst.mods_dir.mkdir(parents=True, exist_ok=True)
                for jar in jars:
                    shutil.copy2(jar, inst.mods_dir/jar.name)
                    self.output.write_ok(f"[auto-mod] {jar.name} → {inst.name}/mods/")

    # ── JDK helper ────────────────────────────────────────────────

    def _java_for(self, inst: MCInstance) -> Optional[Path]:
        java_ver = MC_LOADERS.get(inst.loader, {}).get(inst.mc_version, {}).get("java", 17) if inst.loader != "Vanilla" else 17
        # 1. Cache en mémoire
        if java_ver in self.java_homes: return self.java_homes[java_ver]
        # 2. Dossier app (partagé)
        jdk = find_app_jdk(java_ver)
        if jdk: self.java_homes[java_ver] = jdk; return jdk
        # 3. Dossier projet (rétro-compat)
        if self.project_path:
            jdk = _scan_jdk_dir(self.project_path / ".jdk" / f"jdk{java_ver}")
            if jdk: self.java_homes[java_ver] = jdk; return jdk
        # 4. Système
        return detect_system_java(java_ver)

    # ── Installation ──────────────────────────────────────────────

    def _install_instance(self):
        inst = self._current()
        if not inst: return
        java_ver = MC_LOADERS.get(inst.loader, {}).get(inst.mc_version, {}).get("java", 17) if inst.loader != "Vanilla" else 17
        java_home = self._java_for(inst)
        if not java_home and inst.loader not in ("Vanilla","Fabric","Quilt"):
            r = QMessageBox.question(self, f"JDK {java_ver} requis",
                f"JDK {java_ver} introuvable. Le télécharger automatiquement ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes: return
            dlg = JDKDownloadDialog(java_ver, self)
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.jdk_home:
                self.java_homes[java_ver] = dlg.jdk_home; java_home = dlg.jdk_home
            else: return

        self.install_btn.setEnabled(False)
        self.inst_progress.setRange(0,0); self.inst_progress.show()
        self.inst_status_lbl.setText("⬇ Téléchargement …")
        self._dl_thread = MCDownloadThread(inst.mc_version, get_mc_base())
        self._dl_thread.progress.connect(self._on_dl_progress)
        self._dl_thread.log.connect(self.output.write_info)
        self._dl_thread.finished.connect(lambda ok, msg: self._vanilla_done(ok, msg, inst, java_home))
        self._dl_thread.start()

    def _on_dl_progress(self, step, done, total):
        if total > 0: self.inst_progress.setRange(0,total); self.inst_progress.setValue(done)
        self.inst_status_lbl.setText(f"{step}: {done}/{total}" if total > 0 else step)

    def _vanilla_done(self, ok, msg, inst: MCInstance, java_home):
        if not ok:
            self.install_btn.setEnabled(True); self.inst_progress.hide()
            self.output.write_err(f"[install] ❌ {msg}"); self.inst_status_lbl.setText("❌ Échec"); return
        self.output.write_ok(f"[install] ✓ Vanilla {inst.mc_version}")
        dispatch = {
            "Forge":    lambda: self._run_loader_thread(ForgeInstallThread(inst.mc_version, get_mc_base(), java_home), inst),
            "NeoForge": lambda: self._run_loader_thread(NeoForgeInstallThread(inst.mc_version, get_mc_base(), java_home), inst),
            "Fabric":   lambda: self._run_loader_thread(FabricSetupThread(inst.mc_version, get_mc_base(), java_home), inst),
            "Quilt":    lambda: self._run_loader_thread(FabricSetupThread(inst.mc_version, get_mc_base(), java_home), inst),
        }
        if inst.loader in dispatch:
            self.inst_status_lbl.setText(f"⚙ Installation {inst.loader} …"); dispatch[inst.loader]()
        else:
            self._finalize(inst)

    def _run_loader_thread(self, thread, inst: MCInstance):
        thread.log.connect(self.output.write_info)
        thread.finished.connect(lambda ok, msg: self._loader_done(ok, msg, inst))
        thread.start(); self._loader_thread = thread

    def _loader_done(self, ok, msg, inst: MCInstance):
        self.install_btn.setEnabled(True); self.inst_progress.hide()
        if ok: self.output.write_ok(f"[install] {msg}"); self._finalize(inst)
        else:  self.output.write_err(f"[install] ❌ {msg}"); self.inst_status_lbl.setText("❌ Échec loader")

    def _finalize(self, inst: MCInstance):
        for sub in ["mods","saves","resourcepacks","config","logs","screenshots"]:
            (inst.game_dir/sub).mkdir(parents=True, exist_ok=True)
        (inst.instance_dir/"server").mkdir(parents=True, exist_ok=True)
        (inst.instance_dir/"server"/"eula.txt").write_text("eula=true\n", encoding="utf-8")
        inst.installed = True; inst.save()
        idx = self.inst_list.currentRow()
        if 0 <= idx < len(self._instances): self._instances[idx] = inst; self._on_select(idx)
        self._refresh_list(); self.inst_status_lbl.setText("✅ Installé")
        self.inst_status_lbl.setStyleSheet(f"color:{DARK['green']};font-size:11px;")
        self.output.write_ok(f"[install] ✅ Instance '{inst.name}' prête !")

    # ── Version JSON (merge héritage Forge/Fabric) ────────────────

    def _load_version_json(self, inst: MCInstance) -> Optional[dict]:
        base = get_mc_base(); ver = inst.mc_version; ver_dir = base/"versions"
        if ver_dir.exists():
            for vd in ver_dir.iterdir():
                vn = vd.name
                if ver in vn and inst.loader.lower() in vn.lower():
                    jf = vd/f"{vn}.json"
                    if jf.exists(): return self._merge(json.loads(jf.read_text()), base)
            for vd in ver_dir.iterdir():
                if "fabric" in vd.name.lower() and ver in vd.name:
                    jf = vd/f"{vd.name}.json"
                    if jf.exists(): return self._merge(json.loads(jf.read_text()), base)
        jf = base/"versions"/ver/f"{ver}.json"
        return json.loads(jf.read_text()) if jf.exists() else None

    def _merge(self, child: dict, base: Path) -> dict:
        pid = child.get("inheritsFrom")
        if not pid: return child
        pf = base/"versions"/pid/f"{pid}.json"
        if not pf.exists(): return child
        parent = json.loads(pf.read_text()); merged = {**parent}
        merged["id"] = child.get("id", parent["id"])
        merged["mainClass"] = child.get("mainClass", parent.get("mainClass"))
        parent_names = {l.get("name","") for l in parent.get("libraries",[])}
        merged["libraries"] = parent.get("libraries",[]) + [l for l in child.get("libraries",[]) if l.get("name","") not in parent_names]
        if "arguments" in child and "arguments" in parent:
            merged["arguments"] = {
                "game": parent["arguments"].get("game",[]) + child["arguments"].get("game",[]),
                "jvm":  parent["arguments"].get("jvm",[])  + child["arguments"].get("jvm",[]),
            }
        elif "arguments" in child: merged["arguments"] = child["arguments"]
        if "minecraftArguments" not in merged and "minecraftArguments" in child:
            merged["minecraftArguments"] = child["minecraftArguments"]
        return merged

    # ── Launch solo ───────────────────────────────────────────────

    def _launch_solo(self):
        inst = self._current()
        if not inst: return
        if not inst.installed: QMessageBox.warning(self, "Non installé", "Installez d'abord cette instance."); return
        if self._game_proc and self._game_proc.poll() is None:
            QMessageBox.warning(self, "Jeu actif", "Arrêtez d'abord le jeu en cours."); return

        ver_json = self._load_version_json(inst)
        if not ver_json: self.output.write_err(f"[launch] Version JSON introuvable."); return
        java_home = self._java_for(inst); inst.game_dir.mkdir(parents=True, exist_ok=True)
        try:
            cmd = build_launch_cmd(ver_json, inst.game_dir, get_mc_base(), java_home, inst.ram_mb, inst.username, inst.jvm_extra)
        except Exception as e: self.output.write_err(f"[launch] Erreur commande : {e}"); return

        self.output.write_info("═"*50)
        self.output.write_info(f"🎮 Lancement {inst.name}  [{inst.loader} {inst.mc_version}]")
        self.output.write_info(f"   Pseudo : {inst.username}  |  RAM : {inst.ram_mb}Mo  |  OFFLINE")
        self.output.write_info("═"*50)

        try:
            # RunWorker = QThread avec signaux → aucun accès widget hors thread principal
            self._game_worker = RunWorker(cmd, cwd=str(inst.game_dir))
            self._game_worker.output.connect(self.output.write)
            self._game_worker.error.connect(self.output.write_err)
            self._game_worker.started_pid.connect(lambda pid: (
                self.launch_btn.setEnabled(False),
                self.stop_game_btn.setEnabled(True),
                self.game_status_lbl.setText(f"⬤ Actif  PID {pid}"),
                self.game_status_lbl.setStyleSheet(f"color:{DARK['green']};font-size:11px;")
            ))
            self._game_worker.finished_rc.connect(lambda rc: (
                self.launch_btn.setEnabled(True),
                self.stop_game_btn.setEnabled(False),
                self.game_status_lbl.setText("⬤ Jeu arrêté"),
                self.game_status_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;"),
                self.output.write_info(f"[launch] Terminé (code {rc})")
            ))
            self._game_worker.start()
        except Exception as e: self.output.write_err(f"[launch] ❌ {e}")

    def _stop_game(self):
        if hasattr(self, '_game_worker') and self._game_worker and self._game_worker.isRunning():
            self._game_worker.kill()

    # ── Server ────────────────────────────────────────────────────

    def _install_server(self):
        inst = self._current()
        if not inst: return
        if not inst.installed:
            QMessageBox.warning(self, "Instance non installée",
                "Installez d'abord l'instance cliente avant d'installer le serveur.")
            return

        srv_dir  = inst.instance_dir / "server"
        srv_dir.mkdir(parents=True, exist_ok=True)
        # ⚠ Capturer TOUTES les valeurs widgets AVANT le thread (Qt = non thread-safe)
        srv_port = self.srv_port.value()

        self.inst_srv_btn.setEnabled(False)
        self.output.write_info(f"[server] Installation serveur {inst.loader} {inst.mc_version} …")

        # Utilisation d'un QThread + signaux pour éviter tout accès widget hors thread principal
        self._srv_install_thread = ServerInstallThread(inst, srv_dir, srv_port, get_mc_base())
        self._srv_install_thread.log_out.connect(self.output.write)
        self._srv_install_thread.log_info.connect(self.output.write_info)
        self._srv_install_thread.log_err.connect(self.output.write_err)
        self._srv_install_thread.log_ok.connect(self.output.write_ok)
        self._srv_install_thread.finished_ok.connect(lambda: self.inst_srv_btn.setEnabled(True))
        self._srv_install_thread.finished_ok.connect(
            lambda: self.output.write_ok(f"[server] ✅ Serveur prêt dans {srv_dir}"))
        self._srv_install_thread.finished_err.connect(self.output.write_err)
        self._srv_install_thread.finished_err.connect(
            lambda _: self.inst_srv_btn.setEnabled(True))
        self._srv_install_thread.start()


    def _start_server(self):
        inst = self._current()
        if not inst: return
        srv_dir   = inst.instance_dir / "server"
        java_home = self._java_for(inst)
        java_bin  = str(java_home / "bin" / JAVA_EXE) if java_home else "java"
        # ⚠ Capturer widgets avant tout thread/subprocess
        ram  = self.srv_ram.value()
        port = self.srv_port.value()

        # ── Supprimer session.lock si présent (verrou d'une session précédente) ──
        # Minecraft crée session.lock dans chaque dossier de monde pour
        # empêcher deux serveurs d'ouvrir le même monde simultanément.
        # Si le serveur a crashé, le lock traîne et bloque le prochain démarrage.
        for lock in srv_dir.rglob("session.lock"):
            try: lock.unlink()
            except Exception: pass

        # ── Toujours écrire user_jvm_args.txt avec la RAM choisie ────────────
        (srv_dir / "user_jvm_args.txt").write_text(
            f"-Xmx{ram}m\n-Xms512m\n", encoding="utf-8"
        )

        # ── Construction de la commande de démarrage ──────────────────────────
        #
        # POURQUOI PAS run.bat ?
        # run.bat appelle "java" sans chemin absolu → utilise le Java du PATH
        # système, potentiellement une version incompatible (Java 8, etc.).
        # On utilise donc notre java_bin (chemin absolu vers Java 17/21)
        # avec les argument-files que Forge génère.
        #
        # Forge 1.17+ génère dans srv_dir :
        #   @user_jvm_args.txt          → args JVM (RAM, flags user)
        #   @libraries/.../win_args.txt → args JVM + game (classpath, mainClass…)
        #   @libraries/.../unix_args.txt → idem pour Linux/macOS
        #
        # On cherche ces fichiers et on appelle java_bin directement.

        cmd = None

        # 1. Forge / NeoForge 1.17+ : win_args.txt ou unix_args.txt
        args_pattern = "libraries/**/win_args.txt" if IS_WIN else "libraries/**/unix_args.txt"
        found_args = list(srv_dir.glob(args_pattern))
        if found_args:
            # Chemin relatif à srv_dir (Java doit être appelé avec cwd=srv_dir)
            try:
                rel = found_args[0].relative_to(srv_dir)
            except ValueError:
                rel = found_args[0]
            cmd = [java_bin, "@user_jvm_args.txt", f"@{rel}", "nogui"]

        # 2. Fabric / Quilt : fabric-server-launch.jar
        if cmd is None:
            fabric_jar = srv_dir / "fabric-server-launch.jar"
            if fabric_jar.exists():
                cmd = [java_bin, f"-Xmx{ram}m", "-Xms512m",
                       "-jar", str(fabric_jar), "nogui"]

        # 3. Vanilla / ancien Forge <1.17 : server.jar
        if cmd is None:
            server_jar = srv_dir / "server.jar"
            if server_jar.exists():
                cmd = [java_bin, f"-Xmx{ram}m", "-Xms512m",
                       "-jar", str(server_jar), "nogui"]

        # 4. Fallback : forge-*-universal.jar ou neoforge-*.jar
        if cmd is None:
            jars = (list(srv_dir.glob("forge-*-universal.jar")) +
                    list(srv_dir.glob("neoforge-*.jar")))
            if jars:
                cmd = [java_bin, f"-Xmx{ram}m", "-Xms512m",
                       "-jar", str(jars[0]), "nogui"]

        if cmd is None:
            QMessageBox.warning(self, "Serveur non installé",
                "Aucun fichier de lancement trouvé dans :\n" + str(srv_dir) +
                "\n\nInstallez d'abord le serveur.")
            return

        self.output.write_info("═"*50)
        self.output.write_info(f"🖥 Démarrage serveur {inst.loader} {inst.mc_version}")
        self.output.write_info(f"   Port : {port}  |  RAM : {ram}Mo  |  online-mode=false")
        self.output.write_info(f"   Connexion : localhost:{port}  ou  127.0.0.1:{port}")
        self.output.write_info("═"*50)

        try:
            # RunWorker = QThread avec signaux → thread-safe
            self._srv_worker = RunWorker(cmd, cwd=str(srv_dir))
            self._srv_worker.output.connect(self.output.write)
            self._srv_worker.error.connect(self.output.write_err)
            self._srv_worker.started_pid.connect(lambda pid: (
                self.start_srv_btn.setEnabled(False),
                self.stop_srv_btn.setEnabled(True),
                self.srv_cmd_edit.setEnabled(True),
                self.srv_cmd_btn.setEnabled(True),
                self.srv_status_lbl.setText(f"⬤ Actif  localhost:{port}"),
                self.srv_status_lbl.setStyleSheet(f"color:{DARK['green']};font-size:11px;"),
                self.output.write_info(f"[server] Démarré PID {pid}")
            ))
            self._srv_worker.finished_rc.connect(lambda rc: (
                self.start_srv_btn.setEnabled(True),
                self.stop_srv_btn.setEnabled(False),
                self.srv_cmd_edit.setEnabled(False),
                self.srv_cmd_btn.setEnabled(False),
                self.srv_status_lbl.setText("⬤ Serveur arrêté"),
                self.srv_status_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;"),
                self.output.write_info(f"[server] Serveur arrêté (code {rc}).")
            ))
            self._srv_worker.start()
            # Garde une ref au Popen pour pouvoir envoyer "stop"
            # RunWorker expose _proc après started_pid
        except Exception as e: self.output.write_err(f"[server] ❌ {e}")

    def _send_srv_cmd(self):
        """Envoie une commande au stdin du serveur Minecraft."""
        cmd_text = self.srv_cmd_edit.text().strip()
        if not cmd_text: return
        w = getattr(self, "_srv_worker", None)
        if not w or not w.isRunning():
            self.output.write_err("[server] Serveur non actif."); return
        try:
            if w._proc and w._proc.poll() is None:
                # Forge/MC accepte les commandes sans le / depuis stdin
                cmd_clean = cmd_text.lstrip("/")
                w._proc.stdin.write((cmd_clean + "\n").encode("utf-8"))
                w._proc.stdin.flush()
                self.output.write_info(f"[server] > {cmd_text}")
                self.srv_cmd_edit.clear()
        except Exception as e:
            self.output.write_err(f"[server] Erreur envoi commande : {e}")

    def _stop_server(self):
        w = getattr(self, "_srv_worker", None)
        if w and w.isRunning():
            # Essaie d'abord d'envoyer la commande "stop" au serveur Minecraft
            try:
                if w._proc and w._proc.poll() is None:
                    w._proc.stdin.write(b"stop\n")
                    w._proc.stdin.flush()
                    return
            except Exception:
                pass
            w.kill()  # fallback

    def set_project(self, path: Path): self.project_path = path
    def set_java_homes(self, jh: dict): self.java_homes = jh
    def stop_all(self): self._stop_game(); self._stop_server()



# ════════════════════════════════════════════════════════════════
#  SYSTÈME DE MODULES
# ════════════════════════════════════════════════════════════════

AVAILABLE_MODULES = {
    "python":    {"label": "🐍 Python",            "desc": "Build .exe, auto-dépendances, versioning DEV/STABLE"},
    "java_mc":   {"label": "⛏ Minecraft Java",     "desc": "Build mods Forge/NeoForge/Fabric/Quilt, JDK auto"},
    "instances": {"label": "🎮 Instances MC",       "desc": "Instances Minecraft offline, serveur local LAN"},
    "github":    {"label": "🐙 GitHub",             "desc": "Push/pull/release GitHub, sync par dossier"},
    "updater":   {"label": "🔄 MàJ automatique",    "desc": "Générateur d'installeur + launcher avec MàJ auto"},
}

class ModuleManager:
    """Gère l'activation/désactivation des modules. Persisté dans QSettings."""
    _DEFAULT = {"python": True, "java_mc": True, "instances": True, "github": True, "updater": True}

    def __init__(self, settings: QSettings):
        self._s = settings

    def is_enabled(self, key: str) -> bool:
        return self._s.value(f"module_{key}", self._DEFAULT.get(key, True), type=bool)

    def set_enabled(self, key: str, val: bool):
        self._s.setValue(f"module_{key}", val)

    def enabled_keys(self) -> list[str]:
        return [k for k in AVAILABLE_MODULES if self.is_enabled(k)]


class ModulesPanel(QWidget):
    """Onglet ⚙ Modules — active/désactive les fonctionnalités."""
    modules_changed = pyqtSignal()

    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self._mgr = ModuleManager(settings)
        self._checks: dict[str, QCheckBox] = {}
        lay = QVBoxLayout(self); lay.setContentsMargins(8,8,8,8); lay.setSpacing(8)

        title = QLabel("MODULES INSTALLÉS"); title.setObjectName("section_title")
        lay.addWidget(title)
        lay.addWidget(self._small_lbl(
            "Activez ou désactivez les modules selon vos besoins.\n"
            "Les onglets correspondants apparaissent/disparaissent après redémarrage (ou immédiatement)."))

        for key, info in AVAILABLE_MODULES.items():
            card = QWidget()
            card.setStyleSheet(f"background:{DARK['bg2']};border-radius:6px;border:1px solid {DARK['border']};")
            cl = QHBoxLayout(card); cl.setContentsMargins(12,8,12,8)
            chk = QCheckBox(info["label"])
            chk.setChecked(self._mgr.is_enabled(key))
            chk.setStyleSheet("font-size:13px;font-weight:bold;")
            chk.toggled.connect(lambda v, k=key: self._on_toggle(k, v))
            self._checks[key] = chk
            cl.addWidget(chk)
            desc = QLabel(info["desc"])
            desc.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;")
            cl.addWidget(desc); cl.addStretch()
            lay.addWidget(card)

        info_lbl = QLabel("💡 Les modules désactivés peuvent être réactivés à tout moment.")
        info_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;font-style:italic;")
        lay.addWidget(info_lbl); lay.addStretch()

    @staticmethod
    def _small_lbl(txt):
        l = QLabel(txt); l.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;"); return l

    def _on_toggle(self, key: str, val: bool):
        self._mgr.set_enabled(key, val)
        self.modules_changed.emit()

    def mgr(self) -> ModuleManager:
        return self._mgr



# ════════════════════════════════════════════════════════════════
#  FENÊTRE PRINCIPALE
# ════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self, project_root: Path = None):
        super().__init__()
        self._project_root = project_root or Path.cwd()
        self._run_worker: Optional[RunWorker] = None
        self._settings = QSettings("FFS", "DevStudioPro")
        self._modules = ModuleManager(self._settings)

        self.setWindowTitle(f"DevStudio Pro — {self._project_root.name}")
        self.resize(1440, 900)

        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._restore_state()
        self._load_project(self._project_root)
        # Wire MC build panel → instance panel for auto-copy
        self._mc_panel._inst_panel_ref = self._inst_panel

    def _refresh_tabs(self):
        """Affiche/cache les onglets selon les modules activés."""
        mgr = self._modules
        self._mode_tabs.clear()
        TAB_MAP = [
            ("python",    self._py_panel,   "🐍  Python"),
            ("java_mc",   self._mc_panel,   "⛏  Minecraft"),
            ("instances", self._inst_panel, "🎮  Instances"),
            ("github",    self._gh_panel,   "🐙  GitHub"),
        ]
        for key, panel, label in TAB_MAP:
            if mgr.is_enabled(key):
                self._mode_tabs.addTab(panel, label)
        # L'onglet Modules est toujours présent
        self._mode_tabs.addTab(self._mod_panel, "⚙  Modules")

    # ── Build UI ─────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        vlay = QVBoxLayout(root); vlay.setContentsMargins(0,0,0,0); vlay.setSpacing(0)

        # ── Splitter principal : [explorer + editors] | bottom ──
        self._v_split = QSplitter(Qt.Orientation.Vertical)
        self._h_split = QSplitter(Qt.Orientation.Horizontal)

        # ── Explorateur ─────────────────────────────────────────
        left = QWidget(); left.setFixedWidth(240)
        llay = QVBoxLayout(left); llay.setContentsMargins(0,0,0,0); llay.setSpacing(0)

        proj_bar = QWidget(); proj_bar.setStyleSheet(f"background:{DARK['bg2']};border-bottom:1px solid {DARK['border']};")
        pb = QHBoxLayout(proj_bar); pb.setContentsMargins(8,4,4,4)
        self._proj_label = QLabel("EXPLORATEUR"); self._proj_label.setObjectName("section_title")
        pb.addWidget(self._proj_label); pb.addStretch()
        open_btn = QPushButton("📂"); open_btn.setFixedSize(24,24); open_btn.setToolTip("Ouvrir un projet")
        open_btn.clicked.connect(self._open_project_dialog); pb.addWidget(open_btn); llay.addWidget(proj_bar)

        self._fs_model = QFileSystemModel()
        self._fs_model.setNameFilters(["*.py","*.pyw","*.java","*.gradle","*.groovy","*.json","*.md",
                                        "*.txt","*.yml","*.yaml","*.cfg","*.ini","*.toml","*.properties",
                                        "*.sh","*.bat","*.gitignore","*.*"])
        self._fs_model.setNameFilterDisables(False)
        self._tree = QTreeView(); self._tree.setModel(self._fs_model)
        self._tree.setHeaderHidden(True)
        for c in range(1,4): self._tree.hideColumn(c)
        self._tree.doubleClicked.connect(self._on_tree_double_click)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._tree_context_menu)
        llay.addWidget(self._tree); self._h_split.addWidget(left)

        # ── Zone éditeur ────────────────────────────────────────
        center = QWidget(); clay = QVBoxLayout(center); clay.setContentsMargins(0,0,0,0); clay.setSpacing(0)

        run_bar = QWidget(); run_bar.setStyleSheet(f"background:{DARK['bg2']};border-bottom:1px solid {DARK['border']};")
        rb = QHBoxLayout(run_bar); rb.setContentsMargins(6,3,6,3)
        self._file_label = QLabel("Aucun fichier"); self._file_label.setStyleSheet(f"color:{DARK['text_dim']};font-size:11px;")
        rb.addWidget(self._file_label); rb.addStretch()
        self._run_btn = QPushButton("▶  Exécuter"); self._run_btn.setObjectName("run_btn"); self._run_btn.setFixedHeight(26)
        self._run_btn.clicked.connect(self._run_current); self._run_btn.setToolTip("Lancer le fichier courant (F5)")
        self._kill_btn = QPushButton("■  Arrêter"); self._kill_btn.setObjectName("stop_btn"); self._kill_btn.setFixedHeight(26)
        self._kill_btn.setEnabled(False); self._kill_btn.clicked.connect(self._kill_process)
        self._args_edit = QLineEdit(); self._args_edit.setPlaceholderText("Arguments…"); self._args_edit.setFixedWidth(160); self._args_edit.setFixedHeight(26)
        self._analyse_btn = QPushButton("🔍 Dépendances"); self._analyse_btn.setFixedHeight(26)
        self._analyse_btn.setToolTip("Analyser les imports et injecter le bloc d'auto-installation pip")
        self._analyse_btn.clicked.connect(self._analyse_and_inject)
        rb.addWidget(self._args_edit); rb.addWidget(self._analyse_btn); rb.addWidget(self._run_btn); rb.addWidget(self._kill_btn)
        clay.addWidget(run_bar)

        self._tabs = QTabWidget(); self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        clay.addWidget(self._tabs); self._h_split.addWidget(center)
        self._h_split.setSizes([240, 960])

        self._v_split.addWidget(self._h_split)

        # ── Panneau bas ─────────────────────────────────────────
        bottom = QWidget(); blay = QVBoxLayout(bottom); blay.setContentsMargins(4,4,4,4); blay.setSpacing(4)
        self._output = OutputPanel(); blay.addWidget(self._output, 2)

        # ── Onglets de mode (gérés par ModuleManager) ──────────────────
        self._mode_tabs  = QTabWidget()
        self._py_panel   = PythonBuildPanel(self._project_root, self._output)
        self._mc_panel   = MinecraftBuildPanel(self._output, self._settings)
        self._gh_panel   = GitHubPanel(self._output, self._settings)
        self._inst_panel = InstancePanel(self._output, self._settings)
        self._mod_panel  = ModulesPanel(self._settings)
        self._mod_panel.modules_changed.connect(self._refresh_tabs)
        self._mode_tabs.setMinimumHeight(220)
        blay.addWidget(self._mode_tabs)
        self._refresh_tabs()  # afficher les onglets selon les modules activés

        self._v_split.addWidget(bottom)
        self._v_split.setSizes([640, 300])
        vlay.addWidget(self._v_split)

        self._status = QStatusBar(); self.setStatusBar(self._status)
        self._pos_label = QLabel("Ln 1  Col 1"); self._status.addPermanentWidget(self._pos_label)

    # ── Menu ──────────────────────────────────────────────────────

    @staticmethod
    def _action(parent, text, slot=None, shortcut=None):
        a = QAction(text, parent)
        if slot: a.triggered.connect(slot)
        if shortcut is not None: a.setShortcut(shortcut)
        return a

    def _build_menu(self):
        mb = self.menuBar(); SK = QKeySequence.StandardKey
        fm = mb.addMenu("Fichier")
        fm.addAction(self._action(self, "Nouveau",            self._new_file,               SK.New))
        fm.addAction(self._action(self, "Ouvrir fichier…",    self._open_file,              SK.Open))
        fm.addAction(self._action(self, "Ouvrir projet…",     self._open_project_dialog))
        fm.addSeparator()
        fm.addAction(self._action(self, "Enregistrer",        self._save_current,           SK.Save))
        fm.addAction(self._action(self, "Enregistrer sous…",  self._save_as))
        fm.addSeparator()
        fm.addAction(self._action(self, "Quitter",            self.close,                   SK.Quit))

        em = mb.addMenu("Édition")
        em.addAction(self._action(self, "Tout sélectionner",
                                  lambda: self._current_editor() and self._current_editor().selectAll(), SK.SelectAll))
        em.addSeparator()
        em.addAction(self._action(self, "Rechercher…", self._find_dialog, SK.Find))

        rm = mb.addMenu("Exécution")
        rm.addAction(self._action(self, "Exécuter le fichier courant", self._run_current,  QKeySequence("F5")))
        rm.addAction(self._action(self, "Arrêter le processus",        self._kill_process, QKeySequence("Shift+F5")))

        mm = mb.addMenu("Minecraft")
        mm.addAction(self._action(self, "Build Mod (gradlew)",  self._mc_panel._start_build))
        mm.addAction(self._action(self, "Clean",                self._mc_panel._clean))
        mm.addAction(self._action(self, "Ouvrir build/libs/",   self._mc_panel._open_output))
        mm.addSeparator()
        mm.addAction(self._action(self, "Télécharger JDK requis", self._mc_panel._download_jdk))

        im = mb.addMenu("Instances")
        im.addAction(self._action(self, "Nouvelle instance",       self._inst_panel._create_instance))
        im.addAction(self._action(self, "Installer instance",      self._inst_panel._install_instance))
        im.addSeparator()
        im.addAction(self._action(self, "Lancer Minecraft (solo)", self._inst_panel._launch_solo))
        im.addAction(self._action(self, "Arrêter le jeu",          self._inst_panel._stop_game))
        im.addSeparator()
        im.addAction(self._action(self, "Démarrer serveur local",  self._inst_panel._start_server))
        im.addAction(self._action(self, "Arrêter serveur",         self._inst_panel._stop_server))
        im.addSeparator()
        im.addAction(self._action(self, "Copier mod → instance",   self._inst_panel._copy_mod_from_project))

        gm = mb.addMenu("GitHub")
        gm.addAction(self._action(self, "git status",          self._gh_panel._git_status))
        gm.addAction(self._action(self, "Synchroniser + Push",  self._gh_panel._sync_and_push))
        gm.addAction(self._action(self, "Créer Release…",       self._gh_panel._create_release))

        lm = mb.addMenu("Logs")
        lm.addAction(self._action(self, "Ouvrir le dossier des logs", self._open_logs_dir))
        lm.addAction(self._action(self, "Effacer le terminal",        self._output.clear))

    # ── Toolbar ───────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = QToolBar("Principal"); tb.setMovable(False); self.addToolBar(tb)
        def act(icon_txt, tip, fn, w=32):
            btn = QPushButton(icon_txt); btn.setToolTip(tip); btn.setFixedSize(w,28)
            btn.clicked.connect(fn); tb.addWidget(btn)
        act("📂", "Ouvrir projet",            self._open_project_dialog)
        act("💾", "Enregistrer (Ctrl+S)",      self._save_current)
        tb.addSeparator()
        act("▶",  "Exécuter Python (F5)",      self._run_current)
        act("■",  "Arrêter (Shift+F5)",         self._kill_process)
        act("🔍", "Analyser dépendances",       self._analyse_and_inject)
        tb.addSeparator()
        act("🔨", "Build Minecraft",            self._mc_panel._start_build)
        act("🧹", "Clean Minecraft",            self._mc_panel._clean)
        tb.addSeparator()
        act("🎮", "Lancer Minecraft (solo)",    self._inst_panel._launch_solo, 36)
        act("🖥",  "Démarrer serveur local",     self._inst_panel._start_server, 32)
        tb.addSeparator()
        act("⬆",  "Synchroniser + Push",       self._gh_panel._sync_and_push)
        act("🚀", "Créer Release GitHub",       self._gh_panel._create_release, 36)

    # ── Onglets éditeur ───────────────────────────────────────────

    def _new_tab(self, filepath: Path = None, content: str = "") -> CodeEditor:
        editor = CodeEditor()
        if filepath and filepath.exists():
            editor.load_file(filepath); label = filepath.name
        else:
            editor.setPlainText(content); label = "nouveau.py"
        editor.cursorPositionChanged.connect(self._update_pos_label)
        idx = self._tabs.addTab(editor, label); self._tabs.setCurrentIndex(idx)
        self._tabs.setTabToolTip(idx, str(filepath) if filepath else "")
        return editor

    def _current_editor(self) -> Optional[CodeEditor]:
        w = self._tabs.currentWidget(); return w if isinstance(w, CodeEditor) else None

    def _close_tab(self, idx):
        editor = self._tabs.widget(idx)
        if isinstance(editor, CodeEditor) and editor._modified:
            r = QMessageBox.question(self, "Modifications non sauvegardées",
                f"Enregistrer '{self._tabs.tabText(idx)}' avant de fermer ?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel: return
            if r == QMessageBox.StandardButton.Save:
                if not editor.save_file(): return
        self._tabs.removeTab(idx)

    def _on_tab_changed(self, idx):
        ed = self._current_editor()
        if ed and ed._filepath:
            try: self._file_label.setText(str(ed._filepath.relative_to(self._project_root)))
            except: self._file_label.setText(ed._filepath.name)
        else: self._file_label.setText("Aucun fichier")

    def _update_pos_label(self):
        ed = self._current_editor()
        if ed:
            c = ed.textCursor()
            self._pos_label.setText(f"Ln {c.blockNumber()+1}  Col {c.columnNumber()+1}")

    # ── Fichiers ──────────────────────────────────────────────────

    def _new_file(self): self._new_tab()

    def _open_file(self, path: Path = None):
        if not path:
            p, _ = QFileDialog.getOpenFileName(
                self, "Ouvrir un fichier", str(self._project_root),
                "Python (*.py *.pyw);;Java (*.java);;Gradle (*.gradle);;Tous (*.*)"
            )
            if not p: return
            path = Path(p)
        for i in range(self._tabs.count()):
            ed = self._tabs.widget(i)
            if isinstance(ed, CodeEditor) and ed._filepath == path:
                self._tabs.setCurrentIndex(i); return
        self._new_tab(path)

    def _save_current(self):
        ed = self._current_editor()
        if not ed: return
        if not ed._filepath: self._save_as(); return
        if ed._filepath and ed._filepath.suffix in (".py", ".pyw"):
            self._auto_analyse_on_save(ed)
        ok = ed.save_file()
        if ok:
            idx = self._tabs.currentIndex()
            self._tabs.setTabText(idx, ed._filepath.name)
            self._status.showMessage(f"Enregistré : {ed._filepath.name}", 2000)

    def _save_as(self):
        ed = self._current_editor()
        if not ed: return
        p, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous", str(self._project_root), "Tous (*.*)")
        if not p: return
        path = Path(p)
        if ed.save_file(path): self._tabs.setTabText(self._tabs.currentIndex(), path.name)

    def _find_dialog(self):
        ed = self._current_editor()
        if not ed: return
        term, ok = QInputDialog.getText(self, "Rechercher", "Terme :")
        if not ok or not term: return
        cursor = ed.document().find(term, ed.textCursor())
        if cursor.isNull(): cursor = ed.document().find(term)
        if not cursor.isNull(): ed.setTextCursor(cursor)
        else: self._status.showMessage(f"'{term}' non trouvé", 2000)

    # ── Explorateur ───────────────────────────────────────────────

    def _load_project(self, root: Path):
        self._project_root = root
        self._fs_model.setRootPath(str(root))
        self._tree.setRootIndex(self._fs_model.index(str(root)))
        self._tree.expandToDepth(1)
        self._proj_label.setText(root.name.upper())
        self.setWindowTitle(f"DevStudio Pro — {root.name}")
        self._py_panel.set_project_root(root)
        self._mc_panel.set_project(root)
        self._gh_panel.set_project(root)
        self._inst_panel.set_project(root)
        self._settings.setValue("last_project", str(root))
        # Détection auto du mode
        if (root/"gradlew").exists() or (root/"gradlew.bat").exists():
            self._mode_tabs.setCurrentWidget(self._mc_panel)
            self.output_info(f"⛏ Projet Minecraft détecté — onglet Minecraft activé")
        else:
            self._mode_tabs.setCurrentWidget(self._py_panel)

    def output_info(self, msg): self._output.write_info(msg)

    def _open_project_dialog(self):
        d = QFileDialog.getExistingDirectory(self, "Ouvrir un projet", str(self._project_root))
        if d: self._load_project(Path(d))

    def _on_tree_double_click(self, index):
        path = Path(self._fs_model.filePath(index))
        if path.is_file(): self._open_file(path)

    def _tree_context_menu(self, pos):
        index = self._tree.indexAt(pos)
        if not index.isValid(): return
        path = Path(self._fs_model.filePath(index))
        menu = QMenu(self)
        if path.is_file():
            menu.addAction("Ouvrir",    lambda: self._open_file(path))
            menu.addAction("Exécuter",  lambda: self._run_file(path))
            menu.addSeparator()
            menu.addAction("Renommer",  lambda: self._rename_file(path))
            menu.addAction("Supprimer", lambda: self._delete_file(path))
        else:
            menu.addAction("Nouveau fichier…",  lambda: self._new_file_in(path))
            menu.addAction("Nouveau dossier…",  lambda: self._new_dir_in(path))
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _rename_file(self, path):
        name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom :", text=path.name)
        if ok and name:
            try: path.rename(path.parent / name)
            except Exception as e: QMessageBox.critical(self, "Erreur", str(e))

    def _delete_file(self, path):
        r = QMessageBox.question(self, "Supprimer", f"Supprimer '{path.name}' ?")
        if r == QMessageBox.StandardButton.Yes:
            try: path.unlink()
            except Exception as e: QMessageBox.critical(self, "Erreur", str(e))

    def _new_file_in(self, folder):
        name, ok = QInputDialog.getText(self, "Nouveau fichier", "Nom :")
        if ok and name: p = folder/name; p.touch(); self._open_file(p)

    def _new_dir_in(self, folder):
        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom :")
        if ok and name: (folder/name).mkdir(exist_ok=True)

    # ── Exécution Python ──────────────────────────────────────────

    def _run_current(self):
        ed = self._current_editor()
        if not ed: return
        if ed._modified or not ed._filepath: self._save_current()
        if ed._filepath: self._run_file(ed._filepath)

    def _run_file(self, path: Path):
        if self._run_worker and self._run_worker.isRunning():
            self._run_worker.kill(); self._run_worker.wait(2000)
        self._output.clear()
        args = self._args_edit.text().strip().split() if self._args_edit.text().strip() else []
        cmd  = [sys.executable, str(path)] + args
        self._output.write_info(f"[run] ▶  {path.name}  ({path.parent})")
        self._output.write_info(f"[run] Python : {sys.executable}")
        if args: self._output.write_info(f"[run] Args : {' '.join(args)}")
        self._output.write_info("─"*55)
        self._run_worker = RunWorker(cmd, cwd=str(path.parent))
        self._run_worker.output.connect(self._output.write)
        self._run_worker.error.connect(self._output.write_err)
        self._run_worker.started_pid.connect(lambda pid: (
            self._run_btn.setEnabled(False), self._kill_btn.setEnabled(True),
            self._status.showMessage(f"Exécution en cours… PID {pid}")
        ))
        self._run_worker.finished_rc.connect(self._on_run_done); self._run_worker.start()

    def _kill_process(self):
        if self._run_worker: self._run_worker.kill()

    def _on_run_done(self, rc):
        self._run_btn.setEnabled(True); self._kill_btn.setEnabled(False)
        self._status.showMessage(""); self._output.write_info("─"*55)
        if rc == 0:   self._output.write_ok("✅  Terminé avec succès (code 0)")
        elif rc == -1: self._output.write_err("❌  Échec au démarrage")
        else:          self._output.write_err(f"❌  Terminé avec le code {rc}")

    # ── Dépendances Python ────────────────────────────────────────

    def _analyse_and_inject(self):
        ed = self._current_editor()
        if not ed: self._output.write_err("[deps] Aucun fichier ouvert."); return
        code = ed.toPlainText(); packages = scan_third_party_imports(code)
        new_code, changed = inject_deps_into_code(code, packages)
        if changed:
            pos = ed.textCursor().position()
            ed.setPlainText(new_code)
            cursor = ed.textCursor(); cursor.setPosition(min(pos, len(new_code))); ed.setTextCursor(cursor)
            if ed._filepath: ed.save_file(); self._tabs.setTabText(self._tabs.currentIndex(), ed._filepath.name)
        self._output.write_info(f"[deps] {len(packages)} dépendance(s) : {', '.join(packages) if packages else 'aucune'}")
        if changed: self._output.write_ok("[deps] Bloc d'auto-installation injecté/mis à jour.")
        else:       self._output.write_info("[deps] Bloc déjà à jour ou aucune dépendance tierce.")

    def _auto_analyse_on_save(self, editor: CodeEditor):
        if not self._py_panel.auto_deps_chk.isChecked(): return
        code = editor.toPlainText(); packages = scan_third_party_imports(code)
        new_code, changed = inject_deps_into_code(code, packages)
        if changed:
            pos = editor.textCursor().position()
            editor.setPlainText(new_code)
            cursor = editor.textCursor(); cursor.setPosition(min(pos, len(new_code))); editor.setTextCursor(cursor)
            self._output.write_info(f"[deps] Auto-injection : {', '.join(packages) if packages else '(nettoyage)'}")
        if packages:
            self._py_panel.deps_status.setText(f"{len(packages)} dep(s): {', '.join(packages[:3])}{'…' if len(packages)>3 else ''}")
        else:
            self._py_panel.deps_status.setText("Aucune dépendance tierce")

    # ── Persistance ───────────────────────────────────────────────

    def _restore_state(self):
        last = self._settings.value("last_project")
        if last and Path(last).exists(): self._project_root = Path(last)
        geom = self._settings.value("geometry")
        if geom: self.restoreGeometry(geom)

    def _open_logs_dir(self):
        folder = str(_log_dir)
        Path(folder).mkdir(parents=True, exist_ok=True)
        if IS_WIN:                     subprocess.Popen(["explorer", folder])
        elif platform.system()=="Darwin": subprocess.Popen(["open", folder])
        else:                              subprocess.Popen(["xdg-open", folder])

    def closeEvent(self, event):
        for i in range(self._tabs.count()):
            ed = self._tabs.widget(i)
            if isinstance(ed, CodeEditor) and ed._modified and ed._filepath:
                ed.save_file()
        self._settings.setValue("geometry",     self.saveGeometry())
        self._settings.setValue("last_project", str(self._project_root))
        self._py_panel.stop_server()
        self._inst_panel.stop_all()
        self._output.close_log()
        event.accept()

# ════════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DevStudio Pro")
    app.setOrganizationName("FFS")
    app.setStyleSheet(STYLESHEET)
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(DARK["bg"]))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(DARK["text"]))
    pal.setColor(QPalette.ColorRole.Base,            QColor(DARK["editor_bg"]))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(DARK["bg2"]))
    pal.setColor(QPalette.ColorRole.Text,            QColor(DARK["text"]))
    pal.setColor(QPalette.ColorRole.Button,          QColor(DARK["bg3"]))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(DARK["text"]))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(DARK["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(DARK["bg"]))
    app.setPalette(pal)

    project = Path(sys.argv[1]) if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir() else Path.cwd()
    win = MainWindow(project)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
