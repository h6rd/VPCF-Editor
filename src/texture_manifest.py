import json
from typing import Any, Dict, Optional

from src.config import TEXTURE_MANIFEST_FILE


TextureManifest = Dict[str, Dict[str, Any]]


def loadTextureManifest() -> TextureManifest:
    try:
        data = json.loads(TEXTURE_MANIFEST_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {
                str(k): v for k, v in data.items()
                if isinstance(k, str) and isinstance(v, dict)
            }
    except Exception:
        pass
    return {}


def saveTextureManifest(manifest: TextureManifest):
    try:
        TEXTURE_MANIFEST_FILE.write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except Exception:
        pass


def getTextureManifestEntry(vtex_path: str) -> Optional[Dict[str, Any]]:
    return loadTextureManifest().get(vtex_path)


def setTextureManifestEntry(vtex_path: str, entry: Dict[str, Any]):
    manifest = loadTextureManifest()
    manifest[vtex_path] = entry
    saveTextureManifest(manifest)
