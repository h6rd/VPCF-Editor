import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple

TEXTURE_PATTERN = re.compile(r'resource:"([^"]+\.vtex)"')

def findTextures(text: str) -> List[Dict[str, Any]]:
    entries = []

    import re
    CLASS_RE = re.compile(r'_class\s*=\s*"([^"]+)"')
    def nearestClass(txt: str, pos: int) -> str:
        name = "(root)"
        for m in CLASS_RE.finditer(txt):
            if m.start() > pos:
                break
            name = m.group(1)
        return name

    for match in TEXTURE_PATTERN.finditer(text):
        vtex_path = match.group(1)
        pos = match.start(1)
        line_no = text.count('\n', 0, pos) + 1
        entries.append({
            "vtex_path": vtex_path,
            "start": pos,
            "end": match.end(1),
            "className": nearestClass(text, pos),
            "lineNo": line_no,
            "modified": False,
            "target_hue": None,
            "h_shift": 0.0,
            "s_scale": 1.0,
            "v_scale": 1.0,
            "recolor_mode": "hsv",
            "tint_rgb": None,
        })
    return entries

def applyTextureChanges(text: str, entries: List[Dict[str, Any]], new_paths_map: Dict[int, str]) -> str:
    sorted_entries = sorted(entries, key=lambda e: e["start"], reverse=True)
    new_text = text
    
    for entry in sorted_entries:
        entry_id = id(entry)
        if entry_id in new_paths_map:
            new_path = new_paths_map[entry_id]
            start = entry["start"]
            end = entry["end"]
            new_text = new_text[:start] + new_path + new_text[end:]
            
    return new_text

def generateUniqueName(
    vtex_path: str,
    h_shift: float = 0.0,
    s_scale: float = 1.0,
    v_scale: float = 1.0,
    mode: str = "hsv",
    tint_rgb: Optional[Tuple[int, int, int]] = None,
) -> str:
    base = vtex_path.rsplit(".vtex", 1)[0]
    if mode in ("overlay", "replace") and tint_rgb is not None:
        setting_str = f"{mode}_{tint_rgb[0]}_{tint_rgb[1]}_{tint_rgb[2]}"
    else:
        setting_str = f"{h_shift:.2f}_{s_scale:.2f}_{v_scale:.2f}"
    hash_str = hashlib.md5(setting_str.encode()).hexdigest()[:6]
    return f"{base}_{hash_str}.vtex"
