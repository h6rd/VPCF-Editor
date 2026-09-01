import os
import re
import shutil
import subprocess
import zipfile
import platform
import urllib.request
from pathlib import Path
from typing import Tuple, List, Optional, Dict

from src.config import (
    S2V_CLI_URL_WIN, S2V_CLI_URL_LINUX, S2V_CLI_DIR, TEXTURE_CACHE_DIR,
    IS_WINDOWS, SCRIPT_DIR, RAW_DIR
)
from src.find_dota import findDotaPathForVpk
from src import compiler
from src.compiler import getSslContext, runCompiler, buildCmd, compilerPath
from src.image_editor import adjustImage, autoRecolorImage, tintImage
from src.texture_manifest import getTextureManifestEntry


def getCliPath() -> Optional[Path]:
    cli_name = "Source2Viewer-CLI.exe" if IS_WINDOWS else "Source2Viewer-CLI"
    cli_path = S2V_CLI_DIR / cli_name
    return cli_path if cli_path.exists() else None


def downloadCli() -> Tuple[bool, str]:
    if getCliPath() is not None:
        return True, ""

    url = S2V_CLI_URL_WIN if IS_WINDOWS else S2V_CLI_URL_LINUX
    zip_path = S2V_CLI_DIR / "s2v_cli.zip"

    try:
        ctx = getSslContext()
        with urllib.request.urlopen(url, context=ctx, timeout=30) as response, open(zip_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
    except Exception as exc:
        return False, f"Failed to download Source 2 Viewer CLI:\n{exc}"

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(S2V_CLI_DIR)
        
        if not IS_WINDOWS:
            cli_path = S2V_CLI_DIR / "Source2Viewer-CLI"
            if cli_path.exists():
                os.chmod(cli_path, 0o755)
    except Exception as exc:
        return False, f"Failed to extract CLI:\n{exc}"
    finally:
        if zip_path.exists():
            try:
                os.remove(zip_path)
            except Exception:
                pass

    return True, ""


def getVpkPath() -> Optional[str]:
    local_vpks = sorted(SCRIPT_DIR.glob("pak*_dir.vpk"))
    if local_vpks:
        return str(local_vpks[0])

    candidate_roots: List[Path] = []

    dota_path = findDotaPathForVpk()
    if dota_path:
        candidate_roots.append(Path(dota_path))

    if compiler.COMPILER:
        try:
            candidate_roots.append(Path(compiler.COMPILER).resolve().parents[3])
        except Exception:
            pass

    if compiler.DOTA_GAME:
        try:
            candidate_roots.append(Path(compiler.DOTA_GAME).resolve().parents[3])
        except Exception:
            pass

    seen: set[str] = set()
    for root in candidate_roots:
        root_str = str(root)
        if root_str in seen:
            continue
        seen.add(root_str)
        vpk_path = root / "game" / "dota" / "pak01_dir.vpk"
        if vpk_path.exists():
            return str(vpk_path)

    return None


_HASHED_TEXTURE_SUFFIX_RE = re.compile(r"^(?P<base>.+)_[0-9a-f]{6}$", re.IGNORECASE)


def pngBelongsToStem(png_stem: str, vtex_stem: str) -> bool:
    if png_stem == vtex_stem:
        return True
    for sep in ("_", "-"):
        if png_stem.startswith(f"{vtex_stem}{sep}"):
            return True
    return False


def underlyingTexturePath(vtex_path: str) -> Optional[str]:
    path_obj = Path(vtex_path)
    match = _HASHED_TEXTURE_SUFFIX_RE.match(path_obj.stem)
    if not match:
        return None
    return str(path_obj.with_name(f"{match.group('base')}{path_obj.suffix}")).replace("\\", "/")


def sourceTexturePath(vtex_path: str) -> str:
    manifest_entry = getTextureManifestEntry(vtex_path)
    if manifest_entry and isinstance(manifest_entry.get("source_vtex_path"), str):
        return manifest_entry["source_vtex_path"]
    return underlyingTexturePath(vtex_path) or vtex_path


def pngsForVtex(vtex_out: Path) -> List[str]:
    parent_dir = vtex_out.parent
    if not parent_dir.exists():
        return []
    stem = vtex_out.stem
    return sorted(
        str(f) for f in parent_dir.iterdir()
        if f.suffix.lower() == ".png" and pngBelongsToStem(f.stem, stem)
    )


def legacyPngsForRenamedVtex(vtex_out: Path) -> List[str]:
    parent_dir = vtex_out.parent
    if not parent_dir.exists():
        return []

    original_path = underlyingTexturePath(str(vtex_out).replace("\\", "/"))
    if not original_path:
        return []

    original_stem = Path(original_path).stem
    return sorted(
        str(f) for f in parent_dir.iterdir()
        if f.suffix.lower() == ".png" and pngBelongsToStem(f.stem, original_stem)
    )


def inputCandidatesForVtex(vtex_out: Path, rel_input: str) -> List[Path]:
    candidates: List[Path] = []
    source_root = textureSourceRoot(vtex_out)
    if source_root is not None:
        candidates.append(source_root / rel_input)
    candidates.append(RAW_DIR / rel_input)
    candidates.append(TEXTURE_CACHE_DIR / rel_input)

    unique_candidates: List[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_str = str(candidate)
        if candidate_str in seen:
            continue
        seen.add(candidate_str)
        unique_candidates.append(candidate)
    return unique_candidates


def referencedVtexInputs(vtex_out: Path) -> List[Path]:
    try:
        text = vtex_out.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    matches = re.findall(r'"m_fileName"\s+"string"\s+"([^"]+)"', text)
    referenced: List[Path] = []
    for rel_input in matches:
        for candidate in inputCandidatesForVtex(vtex_out, rel_input):
            if candidate.exists():
                referenced.append(candidate)
                break
    return referenced


def vtexInputFilesExist(vtex_out: Path) -> bool:
    try:
        text = vtex_out.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    matches = re.findall(r'"m_fileName"\s+"string"\s+"([^"]+)"', text)
    if not matches:
        return True

    for rel_input in matches:
        if not any(candidate.exists() for candidate in inputCandidatesForVtex(vtex_out, rel_input)):
            return False
    return True


def copyPathPreservingRelativeLocation(
    src: Path,
    source_root: Optional[Path],
    dest_root: Optional[Path],
    fallback_parent: Path,
) -> Path:
    if source_root is not None and dest_root is not None:
        try:
            rel_path = src.relative_to(source_root)
            dst = dest_root / rel_path
        except ValueError:
            dst = fallback_parent / src.name
    else:
        dst = fallback_parent / src.name

    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    return dst


def renamedStemAssetName(file_name: str, old_stem: str, new_stem: str) -> str:
    path_obj = Path(file_name)
    stem = path_obj.stem
    if stem == old_stem:
        new_name_stem = new_stem
    elif stem.startswith(f"{old_stem}_") or stem.startswith(f"{old_stem}-"):
        new_name_stem = new_stem + stem[len(old_stem):]
    else:
        return file_name
    return f"{new_name_stem}{path_obj.suffix}"


def retargetVtexInputs(vtex_out: Path, old_stem: str, new_stem: str) -> List[str]:
    if old_stem == new_stem:
        pngs = pngsForVtex(vtex_out)
        if not pngs:
            pngs = legacyPngsForRenamedVtex(vtex_out)
        return pngs

    source_root = textureSourceRoot(vtex_out)
    if source_root is None:
        pngs = pngsForVtex(vtex_out)
        if not pngs:
            pngs = legacyPngsForRenamedVtex(vtex_out)
        return pngs

    try:
        text = vtex_out.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pngs = pngsForVtex(vtex_out)
        if not pngs:
            pngs = legacyPngsForRenamedVtex(vtex_out)
        return pngs

    replacements: Dict[str, str] = {}
    for rel_input in re.findall(r'"m_fileName"\s+"string"\s+"([^"]+)"', text):
        old_name = Path(rel_input).name
        new_name = renamedStemAssetName(old_name, old_stem, new_stem)
        if new_name == old_name:
            continue

        old_path = source_root / rel_input
        new_rel = str(Path(rel_input).with_name(new_name)).replace("\\", "/")
        new_path = source_root / new_rel

        try:
            if old_path.exists() and old_path.resolve() != new_path.resolve():
                new_path.parent.mkdir(parents=True, exist_ok=True)
                if new_path.exists():
                    new_path.unlink()
                old_path.rename(new_path)
            replacements[rel_input] = new_rel
        except Exception:
            continue

    for old_rel, new_rel in replacements.items():
        text = text.replace(f'"{old_rel}"', f'"{new_rel}"')

    if replacements:
        try:
            vtex_out.write_text(text, encoding="utf-8")
        except Exception:
            pass

    pngs = pngsForVtex(vtex_out)
    if not pngs:
        pngs = legacyPngsForRenamedVtex(vtex_out)
    return pngs


def copyTextureSourceFiles(src_vtex_out: Path, pngs: List[str], dest_vtex_out: Path) -> List[str]:
    dest_vtex_out.parent.mkdir(parents=True, exist_ok=True)
    if src_vtex_out.resolve() != dest_vtex_out.resolve():
        shutil.copy2(src_vtex_out, dest_vtex_out)

    source_root = textureSourceRoot(src_vtex_out)
    dest_root = textureSourceRoot(dest_vtex_out)

    for extra_input in referencedVtexInputs(src_vtex_out):
        copyPathPreservingRelativeLocation(
            extra_input,
            source_root,
            dest_root,
            dest_vtex_out.parent,
        )

    copied_pngs: List[str] = []
    for png_path in sorted(pngs):
        src = Path(png_path)
        if not src.exists():
            continue
        dst = copyPathPreservingRelativeLocation(
            src,
            source_root,
            dest_root,
            dest_vtex_out.parent,
        )
        copied_pngs.append(str(dst))

    return retargetVtexInputs(dest_vtex_out, src_vtex_out.stem, dest_vtex_out.stem)


def materializeGeneratedTexture(vtex_path: str) -> Optional[Tuple[bool, str, Optional[str], List[str]]]:
    manifest_entry = getTextureManifestEntry(vtex_path)
    if not manifest_entry:
        return None

    source_vtex_path = manifest_entry.get("source_vtex_path")
    if not isinstance(source_vtex_path, str) or not source_vtex_path:
        return None

    success, msg, source_vtex_out, source_pngs = extractTexture(source_vtex_path, force=False)
    if not success or not source_vtex_out:
        return False, msg or f"Failed to extract base texture for {vtex_path}", None, []

    raw_vtex_out = RAW_DIR / vtex_path
    try:
        raw_pngs = copyTextureSourceFiles(Path(source_vtex_out), source_pngs, raw_vtex_out)
        mode = manifest_entry.get("mode", "hsv")
        tint_rgb = manifest_entry.get("tint_rgb")
        target_rgb = manifest_entry.get("target_rgb")
        h_shift = float(manifest_entry.get("h_shift", 0.0))
        s_scale = float(manifest_entry.get("s_scale", 1.0))
        v_scale = float(manifest_entry.get("v_scale", 1.0))

        for png in raw_pngs:
            if mode == "auto" and isinstance(target_rgb, list) and len(target_rgb) == 3:
                auto_rgb = (
                    int(target_rgb[0]),
                    int(target_rgb[1]),
                    int(target_rgb[2]),
                )
                autoRecolorImage(png, png, auto_rgb)
            elif mode in ("overlay", "replace") and isinstance(tint_rgb, list) and len(tint_rgb) == 3:
                tint = (
                    int(tint_rgb[0]),
                    int(tint_rgb[1]),
                    int(tint_rgb[2]),
                )
                tintImage(png, png, tint, mode)
            else:
                adjustImage(png, png, h_shift, s_scale, v_scale)
        return True, "", str(raw_vtex_out), raw_pngs
    except Exception as exc:
        return False, f"Failed to rebuild generated texture {vtex_path}:\n{exc}", None, []


def ensureTextureSourceExists(vtex_path: str, vtex_out: Optional[str]) -> Optional[str]:
    if vtex_out and Path(vtex_out).exists():
        return vtex_out

    success, _msg, fresh_vtex_out, _pngs = extractTexture(vtex_path, force=False)
    if success and fresh_vtex_out and Path(fresh_vtex_out).exists():
        return fresh_vtex_out

    return None


def persistRawTextureFiles(logical_vtex_path: str, disk_vtex_path: str, pngs: List[str]) -> Tuple[str, List[str]]:
    dest_vtex_out = RAW_DIR / logical_vtex_path
    copied_pngs = copyTextureSourceFiles(Path(disk_vtex_path), pngs, dest_vtex_out)
    return str(dest_vtex_out), copied_pngs


def cachedExtraction(vtex_path: str) -> Optional[Tuple[bool, str, Optional[str], List[str]]]:
    raw_vtex_out = RAW_DIR / vtex_path
    if raw_vtex_out.exists() and vtexInputFilesExist(raw_vtex_out):
        pngs = pngsForVtex(raw_vtex_out)
        if not pngs:
            pngs = legacyPngsForRenamedVtex(raw_vtex_out)
        if pngs:
            return True, "", str(raw_vtex_out), pngs

    vtex_out = TEXTURE_CACHE_DIR / vtex_path
    if vtex_out.exists() and vtexInputFilesExist(vtex_out):
        pngs = pngsForVtex(vtex_out)
        if not pngs:
            pngs = legacyPngsForRenamedVtex(vtex_out)
        if pngs:
            return True, "", str(vtex_out), pngs

    source_vtex_path = underlyingTexturePath(vtex_path)
    if not source_vtex_path:
        return None

    source_vtex_out = TEXTURE_CACHE_DIR / source_vtex_path
    if not source_vtex_out.exists():
        return None
    pngs = pngsForVtex(source_vtex_out)
    if not pngs:
        return None
    return True, "", str(source_vtex_out), pngs


def extractTexture(vtex_path: str, force: bool = False) -> Tuple[bool, str, Optional[str], List[str]]:
    if not force:
        cached = cachedExtraction(vtex_path)
        if cached is not None:
            return cached

    cli_path = getCliPath()
    if not cli_path:
        return False, "Source 2 Viewer CLI not found. Please wait for it to download.", None, []

    vpk_path = getVpkPath()
    if not vpk_path:
        return False, "Dota 2 pak01_dir.vpk not found.", None, []

    source_vtex_path = underlyingTexturePath(vtex_path) or vtex_path

    vtex_c_path = source_vtex_path
    if not vtex_c_path.endswith("_c"):
        vtex_c_path += "_c"

    out_dir = TEXTURE_CACHE_DIR
    cmd = [
        str(cli_path),
        "-i", vpk_path,
        "-d",
        "-f", vtex_c_path,
        "-o", str(out_dir)
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
    except subprocess.CalledProcessError as e:
        return False, f"CLI error: {e.stderr}", None, []
    except Exception as exc:
        return False, f"Failed to extract texture:\n{exc}", None, []

    vtex_out = out_dir / source_vtex_path
    if not vtex_out.parent.exists():
        return False, f"Extracted directory not found: {vtex_out.parent}", None, []

    pngs = pngsForVtex(vtex_out)

    if not vtex_out.exists() or not pngs:
        return False, f"Expected output not found in {vtex_out.parent}", None, []

    return True, "", str(vtex_out), pngs


def renameExtractedTextureAssets(old_vtex_path: str, new_vtex_path: str, pngs: List[str]) -> List[str]:
    _ = pngs
    return retargetVtexInputs(Path(new_vtex_path), Path(old_vtex_path).stem, Path(new_vtex_path).stem)


def extractTexturesBatch(vtex_paths: List[str]) -> Dict[str, Tuple[bool, str, Optional[str], List[str]]]:
    unique_paths = list(dict.fromkeys(vtex_paths))
    results: Dict[str, Tuple[bool, str, Optional[str], List[str]]] = {}

    if not unique_paths:
        return results

    requested_to_target: Dict[str, str] = {}
    need_extract_targets: List[str] = []
    for vp in unique_paths:
        cached = cachedExtraction(vp)
        if cached is not None:
            results[vp] = cached
            continue

        target_vp = underlyingTexturePath(vp) or vp
        requested_to_target[vp] = target_vp
        if target_vp not in need_extract_targets:
            need_extract_targets.append(target_vp)

    if not need_extract_targets:
        return results

    cli_path = getCliPath()
    if not cli_path:
        msg = "Source 2 Viewer CLI not found. Please wait for it to download."
        for vp in requested_to_target:
            results[vp] = (False, msg, None, [])
        return results

    vpk_path = getVpkPath()
    if not vpk_path:
        msg = "Dota 2 pak01_dir.vpk not found."
        for vp in requested_to_target:
            results[vp] = (False, msg, None, [])
        return results

    vtex_c_paths = [vp if vp.endswith("_c") else vp + "_c" for vp in need_extract_targets]

    out_dir = TEXTURE_CACHE_DIR
    cmd = [
        str(cli_path),
        "-i", vpk_path,
        "-d",
        "-f", ",".join(vtex_c_paths),
        "-o", str(out_dir)
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)
    except subprocess.CalledProcessError as e:
        msg = f"CLI error: {e.stderr}"
        for vp in requested_to_target:
            results[vp] = (False, msg, None, [])
        return results
    except Exception as exc:
        msg = f"Failed to extract textures:\n{exc}"
        for vp in requested_to_target:
            results[vp] = (False, msg, None, [])
        return results

    target_results: Dict[str, Tuple[bool, str, Optional[str], List[str]]] = {}
    for vp in need_extract_targets:
        vtex_out = out_dir / vp
        if not vtex_out.parent.exists():
            target_results[vp] = (False, f"Extracted directory not found: {vtex_out.parent}", None, [])
            continue

        pngs = pngsForVtex(vtex_out)
        if not vtex_out.exists() or not pngs:
            target_results[vp] = (False, f"Expected output not found in {vtex_out.parent}", None, [])
            continue

        target_results[vp] = (True, "", str(vtex_out), pngs)

    for requested_vp, target_vp in requested_to_target.items():
        results[requested_vp] = target_results.get(
            target_vp,
            (False, f"Texture was not extracted: {target_vp}", None, []),
        )

    return results


def textureSourceRoot(path_obj: Path) -> Optional[Path]:
    for root in (RAW_DIR, TEXTURE_CACHE_DIR):
        try:
            path_obj.relative_to(root)
            return root
        except ValueError:
            continue
    return None


def compileTexture(vtex_path: str, output_dir: Path) -> Tuple[bool, str, Optional[str]]:
    results, errors = compileTextureBatch([vtex_path], output_dir)
    if vtex_path in results:
        return True, "", results[vtex_path]
    return False, errors.get(vtex_path, "Unknown texture compile error."), None


def compileTextureBatch(vtex_paths: List[str], output_dir: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    results: Dict[str, str] = {}
    errors: Dict[str, str] = {}

    if not vtex_paths:
        return results, errors

    if not compiler.DOTA_CONTENT or not compiler.DOTA_GAME:
        for vp in vtex_paths:
            errors[vp] = "Compiler not initialized."
        return results, errors

    content_dests: Dict[str, Path] = {}
    for vp in vtex_paths:
        path_obj = Path(vp)
        source_root = textureSourceRoot(path_obj)
        if source_root is None:
            errors[vp] = f"Not inside raw or texture cache: {path_obj}"
            continue

        rel_path = path_obj.relative_to(source_root)
        content_dest = Path(compiler.DOTA_CONTENT) / rel_path
        try:
            content_dest.parent.mkdir(parents=True, exist_ok=True)
            for item in path_obj.parent.iterdir():
                dest_item = content_dest.parent / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest_item)
        except Exception as exc:
            errors[vp] = f"Failed to copy files to content dir: {exc}"
            continue

        content_dests[vp] = content_dest

    if not content_dests:
        return results, errors

    filelist_path = Path(compiler.DOTA_CONTENT) / "_texture_batch_filelist.txt"
    try:
        with open(filelist_path, "w", encoding="utf-8") as f:
            for dest in content_dests.values():
                f.write(compilerPath(dest) + "\n")
    except Exception as exc:
        for vp in content_dests:
            errors[vp] = f"Failed to write filelist: {exc}"
        return results, errors

    cmd = buildCmd("-f", "-filelist", compilerPath(filelist_path))
    try:
        proc = runCompiler(cmd, 300)
    except Exception as exc:
        for vp in content_dests:
            errors[vp] = f"Compiler execution failed: {exc}"
        try:
            os.remove(filelist_path)
        except Exception:
            pass
        return results, errors

    try:
        os.remove(filelist_path)
    except Exception:
        pass

    for vp, content_dest in content_dests.items():
        rel_path = content_dest.relative_to(compiler.DOTA_CONTENT)
        compiled_file = Path(compiler.DOTA_GAME) / rel_path.with_suffix('.vtex_c')
        if not compiled_file.exists():
            details = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
            if not details:
                details = "(the compiler produced no output)"
            errors[vp] = (
                f"resourcecompiler did not produce: {compiled_file}\n\n"
                f"Command: {' '.join(str(part) for part in cmd)}\n"
                f"Return code: {proc.returncode}\n\n"
                f"Compiler output:\n{details}"
            )
            continue

        final_output = output_dir / rel_path.with_suffix('.vtex_c')
        try:
            final_output.parent.mkdir(parents=True, exist_ok=True)
            if final_output.exists():
                os.remove(final_output)
            shutil.copy2(compiled_file, final_output)
            results[vp] = str(final_output)
        except Exception as exc:
            errors[vp] = f"Failed to move compiled texture: {exc}"

    return results, errors