import json
import os
import sys
import threading
import urllib.request
import urllib.error
import webbrowser
from typing import Optional, Dict, Any

import customtkinter as ctk

from src.config import githubRepo, appVersion
from src.theme import (
    BG, FG, FG_MUTED, ACCENT, ACCENT_HOVER, FONT_FAMILY, ON_ACCENT
)

githubApiUrl = f"https://api.github.com/repos/{githubRepo}/releases/latest"
requestTimeout = 5


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def parseVersion(versionText: str):
    cleaned = versionText.strip().lstrip("vV")
    parts = []
    for chunk in cleaned.split("."):
        digits = ""
        for char in chunk:
            if char.isdigit():
                digits += char
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def isNewerVersion(remoteVersion: str, localVersion: str) -> bool:
    try:
        remoteTuple = parseVersion(remoteVersion)
        localTuple = parseVersion(localVersion)
        length = max(len(remoteTuple), len(localTuple))
        remoteTuple += (0,) * (length - len(remoteTuple))
        localTuple += (0,) * (length - len(localTuple))
        return remoteTuple > localTuple
    except Exception:
        return False


def fetchLatestRelease() -> Optional[Dict[str, Any]]:
    request = urllib.request.Request(
        githubApiUrl,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "VPCF-Editor-UpdateChecker",
        },
    )
    with urllib.request.urlopen(request, timeout=requestTimeout) as response:
        if response.status != 200:
            return None
        rawBody = response.read().decode("utf-8")
        return json.loads(rawBody)


def findDownloadUrl(releaseData: Dict[str, Any]) -> str:
    assets = releaseData.get("assets") or []
    for asset in assets:
        assetName = (asset.get("name") or "").lower()
        if assetName.endswith(".exe") or assetName.endswith(".zip"):
            return asset.get("browser_download_url") or releaseData.get("html_url", "")
    return releaseData.get("html_url", "")


def showUpdatePopup(root: ctk.CTk, latestVersion: str, downloadUrl: str):
    popup = ctk.CTkToplevel(root)
    popup.title("Update Available")

    icon_path = get_resource_path("icon.ico")
    if os.path.isfile(icon_path):
        popup.after(50, lambda: popup.iconbitmap(icon_path))

    popup.geometry("380x180")
    popup.resizable(False, False)
    popup.configure(fg_color=BG)
    popup.transient(root)

    popup.update_idletasks()
    posX = root.winfo_x() + (root.winfo_width() // 2) - 190
    posY = root.winfo_y() + (root.winfo_height() // 2) - 90
    popup.geometry(f"+{max(posX, 0)}+{max(posY, 0)}")

    popup.grab_set()

    ctk.CTkLabel(
        popup, text="A new version is available",
        text_color=FG, font=(FONT_FAMILY, 13, "bold")
    ).pack(pady=(20, 6))

    ctk.CTkLabel(
        popup,
        text=f"VPCF Editor {latestVersion} is out.\nYou are currently on {appVersion}.",
        text_color=FG_MUTED, font=(FONT_FAMILY, 10), justify="center"
    ).pack(pady=(0, 16))

    buttonRow = ctk.CTkFrame(popup, fg_color="transparent")
    buttonRow.pack(pady=(0, 10))

    def onDownloadClick():
        try:
            webbrowser.open(downloadUrl)
        except Exception:
            pass
        popup.destroy()

    ctk.CTkButton(
        buttonRow, text="Download update", command=onDownloadClick,
        fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
        font=(FONT_FAMILY, 10, "bold"), corner_radius=8, height=32, width=170
    ).pack(side="left", padx=6)

    ctk.CTkButton(
        buttonRow, text="Later", command=popup.destroy,
        fg_color="#27272a", hover_color="#3f3f46", text_color=FG,
        font=(FONT_FAMILY, 10, "bold"), corner_radius=8, height=32, width=90
    ).pack(side="left", padx=6)


def backgroundCheck(root: ctk.CTk):
    try:
        releaseData = fetchLatestRelease()
        if not releaseData:
            return

        latestTag = releaseData.get("tag_name") or releaseData.get("name")
        if not latestTag:
            return

        if not isNewerVersion(latestTag, appVersion):
            return

        downloadUrl = findDownloadUrl(releaseData)
        if not downloadUrl:
            return

        root.after(0, lambda: showUpdatePopup(root, latestTag, downloadUrl))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError, OSError):
        return
    except Exception:
        return


def checkForUpdatesAsync(root: ctk.CTk):
    updateThread = threading.Thread(target=backgroundCheck, args=(root,), daemon=True)
    updateThread.start()
