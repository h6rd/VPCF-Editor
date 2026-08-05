import json
import re
from typing import List

from src.config import RECENT_COLORS_FILE, MAX_RECENT_COLORS


def loadRecentColors() -> List[str]:
    try:
        data = json.loads(RECENT_COLORS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [
                c for c in data
                if isinstance(c, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", c)
            ][:MAX_RECENT_COLORS]
    except Exception:
        pass
    return []


def saveRecentColors(colors: List[str]):
    try:
        RECENT_COLORS_FILE.write_text(
            json.dumps(colors[:MAX_RECENT_COLORS]), encoding="utf-8"
        )
    except Exception:
        pass


RECENT_COLORS: List[str] = loadRecentColors()


def addRecentColor(hex_color: str):
    """Adds a color to the front of the recent colors palette (no duplicates) and saves it to disk."""
    global RECENT_COLORS
    hex_color = hex_color.lower()
    RECENT_COLORS = [c for c in RECENT_COLORS if c.lower() != hex_color]
    RECENT_COLORS.insert(0, hex_color)
    RECENT_COLORS = RECENT_COLORS[:MAX_RECENT_COLORS]
    saveRecentColors(RECENT_COLORS)
