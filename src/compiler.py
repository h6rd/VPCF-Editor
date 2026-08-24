import os
import shutil
import subprocess
import time
import ssl
import zipfile
import urllib.request
from pathlib import Path
from typing import Tuple

from src.config import (
    SCRIPT_DIR, OUTPUT_DIR, COMPILER_URL, LOCAL_COMPILER_ZIP,
    IS_WINDOWS, RESCOMP_OVERRIDE_DIR, TOOLS_SUBPATHS,
)
from src.find_dota import findDotaPath, validateDotaPath

DOTA_CONTENT = None
DOTA_GAME = None
COMPILER = None
COMPILER_INIT_ERROR = ""
LAST_COMPILE_ERROR = ""


def getSslContext():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass

    for path in (
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/etc/ssl/cert.pem",
        "/etc/ssl/ca-bundle.pem",
    ):
        if os.path.exists(path):
            try:
                return ssl.create_default_context(cafile=path)
            except Exception:
                continue

    return ssl.create_default_context()


def downloadUrlToFile(url, dest_path, timeout=30):
    ctx = getSslContext()
    with urllib.request.urlopen(url, context=ctx, timeout=timeout) as response, open(dest_path, "wb") as out_file:
        shutil.copyfileobj(response, out_file)


def downloadCompiler(dota_path) -> Tuple[bool, str]:
    content_addons = os.path.join(dota_path, "content", "dota_addons")
    game_addons = os.path.join(dota_path, "game", "dota_addons")

    try:
        os.makedirs(content_addons, exist_ok=True)
        os.makedirs(game_addons, exist_ok=True)
    except Exception as exc:
        return False, (
            f"No permission to create folders in:\n{dota_path}\n\n"
            f"Error: {exc}\n\n"
            "Try running the program as administrator "
            "(a common cause is Dota 2 being installed under Program Files)."
        )

    downloaded_zip_path = os.path.join(
        SCRIPT_DIR, "d2pfx_compiler_download.tmp.zip"
    )
    zip_path = None
    is_temp_download = False

    try:
        downloadUrlToFile(COMPILER_URL, downloaded_zip_path)
        zip_path = downloaded_zip_path
        is_temp_download = True
    except Exception as exc:
        if os.path.exists(LOCAL_COMPILER_ZIP):
            zip_path = str(LOCAL_COMPILER_ZIP)
        else:
            return False, (
                f"Failed to download the compiler addon from:\n{COMPILER_URL}\n\n"
                f"Error: {exc}\n\n"
                "Check your internet connection. "
                "Antivirus or firewall might be blocking access to raw.githubusercontent.com.\n\n"
                f"The fallback file {LOCAL_COMPILER_ZIP.name} next to the script "
                "was not found either — place it there to work offline."
            )

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(content_addons)
    except zipfile.BadZipFile as exc:
        return False, f"The downloaded file is corrupted or is not a zip archive: {exc}"
    except Exception as exc:
        return False, f"Failed to extract the archive into {content_addons}:\n{exc}"

    try:
        game_img_compiler = os.path.join(game_addons, "d2pfx_compiler")
        os.makedirs(os.path.join(game_img_compiler, "particles"), exist_ok=True)
    except Exception as exc:
        return False, f"Failed to create the particles folder in {game_addons}:\n{exc}"

    if is_temp_download:
        try:
            os.remove(zip_path)
        except Exception:
            pass
    return True, ""


def extractWorkshopTools(dota_path) -> bool:
    compiler_check = os.path.join(dota_path, "game", "bin", "win64", "resourcecompiler.exe")
    if not os.path.exists(compiler_check):
        return False

    ok = True
    for rel in TOOLS_SUBPATHS:
        src = os.path.join(dota_path, rel)
        dst = os.path.join(str(RESCOMP_OVERRIDE_DIR), rel)

        if not os.path.exists(src):
            continue

        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        except Exception:
            ok = False

    return ok


def compilerPath(path) -> str:
    if IS_WINDOWS:
        return str(path)
    return os.path.abspath(str(path))


def buildCmd(*args) -> list:
    prefix = [] if IS_WINDOWS else ["wine"]
    return prefix + [str(COMPILER)] + list(args)


def runCompiler(cmd: list, timeout: int):
    env = os.environ.copy()
    if not IS_WINDOWS:
        env.setdefault("WINEDEBUG", "-all")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)


def initializeCompiler():
    global DOTA_CONTENT, DOTA_GAME, COMPILER, COMPILER_INIT_ERROR
    COMPILER_INIT_ERROR = ""

    if not IS_WINDOWS and not shutil.which("wine"):
        COMPILER_INIT_ERROR = (
            "Wine was not found in PATH.\n"
            "resourcecompiler.exe is a Windows binary and needs wine to run on Linux "
            "(e.g. `sudo apt install wine`)."
        )
        return False

    if RESCOMP_OVERRIDE_DIR.exists():
        dota_path = str(RESCOMP_OVERRIDE_DIR)
        if not validateDotaPath(dota_path):
            COMPILER_INIT_ERROR = (
                f"{RESCOMP_OVERRIDE_DIR} exists, but resourcecompiler.exe or "
                "game/dota is missing inside it."
            )
            return False
    else:
        dota_path = findDotaPath()
        if not dota_path:
            COMPILER_INIT_ERROR = (
                "Could not find the Dota 2 installation folder.\n"
                "Make sure Steam and Dota 2 are installed, and that the Steam "
                "library is visible in the registry or on one of the local drives."
            )
            if not IS_WINDOWS:
                COMPILER_INIT_ERROR += (
                    "\n\nOn Linux, Workshop Tools only get mounted when Dota 2 is "
                    "forced to run under Proton Experimental (Steam -> right-click "
                    "Dota 2 -> Properties -> Compatibility). You can also manually "
                    f"extract a Workshop Tools depot into:\n{RESCOMP_OVERRIDE_DIR}"
                )
            return False

        if not IS_WINDOWS:
            if extractWorkshopTools(dota_path) and validateDotaPath(str(RESCOMP_OVERRIDE_DIR)):
                dota_path = str(RESCOMP_OVERRIDE_DIR)

    DOTA_CONTENT = os.path.join(
        dota_path, "content", "dota_addons", "d2pfx_compiler"
    )
    DOTA_GAME = os.path.join(
        dota_path, "game", "dota_addons", "d2pfx_compiler"
    )
    COMPILER = os.path.join(
        dota_path, "game", "bin", "win64", "resourcecompiler.exe"
    )

    if not os.path.exists(COMPILER):
        COMPILER_INIT_ERROR = (
            f"resourcecompiler.exe was not found at:\n{COMPILER}\n\n"
            "Make sure the Dota 2 Workshop Tools are installed "
            "(Steam → Library → Tools → Dota 2 Workshop Tools)."
        )
        return False

    if not os.path.exists(DOTA_CONTENT):
        ok, err = downloadCompiler(dota_path)
        if not ok:
            COMPILER_INIT_ERROR = err
            return False

    try:
        os.makedirs(os.path.join(DOTA_CONTENT, "particles"), exist_ok=True)
        os.makedirs(os.path.join(DOTA_GAME, "particles"), exist_ok=True)
    except Exception as exc:
        COMPILER_INIT_ERROR = (
            f"Failed to create the particles folders:\n{exc}\n\n"
            f"Check write permissions for:\n{dota_path}\n"
            "(try running the program as administrator)."
        )
        return False

    return True


def compileBatch(file_paths: list, root_dir: str) -> Tuple[int, int, dict]:
    global LAST_COMPILE_ERROR
    LAST_COMPILE_ERROR = ""

    if not COMPILER:
        LAST_COMPILE_ERROR = "The compiler was not initialized (resourcecompiler.exe not found)."
        return 0, 0, {}

    if not file_paths:
        return 0, 0, {}

    content_dir = os.path.join(DOTA_CONTENT, "particles")
    game_dir = os.path.join(DOTA_GAME, "particles")

    stem_map: dict = {}
    errors: dict = {}
    copied: list = []

    for file_path in file_paths:
        path_obj = Path(file_path)
        file_name = path_obj.name
        file_stem = path_obj.stem
        dest_file = os.path.join(content_dir, file_name)

        try:
            shutil.copy2(file_path, dest_file)
            stem_map[file_stem] = (file_path, dest_file)
            copied.append(dest_file)
        except Exception as exc:
            rel = os.path.relpath(file_path, root_dir)
            errors[rel] = f"Failed to copy to {content_dir}: {exc}"

    if not copied:
        return len(file_paths), 0, errors

    filelist_path = os.path.join(content_dir, "_batch_filelist.txt")
    try:
        with open(filelist_path, "w", encoding="utf-8") as f:
            for dest in copied:
                f.write(dest + "\n")
    except Exception as exc:
        LAST_COMPILE_ERROR = f"Failed to write filelist: {exc}"
        return len(file_paths), 0, errors

    cmd = buildCmd("-f", "-filelist", compilerPath(filelist_path))
    try:
        runCompiler(cmd, 300)
    except Exception as exc:
        LAST_COMPILE_ERROR = f"Failed to run resourcecompiler.exe: {exc}"
        try:
            os.remove(filelist_path)
        except Exception:
            pass
        return len(file_paths), 0, errors

    time.sleep(0.5)

    try:
        os.remove(filelist_path)
    except Exception:
        pass

    succeeded = 0

    for file_stem, (file_path, dest_file) in stem_map.items():
        compiled_file = os.path.join(game_dir, f"{file_stem}.vpcf_c")
        rel = os.path.relpath(file_path, root_dir)

        if not os.path.exists(compiled_file):
            errors[rel] = f"resourcecompiler did not produce: {compiled_file}"
            try:
                os.remove(dest_file)
            except Exception:
                pass
            continue

        rel_dir = os.path.dirname(rel)
        final_dir = OUTPUT_DIR / rel_dir
        final_dir.mkdir(parents=True, exist_ok=True)
        final_output = final_dir / f"{file_stem}.vpcf_c"

        try:
            if os.path.exists(final_output):
                os.remove(final_output)
            shutil.move(compiled_file, final_output)
            succeeded += 1
        except Exception as exc:
            errors[rel] = f"Failed to move compiled file to {final_output}: {exc}"

        try:
            os.remove(dest_file)
        except Exception:
            pass

    return len(file_paths), succeeded, errors


def compileVpcf(file_path: str, root_dir: str) -> bool:
    global LAST_COMPILE_ERROR
    LAST_COMPILE_ERROR = ""

    if not COMPILER:
        LAST_COMPILE_ERROR = "The compiler was not initialized (resourcecompiler.exe not found)."
        return False

    path_obj = Path(file_path)
    file_name = path_obj.name
    file_stem = path_obj.stem

    content_dir = os.path.join(DOTA_CONTENT, "particles")
    game_dir = os.path.join(DOTA_GAME, "particles")
    dest_file = os.path.join(content_dir, file_name)

    try:
        shutil.copy2(file_path, dest_file)
    except Exception as exc:
        LAST_COMPILE_ERROR = f"Failed to copy the file to:\n{content_dir}\n\nError: {exc}"
        return False

    cmd = buildCmd("-f", compilerPath(dest_file))
    try:
        proc = runCompiler(cmd, 60)
    except Exception as exc:
        LAST_COMPILE_ERROR = f"Failed to run resourcecompiler.exe:\n{exc}"
        return False

    time.sleep(0.5)
    compiled_file = os.path.join(game_dir, f"{file_stem}.vpcf_c")

    if not os.path.exists(compiled_file):
        details = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        if not details:
            details = "(the compiler produced no output)"
        LAST_COMPILE_ERROR = (
            f"resourcecompiler.exe did not create the file:\n{compiled_file}\n\n"
            f"Command: {' '.join(cmd)}\n"
            f"Return code: {proc.returncode}\n\n"
            f"Compiler output:\n{details}"
        )
        return False

    rel_path = os.path.relpath(file_path, root_dir)
    rel_dir = os.path.dirname(rel_path)

    final_dir = OUTPUT_DIR / rel_dir
    final_dir.mkdir(parents=True, exist_ok=True)

    final_output = final_dir / f"{file_stem}.vpcf_c"
    try:
        if os.path.exists(final_output):
            os.remove(final_output)
        shutil.move(compiled_file, final_output)
    except Exception as exc:
        LAST_COMPILE_ERROR = (
            f"Failed to move the compiled file to:\n{final_output}\n\nError: {exc}"
        )
        return False

    try:
        os.remove(dest_file)
    except Exception:
        pass

    return True
