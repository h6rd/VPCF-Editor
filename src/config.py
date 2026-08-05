import sys
import re
from pathlib import Path

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = Path(sys.executable).parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = SCRIPT_DIR / "compiled"
OUTPUT_DIR.mkdir(exist_ok=True)

COMPILER_URL = "https://raw.githubusercontent.com/h6rd/Compiler/refs/heads/main/d2pfx_compiler.zip"
LOCAL_COMPILER_ZIP = SCRIPT_DIR / "d2pfx_compiler.zip"


RECENT_COLORS_FILE = SCRIPT_DIR / "recent_colors.json"
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
