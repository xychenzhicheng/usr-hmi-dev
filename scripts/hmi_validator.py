#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Industrial Semantic & Layout Conflict Validator for USRHMIToolsPro HMI Screens.
Performs pre-compilation checks to prevent field errors:
  - Canvas bounding box violations (1024x600 limits)
  - Severe widget overlap detection
  - Industrial unit mismatch warnings (e.g., mixing "斤" with "kg" / "公斤")
  - Duplicate Modbus register conflicts (e.g. multiple input widgets bound to the same 4x address)
"""

from collections import defaultdict
import math


def validate_screen_spec(screen_spec: dict, canvas_w: float = 1024.0, canvas_h: float = 600.0) -> tuple[bool, list[str], list[str]]:
    """Validate a screen spec dictionary before compilation into a .pro file.

    Returns:
        (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    widgets = screen_spec.get("widgets", [])
    if not widgets:
        errors.append("Screen has no widgets defined.")
        return False, errors, warnings

    # 1. Canvas Bounds & Geometry Check
    rects = []
    for idx, w in enumerate(widgets):
        wtype = w.get("type", "unknown")
        for k in ("x", "y", "w", "h"):
            if k not in w or not isinstance(w[k], (int, float)) or not math.isfinite(w[k]):
                errors.append(f"Widget #{idx} ({wtype}): Invalid or missing coordinate '{k}'.")
                break
        else:
            x, y, width, height = float(w["x"]), float(w["y"]), float(w["w"]), float(w["h"])
            if width <= 0 or height <= 0:
                errors.append(f"Widget #{idx} ({wtype}): Non-positive dimensions {width}x{height}.")
            if x < 0 or y < 0:
                errors.append(f"Widget #{idx} ({wtype}): Negative position ({x}, {y}).")
            if x + width > canvas_w or y + height > canvas_h:
                errors.append(
                    f"Widget #{idx} ({wtype}): Out of canvas bounds ({x}+{width}={x+width}>{canvas_w} or {y}+{height}={y+height}>{canvas_h})."
                )
            rects.append((idx, wtype, x, y, width, height))

    # 2. Severe Overlap Detection
    for i in range(len(rects)):
        idx_i, type_i, xi, yi, wi, hi = rects[i]
        for j in range(i + 1, len(rects)):
            idx_j, type_j, xj, yj, wj, hj = rects[j]
            # Skip checking overlaps between full-screen backgrounds and other widgets
            if (wi >= canvas_w * 0.9 and hi >= canvas_h * 0.9) or (wj >= canvas_w * 0.9 and hj >= canvas_h * 0.9):
                continue
            inter_x1 = max(xi, xj)
            inter_y1 = max(yi, yj)
            inter_x2 = min(xi + wi, xj + wj)
            inter_y2 = min(yi + hi, yj + hj)
            if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                overlap_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                min_area = min(wi * hi, wj * hj)
                overlap_pct = (overlap_area / min_area) * 100.0 if min_area > 0 else 0
                if overlap_pct > 75.0:
                    warnings.append(
                        f"High widget overlap ({overlap_pct:.0f}%): #{idx_i} ({type_i}) overlaps #{idx_j} ({type_j})."
                    )

    # 3. Unit Consistency Check (Chinese 斤 vs kg/公斤)
    all_texts = []
    for w in widgets:
        for k in ("text", "label", "name"):
            if k in w and isinstance(w[k], str):
                all_texts.append(w[k])
    joined_text = " ".join(all_texts)
    has_jin = any(
        term in joined_text
        for term in ("斤", "几斤", "喂多少斤", "总斤数")
    )
    has_kg = any(
        term in joined_text.lower()
        for term in ("kg", "公斤", "千克")
    )
    if has_jin and has_kg:
        warnings.append(
            "Industrial unit warning: Both '斤' and 'kg'/'公斤' appear in widget labels on the same screen. "
            "Ensure Modbus PLC registers (scaled to 0.1kg) match the display unit intended for operators."
        )

    # 4. Duplicate Modbus Register Conflict Check
    reg_usage = defaultdict(list)
    for idx, w in enumerate(widgets):
        wtype = w.get("type", "")
        if "reg_num" in w:
            key = f"{w.get('reg_type', '4x')}{w['reg_num']}"
            reg_usage[key].append((idx, wtype, w.get("editable", True)))
        elif "bit_addr" in w:
            key = f"{w.get('reg_type', '4x_bit')}{w['bit_addr']}"
            reg_usage[key].append((idx, wtype, True))

    for reg_key, users in reg_usage.items():
        # Check if multiple EDITABLE inputs use the exact same register
        editable_users = [u for u in users if u[1].startswith("numeric") and u[2]]
        if len(editable_users) > 1:
            indices = [f"#{u[0]}" for u in editable_users]
            warnings.append(
                f"Duplicate input register conflict: Register {reg_key} is bound to multiple editable inputs ({', '.join(indices)})."
            )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings
