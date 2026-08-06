import os
from typing import List, Tuple

from src.config import ENCODINGS_TO_TRY
from src.color_parser import findColors


def readTextFile(path: str) -> Tuple[str, str]:
    for enc in ENCODINGS_TO_TRY:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        return f.read(), "utf-8"


def writeTextFile(path: str, text: str, encoding: str) -> None:
    with open(path, "w", encoding=encoding, newline="") as f:
        f.write(text)


def scanFolder(root_dir: str) -> List[Tuple[str, str, int]]:
    results = []
    _skip = {"raw", "compiled"}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in _skip]
        for fn in filenames:
            if fn.lower().endswith(".vpcf"):
                abs_path = os.path.join(dirpath, fn)
                try:
                    text, _enc = readTextFile(abs_path)
                except Exception:
                    continue
                count = len(findColors(text))
                if count > 0:
                    rel_path = os.path.relpath(abs_path, root_dir)
                    results.append((rel_path, abs_path, count))
    return results
