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

    bottom = ctk.CTkFrame(right, fg_color="transparent")
    bottom.pack(side="bottom", fill="x", padx=16, pady=12)

    state["save_btn"] = ctk.CTkButton(
        bottom, text="Save & Compile", height=34,
        fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT, font=(
            FONT_FAMILY, 10, "bold"),
        corner_radius=8, command=lambda: saveCurrentFile(state), state="disabled"
    )
    state["save_btn"].pack(side="left")

    state["revert_btn"] = ctk.CTkButton(
        bottom, text="Discard Changes", height=34,
        fg_color="#27272a", hover_color="#3a2020", text_color=DANGER, font=(FONT_FAMILY, 10, "bold"),
        corner_radius=8, command=lambda: revertCurrentFile(state), state="disabled"
    )
    state["revert_btn"].pack(side="left", padx=8)

    # status
    status = ctk.CTkFrame(root, fg_color="#18181b", height=32, corner_radius=0)
    status.pack(side="bottom", fill="x")

    status_text = "Ready" if state["compiler_ready"] else "Ready (Warning: Compiler not found!)"
    state["status_var"] = tk.StringVar(value=status_text)
    ctk.CTkLabel(status, textvariable=state["status_var"], text_color=FG_MUTED, font=(
        FONT_FAMILY, 9)).pack(side="left", padx=16)

    state["progress_bar"] = ctk.CTkProgressBar(
        status, orientation="horizontal", width=200, height=8, corner_radius=4, progress_color=ACCENT)
    state["progress_bar"].set(0)


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
    state["status_var"].set(f"Found {len(results)} file(s) with colors")
    clearRightPanel(state)


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

    if not applyCurrentEditsToDisk(state):
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



def applyCurrentEditsToDisk(state: Dict[str, Any]) -> bool:
    if not state["current_path"] or not state["dirty"]:
        return True

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
            return False
        if entry["kind"] == "byte":
            vals = [float(v) for v in raw_255]
        else:
            vals = [v / 255.0 for v in raw_255]
        new_values_map[id(entry)] = vals

    new_text = applyColorChanges(
        state["current_text"], state["current_entries"], new_values_map)

    if new_text != state["current_text"]:
        try:
            writeTextFile(state["current_path"],
                          new_text, state["current_encoding"])
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))
            return False
        state["current_text"] = new_text
        state["current_entries"] = findColors(new_text)

    state["dirty"] = False
    return True


def maybePromptSave(state: Dict[str, Any]) -> bool:
    if not applyCurrentEditsToDisk(state):
        return False
    if not state["has_pending_changes"]:
        return True
    answer = messagebox.askyesnocancel(
        "Unsaved Changes",
        "There are unsaved/uncompiled changes.\n\nSave & Compile before continuing?"
    )
    if answer is None:
        return False
    if answer:
        saveCurrentFile(state)
    else:
        state["has_pending_changes"] = False
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
    state["dirty"] = False
    state["file_title_var"].set(os.path.relpath(path, state["root_dir"]))
    renderEntries(state)
    state["save_btn"].configure(
        state="normal" if state["has_pending_changes"] else "disabled")
    state["revert_btn"].configure(state="disabled")
    state["status_var"].set(
        f"Opened: {os.path.relpath(path, state['root_dir'])} — colors: {len(state['current_entries'])}")


def revertCurrentFile(state: Dict[str, Any]):
    if state["current_path"]:
        loadFile(state, state["current_path"])


def clearRightPanel(state: Dict[str, Any]):
    state["current_path"] = None
    state["current_entries"] = []
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

    if not state["current_entries"]:
        ctk.CTkLabel(state["scrollable_frame"], text="No colors found in this file.",
                     text_color=FG_MUTED).pack(anchor="w", padx=12, pady=12)
        return

    for entry in state["current_entries"]:
        buildRow(state, entry)


def buildRow(state: Dict[str, Any], entry: Dict[str, Any]):
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
    state["status_var"].set(f"Compiling {total_files} file(s) in batch...")
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


def saveCurrentFile(state: Dict[str, Any]):
    if state["current_path"]:
        if not applyCurrentEditsToDisk(state):
            return
        renderEntries(state)
        state["revert_btn"].configure(state="disabled")
        rel = os.path.relpath(state["current_path"], state["root_dir"])
        state["file_title_var"].set(rel)
        refreshTreeLabel(state, state["current_path"])

    total_files, compiled_files, compile_errors = compileAllScannedFiles(state)

    vpk_path = buildVpkFromCompiled()

    state["has_pending_changes"] = False
    state["save_btn"].configure(state="disabled")

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


def bulkRecolor(state: Dict[str, Any], color_picker_fn) -> Tuple[int, int, int]:
    changed_files = 0
    compile_errors: List[str] = []

    total_files = len(state["last_scan_results"])
    if total_files == 0:
        return 0, 0, 0

    state["progress_bar"].set(0)
    state["progress_bar"].pack(side="right", padx=(0, 16))

    raw_root = RAW_DIR
    files_to_compile: List[str] = []

    for idx, (rel_path, abs_path, _count) in enumerate(state["last_scan_results"], 1):
        state["status_var"].set(
            f"Recoloring [{idx}/{total_files}]: {rel_path}...")
        state["progress_bar"].set(idx / (total_files * 2))
        state["root"].update()

        try:
            text, enc = readTextFile(abs_path)
        except Exception:
            continue

        entries = findColors(text)
        if not entries:
            continue

        new_values_map: Dict[int, List[float]] = {}
        for entry in entries:
            current = colorEntryRgba255(entry)
            rgb = current[:3]

            if isGrayscale(rgb):
                continue

            target_rgb = color_picker_fn()
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

        if not new_values_map:
            continue

        new_text = applyColorChanges(text, entries, new_values_map)
        if new_text == text:
            continue

        raw_dest = raw_root / rel_path
        try:
            raw_dest.parent.mkdir(parents=True, exist_ok=True)
            writeTextFile(str(raw_dest), new_text, enc)
            changed_files += 1
            files_to_compile.append(str(raw_dest))
        except Exception as exc:
            compile_errors.append(f"{rel_path}: (save error) {exc}\n{'-'*60}")

    compiled_files = 0
    if files_to_compile:
        state["status_var"].set(
            f"Compiling {len(files_to_compile)} changed file(s) in batch...")
        state["progress_bar"].set(0.6)
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

    return changed_files, compiled_files, len(compile_errors)


def afterBulkRecolor(state: Dict[str, Any]):
    state["has_pending_changes"] = False
    reopen_path = state["current_path"]
    rescan(state)
    if reopen_path and os.path.exists(reopen_path):
        updateTreeSelection(state, reopen_path)
        loadFile(state, reopen_path)
    else:
        clearRightPanel(state)


def cleanupRaw():
    import shutil
    try:
        if RAW_DIR.exists():
            shutil.rmtree(RAW_DIR)
            RAW_DIR.mkdir(exist_ok=True)
    except Exception:
        pass


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
        "Black, white, and gray tones will be ignored.\n"
        "Each color's original saturation/brightness will be preserved (only the hue changes).\n"
        "Alpha values will be preserved. Folders structure will mirror into 'compiled'.\n\n"
        "Continue?"
    ):
        return

    changed, compiled, failed = bulkRecolor(
        state, lambda rr=r, gg=g, bb=b: (rr, gg, bb))
    afterBulkRecolor(state)

    vpk_path = buildVpkFromCompiled()
    cleanupRaw()

    msg = f"Recolored {changed} file(s). Compiled {compiled} file(s)."
    if vpk_path:
        msg += f"\n\nVPK created: {vpk_path}"
    if failed:
        msg += f"\n\n{failed} file(s) failed to compile — details saved to:\n{OUTPUT_DIR / 'compile_errors.log'}"
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
        "Black, white, and gray tones will be ignored.\n"
        "Each color's original saturation/brightness will be preserved (only the hue changes).\n"
        "Alpha values will be preserved. Folders structure will mirror into 'compiled'.\n\n"
        "Continue?"
    ):
        return

    changed, compiled, failed = bulkRecolor(
        state, lambda a=color_a, b=color_b: random.choice([a, b]))
    afterBulkRecolor(state)

    vpk_path = buildVpkFromCompiled()
    cleanupRaw()

    msg = f"Recolored {changed} file(s). Compiled {compiled} file(s)."
    if vpk_path:
        msg += f"\n\nVPK created: {vpk_path}"
    if failed:
        msg += f"\n\n{failed} file(s) failed to compile — details saved to:\n{OUTPUT_DIR / 'compile_errors.log'}"
    messagebox.showinfo("Done", msg)


def onClose(state: Dict[str, Any]):
    if maybePromptSave(state):
        state["root"].destroy()


def createVpcfColorEditorApp(root: ctk.CTk, start_dir: str) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "root": root,
        "root_dir": start_dir,
        "current_path": None,
        "current_text": "",
        "current_encoding": "utf-8",
        "current_entries": [],
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

