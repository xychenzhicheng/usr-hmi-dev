#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVG Layout Wireframe Generator for USRHMIToolsProV1.0 HMI Screens.
Generates lightweight, dependency-free SVG schematics from screen specifications or
parsed widget lists for instant visual layout verification without launching the Windows IDE.
"""

import html
from pathlib import Path


def generate_screen_svg(screen_spec: dict, canvas_w: float = 1024.0, canvas_h: float = 600.0) -> str:
    """Generate SVG layout schematic from a screen dictionary spec."""
    s_no = screen_spec.get("screen_no", "000")
    s_name = screen_spec.get("screen_name", "Screen")
    bg = screen_spec.get("bg_rgb", [244, 246, 249])
    bg_hex = f"#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}"

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}">',
        f'  <title>[{s_no}:{s_name}] Layout Schematic (USRHMIToolsPro)</title>',
        f'  <defs>',
        f'    <style>',
        f'      text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif; }}',
        f'      .widget-rect {{ stroke-width: 1.5; rx: 4; ry: 4; }}',
        f'      .badge {{ font-size: 11px; font-weight: bold; fill: #ffffff; }}',
        f'    </style>',
        f'  </defs>',
        f'  <!-- Canvas Background -->',
        f'  <rect width="{canvas_w}" height="{canvas_h}" fill="{bg_hex}"/>',
        f'  <!-- Grid Overlay (100px) -->',
    ]

    # Subtle 100px grid
    for gx in range(100, int(canvas_w), 100):
        elements.append(f'  <line x1="{gx}" y1="0" x2="{gx}" y2="{canvas_h}" stroke="#e0e0e0" stroke-width="0.5" stroke-dasharray="4,4"/>')
    for gy in range(100, int(canvas_h), 100):
        elements.append(f'  <line x1="0" y1="{gy}" x2="{canvas_w}" y2="{gy}" stroke="#e0e0e0" stroke-width="0.5" stroke-dasharray="4,4"/>')

    elements.append(f'  <!-- Widgets Layer -->')
    widgets = screen_spec.get("widgets", [])
    for idx, w in enumerate(widgets):
        x, y, width, height = float(w["x"]), float(w["y"]), float(w["w"]), float(w["h"])
        wtype = w.get("type", "widget")
        w_bg = w.get("bg_rgb")
        w_fg = w.get("fg_rgb")

        # Color defaults per widget type if not specified
        if not w_bg:
            if wtype == "label":
                w_bg = [46, 125, 50]
            elif wtype in ("numeric_1dec", "numeric_int"):
                w_bg = [227, 242, 253]
            elif wtype == "write_button":
                w_bg = [230, 81, 0]
            elif wtype == "jump_button":
                w_bg = [69, 90, 100]
            elif wtype == "bit_button":
                w_bg = [21, 101, 192]
            elif wtype == "bit_lamp":
                w_bg = [120, 144, 156]
            else:
                w_bg = [207, 216, 220]

        if not w_fg:
            w_fg = [255, 255, 255] if (w_bg[0] * 0.299 + w_bg[1] * 0.587 + w_bg[2] * 0.114) < 140 else [33, 33, 33]

        fill_hex = f"#{w_bg[0]:02x}{w_bg[1]:02x}{w_bg[2]:02x}"
        fg_hex = f"#{w_fg[0]:02x}{w_fg[1]:02x}{w_fg[2]:02x}"
        stroke_hex = "#263238" if wtype.endswith("button") else "#78909c"

        # Text label
        label = w.get("text", w.get("label", w.get("name", "")))
        reg_tag = ""
        if "reg_num" in w:
            reg_tag = f"[{w.get('reg_type', '4x')}{w['reg_num']}]"
        elif "bit_addr" in w:
            reg_tag = f"[{w.get('reg_type', '4x_bit')}{w['bit_addr']}]"
        elif wtype == "jump_button":
            reg_tag = f"-> {w.get('target_screen', '')}"

        disp_text = label
        if reg_tag and not label.endswith(reg_tag):
            disp_text = f"{label} {reg_tag}" if label else reg_tag

        font_size = min(int(w.get("font_size", 20)), max(12, int(height * 0.45)))

        elements.append(f'  <!-- Widget #{idx}: {wtype} -->')
        elements.append(
            f'  <rect class="widget-rect" x="{x}" y="{y}" width="{width}" height="{height}" '
            f'fill="{fill_hex}" stroke="{stroke_hex}"/>'
        )

        # Centered label
        text_y = y + (height / 2.0) + (font_size * 0.35)
        text_x = x + (width / 2.0)
        elements.append(
            f'  <text x="{text_x}" y="{text_y}" font-size="{font_size}" fill="{fg_hex}" '
            f'text-anchor="middle" font-weight="500">{html.escape(disp_text)}</text>'
        )

        # Small index badge at top-left
        elements.append(
            f'  <rect x="{x}" y="{y}" width="22" height="15" fill="#37474f" rx="3" ry="3"/>'
            f'<text class="badge" x="{x+11}" y="{y+11}" text-anchor="middle">#{idx}</text>'
        )

    elements.append("</svg>")
    return "\n".join(elements)


def save_screen_svg(screen_spec: dict, out_path: str, canvas_w: float = 1024.0, canvas_h: float = 600.0):
    """Generate and write SVG file to disk."""
    svg_content = generate_screen_svg(screen_spec, canvas_w, canvas_h)
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(svg_content, encoding="utf-8")
    return p
