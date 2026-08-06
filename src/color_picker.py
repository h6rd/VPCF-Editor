import colorsys
import math
import os
import sys
import tkinter as tk
from typing import Any, Dict, Optional, Tuple

import customtkinter as ctk

from src.theme import (
    BG_PANEL, BORDER, ACCENT, ACCENT_HOVER, ON_ACCENT, BG, BG_ELEV, BG_ELEV_HOVER,
    FG, FG_MUTED, FONT_FAMILY, DANGER, SUCCESS,
)
from src import recent_colors as recent_colors_store

WHEEL_SIZE = 150
wheelImageCache: Optional[tk.PhotoImage] = None


def getWheelImage() -> tk.PhotoImage:
    global wheelImageCache
    if wheelImageCache is not None and wheelImageCache.width() == WHEEL_SIZE:
        return wheelImageCache

    size = WHEEL_SIZE
    radius = size / 2.0
    img = tk.PhotoImage(width=size, height=size)
    rows = []
    for y in range(size):
        dy = y - radius
        pixels = []
        for x in range(size):
            dx = x - radius
            dist = math.hypot(dx, dy)
            if dist <= radius:
                angle = math.atan2(dy, dx)
                hue = (math.degrees(angle) + 360.0) % 360.0 / 360.0
                sat = min(dist / radius, 1.0)
                r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
                pixels.append(
                    f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
                )
            else:
                pixels.append("#18181b")
        rows.append("{" + " ".join(pixels) + "}")
    img.put(" ".join(rows))
    wheelImageCache = img
    return img


def currentRgb(state: Dict[str, Any]) -> Tuple[int, int, int]:
    try:
        r = max(0, min(255, int(round(state["rVar"].get()))))
        g = max(0, min(255, int(round(state["gVar"].get()))))
        b = max(0, min(255, int(round(state["bVar"].get()))))
    except (tk.TclError, ValueError, TypeError):
        r = g = b = 255
    return r, g, b


def updatePreview(state: Dict[str, Any]):
    r, g, b = currentRgb(state)
    hexcolor = f"#{r:02x}{g:02x}{b:02x}"
    if "previewFrame" in state:
        state["previewFrame"].configure(fg_color=hexcolor)
    for label, val in (("R", r), ("G", g), ("B", b)):
        if label in state["valueLabels"]:
            state["valueLabels"][label].configure(text=str(val))


def updateWheelCursor(state: Dict[str, Any]):
    r, g, b = currentRgb(state)
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    radius = WHEEL_SIZE / 2.0
    angle = math.radians(h * 360.0)
    dist = s * radius
    x = radius + dist * math.cos(angle)
    y = radius + dist * math.sin(angle)
    state["wheelCanvas"].delete("cursor")
    r_dot = 5
    outline = "#ffffff" if s > 0.4 or v < 0.6 else "#000000"
    state["wheelCanvas"].create_oval(
        x - r_dot, y - r_dot, x + r_dot, y + r_dot,
        outline=outline, width=2, tags="cursor",
    )


def updateSliders(state: Dict[str, Any]):
    r, g, b = currentRgb(state)
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    s_val = int(round(s * 100))
    v_val = int(round(v * 100))
    state["sVar"].set(s_val)
    state["vVar"].set(v_val)
    if "sSlider" in state:
        state["sSlider"].set(s_val)
    if "vSlider" in state:
        state["vSlider"].set(v_val)
    if "rSlider" in state:
        state["rSlider"].set(r)
    if "gSlider" in state:
        state["gSlider"].set(g)
    if "bSlider" in state:
        state["bSlider"].set(b)


def syncFromRgb(state: Dict[str, Any]):
    if state["updating"]:
        return
    state["updating"] = True
    try:
        r, g, b = currentRgb(state)
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if s > 0.0:
            state["lastHue"] = h
        state["hexVar"].set(f"#{r:02x}{g:02x}{b:02x}")
        updatePreview(state)
        updateWheelCursor(state)
        updateSliders(state)
    finally:
        state["updating"] = False


def onRgbSliderChange(state: Dict[str, Any], channel: str, value: float):
    if state["updating"]:
        return
    state["updating"] = True
    try:
        val = int(round(value))
        if channel == "R":
            state["rVar"].set(val)
        elif channel == "G":
            state["gVar"].set(val)
        elif channel == "B":
            state["bVar"].set(val)
        r, g, b = currentRgb(state)
        state["hexVar"].set(f"#{r:02x}{g:02x}{b:02x}")
        updatePreview(state)
        updateWheelCursor(state)
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if s > 0.0:
            state["lastHue"] = h
        s_val = int(round(s * 100))
        v_val = int(round(v * 100))
        state["sVar"].set(s_val)
        state["vVar"].set(v_val)
        if "sSlider" in state:
            state["sSlider"].set(s_val)
        if "vSlider" in state:
            state["vSlider"].set(v_val)
    finally:
        state["updating"] = False


def onWheelEvent(state: Dict[str, Any], event):
    radius = WHEEL_SIZE / 2.0
    dx = event.x - radius
    dy = event.y - radius
    dist = min(math.hypot(dx, dy), radius)
    angle = math.atan2(dy, dx)
    hue = (math.degrees(angle) + 360.0) % 360.0 / 360.0
    sat = dist / radius if radius else 0.0
    val = max(0.0, min(1.0, state["vVar"].get() / 100.0))
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)

    state["updating"] = True
    try:
        nr, ng, nb = int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
        s_val = int(round(sat * 100))
        if sat > 0.0:
            state["lastHue"] = hue
        state["rVar"].set(nr)
        state["gVar"].set(ng)
        state["bVar"].set(nb)
        state["sVar"].set(s_val)
        if "rSlider" in state:
            state["rSlider"].set(nr)
        if "gSlider" in state:
            state["gSlider"].set(ng)
        if "bSlider" in state:
            state["bSlider"].set(nb)
        if "sSlider" in state:
            state["sSlider"].set(s_val)
        state["hexVar"].set(f"#{nr:02x}{ng:02x}{nb:02x}")
        updatePreview(state)
        updateWheelCursor(state)
    finally:
        state["updating"] = False


def onSaturationSliderChange(state: Dict[str, Any], value: float):
    if state["updating"]:
        return
    sat_val = float(value)
    state["sVar"].set(int(round(sat_val)))
    r, g, b = currentRgb(state)
    _, cur_s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    h = state["lastHue"] if cur_s == 0.0 else _
    sat = max(0.0, min(1.0, sat_val / 100.0))
    nr, ng, nb = colorsys.hsv_to_rgb(h, sat, v)

    state["updating"] = True
    try:
        ir, ig, ib = int(round(nr * 255)), int(round(ng * 255)), int(round(nb * 255))
        state["rVar"].set(ir)
        state["gVar"].set(ig)
        state["bVar"].set(ib)
        if "rSlider" in state:
            state["rSlider"].set(ir)
        if "gSlider" in state:
            state["gSlider"].set(ig)
        if "bSlider" in state:
            state["bSlider"].set(ib)
        state["hexVar"].set(f"#{ir:02x}{ig:02x}{ib:02x}")
        updatePreview(state)
        updateWheelCursor(state)
    finally:
        state["updating"] = False


def onValueSliderChange(state: Dict[str, Any], value: float):
    if state["updating"]:
        return
    val_val = float(value)
    state["vVar"].set(int(round(val_val)))
    r, g, b = currentRgb(state)
    _, s, _ = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    h = state["lastHue"] if s == 0.0 else _
    val = max(0.0, min(1.0, val_val / 100.0))
    nr, ng, nb = colorsys.hsv_to_rgb(h, s, val)

    state["updating"] = True
    try:
        ir, ig, ib = int(round(nr * 255)), int(round(ng * 255)), int(round(nb * 255))
        state["rVar"].set(ir)
        state["gVar"].set(ig)
        state["bVar"].set(ib)
        if "rSlider" in state:
            state["rSlider"].set(ir)
        if "gSlider" in state:
            state["gSlider"].set(ig)
        if "bSlider" in state:
            state["bSlider"].set(ib)
        state["hexVar"].set(f"#{ir:02x}{ig:02x}{ib:02x}")
        updatePreview(state)
        updateWheelCursor(state)
    finally:
        state["updating"] = False


def onHexChange(state: Dict[str, Any]):
    if state["updating"]:
        return
    raw = state["hexVar"].get().strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    if len(raw) != 6:
        r, g, b = currentRgb(state)
        state["hexVar"].set(f"#{r:02x}{g:02x}{b:02x}")
        return
    try:
        r = int(raw[0:2], 16)
        g = int(raw[2:4], 16)
        b = int(raw[4:6], 16)
    except ValueError:
        r, g, b = currentRgb(state)
        state["hexVar"].set(f"#{r:02x}{g:02x}{b:02x}")
        return

    state["updating"] = True
    try:
        state["rVar"].set(r)
        state["gVar"].set(g)
        state["bVar"].set(b)
        updatePreview(state)
        updateWheelCursor(state)
        updateSliders(state)
    finally:
        state["updating"] = False


def renderPalette(state: Dict[str, Any]):
    for child in state["paletteWrap"].winfo_children():
        child.destroy()

    if not recent_colors_store.RECENT_COLORS:
        ctk.CTkLabel(
            state["paletteWrap"],
            text="Empty for now — click «Save to palette»",
            text_color=FG_MUTED, font=(FONT_FAMILY, 9),
        ).pack(anchor="w")
        return

    per_row = 10
    for idx, hexcolor in enumerate(recent_colors_store.RECENT_COLORS):
        row_idx, col_idx = divmod(idx, per_row)
        swatch = ctk.CTkButton(
            state["paletteWrap"],
            text="", width=22, height=22, corner_radius=4,
            border_width=1, border_color="#3f3f46",
            fg_color=hexcolor, hover_color=hexcolor,
            command=lambda hc=hexcolor, st=state: onPalettePick(st, hc),
        )
        swatch.grid(row=row_idx, column=col_idx, padx=2, pady=2)
        swatch.bind(
            "<Double-Button-1>",
            lambda e, hc=hexcolor, st=state: (onPalettePick(st, hc), onOk(st)),
        )


def onPalettePick(state: Dict[str, Any], hexcolor: str):
    state["hexVar"].set(hexcolor)
    onHexChange(state)


def onSaveToPalette(state: Dict[str, Any]):
    r, g, b = currentRgb(state)
    recent_colors_store.addRecentColor(f"#{r:02x}{g:02x}{b:02x}")
    renderPalette(state)


def onOk(state: Dict[str, Any]):
    r, g, b = currentRgb(state)
    state["result"] = (r, g, b)
    recent_colors_store.addRecentColor(f"#{r:02x}{g:02x}{b:02x}")
    try:
        state["window"].grab_release()
    except Exception:
        pass
    state["window"].destroy()


def onCancel(state: Dict[str, Any]):
    state["result"] = None
    try:
        state["window"].grab_release()
    except Exception:
        pass
    state["window"].destroy()


def buildColorPickerUi(state: Dict[str, Any], initial_rgb: Tuple[int, int, int], title: str):
    window = state["window"]
    window.title(title)
    window.configure(fg_color="#18181b")
    window.resizable(False, False)

    r, g, b = initial_rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    
    state["lastHue"] = h if s > 0.0 else 0.0

    state["rVar"] = tk.IntVar(value=r)
    state["gVar"] = tk.IntVar(value=g)
    state["bVar"] = tk.IntVar(value=b)
    state["sVar"] = tk.IntVar(value=int(round(s * 100)))
    state["vVar"] = tk.IntVar(value=int(round(v * 100)))
    state["hexVar"] = tk.StringVar(value=f"#{r:02x}{g:02x}{b:02x}")
    state["valueLabels"] = {}

    outer = ctk.CTkFrame(window, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=12, pady=10)

    top = ctk.CTkFrame(outer, fg_color="transparent")
    top.pack(fill="x")

    wheel_wrap = ctk.CTkFrame(top, fg_color="transparent")
    wheel_wrap.pack(side="left")
    wheel_image = getWheelImage()
    state["wheelImage"] = wheel_image
    wheel_canvas = tk.Canvas(
        wheel_wrap, width=WHEEL_SIZE, height=WHEEL_SIZE,
        highlightthickness=0, bg="#18181b", bd=0,
    )
    state["wheelCanvas"] = wheel_canvas
    wheel_canvas.pack()
    wheel_canvas.create_image(0, 0, image=wheel_image, anchor="nw")
    wheel_canvas.bind("<Button-1>", lambda e: onWheelEvent(state, e))
    wheel_canvas.bind("<B1-Motion>", lambda e: onWheelEvent(state, e))

    # saturation
    sat_col = ctk.CTkFrame(top, fg_color="transparent")
    sat_col.pack(side="left", fill="y", padx=(10, 0))
    ctk.CTkLabel(
        sat_col, text="Sat", text_color=FG_MUTED, font=(FONT_FAMILY, 9, "bold"),
    ).pack(anchor="w", pady=(0, 2))
    s_slider = ctk.CTkSlider(
        sat_col, from_=100, to=0, orientation="vertical",
        width=16, height=WHEEL_SIZE - 20,
        fg_color="#27272a", progress_color=ACCENT, button_color=ACCENT,
        button_hover_color=ACCENT_HOVER,
        command=lambda v: onSaturationSliderChange(state, v),
    )
    s_slider.set(int(round(s * 100)))
    s_slider.pack(fill="y", expand=True)
    state["sSlider"] = s_slider

    # brightness
    val_col = ctk.CTkFrame(top, fg_color="transparent")
    val_col.pack(side="left", fill="y", padx=(8, 0))
    ctk.CTkLabel(
        val_col, text="Val", text_color=FG_MUTED, font=(FONT_FAMILY, 9, "bold"),
    ).pack(anchor="w", pady=(0, 2))
    v_slider = ctk.CTkSlider(
        val_col, from_=100, to=0, orientation="vertical",
        width=16, height=WHEEL_SIZE - 20,
        fg_color="#27272a", progress_color=ACCENT, button_color=ACCENT,
        button_hover_color=ACCENT_HOVER,
        command=lambda v: onValueSliderChange(state, v),
    )
    v_slider.set(int(round(v * 100)))
    v_slider.pack(fill="y", expand=True)
    state["vSlider"] = v_slider

    preview_frame = ctk.CTkFrame(
        outer, height=34, corner_radius=6,
        fg_color=f"#{r:02x}{g:02x}{b:02x}", border_width=1, border_color="#3f3f46"
    )
    state["previewFrame"] = preview_frame
    preview_frame.pack(fill="x", pady=(8, 0))

    # save to palette
    save_row = ctk.CTkFrame(outer, fg_color="transparent")
    save_row.pack(fill="x", pady=(6, 0))
    ctk.CTkButton(
        save_row, text="💾  Save to palette",
        height=26, width=120, corner_radius=6,
        fg_color="#27272a", hover_color="#3f3f46", text_color=FG,
        font=(FONT_FAMILY, 9, "bold"),
        command=lambda: onSaveToPalette(state),
    ).pack(side="left")

    # rgb
    sliders_frame = ctk.CTkFrame(outer, fg_color="transparent")
    sliders_frame.pack(fill="x", pady=(8, 0))

    for label, var, color, ch_name in (
        ("R", state["rVar"], "#ff6b6b", "R"),
        ("G", state["gVar"], "#5be27d", "G"),
        ("B", state["bVar"], "#5b8cff", "B"),
    ):
        row = ctk.CTkFrame(sliders_frame, fg_color="transparent")
        row.pack(fill="x", pady=1)

        ctk.CTkLabel(
            row, text=label, width=14, text_color=color, font=(FONT_FAMILY, 9, "bold"),
        ).pack(side="left")

        slider = ctk.CTkSlider(
            row, from_=0, to=255, height=16,
            fg_color="#27272a", progress_color=color, button_color=color,
            button_hover_color=color,
            command=lambda v, ch=ch_name: onRgbSliderChange(state, ch, v),
        )
        slider.set(var.get())
        slider.pack(side="left", fill="x", expand=True, padx=(6, 6))
        state[f"{ch_name.lower()}Slider"] = slider



        value_label = ctk.CTkLabel(
            row, text=str(var.get()), width=26, text_color=FG, font=(FONT_FAMILY, 9),
        )
        value_label.pack(side="left")
        state["valueLabels"][label] = value_label

    # hex
    hex_row = ctk.CTkFrame(outer, fg_color="transparent")
    hex_row.pack(fill="x", pady=(6, 0))

    ctk.CTkLabel(
        hex_row, text="HEX:", text_color=FG_MUTED, font=(FONT_FAMILY, 9, "bold"),
    ).pack(side="left", padx=(0, 6))

    hex_entry = ctk.CTkEntry(
        hex_row, textvariable=state["hexVar"], height=28, corner_radius=6,
        fg_color="#27272a", border_width=0, text_color=FG, font=(FONT_FAMILY, 9),
    )
    hex_entry.pack(side="left", fill="x", expand=True)
    hex_entry.bind("<Return>", lambda e: onHexChange(state))
    hex_entry.bind("<FocusOut>", lambda e: onHexChange(state))

    # palette
    palette_frame = ctk.CTkFrame(outer, fg_color="transparent")
    palette_frame.pack(fill="x", pady=(8, 0))

    ctk.CTkLabel(
        palette_frame, text="RECENT COLORS", text_color=FG_MUTED, font=(FONT_FAMILY, 9, "bold"),
    ).pack(anchor="w")

    palette_wrap = ctk.CTkFrame(palette_frame, fg_color="transparent")
    palette_wrap.pack(fill="x", pady=(4, 0))
    state["paletteWrap"] = palette_wrap
    renderPalette(state)

    btn_row = ctk.CTkFrame(outer, fg_color="transparent")
    btn_row.pack(fill="x", pady=(10, 0))

    ctk.CTkButton(
        btn_row, text="OK", width=80, height=28, corner_radius=6,
        fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ON_ACCENT,
        font=(FONT_FAMILY, 9, "bold"), command=lambda: onOk(state),
    ).pack(side="right")

    ctk.CTkButton(
        btn_row, text="Cancel", width=80, height=28, corner_radius=6,
        fg_color="#27272a", hover_color="#3f3f46", text_color=FG,
        font=(FONT_FAMILY, 9), command=lambda: onCancel(state),
    ).pack(side="right", padx=(0, 6))

    syncFromRgb(state)

    window.protocol("WM_DELETE_WINDOW", lambda: onCancel(state))
    window.bind("<Return>", lambda e: onOk(state))
    window.bind("<Escape>", lambda e: onCancel(state))

    parent = state["parent"]
    if parent is not None:
        try:
            parent.update_idletasks()
            px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 150
            py = parent.winfo_rooty() + (parent.winfo_height() // 2) - 220
            window.geometry(f"+{max(px, 0)}+{max(py, 0)}")
        except Exception:
            pass

    window.after(10, lambda: [window.lift(), window.focus_force(), window.grab_set()])


def get_icon_path() -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "icon.ico")
    return os.path.join(os.path.abspath("."), "icon.ico")


def createColorPicker(parent: tk.Misc, initial_rgb: Tuple[int, int, int], title: str) -> Dict[str, Any]:
    window = ctk.CTkToplevel(parent)
    state: Dict[str, Any] = {
        "parent": parent,
        "window": window,
        "result": None,
        "updating": False,
    }
    buildColorPickerUi(state, initial_rgb, title)
    icon_path = get_icon_path()
    if os.path.isfile(icon_path):
        window.after(50, lambda: window.iconbitmap(icon_path))
    return state


def askCustomColor(
    parent: tk.Misc,
    initialHex: str = "#ffffff",
    title: str = "Choose Color",
) -> Optional[Tuple[int, int, int]]:
    raw = initialHex.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    try:
        r = int(raw[0:2], 16)
        g = int(raw[2:4], 16)
        b = int(raw[4:6], 16)
    except (ValueError, IndexError):
        r = g = b = 255
    state = createColorPicker(parent, initial_rgb=(r, g, b), title=title)
    parent.wait_window(state["window"])
    return state["result"]

