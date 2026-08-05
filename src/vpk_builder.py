import random
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

try:
    import vpk
except ImportError:
    vpk = None

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

from src.config import SYMBOLS, GARBAGE_SUFFIX_RE


def cleanupGarbageFiles(path: Path):
    for item in path.rglob("*"):
        if item.is_file() and GARBAGE_SUFFIX_RE.search(item.name):
            try:
                item.unlink()
            except Exception:
                pass


def moveToTrashOrDelete(item: Path) -> bool:
    try:
        if send2trash is not None:
            send2trash(str(item))
        else:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        return True
    except Exception:
        return False


def compileToVpk(
    items_to_compile: List[Path],
    work_dir: Path,
    delete_sources: bool = True,
) -> Optional[Path]:
    items_to_compile = [
        item for item in items_to_compile
        if not GARBAGE_SUFFIX_RE.search(item.name)
    ]
    if not items_to_compile:
        print(f"{SYMBOLS['cross']} No files to pack into a VPK.")
        return None
    if vpk is None:
        print(
            f"{SYMBOLS['cross']} The 'vpk' module is not installed "
            "(pip install vpk). VPK was not created."
        )
        return None

    print(
        f"{SYMBOLS['package']} Compiling {len(items_to_compile)} items to VPK..."
    )
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            blacklisted_nums = {66}
            random_num = random.randint(9, 99)
            while random_num in blacklisted_nums:
                random_num = random.randint(9, 99)
            compile_dir = temp_path / f"pak{random_num:02d}_dir"
            compile_dir.mkdir()
            for item in items_to_compile:
                destination = compile_dir / item.name
                if item.is_dir():
                    shutil.copytree(str(item), str(destination))
                    cleanupGarbageFiles(destination)
                    print(f"  {SYMBOLS['check']} Added directory: {item.name}")
                else:
                    shutil.copy2(str(item), str(destination))
                    print(f"  {SYMBOLS['check']} Added file: {item.name}")
            output_path = work_dir / f"pak{random_num:02d}_dir.vpk"
            print(f"\n{SYMBOLS['save']} Saving VPK to: {output_path.name}")
            newpak = vpk.new(str(output_path))
            newpak.read_dir(str(compile_dir))
            newpak.save(str(output_path))
            print(f"{SYMBOLS['check']} VPK compilation complete!")
        if delete_sources:
            print(f"\n{SYMBOLS['trash']} Deleting source files...")
            for item in items_to_compile:
                success = moveToTrashOrDelete(item)
                if success:
                    print(f"  {SYMBOLS['check']} Moved to trash: {item.name}")
                else:
                    print(f"  {SYMBOLS['cross']} Failed to delete: {item.name}")
        return output_path
    except Exception as e:
        print(f"{SYMBOLS['cross']} Compilation error: {e}")
        raise
