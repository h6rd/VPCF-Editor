import os
import sys
import platform
import re
from pathlib import Path

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = SCRIPT_DIR / "compiled"
OUTPUT_DIR.mkdir(exist_ok=True)

RAW_DIR = SCRIPT_DIR / "raw"
RAW_DIR.mkdir(exist_ok=True)

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"

BIN_DIR = SCRIPT_DIR / "bin"
BIN_DIR.mkdir(exist_ok=True)

RESCOMP_OVERRIDE_DIR = BIN_DIR / "resourcecompiler"

TOOLS_SUBPATHS = [
    os.path.join("game", "bin"),
    os.path.join("game", "core"),
    os.path.join("game", "dota", "bin"),
    os.path.join("game", "dota", "tools"),
    os.path.join("game", "dota", "gameinfo.gi"),
]

COMPILER_URL = "https://raw.githubusercontent.com/h6rd/Compiler/refs/heads/main/d2pfx_compiler.zip"
LOCAL_COMPILER_ZIP = SCRIPT_DIR / "d2pfx_compiler.zip"

S2V_CLI_URL_WIN = "https://github.com/ValveResourceFormat/ValveResourceFormat/releases/download/18.0/cli-windows-x64.zip"
S2V_CLI_URL_LINUX = "https://github.com/ValveResourceFormat/ValveResourceFormat/releases/download/18.0/cli-linux-x64.zip"
S2V_CLI_DIR = BIN_DIR / "s2v_cli"
S2V_CLI_DIR.mkdir(parents=True, exist_ok=True)

TEXTURE_CACHE_DIR = BIN_DIR / "texture_cache"
TEXTURE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

TEXTURE_MANIFEST_FILE = BIN_DIR / "texture_manifest.json"

RECENT_COLORS_FILE = BIN_DIR / "recent_colors.json"
MAX_RECENT_COLORS = 24

SYMBOLS = {
    "package": "📦",
    "check": "✅",
    "save": "💾",
    "cross": "❌",
    "trash": "🗑️",
}

GARBAGE_SUFFIX_RE = re.compile(
    r'(\.tmp|\.temp|Thumbs\.db|\.DS_Store)$', re.IGNORECASE)

GRAYSCALE_TOLERANCE = 10

ENCODINGS_TO_TRY = ("utf-8-sig", "utf-8", "cp1251", "latin-1")

appVersion = "1.3"

githubRepo = "h6rd/VPCF-Editor"
