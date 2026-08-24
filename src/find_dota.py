import os
import re
import string

from src.config import IS_WINDOWS, IS_MAC

if IS_WINDOWS:
    import winreg


def validateDotaPath(path):
    if not os.path.exists(path):
        return False
    compiler_path = os.path.join(
        path, "game", "bin", "win64", "resourcecompiler.exe"
    )
    game_folder = os.path.join(path, "game", "dota")
    return os.path.exists(compiler_path) and os.path.exists(game_folder)


def findSteamPathWindows():
    for key_path in [r"SOFTWARE\WOW6432Node\Valve\Steam", r"SOFTWARE\Valve\Steam"]:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            steam_path = winreg.QueryValueEx(key, "InstallPath")[0]
            winreg.CloseKey(key)
            return steam_path
        except Exception:
            continue
    return None


def findSteamRootsUnix():
    home = os.path.expanduser("~")
    if IS_MAC:
        candidates = [os.path.join(home, "Library", "Application Support", "Steam")]
    else:
        candidates = [
            os.path.join(home, ".local", "share", "Steam"),
            os.path.join(home, ".steam", "steam"),
            os.path.join(home, ".steam", "root"),
            os.path.join(home, ".var", "app", "com.valvesoftware.Steam", "data", "Steam"),
        ]
    return [c for c in candidates if os.path.exists(c)]


def searchAllDrives(seen_paths=None):
    if seen_paths is None:
        seen_paths = set()
        
    available_drives = [
        f"{letter}:\\"
        for letter in string.ascii_uppercase
        if os.path.exists(f"{letter}:\\")
    ]
    common_paths = [
        r"SteamLibrary\steamapps\common\dota 2 beta",
        r"Steam\steamapps\common\dota 2 beta",
        r"Program Files (x86)\Steam\steamapps\common\dota 2 beta",
        r"Program Files\Steam\steamapps\common\dota 2 beta",
    ]
    
    for drive in available_drives:
        for path in common_paths:
            full_path = os.path.normpath(os.path.join(drive, path))
            
            if full_path in seen_paths:
                continue
                
            seen_paths.add(full_path)
            if os.path.exists(full_path) and validateDotaPath(full_path):
                return full_path
    return None


def findDotaInSteamRoot(steam_path, seen_paths=None):
    if seen_paths is None:
        seen_paths = set()
        
    default_dota = os.path.normpath(os.path.join(
        steam_path, "steamapps", "common", "dota 2 beta"
    ))
    
    if default_dota not in seen_paths:
        seen_paths.add(default_dota)
        if os.path.exists(default_dota) and validateDotaPath(default_dota):
            return default_dota

    library_file = os.path.join(
        steam_path, "steamapps", "libraryfolders.vdf"
    )
    
    if os.path.exists(library_file):
        try:
            with open(library_file, "r", encoding="utf-8") as f:
                content = f.read()
            paths = re.findall(r'"path"\s+"([^"]+)"', content)
            
            for lib_path in paths:
                lib_path = lib_path.replace("\\\\", "\\")
                dota_path = os.path.normpath(os.path.join(
                    lib_path, "steamapps", "common", "dota 2 beta"
                ))
                
                if dota_path in seen_paths:
                    continue
                    
                seen_paths.add(dota_path)
                if os.path.exists(dota_path) and validateDotaPath(dota_path):
                    return dota_path
        except Exception:
            pass
            
    return None


def findDotaPath():
    seen_paths = set()
    
    if IS_WINDOWS:
        steam_path = findSteamPathWindows()
        if steam_path:
            dota_path = findDotaInSteamRoot(steam_path, seen_paths)
            if dota_path:
                return dota_path
        return searchAllDrives(seen_paths)

    for steam_path in findSteamRootsUnix():
        dota_path = findDotaInSteamRoot(steam_path, seen_paths)
        if dota_path:
            return dota_path
            
    return None