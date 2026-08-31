import os
import random
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from typing import List, Optional, Tuple, Dict, Any

import customtkinter as ctk

from src.config import SCRIPT_DIR, OUTPUT_DIR, RAW_DIR
from src import compiler
from src.compiler import initializeCompiler, compileVpcf, compileBatch
from src.vpk_builder import compileToVpk
from src.color_parser import findColors, applyColorChanges, colorEntryRgba255, colorEntryLabel
from src.recolor import isGrayscale, recolorPreservingSv
from src.file_utils import readTextFile, writeTextFile, scanFolder
from src.theme import (
    setupDarkStyle, BG, BG_PANEL, BG_CARD, BG_ELEV, BG_ELEV_HOVER,
    BORDER, FG, FG_MUTED, ACCENT, ACCENT_HOVER, FONT_FAMILY, FONT_BOLD, FONT_SMALL,
    DANGER, ON_ACCENT
)
from src.color_picker import askCustomColor
from src.texture_parser import findTextures, applyTextureChanges, generateUniqueName
from src.texture_manager import (
    extractTexture, extractTexturesBatch, compileTextureBatch,
    downloadCli, renameExtractedTextureAssets,
    persistRawTextureFiles, sourceTexturePath, ensureTextureSourceExists,
)
from src.image_editor import (
    adjustImage, autoRecolorImage, tintImage, isMostlyGrayscale, previewTextureImage,
)
from src.texture_manifest import getTextureManifestEntry, setTextureManifestEntry
from PIL import Image, ImageTk
try:
    import PIL._tkinter_finder
except ImportError:
    pass


_scrollable_frame_patched = False


def buildUi(state: Dict[str, Any]):
    root = state["root"]
    root.configure(fg_color="#0f0f11")

    # top
    top = ctk.CTkFrame(root, fg_color="#18181b", corner_radius=12)
    top.pack(side="top", fill="x", padx=16, pady=12)

    row1 = ctk.CTkFrame(top, fg_color="transparent")
    row1.pack(fill="x", padx=12, pady=(12, 8))

    ctk.CTkLabel(row1, text="Folder:", text_color=FG_MUTED, font=(
        FONT_FAMILY, 11, "bold")).pack(side="left", padx=(0, 8))

    state["folder_var"] = tk.StringVar(value=state["root_dir"])
    folder_entry = ctk.CTkEntry(
        row1, textvariable=state["folder_var"], state="readonly",
        height=32, corner_radius=8, fg_color="#27272a", border_width=0, text_color=FG
    )
    folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

    ctk.CTkButton(
        row1, text="Browse...", command=lambda: chooseFolder(state), width=90, height=32,
        corner_radius=8, fg_color="#27272a", hover_color="#3f3f46", text_color=FG
    ).pack(side="left", padx=(0, 6))

    ctk.CTkButton(
        row1, text="Rescan", command=lambda: rescan(state), width=80, height=32,
        corner_radius=8, fg_color="#27272a", hover_color="#3f3f46", text_color=FG
    ).pack(side="left")

    row2 = ctk.CTkFrame(top, fg_color="transparent")
    row2.pack(fill="x", padx=12, pady=(0, 12))

    ctk.CTkLabel(row2, text="BULK ACTIONS", text_color=FG_MUTED, font=(
        FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 12))

    ctk.CTkButton(
        row2, text="🎨  Recolor all → 1 color", height=30,
        fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT, font=(
            FONT_FAMILY, 10, "bold"),
        corner_radius=6, command=lambda: recolorAllFilesSingleColor(state)
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        row2, text="🎲  Recolor all → 2 colors (random)", height=30,
        fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT, font=(
            FONT_FAMILY, 10, "bold"),
        corner_radius=6, command=lambda: recolorAllFilesTwoColors(state)
    ).pack(side="left")

    # main
    main_container = ctk.CTkFrame(root, fg_color="transparent")
    main_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

    # left
    left = ctk.CTkFrame(main_container, fg_color="#18181b",
                        width=280, corner_radius=12)
    left.pack(side="left", fill="both", padx=(0, 8))
    left.pack_propagate(False)

    ctk.CTkLabel(left, text="FILES WITH COLORS", text_color=FG_MUTED, font=(
        FONT_FAMILY, 10, "bold")).pack(anchor="w", padx=14, pady=(12, 6))

    file_scroll = ctk.CTkScrollableFrame(
        left, fg_color="transparent", corner_radius=0)
    file_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 8))
    state["file_scroll"] = file_scroll

    # right
    right = ctk.CTkFrame(main_container, fg_color="#18181b", corner_radius=12)
    right.pack(side="left", fill="both", expand=True)

    title_container = ctk.CTkFrame(right, fg_color="transparent")
    title_container.pack(fill="x", padx=16, pady=(12, 4))

    state["file_title_var"] = tk.StringVar(value="Select a file on the left")
    ctk.CTkLabel(title_container, textvariable=state["file_title_var"], text_color=FG, font=(
        FONT_FAMILY, 11, "bold")).pack(anchor="w")

    state["scrollable_frame"] = ctk.CTkScrollableFrame(
        right, fg_color="transparent", corner_radius=0)
    state["scrollable_frame"].pack(fill="both", expand=True, padx=8, pady=4)

    # status
    status = ctk.CTkFrame(root, fg_color="#18181b", height=32, corner_radius=0)
    status.pack(side="bottom", fill="x")

    status_text = "Ready" if state["compiler_ready"] else "Ready (Warning: Compiler not found!)"
    state["status_var"] = tk.StringVar(value=status_text)
    ctk.CTkLabel(status, textvariable=state["status_var"], text_color=FG_MUTED, font=(
        FONT_FAMILY, 9)).pack(side="left", padx=16)

    actions = ctk.CTkFrame(status, fg_color="transparent")
    actions.pack(side="right", padx=16, pady=4)

    state["revert_btn"] = ctk.CTkButton(
        actions, text="Discard", height=24, width=92,
        fg_color="#27272a", hover_color="#3a2020", text_color=DANGER, font=(FONT_FAMILY, 9, "bold"),
        corner_radius=6, command=lambda: revertCurrentFile(state), state="disabled"
    )
    state["revert_btn"].pack(side="right")

    state["save_btn"] = ctk.CTkButton(
        actions, text="Save", height=24, width=76,
        fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT, font=(
            FONT_FAMILY, 9, "bold"),
        corner_radius=6, command=lambda: saveCurrentFile(state), state="disabled"
    )
    state["save_btn"].pack(side="right", padx=(0, 8))

    state["progress_bar"] = ctk.CTkProgressBar(
        status, orientation="horizontal", width=200, height=8, corner_radius=4, progress_color=ACCENT)
    state["progress_bar"].set(0)


def collectAllTexturePaths(scan_results: List[Tuple[str, str, int]]) -> List[str]:
    texture_paths: set[str] = set()
    for _rel_path, abs_path, _count in scan_results:
        try:
            text, _enc = readTextFile(abs_path)
        except Exception:
            continue
        for entry in findTextures(text):
            texture_paths.add(entry["vtex_path"])
    return sorted(texture_paths)


def recordTextureManifest(
    logical_vtex_path: str,
    source_vtex_path: str,
    mode: str,
    h_shift: float = 0.0,
    s_scale: float = 1.0,
    v_scale: float = 1.0,
    tint_rgb: Optional[Tuple[int, int, int]] = None,
    target_rgb: Optional[Tuple[int, int, int]] = None,
):
    setTextureManifestEntry(logical_vtex_path, {
        "source_vtex_path": source_vtex_path,
        "mode": mode,
        "h_shift": h_shift,
        "s_scale": s_scale,
        "v_scale": v_scale,
        "tint_rgb": list(tint_rgb) if tint_rgb else None,
        "target_rgb": list(target_rgb) if target_rgb else None,
    })


def clearDirectoryContents(dir_path: Path):
    import shutil

    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        return

    for child in dir_path.iterdir():
        try:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        except Exception:
            pass


def resetSessionArtifacts():
    clearDirectoryContents(RAW_DIR)
    clearDirectoryContents(OUTPUT_DIR)

    if compiler.DOTA_CONTENT:
        clearDirectoryContents(Path(compiler.DOTA_CONTENT) / "materials")
    if compiler.DOTA_GAME:
        clearDirectoryContents(Path(compiler.DOTA_GAME) / "materials")



def preloadAllTextures(state: Dict[str, Any]):
    scan_results = state.get("last_scan_results", [])
    if not scan_results:
        return

    total_files = len(scan_results)
    state["progress_bar"].set(0)
    state["progress_bar"].pack(side="right", padx=(0, 16))
    state["status_var"].set(f"Indexing textures in {total_files} file(s)...")
    state["root"].update()

    texture_paths = collectAllTexturePaths(scan_results)
    if not texture_paths:
        state["progress_bar"].pack_forget()
        state["status_var"].set(f"Found {total_files} file(s) with colors")
        return

    state["status_var"].set(f"Preloading {len(texture_paths)} texture(s)...")
    state["progress_bar"].set(0.5)
    state["root"].update()

    extracted = extractTexturesBatch(texture_paths)
    preloaded = sum(1 for success, _msg, _vtex_out, pngs in extracted.values() if success and pngs)

    generated_sources = sorted({
        vtex_out for success, _msg, vtex_out, pngs in extracted.values()
        if success and pngs and vtex_out and str(vtex_out).startswith(str(RAW_DIR))
    })
    if generated_sources:
        state["status_var"].set(f"Recompiling {len(generated_sources)} generated texture(s)...")
        state["progress_bar"].set(0.8)
        state["root"].update()
        compileTextureBatch(generated_sources, OUTPUT_DIR)

    state["progress_bar"].set(1.0)
    state["root"].update()
    state["progress_bar"].pack_forget()
    state["status_var"].set(
        f"Found {total_files} file(s) with colors — preloaded {preloaded}/{len(texture_paths)} texture(s)"
    )


def chooseFolder(state: Dict[str, Any]):
    new_dir = filedialog.askdirectory(
        initialdir=state["root_dir"], title="Choose a folder with .vpcf files")
    if new_dir:
        if not maybePromptSave(state):
            return
        state["root_dir"] = new_dir
        state["folder_var"].set(state["root_dir"])
        rescan(state)


def rescan(state: Dict[str, Any]):
    state["status_var"].set("Scanning...")
    state["root"].update_idletasks()
    results = scanFolder(state["root_dir"])
    state["last_scan_results"] = results
    populateTree(state, results)
    clearRightPanel(state)
    preloadAllTextures(state)
    if not results:
        state["status_var"].set("Found 0 file(s) with colors")


def updateTreeSelection(state: Dict[str, Any], selected_path: Optional[str]):
    prev_path = state.get("active_selected_path")
    if prev_path and prev_path != selected_path and prev_path in state["file_buttons"]:
        state["file_buttons"][prev_path].configure(
            fg_color="transparent", hover_color="#27272a", text_color=FG)

    state["active_selected_path"] = selected_path
    if selected_path and selected_path in state["file_buttons"]:
        state["file_buttons"][selected_path].configure(
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT)


def onFileSelect(state: Dict[str, Any], path: str):
    if path == state.get("current_path"):
        return

    updateTreeSelection(state, path)
    state["root"].update_idletasks()

    ok, _pending_texture_paths = applyCurrentEditsToDisk(state)
    if not ok:
        updateTreeSelection(state, state.get("current_path"))
        return

    loadFile(state, path)


def populateTree(state: Dict[str, Any], results: List[Tuple[str, str, int]]):
    scroll = state["file_scroll"]
    for child in scroll.winfo_children():
        child.destroy()

    state["tree_item_paths"].clear()
    state["tree_item_for_path"].clear()
    state["file_buttons"].clear()
    state["active_selected_path"] = None


    if not results:
        ctk.CTkLabel(
            scroll, text="No files with colors found.",
            text_color=FG_MUTED, font=(FONT_FAMILY, 9),
        ).pack(anchor="w", padx=10, pady=12)
        return

    tree_struct: Dict[str, Any] = {"_files": [], "_dirs": {}}

    for rel_path, abs_path, count in sorted(results, key=lambda r: r[0].lower()):
        parts = rel_path.split(os.sep)
        curr = tree_struct
        for part in parts[:-1]:
            if part not in curr["_dirs"]:
                curr["_dirs"][part] = {"_files": [], "_dirs": {}}
            curr = curr["_dirs"][part]
        curr["_files"].append((parts[-1], abs_path, count))

    def renderLevel(parent_widget, dirs_map, files_list, indent_level=0):
        for dir_name, sub_data in sorted(dirs_map.items()):
            folder_frame = ctk.CTkFrame(parent_widget, fg_color="transparent")
            folder_frame.pack(fill="x", pady=(2, 0))

            is_open = tk.BooleanVar(value=True)

            header_btn = ctk.CTkButton(
                folder_frame,
                text=f"▼  📁  {dir_name}",
                anchor="w",
                height=28,
                corner_radius=6,
                fg_color="transparent",
                hover_color="#27272a",
                text_color=FG_MUTED,
                font=(FONT_FAMILY, 10, "bold"),
            )
            header_btn.pack(fill="x", padx=(indent_level * 10, 0))

            sub_container = ctk.CTkFrame(folder_frame, fg_color="transparent")
            sub_container.pack(fill="x")

            def toggleFolder(b=header_btn, c=sub_container, var=is_open, name=dir_name):
                if var.get():
                    c.pack_forget()
                    var.set(False)
                    b.configure(text=f"▶  📁  {name}")
                else:
                    c.pack(fill="x")
                    var.set(True)
                    b.configure(text=f"▼  📁  {name}")

            header_btn.configure(command=toggleFolder)
            renderLevel(sub_container, sub_data["_dirs"], sub_data["_files"], indent_level + 1)

        for filename, abs_path, count in files_list:
            item_id = abs_path
            state["tree_item_paths"][item_id] = abs_path
            state["tree_item_for_path"][abs_path] = item_id

            is_selected = (abs_path == state.get("current_path"))
            fg_col = ACCENT if is_selected else "transparent"
            txt_col = ON_ACCENT if is_selected else FG

            file_btn = ctk.CTkButton(
                parent_widget,
                text=f"📄  {filename}  ({count})",
                anchor="w",
                height=28,
                corner_radius=6,
                fg_color=fg_col,
                hover_color=ACCENT_HOVER if is_selected else "#27272a",
                text_color=txt_col,
                font=(FONT_FAMILY, 9),
                command=lambda p=abs_path: onFileSelect(state, p),
            )
            file_btn.pack(fill="x", padx=(indent_level * 10, 0), pady=1)
            state["file_buttons"][abs_path] = file_btn

    renderLevel(scroll, tree_struct["_dirs"], tree_struct["_files"], indent_level=0)


def refreshTreeLabel(state: Dict[str, Any], abs_path: str):
    btn = state["file_buttons"].get(abs_path)
    if not btn:
        return
    count = len(state["current_entries"])
    name = os.path.basename(abs_path)
    btn.configure(text=f"📄  {name}  ({count})")



def applyCurrentEditsToDisk(state: Dict[str, Any]) -> Tuple[bool, List[str]]:
    if not state["current_path"] or not state["dirty"]:
        return True, []

    new_values_map: Dict[int, List[float]] = {}
    for entry in state["current_entries"]:
        vars_ = state["entry_vars"].get(id(entry))
        if not vars_:
            continue
        try:
            raw_255 = [max(0, min(255, v.get())) for v in vars_]
        except tk.TclError:
            messagebox.showwarning(
                "Invalid Value", f"Check the values for color '{entry['key']}' — they must be numbers between 0-255.")
            return False, []
        if entry["kind"] == "byte":
            vals = [float(v) for v in raw_255]
        else:
            vals = [v / 255.0 for v in raw_255]
        new_values_map[id(entry)] = vals

    new_text = applyColorChanges(
        state["current_text"], state["current_entries"], new_values_map)

    pending_texture_paths: List[str] = []
    new_texture_paths: Dict[int, str] = {}
    modified_map = state.setdefault("modified_textures", {})
    texture_errors: List[str] = []

    for entry in state.get("current_textures", []):
        if not (entry.get("modified") and "vtex_out" in entry):
            continue

        original_vtex_path = entry["vtex_path"]

        try:
            source_vtex = sourceTexturePath(original_vtex_path)
            new_vtex_name = generateUniqueName(
                source_vtex,
                entry.get("h_shift", 0.0),
                entry.get("s_scale", 1.0),
                entry.get("v_scale", 1.0),
                entry.get("recolor_mode", "hsv"),
                entry.get("tint_rgb"),
            )

            valid_vtex_out = ensureTextureSourceExists(original_vtex_path, entry.get("vtex_out"))
            if not valid_vtex_out:
                texture_errors.append(
                    f"{original_vtex_path.split('/')[-1]}: source texture is missing on disk "
                    "and could not be re-extracted. This edit was skipped."
                )
                continue
            entry["vtex_out"] = valid_vtex_out
            if not entry.get("pngs"):
                from src.texture_manager import pngsForVtex
                entry["pngs"] = pngsForVtex(Path(valid_vtex_out))

            mode = entry.get("recolor_mode", "hsv")
            tint_rgb = entry.get("tint_rgb")
            for png in entry.get("pngs", []):
                if mode in ("overlay", "replace") and tint_rgb:
                    tintImage(png, png, tuple(tint_rgb), mode)
                else:
                    adjustImage(png, png, entry["h_shift"], entry["s_scale"], entry["v_scale"])

            old_vtex_path = Path(entry["vtex_out"])
            new_vtex_path = old_vtex_path.with_name(new_vtex_name.split("/")[-1])
            renamed_pngs = entry.get("pngs", [])
            if old_vtex_path.exists() and old_vtex_path != new_vtex_path:
                old_vtex_path.rename(new_vtex_path)
                renamed_pngs = renameExtractedTextureAssets(
                    str(old_vtex_path), str(new_vtex_path), entry.get("pngs", [])
                )
            entry["vtex_out"] = str(new_vtex_path)
            entry["pngs"] = renamed_pngs

            raw_vtex_path, _raw_pngs = persistRawTextureFiles(
                new_vtex_name, str(new_vtex_path), renamed_pngs
            )

            recordTextureManifest(
                new_vtex_name,
                source_vtex,
                entry.get("recolor_mode", "hsv"),
                float(entry.get("h_shift", 0.0)),
                float(entry.get("s_scale", 1.0)),
                float(entry.get("v_scale", 1.0)),
                tuple(entry.get("tint_rgb")) if entry.get("tint_rgb") else None,
                None,
            )

            base_dir = source_vtex.rsplit("/", 1)[0]
            final_vtex_str = f"{base_dir}/{Path(raw_vtex_path).name}"
            new_texture_paths[id(entry)] = final_vtex_str
            if final_vtex_str != original_vtex_path:
                modified_map.pop(original_vtex_path, None)
            modified_map[final_vtex_str] = textureEditInfo(entry)
            pending_texture_paths.append(raw_vtex_path)

        except Exception as exc:
            texture_errors.append(f"{original_vtex_path.split('/')[-1]}: {exc}")
            continue

    if texture_errors:
        messagebox.showwarning(
            "Some texture edits could not be saved",
            "The .vpcf color changes were saved, but these texture edits ran "
            "into a problem and were skipped:\n\n" + "\n".join(texture_errors)
        )

    new_text = applyTextureChanges(new_text, state.get("current_textures", []), new_texture_paths)

    if new_text != state["current_text"]:
        try:
            writeTextFile(state["current_path"],
                          new_text, state["current_encoding"])
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))
            return False, []
        state["current_text"] = new_text
        state["current_entries"] = findColors(new_text)
        state["current_textures"] = findTextures(new_text)

    pending_texture_paths = list(dict.fromkeys(pending_texture_paths))
    if pending_texture_paths:
        queued = state.setdefault("pending_texture_compiles", [])
        queued.extend(pending_texture_paths)
        state["pending_texture_compiles"] = list(dict.fromkeys(queued))

    state["dirty"] = False
    return True, pending_texture_paths


def discardCurrentTextureEdits(state: Dict[str, Any]):
    modified_map = state.get("modified_textures")
    if not isinstance(modified_map, dict):
        return
    for entry in state.get("current_textures", []):
        vtex_path = entry.get("vtex_path")
        if isinstance(vtex_path, str):
            modified_map.pop(vtex_path, None)


def discardPendingChanges(state: Dict[str, Any]):
    discardCurrentTextureEdits(state)
    state["dirty"] = False
    state["has_pending_changes"] = False
    state["save_btn"].configure(state="disabled")
    state["revert_btn"].configure(state="disabled")
    if state.get("current_path"):
        state["file_title_var"].set(os.path.relpath(state["current_path"], state["root_dir"]))


def maybePromptSave(state: Dict[str, Any]) -> bool:
    if not state["has_pending_changes"]:
        return True
    answer = messagebox.askyesnocancel(
        "Unsaved Changes",
        "There are unsaved/uncompiled changes.\n\nSave & Compile before continuing?"
    )
    if answer is None:
        return False
    if answer:
        return bool(saveCurrentFile(state))
    discardPendingChanges(state)
    return True


def loadFile(state: Dict[str, Any], path: str):
    try:
        text, enc = readTextFile(path)
    except Exception as exc:
        messagebox.showerror("File Read Error", str(exc))
        return
    state["current_path"] = path
    state["current_text"] = text
    state["current_encoding"] = enc
    state["current_entries"] = findColors(text)
    state["current_textures"] = findTextures(text)
    
    vtex_paths = [t["vtex_path"] for t in state["current_textures"]]
    if vtex_paths:
        state["status_var"].set(f"Loading {len(vtex_paths)} texture(s)...")
        state["root"].update_idletasks()
        extracted = extractTexturesBatch(vtex_paths)
        for t_entry in state["current_textures"]:
            success, msg, vtex_out, pngs = extracted.get(
                t_entry["vtex_path"], (False, "Texture was not extracted.", None, []))
            if success and pngs:
                t_entry["vtex_out"] = vtex_out
                t_entry["pngs"] = sorted(pngs)
            else:
                t_entry["error"] = msg
        for t_entry in state["current_textures"]:
            mod = state.get("modified_textures", {}).get(t_entry["vtex_path"])
            if not mod:
                manifest_entry = getTextureManifestEntry(t_entry["vtex_path"])
                if manifest_entry and manifest_entry.get("mode") != "auto":
                    mod = {
                        "h_shift": manifest_entry.get("h_shift", 0.0),
                        "s_scale": manifest_entry.get("s_scale", 1.0),
                        "v_scale": manifest_entry.get("v_scale", 1.0),
                        "recolor_mode": manifest_entry.get("mode", "hsv"),
                        "tint_rgb": tuple(manifest_entry["tint_rgb"]) if manifest_entry.get("tint_rgb") else None,
                    }
            if not mod:
                continue
            t_entry["modified"] = True
            t_entry["h_shift"] = mod.get("h_shift", 0.0)
            t_entry["s_scale"] = mod.get("s_scale", 1.0)
            t_entry["v_scale"] = mod.get("v_scale", 1.0)
            t_entry["recolor_mode"] = mod.get("recolor_mode", "hsv")
            t_entry["tint_rgb"] = mod.get("tint_rgb")
            
    state["dirty"] = False
    state["file_title_var"].set(os.path.relpath(path, state["root_dir"]))
    renderEntries(state)
    state["save_btn"].configure(
        state="normal" if state["has_pending_changes"] else "disabled")
    state["revert_btn"].configure(state="disabled")
    state["status_var"].set(
        f"Opened: {os.path.relpath(path, state['root_dir'])} — colors: {len(state['current_entries'])} textures: {len(state['current_textures'])}")


def revertCurrentFile(state: Dict[str, Any]):
    if state["current_path"]:
        discardPendingChanges(state)
        loadFile(state, state["current_path"])


def clearRightPanel(state: Dict[str, Any]):
    state["current_path"] = None
    state["current_entries"] = []
    state["current_textures"] = []
    state["file_title_var"].set("Select a file on the left")
    for child in state["scrollable_frame"].winfo_children():
        child.destroy()
    state["save_btn"].configure(state="disabled")
    state["revert_btn"].configure(state="disabled")


def renderEntries(state: Dict[str, Any]):
    for child in state["scrollable_frame"].winfo_children():
        child.destroy()
    state["entry_vars"].clear()
    state["entry_rgba_vars"].clear()
    state["entry_hex_vars"].clear()
    state["entry_swatch"].clear()
    state.setdefault("texture_images", {}).clear()

    if not state["current_entries"] and not state.get("current_textures"):
        ctk.CTkLabel(state["scrollable_frame"], text="No colors found in this file.",
                     text_color=FG_MUTED).pack(anchor="w", padx=12, pady=12)
        return

    textures_by_class: Dict[str, List[Dict[str, Any]]] = {}
    for t in state.get("current_textures", []):
        cls = t.get("className", "(root)")
        textures_by_class.setdefault(cls, []).append(t)
    rendered_texture_ids: set[int] = set()

    for entry in state["current_entries"]:
        cls = entry.get("className", "(root)")
        matching_textures = [t for t in textures_by_class.get(cls, [])
                             if id(t) not in rendered_texture_ids]
        for t in matching_textures:
            rendered_texture_ids.add(id(t))
        buildRow(state, entry, matching_textures)

    orphan_textures = [t for t in state.get("current_textures", [])
                       if id(t) not in rendered_texture_ids]
    if orphan_textures:
        for t in orphan_textures:
            buildOrphanTextureCard(state, t)


def buildRow(state: Dict[str, Any], entry: Dict[str, Any],
             textures: Optional[List[Dict[str, Any]]] = None):
    card = ctk.CTkFrame(state["scrollable_frame"],
                        fg_color="#212126", corner_radius=10)
    card.pack(fill="x", padx=4, pady=4)

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(10, 6))

    ctk.CTkLabel(header, text=colorEntryLabel(entry), text_color=FG_MUTED,
                 font=(FONT_FAMILY, 9, "bold")).pack(side="left")

    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="x", padx=12, pady=(0, 10))

    rgba = colorEntryRgba255(entry)
    r, g, b = rgba[0], rgba[1], rgba[2]
    hexcolor = f"#{r:02x}{g:02x}{b:02x}"

    swatch = ctk.CTkButton(
        body, text="", width=42, height=32, corner_radius=6,
        border_width=0, fg_color=hexcolor, hover_color=hexcolor,
        command=lambda en=entry: pickColor(state, en)
    )
    swatch.pack(side="left", padx=(0, 16))

    channel_count = len(entry["components"])
    vars_: List[tk.IntVar] = [tk.IntVar(value=rgba[i])
                              for i in range(channel_count)]
    state["entry_vars"][id(entry)] = vars_

    rgba_var = tk.StringVar(value=",".join(str(v.get()) for v in vars_))
    hex_var = tk.StringVar(value=hexcolor)

    state["entry_rgba_vars"][id(entry)] = rgba_var
    state["entry_hex_vars"][id(entry)] = hex_var

    def onRgbaEdit(event=None, e=entry):
        try:
            parts = [int(x.strip())
                     for x in state["entry_rgba_vars"][id(e)].get().split(",")]
            v_list = state["entry_vars"][id(e)]
            for i, v in enumerate(v_list):
                if i < len(parts):
                    v.set(max(0, min(255, parts[i])))
            cr, cg, cb = v_list[0].get(), v_list[1].get(), v_list[2].get()
            state["entry_hex_vars"][id(e)].set(f"#{cr:02x}{cg:02x}{cb:02x}")
            updateSwatch(state, e)
            markDirty(state)
        except Exception:
            pass

    def onHexEdit(event=None, e=entry):
        try:
            hx = state["entry_hex_vars"][id(e)].get().strip().lstrip("#")
            if len(hx) == 6:
                cr, cg, cb = int(hx[0:2], 16), int(
                    hx[2:4], 16), int(hx[4:6], 16)
                v_list = state["entry_vars"][id(e)]
                v_list[0].set(cr)
                v_list[1].set(cg)
                v_list[2].set(cb)
                state["entry_rgba_vars"][id(e)].set(
                    ",".join(str(v.get()) for v in v_list))
                updateSwatch(state, e)
                markDirty(state)
        except Exception:
            pass

    inputs_frame = ctk.CTkFrame(body, fg_color="transparent")
    inputs_frame.pack(side="left", fill="x", expand=True)

    label_txt = "RGBA:" if channel_count == 4 else "RGB:"
    ctk.CTkLabel(inputs_frame, text=label_txt, text_color=FG_MUTED, font=(
        FONT_FAMILY, 10, "bold")).pack(side="left", padx=(0, 6))

    rgba_entry = ctk.CTkEntry(
        inputs_frame, textvariable=rgba_var, width=120, height=32, corner_radius=6,
        fg_color="#27272a", border_width=0, text_color=FG
    )
    rgba_entry.pack(side="left", padx=(0, 16))
    rgba_entry.bind("<Return>", onRgbaEdit)
    rgba_entry.bind("<FocusOut>", onRgbaEdit)

    ctk.CTkLabel(inputs_frame, text="HEX:", text_color=FG_MUTED, font=(
        FONT_FAMILY, 10, "bold")).pack(side="left", padx=(0, 6))

    hex_entry = ctk.CTkEntry(
        inputs_frame, textvariable=hex_var, width=80, height=32, corner_radius=6,
        fg_color="#27272a", border_width=0, text_color=FG
    )
    hex_entry.pack(side="left")
    hex_entry.bind("<Return>", onHexEdit)
    hex_entry.bind("<FocusOut>", onHexEdit)

    state["entry_swatch"][id(entry)] = swatch
    updateSwatch(state, entry)

    if textures:
        for t_entry in textures:
            buildTextureInline(state, card, t_entry)


def lanczosResample():
    resampling = getattr(Image, "Resampling", None)
    if resampling is not None:
        return resampling.LANCZOS
    return getattr(Image, "LANCZOS")


def loadTkImage(png_path: str, size: Tuple[int, int] = (80, 80)) -> Optional[ImageTk.PhotoImage]:
    try:
        pil_img = Image.open(png_path).convert("RGBA")
        pil_img.thumbnail(size, lanczosResample())
        return ImageTk.PhotoImage(pil_img)
    except Exception as exc:
        print(f"[thumbnail] failed to load {png_path}: {exc!r}")
        return None


def loadPreviewBase(png_path: str, size: Tuple[int, int] = (64, 64)) -> Optional[Image.Image]:
    try:
        pil_img = Image.open(png_path).convert("RGBA")
        pil_img.thumbnail(size, lanczosResample())
        return pil_img
    except Exception:
        return None


def texturePngsMostlyGrayscale(png_paths: List[str]) -> bool:
    saw_image = False
    for png_path in png_paths:
        preview_base = loadPreviewBase(png_path, (64, 64))
        if preview_base is None:
            continue
        saw_image = True
        if not isMostlyGrayscale(preview_base):
            return False
    return saw_image


def previewTkImage(base_img: Image.Image, entry: Dict[str, Any]) -> ImageTk.PhotoImage:
    preview = previewTextureImage(
        base_img,
        entry.get("h_shift", 0.0),
        entry.get("s_scale", 1.0),
        entry.get("v_scale", 1.0),
        entry.get("recolor_mode", "hsv"),
        tuple(entry["tint_rgb"]) if entry.get("tint_rgb") else None,
    )
    return ImageTk.PhotoImage(preview)


def textureEditInfo(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "h_shift": entry.get("h_shift", 0.0),
        "s_scale": entry.get("s_scale", 1.0),
        "v_scale": entry.get("v_scale", 1.0),
        "recolor_mode": entry.get("recolor_mode", "hsv"),
        "tint_rgb": entry.get("tint_rgb"),
    }


def buildTextureInline(state: Dict[str, Any], parent_card: ctk.CTkFrame,
                       t_entry: Dict[str, Any]):
    vtex_path = t_entry["vtex_path"]
    pngs = t_entry.get("pngs")
    error = t_entry.get("error")

    sep = ctk.CTkFrame(parent_card, fg_color="#2a2a30", height=1, corner_radius=0)
    sep.pack(fill="x", padx=12, pady=(0, 6))

    tex_row = ctk.CTkFrame(parent_card, fg_color="transparent")
    tex_row.pack(fill="x", padx=12, pady=(0, 8))

    thumb_size = (64, 64)
    tk_img = None
    preview_base = None
    is_gray = False
    if pngs:
        preview_source = sorted(pngs)[0]
        preview_base = loadPreviewBase(preview_source, thumb_size)
        if preview_base is not None:
            is_gray = isMostlyGrayscale(preview_base)
        if t_entry.get("modified") and preview_base is not None:
            tk_img = previewTkImage(preview_base, t_entry)
        else:
            tk_img = loadTkImage(preview_source, thumb_size)

    if tk_img:
        thumb_btn = tk.Button(
            tex_row, image=tk_img,
            bd=0, highlightthickness=1, highlightbackground="#3f3f46",
            cursor="hand2", relief="flat", bg="#212126", activebackground="#212126"
        )
        setattr(thumb_btn, "image", tk_img)
        thumb_btn.pack(side="left", padx=(0, 12))
        state["texture_images"][id(t_entry)] = tk_img
    else:
        placeholder = ctk.CTkFrame(tex_row, fg_color="#2a2a30", width=64, height=64,
                                   corner_radius=6)
        placeholder.pack(side="left", padx=(0, 12))
        placeholder.pack_propagate(False)
        err_hint = "?" if not error else "!"
        ctk.CTkLabel(placeholder, text=err_hint, text_color=FG_MUTED,
                     font=(FONT_FAMILY, 18)).place(relx=0.5, rely=0.5, anchor="center")
        thumb_btn = placeholder

    name_col = ctk.CTkFrame(tex_row, fg_color="transparent")
    name_col.pack(side="left", fill="x", expand=True)

    def getLabel(e=t_entry):
        tag = "  ✏ edited" if e.get("modified") else ""
        return f"🖼  {e['vtex_path'].split('/')[-1]}{tag}"

    name_var = tk.StringVar(value=getLabel())
    name_lbl = ctk.CTkLabel(name_col, textvariable=name_var, text_color=FG_MUTED,
                             font=(FONT_FAMILY, 9, "bold"), anchor="w")
    name_lbl.pack(anchor="w")

    if error and not pngs:
        ctk.CTkLabel(name_col, text=f"⚠ {error}", text_color=DANGER,
                     font=(FONT_FAMILY, 8), wraplength=300, anchor="w").pack(anchor="w")
        return

    slider_panel = ctk.CTkFrame(parent_card, fg_color="#1a1a1f", corner_radius=8)

    def toggleSliders(e=t_entry, panel=slider_panel, var=name_var):
        if panel.winfo_ismapped():
            panel.pack_forget()
        else:
            panel.pack(fill="x", padx=16, pady=(0, 8))

    if tk_img:
        thumb_btn.configure(command=toggleSliders)
    name_lbl.bind("<Button-1>", lambda ev: toggleSliders())

    if is_gray:
        ctk.CTkLabel(
            name_col,
            text="Grayscale — hue has no effect. Use overlay / replace below.",
            text_color=FG_MUTED, font=(FONT_FAMILY, 8), wraplength=360, anchor="w",
        ).pack(anchor="w")

    def makeSlider(parent, label_text, from_, to_, init, callback):
        ctk.CTkLabel(parent, text=label_text, text_color=FG_MUTED,
                     font=(FONT_FAMILY, 9)).pack(anchor="w", padx=12, pady=(8, 0))
        sl = ctk.CTkSlider(parent, from_=from_, to=to_, command=callback)
        sl.set(init)
        sl.pack(fill="x", padx=12, pady=(0, 4))
        return sl

    def persistAndPreview(e=t_entry, lbl_var=name_var):
        state.setdefault("modified_textures", {})[e["vtex_path"]] = textureEditInfo(e)
        lbl_var.set(getLabel(e))
        markDirty(state)
        if preview_base is not None and isinstance(thumb_btn, tk.Button):
            new_tk_img = previewTkImage(preview_base, e)
            thumb_btn.configure(image=new_tk_img)
            setattr(thumb_btn, "image", new_tk_img)
            state["texture_images"][id(e)] = new_tk_img

    def onSlider(val=None, e=t_entry):
        e["modified"] = True
        e["recolor_mode"] = "hsv"
        e["tint_rgb"] = None
        e["h_shift"] = hue_sl.get()
        e["s_scale"] = sat_sl.get()
        e["v_scale"] = val_sl.get()
        persistAndPreview()
        refreshTintUi()

    def currentTintHex(e=t_entry) -> str:
        rgb = e.get("tint_rgb") or (255, 255, 255)
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def refreshTintUi(e=t_entry):
        mode = e.get("recolor_mode", "hsv")
        overlay_btn.configure(
            fg_color=ACCENT if mode == "overlay" else "#27272a",
            hover_color=ACCENT_HOVER if mode == "overlay" else "#3f3f46",
            text_color=ON_ACCENT if mode == "overlay" else FG,
        )
        replace_btn.configure(
            fg_color=ACCENT if mode == "replace" else "#27272a",
            hover_color=ACCENT_HOVER if mode == "replace" else "#3f3f46",
            text_color=ON_ACCENT if mode == "replace" else FG,
        )
        hx = currentTintHex(e)
        tint_swatch.configure(fg_color=hx, hover_color=hx)

    def setTintMode(mode: str, e=t_entry):
        e["recolor_mode"] = mode
        if not e.get("tint_rgb"):
            e["tint_rgb"] = (255, 255, 255)
        e["modified"] = True
        persistAndPreview()
        refreshTintUi()

    def pickTintColor(e=t_entry):
        initial = currentTintHex(e)
        result = askCustomColor(
            state["root"], initialHex=initial, title="Texture tint color")
        if not result:
            return
        e["tint_rgb"] = result
        if e.get("recolor_mode", "hsv") == "hsv":
            e["recolor_mode"] = "overlay"
        e["modified"] = True
        persistAndPreview()
        refreshTintUi()

    tint_row = ctk.CTkFrame(slider_panel, fg_color="transparent")
    tint_row.pack(fill="x", padx=12, pady=(10, 4))
    ctk.CTkLabel(tint_row, text="Colorize", text_color=FG_MUTED,
                 font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 8))
    overlay_btn = ctk.CTkButton(
        tint_row, text="Overlay", width=72, height=24, corner_radius=6,
        font=(FONT_FAMILY, 9), command=lambda: setTintMode("overlay"),
    )
    overlay_btn.pack(side="left", padx=(0, 4))
    replace_btn = ctk.CTkButton(
        tint_row, text="Replace", width=72, height=24, corner_radius=6,
        font=(FONT_FAMILY, 9), command=lambda: setTintMode("replace"),
    )
    replace_btn.pack(side="left", padx=(0, 8))
    tint_swatch = ctk.CTkButton(
        tint_row, text="", width=32, height=24, corner_radius=6, border_width=0,
        command=pickTintColor,
    )
    tint_swatch.pack(side="left")
    ctk.CTkButton(
        tint_row, text="Pick…", width=56, height=24, corner_radius=6,
        fg_color="#27272a", hover_color="#3f3f46", text_color=FG,
        font=(FONT_FAMILY, 9), command=pickTintColor,
    ).pack(side="left", padx=(6, 0))

    hue_sl = makeSlider(slider_panel, "Hue Shift   (−1 … +1)", -1.0, 1.0,
                        t_entry.get("h_shift", 0.0), onSlider)
    sat_sl = makeSlider(slider_panel, "Saturation  (0 … 2×)", 0.0, 2.0,
                        t_entry.get("s_scale", 1.0), onSlider)
    val_sl = makeSlider(slider_panel, "Brightness  (0 … 2×)", 0.0, 2.0,
                        t_entry.get("v_scale", 1.0), onSlider)
    ctk.CTkFrame(slider_panel, fg_color="transparent", height=6).pack()
    refreshTintUi()


def buildOrphanTextureCard(state: Dict[str, Any], t_entry: Dict[str, Any]):
    card = ctk.CTkFrame(state["scrollable_frame"], fg_color="#1e1e24", corner_radius=10)
    card.pack(fill="x", padx=4, pady=4)
    ctk.CTkLabel(card, text="TEXTURE (no colour match)", text_color=FG_MUTED,
                 font=(FONT_FAMILY, 9, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
    buildTextureInline(state, card, t_entry)


def updateSwatch(state: Dict[str, Any], entry: Dict[str, Any]):
    vars_ = state["entry_vars"].get(id(entry))
    if not vars_:
        return
    try:
        r = max(0, min(255, vars_[0].get()))
        g = max(0, min(255, vars_[1].get()))
        b = max(0, min(255, vars_[2].get()))
    except tk.TclError:
        return
    hexcolor = f"#{r:02x}{g:02x}{b:02x}"
    swatch = state["entry_swatch"].get(id(entry))
    if swatch:
        swatch.configure(fg_color=hexcolor, hover_color=hexcolor)


def pickColor(state: Dict[str, Any], entry: Dict[str, Any]):
    vars_ = state["entry_vars"].get(id(entry))
    if not vars_:
        return
    try:
        r = max(0, min(255, vars_[0].get()))
        g = max(0, min(255, vars_[1].get()))
        b = max(0, min(255, vars_[2].get()))
    except tk.TclError:
        r = g = b = 255
    initial_hex = f"#{r:02x}{g:02x}{b:02x}"
    result = askCustomColor(
        state["root"], initialHex=initial_hex, title=f"Choose Color — {entry['key']}")
    if result:
        nr, ng, nb = result
        vars_[0].set(nr)
        vars_[1].set(ng)
        vars_[2].set(nb)

        if id(entry) in state["entry_rgba_vars"]:
            state["entry_rgba_vars"][id(entry)].set(
                ",".join(str(v.get()) for v in vars_))
        if id(entry) in state["entry_hex_vars"]:
            state["entry_hex_vars"][id(entry)].set(
                f"#{nr:02x}{ng:02x}{nb:02x}")

        updateSwatch(state, entry)
        markDirty(state)


def markDirty(state: Dict[str, Any]):
    state["dirty"] = True
    state["has_pending_changes"] = True
    state["save_btn"].configure(state="normal")
    state["revert_btn"].configure(state="normal")
    title = os.path.relpath(
        state["current_path"], state["root_dir"]) if state["current_path"] else ""
    state["file_title_var"].set(f"{title}   •   unsaved changes")


def buildVpkFromCompiled() -> Optional[Path]:
    try:
        items = [p for p in OUTPUT_DIR.iterdir()]
    except Exception:
        items = []
    if not items:
        return None
    try:
        return compileToVpk(items, SCRIPT_DIR, delete_sources=False)
    except Exception as exc:
        messagebox.showwarning(
            "VPK Error", f"Failed to create the VPK file:\n\n{exc}")
        return None


def compileAllScannedFiles(state: Dict[str, Any]) -> Tuple[int, int, List[str]]:
    if not state["last_scan_results"]:
        rescan(state)

    total_files = len(state["last_scan_results"])
    compile_errors: List[str] = []

    if total_files == 0:
        return 0, 0, compile_errors

    state["progress_bar"].set(0.1)
    state["progress_bar"].pack(side="right", padx=(0, 16))
    state["status_var"].set(f"Compiling {total_files} files...")
    state["root"].update()

    file_paths = [abs_path for (_rel, abs_path, _c) in state["last_scan_results"]]
    _total, compiled_files, errors_dict = compileBatch(file_paths, state["root_dir"])

    state["progress_bar"].set(1.0)
    state["root"].update()
    state["progress_bar"].pack_forget()

    for rel_path, err_msg in errors_dict.items():
        compile_errors.append(f"{rel_path}:\n{err_msg}\n{'-'*60}")

    if compile_errors:
        log_path = OUTPUT_DIR / "compile_errors.log"
        try:
            log_path.write_text("\n".join(compile_errors), encoding="utf-8")
        except Exception:
            pass

    return total_files, compiled_files, compile_errors


def saveCurrentFile(state: Dict[str, Any]) -> bool:
    texture_compile_errors: List[str] = []

    if state["current_path"]:
        ok, pending_texture_paths = applyCurrentEditsToDisk(state)
        if not ok:
            return False

        all_pending_texture_paths = list(dict.fromkeys(state.get("pending_texture_compiles", [])))
        if pending_texture_paths:
            all_pending_texture_paths = list(dict.fromkeys(all_pending_texture_paths + pending_texture_paths))

        if all_pending_texture_paths:
            state["progress_bar"].set(0.05)
            state["progress_bar"].pack(side="right", padx=(0, 16))
            state["status_var"].set(f"Compiling {len(all_pending_texture_paths)} edited texture(s)...")
            state["root"].update()
            texture_results, texture_errors = compileTextureBatch(all_pending_texture_paths, OUTPUT_DIR)
            for raw_vtex_path in all_pending_texture_paths:
                if raw_vtex_path not in texture_results:
                    err = texture_errors.get(raw_vtex_path, "unknown texture compile error")
                    texture_compile_errors.append(f"{raw_vtex_path}:\n{err}\n{'-'*60}")
            state["pending_texture_compiles"] = []

        renderEntries(state)
        state["revert_btn"].configure(state="disabled")
        rel = os.path.relpath(state["current_path"], state["root_dir"])
        state["file_title_var"].set(rel)
        refreshTreeLabel(state, state["current_path"])

    total_files, compiled_files, compile_errors = compileAllScannedFiles(state)
    compile_errors = texture_compile_errors + compile_errors
    if compile_errors:
        log_path = OUTPUT_DIR / "compile_errors.log"
        try:
            log_path.write_text("\n".join(compile_errors), encoding="utf-8")
        except Exception:
            pass

    vpk_path = buildVpkFromCompiled()
    reopen_path = state.get("current_path")

    state["has_pending_changes"] = False
    state["save_btn"].configure(state="disabled")

    if reopen_path and os.path.exists(reopen_path):
        updateTreeSelection(state, reopen_path)
        loadFile(state, reopen_path)

    status_msg = f"Compiled {compiled_files}/{total_files} file(s)."
    if vpk_path:
        status_msg += f" VPK: {vpk_path.name}"
    state["status_var"].set(status_msg)

    msg = f"Compiled {compiled_files} of {total_files} file(s)."
    if vpk_path:
        msg += f"\n\nVPK created: {vpk_path}"
    if compile_errors:
        msg += (
            f"\n\n{len(compile_errors)} file(s) failed to compile — details saved to:\n"
            f"{OUTPUT_DIR / 'compile_errors.log'}"
        )
    messagebox.showinfo("Save & Compile", msg)
    return True


def bulkRecolor(state: Dict[str, Any], color_picker_fn) -> Tuple[int, int, List[str], int]:
    changed_files = 0
    compile_errors: List[str] = []
    skipped_grayscale_textures = 0

    total_files = len(state["last_scan_results"])
    if total_files == 0:
        return 0, 0, [], 0

    state["progress_bar"].set(0)
    state["progress_bar"].pack(side="right", padx=(0, 16))

    raw_root = RAW_DIR

    file_jobs: List[Dict[str, Any]] = []
    all_source_vtex_paths: set[str] = set()

    for idx, (rel_path, abs_path, _count) in enumerate(state["last_scan_results"], 1):
        state["status_var"].set(
            f"Recoloring [{idx}/{total_files}]: {rel_path}...")
        state["progress_bar"].set(idx / (total_files * 4))
        state["root"].update()

        try:
            text, enc = readTextFile(abs_path)
        except Exception:
            continue

        entries = findColors(text)
        textures = findTextures(text)
        if not entries and not textures:
            continue

        target_rgb_cache = None

        new_values_map: Dict[int, List[float]] = {}
        for entry in entries:
            current = colorEntryRgba255(entry)
            rgb = current[:3]

            if isGrayscale(rgb):
                continue

            if not target_rgb_cache:
                target_rgb_cache = color_picker_fn()
            target_rgb = target_rgb_cache

            r, g, b = recolorPreservingSv(rgb, target_rgb)
            has_alpha = len(entry["components"]) == 4
            a = current[3] if has_alpha else None

            if entry["kind"] == "byte":
                vals = [float(r), float(g), float(b)]
                if a is not None:
                    vals.append(float(a))
            else:
                vals = [r / 255.0, g / 255.0, b / 255.0]
                if a is not None:
                    vals.append(a / 255.0)
            new_values_map[id(entry)] = vals

        new_text = applyColorChanges(text, entries, new_values_map) if entries else text

        texture_specs: List[Dict[str, Any]] = []
        for entry in textures:
            vtex_path = entry["vtex_path"]
            source_vtex_path = sourceTexturePath(vtex_path)
            mod_info = state.get("modified_textures", {}).get(vtex_path)

            if not target_rgb_cache:
                target_rgb_cache = color_picker_fn()

            if mod_info:
                h_shift = mod_info["h_shift"]
                s_scale = mod_info["s_scale"]
                v_scale = mod_info["v_scale"]
                recolor_mode = mod_info.get("recolor_mode", "hsv")
                tint_rgb = mod_info.get("tint_rgb")
            else:
                h_shift = target_rgb_cache[0] * 0.01
                s_scale = target_rgb_cache[1] * 0.01
                v_scale = target_rgb_cache[2] * 0.01
                recolor_mode = "hsv"
                tint_rgb = None
            new_vtex_name = generateUniqueName(
                source_vtex_path, h_shift, s_scale, v_scale, recolor_mode, tint_rgb)

            texture_specs.append({
                "entry": entry,
                "vtex_path": vtex_path,
                "source_vtex_path": source_vtex_path,
                "mod_info": mod_info,
                "h_shift": h_shift,
                "s_scale": s_scale,
                "v_scale": v_scale,
                "recolor_mode": recolor_mode,
                "tint_rgb": tint_rgb,
                "target_rgb": target_rgb_cache,
                "new_vtex_name": new_vtex_name,
                "cache_key": (vtex_path, new_vtex_name),
            })
            all_source_vtex_paths.add(source_vtex_path)

        file_jobs.append({
            "rel_path": rel_path,
            "enc": enc,
            "text": text,
            "new_text": new_text,
            "textures": textures,
            "texture_specs": texture_specs,
        })

    pristine: Dict[str, Tuple[bool, str, Optional[str], List[str]]] = {}
    if all_source_vtex_paths:
        state["status_var"].set(
            f"Extracting {len(all_source_vtex_paths)} textures...")
        state["progress_bar"].set(1 / 4)
        state["root"].update()
        pristine = extractTexturesBatch(list(all_source_vtex_paths))

    available_pristine = dict(pristine)
    texture_edit_cache: Dict[Tuple[str, str], str] = {}
    auto_skipped_textures: set[str] = set()
    all_new_vtex_paths: List[str] = []

    for job in file_jobs:
        rel_path = job["rel_path"]
        pending_textures: List[Tuple[Dict[str, Any], str, str]] = []

        for spec in job["texture_specs"]:
            entry = spec["entry"]
            vtex_path = spec["vtex_path"]
            source_vtex_path = spec["source_vtex_path"]
            cache_key = spec["cache_key"]
            new_vtex_name = spec["new_vtex_name"]

            cached_disk_path = texture_edit_cache.get(cache_key)
            if cached_disk_path is not None:
                base_dir = source_vtex_path.rsplit("/", 1)[0]
                resource_str = f"{base_dir}/{Path(cached_disk_path).name}"
                pending_textures.append((entry, cached_disk_path, resource_str))
                continue

            if not spec["mod_info"] and source_vtex_path in auto_skipped_textures:
                continue

            pristine_entry = available_pristine.pop(source_vtex_path, None)
            if pristine_entry is not None and pristine_entry[0]:
                vtex_out, pngs = pristine_entry[2], pristine_entry[3]
            else:
                success, msg, vtex_out, pngs = extractTexture(source_vtex_path, force=True)
                if not success:
                    compile_errors.append(f"{rel_path}: failed to extract {vtex_path}\n{msg}\n")
                    continue

            if not vtex_out:
                compile_errors.append(f"{rel_path}: texture extraction returned no .vtex for {vtex_path}\n")
                continue

            pngs = [png for png in pngs if os.path.exists(png)]
            if not pngs:
                success, msg, vtex_out, pngs = extractTexture(source_vtex_path, force=True)
                if not success or not vtex_out:
                    compile_errors.append(f"{rel_path}: failed to refresh {vtex_path}\n{msg}\n")
                    continue
                pngs = [png for png in pngs if os.path.exists(png)]
                if not pngs:
                    compile_errors.append(f"{rel_path}: refreshed texture has no PNGs for {vtex_path}\n")
                    continue

            if not spec["mod_info"] and texturePngsMostlyGrayscale(pngs):
                auto_skipped_textures.add(source_vtex_path)
                skipped_grayscale_textures += 1
                if vtex_out:
                    available_pristine[source_vtex_path] = (True, "", vtex_out, pngs)
                continue

            if spec["mod_info"]:
                mode = spec.get("recolor_mode", "hsv")
                tint_rgb = spec.get("tint_rgb")
                if mode in ("overlay", "replace") and tint_rgb:
                    for png in pngs:
                        tintImage(png, png, tuple(tint_rgb), mode)
                else:
                    for png in pngs:
                        adjustImage(png, png, spec["h_shift"], spec["s_scale"], spec["v_scale"])
            else:
                for png in pngs:
                    autoRecolorImage(png, png, spec["target_rgb"])

            old_vtex_path = Path(vtex_out)
            new_vtex_path = old_vtex_path.with_name(new_vtex_name.split("/")[-1])
            renamed_pngs = pngs
            if old_vtex_path.exists() and old_vtex_path != new_vtex_path:
                old_vtex_path.rename(new_vtex_path)
                renamed_pngs = renameExtractedTextureAssets(
                    str(old_vtex_path), str(new_vtex_path), pngs
                )

            raw_vtex_path, raw_pngs = persistRawTextureFiles(
                new_vtex_name, str(new_vtex_path), renamed_pngs
            )
            if spec["mod_info"]:
                recordTextureManifest(
                    new_vtex_name,
                    source_vtex_path,
                    spec.get("recolor_mode", "hsv"),
                    float(spec.get("h_shift", 0.0)),
                    float(spec.get("s_scale", 1.0)),
                    float(spec.get("v_scale", 1.0)),
                    tuple(spec.get("tint_rgb")) if spec.get("tint_rgb") else None,
                    None,
                )
            else:
                recordTextureManifest(
                    new_vtex_name,
                    source_vtex_path,
                    "auto",
                    0.0,
                    1.0,
                    1.0,
                    None,
                    tuple(spec["target_rgb"]),
                )

            base_dir = source_vtex_path.rsplit("/", 1)[0]
            resource_str = f"{base_dir}/{Path(raw_vtex_path).name}"
            texture_edit_cache[cache_key] = str(raw_vtex_path)
            pending_textures.append((entry, str(raw_vtex_path), resource_str))
            all_new_vtex_paths.append(str(raw_vtex_path))

        job["pending_textures"] = pending_textures

    texture_results: Dict[str, str] = {}
    texture_errors: Dict[str, str] = {}
    if all_new_vtex_paths:
        state["status_var"].set(
            f"Compiling {len(all_new_vtex_paths)} textures...")
        state["progress_bar"].set(2 / 4)
        state["root"].update()
        texture_results, texture_errors = compileTextureBatch(all_new_vtex_paths, OUTPUT_DIR)

    files_to_compile: List[str] = []
    for job in file_jobs:
        rel_path = job["rel_path"]
        new_texture_paths: Dict[int, str] = {}
        for entry, vtex_disk_path, resource_str in job["pending_textures"]:
            if vtex_disk_path in texture_results:
                new_texture_paths[id(entry)] = resource_str
            else:
                err = texture_errors.get(vtex_disk_path, "unknown texture compile error")
                compile_errors.append(f"{rel_path}: failed to compile texture\n{err}\n")

        new_text = job["new_text"]
        if new_texture_paths:
            updated_textures = findTextures(new_text)
            remapped_texture_paths: Dict[int, str] = {}

            if len(updated_textures) != len(job["textures"]):
                compile_errors.append(
                    f"{rel_path}: texture entries changed unexpectedly after color rewrite; skipped texture path updates\n{'-'*60}"
                )
            else:
                for original_entry, updated_entry in zip(job["textures"], updated_textures):
                    new_path = new_texture_paths.get(id(original_entry))
                    if new_path:
                        remapped_texture_paths[id(updated_entry)] = new_path

                if remapped_texture_paths:
                    new_text = applyTextureChanges(new_text, updated_textures, remapped_texture_paths)

        if new_text == job["text"]:
            continue

        raw_dest = raw_root / rel_path
        try:
            raw_dest.parent.mkdir(parents=True, exist_ok=True)
            writeTextFile(str(raw_dest), new_text, job["enc"])
            changed_files += 1
            files_to_compile.append(str(raw_dest))
        except Exception as exc:
            compile_errors.append(f"{rel_path}: (save error) {exc}\n{'-'*60}")

    compiled_files = 0
    if files_to_compile:
        state["status_var"].set(
            f"Compiling {len(files_to_compile)} changed files...")
        state["progress_bar"].set(3 / 4)
        state["root"].update()

        _total, compiled_files, errors_dict = compileBatch(
            files_to_compile, str(raw_root)
        )
        for rel_path, err_msg in errors_dict.items():
            compile_errors.append(f"{rel_path}:\n{err_msg}\n{'-'*60}")

    state["progress_bar"].set(1.0)
    state["root"].update()
    state["progress_bar"].pack_forget()

    if compile_errors:
        log_path = OUTPUT_DIR / "compile_errors.log"
        try:
            log_path.write_text("\n".join(compile_errors), encoding="utf-8")
        except Exception:
            pass

    return changed_files, compiled_files, compile_errors, skipped_grayscale_textures


def afterBulkRecolor(state: Dict[str, Any]):
    state["has_pending_changes"] = False
    reopen_path = state["current_path"]
    rescan(state)
    if reopen_path and os.path.exists(reopen_path):
        updateTreeSelection(state, reopen_path)
        loadFile(state, reopen_path)
    else:
        clearRightPanel(state)


def recolorAllFilesSingleColor(state: Dict[str, Any]):
    if not state["last_scan_results"]:
        messagebox.showinfo(
            "No Files", "No .vpcf files with colors were found. Rescan the folder first.")
        return

    result = askCustomColor(
        state["root"], initialHex="#ffffff", title="Choose the replacement color")
    if not result:
        return
    r, g, b = result

    file_count = len(state["last_scan_results"])
    if not messagebox.askyesno(
        "Confirm Bulk Recolor",
        f"This will recolor ALL colors in {file_count} file(s) towards a single hue "
        f"(RGB {r}, {g}, {b}).\n\n"
        "Black, white, and gray color values will be ignored.\n"
        "White/gray/black textures will also be ignored by bulk recolor and can only be colored manually.\n"
        "Colored textures get a hue shift.\n"
        "Each color's original saturation/brightness will be preserved (only the hue changes).\n"
        "Alpha values will be preserved. Folders structure will mirror into 'compiled'.\n\n"
        "Continue?"
    ):
        return

    changed, compiled, compile_errors, skipped_gray = bulkRecolor(
        state, lambda rr=r, gg=g, bb=b: (rr, gg, bb))
    afterBulkRecolor(state)

    vpk_path = buildVpkFromCompiled()

    msg = f"Recolored {changed} file(s). Compiled {compiled} file(s)."
    if skipped_gray:
        msg += f"\n\nSkipped {skipped_gray} white/gray/black texture(s)."
    if vpk_path:
        msg += f"\n\nVPK created: {vpk_path}"
    if compile_errors:
        msg += (
            f"\n\n{len(compile_errors)} file(s) failed to compile — details saved to:\n"
            f"{OUTPUT_DIR / 'compile_errors.log'}"
        )
    messagebox.showinfo("Done", msg)


def recolorAllFilesTwoColors(state: Dict[str, Any]):
    if not state["last_scan_results"]:
        messagebox.showinfo(
            "No Files", "No .vpcf files with colors were found. Rescan the folder first.")
        return

    color_a = askCustomColor(
        state["root"], initialHex="#39ff88", title="Choose the first color")
    if not color_a:
        return
    color_b = askCustomColor(
        state["root"], initialHex="#39c5ff", title="Choose the second color")
    if not color_b:
        return

    file_count = len(state["last_scan_results"])
    if not messagebox.askyesno(
        "Confirm Bulk Recolor",
        f"This will randomly recolor colors in {file_count} file(s) towards EITHER hue:\n  • RGB {color_a}\n  • RGB {color_b}\n\n"
        "Black, white, and gray color values will be ignored.\n"
        "White/gray/black textures will also be ignored by bulk recolor and can only be colored manually.\n"
        "Colored textures get a hue shift.\n"
        "Each color's original saturation/brightness will be preserved (only the hue changes).\n"
        "Alpha values will be preserved. Folders structure will mirror into 'compiled'.\n\n"
        "Continue?"
    ):
        return

    changed, compiled, compile_errors, skipped_gray = bulkRecolor(
        state, lambda a=color_a, b=color_b: random.choice([a, b]))
    afterBulkRecolor(state)

    vpk_path = buildVpkFromCompiled()

    msg = f"Recolored {changed} file(s). Compiled {compiled} file(s)."
    if skipped_gray:
        msg += f"\n\nSkipped {skipped_gray} white/gray/black texture(s)."
    if vpk_path:
        msg += f"\n\nVPK created: {vpk_path}"
    if compile_errors:
        msg += (
            f"\n\n{len(compile_errors)} file(s) failed to compile — details saved to:\n"
            f"{OUTPUT_DIR / 'compile_errors.log'}"
        )
    messagebox.showinfo("Done", msg)


def onClose(state: Dict[str, Any]):
    if maybePromptSave(state):
        state["root"].destroy()


def patchScrollableFrameMousewheel():
    global _scrollable_frame_patched

    original_check = getattr(ctk.CTkScrollableFrame, "_check_if_valid_scroll", None)
    if not callable(original_check):
        return
    if _scrollable_frame_patched:
        return

    def safe_check(self, widget):
        if isinstance(widget, str):
            return False
        try:
            return original_check(self, widget)
        except AttributeError:
            return False

    ctk.CTkScrollableFrame._check_if_valid_scroll = safe_check
    _scrollable_frame_patched = True


def createVpcfColorEditorApp(root: ctk.CTk, start_dir: str) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "root": root,
        "root_dir": start_dir,
        "current_path": None,
        "current_text": "",
        "current_encoding": "utf-8",
        "current_entries": [],
        "current_textures": [],
        "texture_images": {},
        "texture_widgets": {},
        "modified_textures": {},
        "pending_texture_compiles": [],
        "dirty": False,
        "has_pending_changes": False,
        "last_scan_results": [],
        "entry_vars": {},
        "entry_rgba_vars": {},
        "entry_hex_vars": {},
        "entry_swatch": {},
        "file_buttons": {},
        "tree_item_paths": {},
        "tree_item_for_path": {},
        "compiler_ready": initializeCompiler()
    }
    downloadCli()
    resetSessionArtifacts()
    patchScrollableFrameMousewheel()

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    setupDarkStyle(state["root"])

    buildUi(state)
    state["root"].protocol("WM_DELETE_WINDOW", lambda: onClose(state))
    rescan(state)

    if not state["compiler_ready"] and compiler.COMPILER_INIT_ERROR:
        messagebox.showwarning(
            "Compiler Setup Issue",
            "Automatic compilation to .vpcf_c will not work:\n\n"
            f"{compiler.COMPILER_INIT_ERROR}\n\n"
            "Colors can still be edited and saved — .vpcf files "
            "will save correctly, they just won't compile automatically."
        )

    return state