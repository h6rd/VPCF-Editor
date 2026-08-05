import re
from typing import List, Optional, Tuple, Dict, Any

COLOR_KEY_RE = re.compile(r"colou?r", re.IGNORECASE)
ARRAY_RE = re.compile(
    r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*\r?\n?[ \t]*"
    r"\[(?P<body>[^\[\]]*)\]"
)
NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
CLASS_RE = re.compile(r'_class\s*=\s*"([^"]+)"')


def makeColorComponent(start: int, end: int, text: str, decimals: Optional[int]) -> Dict[str, Any]:
    return {
        "start": start,
        "end": end,
        "text": text,
        "decimals": decimals,
    }


def makeColorEntry(
    key: str,
    line_no: int,
    class_name: str,
    kind: str,
    components: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "key": key,
        "lineNo": line_no,
        "className": class_name,
        "kind": kind,
        "components": components,
    }


def colorEntryRgba255(entry: Dict[str, Any]) -> Tuple[int, int, int, int]:
    vals = [float(c["text"]) for c in entry["components"]]
    if entry["kind"] == "byte":
        ints = [max(0, min(255, int(round(v)))) for v in vals]
    else:
        ints = [max(0, min(255, int(round(max(0.0, min(1.0, v)) * 255))))
                for v in vals]
    while len(ints) < 4:
        ints.append(255)
    return tuple(ints[:4])


def colorEntryLabel(entry: Dict[str, Any]) -> str:
    tag = "RGBA" if len(entry["components"]) == 4 else "RGB"
    kind_tag = "0-255" if entry["kind"] == "byte" else "0-1"
    return (
        f"line {entry['lineNo']}  ·  {entry['className']}  ·  "
        f"{entry['key']}  ({tag}, {kind_tag})"
    )


def nearestClass(text: str, pos: int) -> str:
    name = "(root)"
    for m in CLASS_RE.finditer(text):
        if m.start() > pos:
            break
        name = m.group(1)
    return name


def findColors(text: str) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for m in ARRAY_RE.finditer(text):
        key = m.group("key")
        if not COLOR_KEY_RE.search(key):
            continue

        body = m.group("body")
        body_start = m.start("body")
        nums = list(NUMBER_RE.finditer(body))
        if len(nums) not in (3, 4):
            continue

        remainder = NUMBER_RE.sub("", body).replace(",", "").strip()
        if remainder != "":
            continue

        components: List[Dict[str, Any]] = []
        values: List[float] = []
        all_int = True
        for nm in nums:
            raw = nm.group(0)
            values.append(float(raw))
            if "." in raw:
                all_int = False
                decimals = len(raw.split(".")[1])
            else:
                decimals = None
            components.append(makeColorComponent(
                start=body_start + nm.start(),
                end=body_start + nm.end(),
                text=raw,
                decimals=decimals,
            ))

        if all_int:
            if not all(0 <= v <= 255 for v in values):
                continue
            kind = "byte"
        else:
            kind = "float"

        line_no = text.count("\n", 0, m.start()) + 1
        class_name = nearestClass(text, m.start())

        entries.append(makeColorEntry(
            key=key,
            line_no=line_no,
            class_name=class_name,
            kind=kind,
            components=components,
        ))
    return entries


def applyColorChanges(
    text: str,
    entries: List[Dict[str, Any]],
    new_values_map: Dict[int, List[float]],
) -> str:
    edits: List[Tuple[int, int, str]] = []
    for entry in entries:
        new_vals = new_values_map.get(id(entry))
        if new_vals is None:
            continue
        for comp, new_val in zip(entry["components"], new_vals):
            if entry["kind"] == "byte":
                new_text = str(int(round(new_val)))
            else:
                dec = comp["decimals"] if comp["decimals"] is not None else 6
                new_text = f"{new_val:.{dec}f}"
            if new_text != comp["text"]:
                edits.append((comp["start"], comp["end"], new_text))

    edits.sort(key=lambda e: e[0], reverse=True)
    for start, end, new_text in edits:
        text = text[:start] + new_text + text[end:]
    return text
