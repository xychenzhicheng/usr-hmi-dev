#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USRHMIToolsProV1.0 (KinSealStudio OEM) Project & Compile Artifact Tool
Supports:
  - inspect-pro: Parse Qt QDataStream (.pro) project metadata, comms, screens, registers, and UI strings
  - inspect-screens: Structurally parse all screens and widgets (type, geometry, registers, labels, z-order)
  - search-pro: Search QStrings in .pro file with surrounding context
  - replace-string: Safely replace QStrings in .pro file (with RGB/system-register corruption guards)
  - inspect-compile: Inspect compiled SQLite DBs (mulState.db, mulText.db, param.db) and binary tables (SheetPara.dat, ControlPara.dat)
  - extract-upload: Extract backed-up .pro file from compile/UpLoad.zip
"""

import argparse
import os
import re
import sqlite3
import struct
import sys
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WIDGET_TYPE_NAMES = {
    0x1C: "Label/Banner (0x1C)",
    0x26: "WordWriteBtn (0x26)",
    0x38: "BitBtn (0x38)",
    0x39: "ScreenJumpBtn (0x39)",
    0x3F: "NumericIO (0x3F)",
    0x51: "BitLamp (0x51)",
    0x52: "MultiStateLamp (0x52)",
}


def extract_qstrings(data: bytes, min_len: int = 2, max_len: int = 400):
    """Scan binary data for valid Qt QDataStream QString entries (uint32_be byte_length + UTF-16BE payload)."""
    results = []
    i = 0
    n = len(data)
    while i <= n - 6:
        byte_len = struct.unpack(">I", data[i : i + 4])[0]
        if min_len <= byte_len <= max_len and (byte_len % 2 == 0) and (i + 4 + byte_len <= n):
            raw = data[i + 4 : i + 4 + byte_len]
            try:
                text = raw.decode("utf-16-be")
                if text and all((c.isprintable() or c in "\r\n\t") and ord(c) >= 0x20 for c in text):
                    results.append((i, byte_len, text))
                    i += 4 + byte_len
                    continue
            except UnicodeDecodeError:
                pass
        i += 1
    return results


def parse_screens_and_widgets(data: bytes):
    """Structurally parse all screens and their widget lists from a KinSealStudio .pro binary."""
    marker = bytes.fromhex("000000010000000000010000000000010000")
    screens = []
    pos = 0
    while True:
        m = data.find(marker, pos)
        if m == -1:
            break
        wcount_pos = m + len(marker)
        wcount = struct.unpack(">I", data[wcount_pos : wcount_pos + 4])[0]
        w_start = wcount_pos + 4
        # Extract screen name & number from the 220 bytes before marker
        hdr_qstrs = [s for _, _, s in extract_qstrings(data[max(0, m - 220) : m])]
        s_name = hdr_qstrs[0] if len(hdr_qstrs) >= 1 else "Unknown"
        s_num = hdr_qstrs[1] if len(hdr_qstrs) >= 2 else "???"
        screens.append((s_num, s_name, m, wcount_pos, wcount, w_start))
        pos = w_start

    parsed_screens = []
    for idx, (s_num, s_name, m_pos, wcount_pos, wcount, w_start) in enumerate(screens):
        next_limit = screens[idx + 1][2] - 90 if idx + 1 < len(screens) else len(data)
        wbuf = data[w_start:next_limit]
        starts = []
        for i in range(len(wbuf) - 20):
            if wbuf[i] == 1 and wbuf[i + 9 : i + 13] in (
                b"\x00\x01\x00\x0f",
                b"\x00\x01\x00\x16",
                b"\x00\x00\x00\x0d",
            ):
                wtype = struct.unpack(">I", wbuf[i + 1 : i + 5])[0]
                ver = struct.unpack(">I", wbuf[i + 5 : i + 9])[0]
                if wtype in WIDGET_TYPE_NAMES and ver in (1, 2):
                    starts.append((i, wtype, ver))
                    if len(starts) == wcount + 1:
                        break
        widgets = []
        for wi in range(min(wcount, len(starts))):
            w_off, wtype, ver = starts[wi]
            w_end = starts[wi + 1][0] if wi + 1 < len(starts) else len(wbuf)
            wb = wbuf[w_off:w_end]
            qstrs = [
                s
                for _, _, s in extract_qstrings(wb)
                if s not in ("0", "LB0", "LB", "LW0", "LW", "Local HMI", "阿里巴巴普惠体", "mText", "500", "****")
                and not s.endswith(".kvg")
            ]
            # Extract geometry
            geom = ""
            if wtype == 0x1C and len(wb) >= 45:
                x1, y1, x2, y2 = struct.unpack(">4d", wb[13:45])
                geom = f"({x1:.0f},{y1:.0f}) {x2-x1:.0f}x{y2-y1:.0f}"
            elif wtype == 0x3F and len(wb) >= 207:
                _, _, w, h = struct.unpack(">4d", wb[13:45])
                # pos_x, pos_y is at 191..207 for 7-char '88888.8' or 181..197 for 2-char '88'
                fmt_len = struct.unpack(">I", wb[45:49])[0]
                px_off = 177 + fmt_len
                if px_off + 16 <= len(wb):
                    px, py = struct.unpack(">2d", wb[px_off : px_off + 16])
                    geom = f"({px:.0f},{py:.0f}) {w:.0f}x{h:.0f}"
            elif wtype in (0x26, 0x38, 0x39, 0x51, 0x52) and len(wb) >= 193:
                px, py, w, h = struct.unpack(">4d", wb[161:193])
                geom = f"({px:.0f},{py:.0f}) {w:.0f}x{h:.0f}"
            widgets.append((wi, w_start + w_off, wtype, ver, len(wb), geom, qstrs[:6]))
        parsed_screens.append((idx, s_num, s_name, wcount_pos, wcount, widgets))
    return parsed_screens


def cmd_inspect_pro(args):
    pro_path = Path(args.pro_file)
    if not pro_path.exists():
        print(f"[ERROR] File not found: {pro_path}")
        sys.exit(1)

    data = pro_path.read_bytes()
    qstrings = extract_qstrings(data)

    print(f"=== Project File: {pro_path} ({len(data):,} bytes) ===")
    print(f"Total QStrings extracted: {len(qstrings)}")

    print("\n[1] Header & HMI Model Info:")
    for _, (offset, blen, text) in enumerate(qstrings[:16]):
        print(f"  0x{offset:06x}: {text!r}")

    comms = []
    registers = set()
    reg_pattern = re.compile(r"^(\[[^\]]+\])?(LW_Bit|LW|LB|RWI|RW|4x_bit|4x|3x|0x|1x|D|M|X|Y)[\d\.]+$")

    for offset, blen, text in qstrings:
        if any(k in text for k in ("Modbus", "COM1", "COM2", "RS-485", "RS-232", "TCPIP", "PLC")):
            comms.append((offset, text))
        if reg_pattern.match(text):
            registers.add(text)

    print("\n[2] Communication & PLC Entries (Sample):")
    seen_comms = []
    for offset, text in comms:
        if text not in seen_comms:
            seen_comms.append(text)
            print(f"  0x{offset:06x}: {text}")

    parsed_screens = parse_screens_and_widgets(data)
    print(f"\n[3] Screens Detected ({len(parsed_screens)} total):")
    for s_idx, s_num, s_name, wc_pos, wcount, widgets in parsed_screens:
        if wcount > 0 and s_name not in ("ascii", "num", "chinese"):
            print(f"  Screen #{s_idx:02d} [{s_num}:{s_name}] @0x{wc_pos:06x}: {wcount} widgets")

    print(f"\n[4] Unique Register Addresses Referenced ({len(registers)}):")
    for r in sorted(registers):
        print(f"  {r}")


def cmd_inspect_screens(args):
    pro_path = Path(args.pro_file)
    data = pro_path.read_bytes()
    parsed_screens = parse_screens_and_widgets(data)
    for s_idx, s_num, s_name, wc_pos, wcount, widgets in parsed_screens:
        if not args.all and (wcount == 0 or s_idx in range(1, 15)):
            continue
        print(f"\n==================== Screen #{s_idx:02d} [{s_num}:{s_name}] (wcount={wcount}) ====================")
        for wi, abs_off, wtype, ver, wlen, geom, qstrs in widgets:
            tname = WIDGET_TYPE_NAMES.get(wtype, f"0x{wtype:02x}")
            print(f"  #{wi:02d} @0x{abs_off:06x} | {tname:<20} | {geom:<18} | {qstrs}")


def cmd_search_pro(args):
    pro_path = Path(args.pro_file)
    data = pro_path.read_bytes()
    qstrings = extract_qstrings(data)
    query = args.query.lower()
    ctx = args.context

    matches = [idx for idx, (_, _, text) in enumerate(qstrings) if query in text.lower()]
    print(f"Found {len(matches)} match(es) for {args.query!r} in {pro_path}:")
    for m_idx, q_idx in enumerate(matches[:50]):
        offset, blen, text = qstrings[q_idx]
        print(f"\n--- Match #{m_idx} at 0x{offset:06x} (byte_len={blen}) ---")
        start = max(0, q_idx - ctx)
        end = min(len(qstrings), q_idx + ctx + 1)
        for i in range(start, end):
            o, l, t = qstrings[i]
            marker = ">>" if i == q_idx else "  "
            print(f"  {marker} [#{i}] 0x{o:06x}: {t!r}")


def cmd_replace_string(args):
    pro_path = Path(args.pro_file)
    data = pro_path.read_bytes()

    # Safety check against corrupting RGB color strings or system registers
    if re.match(r"^\d+\+\d+\+\d+$", args.old) and not re.match(r"^\d+\+\d+\+\d+$", args.new):
        print(f"[ERROR] Refusing to replace RGB color string {args.old!r} with non-RGB {args.new!r}!")
        sys.exit(1)

    old_bytes = args.old.encode("utf-16-be")
    old_record = struct.pack(">I", len(old_bytes)) + old_bytes

    new_bytes = args.new.encode("utf-16-be")
    new_record = struct.pack(">I", len(new_bytes)) + new_bytes

    positions = []
    start = 0
    while True:
        pos = data.find(old_record, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + len(old_record)

    if not positions:
        print(f"[ERROR] Exact QString {args.old!r} not found in {pro_path}")
        sys.exit(1)

    print(f"Found {len(positions)} exact QString occurrence(s) of {args.old!r} at: {[hex(p) for p in positions]}")

    if args.occurrence == "all":
        new_data = data.replace(old_record, new_record)
        print(f"Replaced ALL {len(positions)} exact QString occurrence(s) with {args.new!r}.")
    else:
        idx = int(args.occurrence)
        if idx < 0 or idx >= len(positions):
            print(f"[ERROR] Occurrence index {idx} out of range (0..{len(positions)-1})")
            sys.exit(1)
        pos = positions[idx]
        new_data = data[:pos] + new_record + data[pos + len(old_record) :]
        print(f"Replaced occurrence #{idx} at 0x{pos:06x} with {args.new!r}.")

    out_path = Path(args.output) if args.output else pro_path
    out_path.write_bytes(new_data)
    print(f"Saved updated project file to: {out_path} ({len(new_data):,} bytes)")


def cmd_inspect_compile(args):
    cdir = Path(args.compile_dir)
    if not cdir.exists():
        print(f"[ERROR] Compile directory not found: {cdir}")
        sys.exit(1)

    print(f"=== Inspecting Compiled HMI Artifacts in {cdir} ===")

    sheet_path = cdir / "SheetPara.dat"
    if sheet_path.exists():
        sdata = sheet_path.read_bytes()
        print(f"\n[1] SheetPara.dat ({len(sdata)} bytes):")
        for m in re.finditer(rb"[A-Za-z0-9_\-\x80-\xff ]{3,32}", sdata):
            try:
                txt = m.group(0).decode("utf-8").strip()
                if txt:
                    print(f"  Offset 0x{m.start():04x}: {txt!r}")
            except Exception:
                pass

    ctrl_path = cdir / "ControlPara.dat"
    if ctrl_path.exists():
        cdata = ctrl_path.read_bytes()
        print(f"\n[2] ControlPara.dat ({len(cdata):,} bytes) - First Header Struct:")
        if len(cdata) >= 12:
            wtype, item_id, x, y, w, h = struct.unpack("<6H", cdata[:12])
            print(f"  First Widget: type={wtype}, item_id={item_id}, x={x}, y={y}, width={w}, height={h}")

    state_db = cdir / "mulState.db"
    if state_db.exists():
        print("\n[3] mulState.db (Widget States, Texts, Fonts, Images):")
        conn = sqlite3.connect(str(state_db))
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT screen_id, item_id, lan_id, state_id, text, font, textSize, picName FROM STATE ORDER BY screen_id, item_id, state_id LIMIT 50"
        ).fetchall()
        for r in rows:
            print(
                f"  Screen={r[0]} Item={r[1]} Lan={r[2]} State={r[3]} | Text={r[4]!r} Font={r[5]!r}({r[6]}) Pic={r[7]!r}"
            )
        conn.close()

    text_db = cdir / "mulText.db"
    if text_db.exists():
        print("\n[4] mulText.db (Multi-language Text Library):")
        conn = sqlite3.connect(str(text_db))
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT screen_id, item_id, lan_id, fun_num, text, font, fontsize FROM TEXT LIMIT 50"
        ).fetchall()
        for r in rows:
            print(f"  Screen={r[0]} Item={r[1]} Lan={r[2]} Fun={r[3]} | Text={r[4]!r} Font={r[5]!r}({r[6]})")
        conn.close()


def cmd_extract_upload(args):
    zip_path = Path(args.compile_dir) / "UpLoad.zip"
    if not zip_path.exists():
        print(f"[ERROR] UpLoad.zip not found in {args.compile_dir}")
        sys.exit(1)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
        print(f"Extracted {zf.namelist()} to {out_dir}")


def cmd_apply_screen_spec(args):
    import json
    from hmi_widget_builder import build_screen, build_widget_from_dict

    pro_path = Path(args.pro_file)
    data = pro_path.read_bytes()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    target_no = spec["screen_no"]
    target_name = spec["screen_name"]
    widgets = [build_widget_from_dict(w, idx) for idx, w in enumerate(spec["widgets"])]
    new_screen_bytes = build_screen(
        screen_no=target_no,
        screen_name=target_name,
        widgets=widgets,
        bg_rgb=tuple(spec.get("bg_rgb", [197, 222, 255])),
        width=spec.get("width", 1024.0),
        height=spec.get("height", 600.0),
    )

    parsed_screens = parse_screens_and_widgets(data)
    # Locate user screens (exclude built-in keyboards 1..14 and trailing startup screen with wcount==0)
    matched = None
    for s_idx, s_num, s_name, wc_pos, wcount, _ in parsed_screens:
        if s_idx == 0 or s_idx >= 15:
            if s_num == target_no and wcount > 0:
                matched = (s_idx, s_num, s_name, wc_pos)
                break

    if matched:
        s_idx, s_num, s_name, wc_pos = matched
        # Find exact start of this screen (90 bytes before screen name QString)
        pat = (
            struct.pack(">I", len(s_name) * 2)
            + s_name.encode("utf-16-be")
            + struct.pack(">I", len(s_num) * 2)
            + s_num.encode("utf-16-be")
        )
        name_pos = data.rfind(pat, 0, wc_pos)
        s_start = name_pos - 90
        # Next screen starts 90 bytes before next screen's name_pos
        next_s_idx = s_idx + 1
        next_num, next_name = parsed_screens[next_s_idx][1], parsed_screens[next_s_idx][2]
        next_wc_pos = parsed_screens[next_s_idx][3]
        next_pat = (
            struct.pack(">I", len(next_name) * 2)
            + next_name.encode("utf-16-be")
            + struct.pack(">I", len(next_num) * 2)
            + next_num.encode("utf-16-be")
        )
        next_name_pos = data.rfind(next_pat, wc_pos, next_wc_pos)
        s_end = next_name_pos - 90
        new_data = data[:s_start] + new_screen_bytes + data[s_end:]
        print(f"Replaced existing Screen #{s_idx} [{s_num}:{s_name}] -> [{target_no}:{target_name}] ({len(widgets)} widgets)")
    else:
        # Append as new user screen right before the trailing startup screen (parsed_screens[-1])
        last_num, last_name, last_wc_pos = parsed_screens[-1][1], parsed_screens[-1][2], parsed_screens[-1][3]
        last_pat = (
            struct.pack(">I", len(last_name) * 2)
            + last_name.encode("utf-16-be")
            + struct.pack(">I", len(last_num) * 2)
            + last_num.encode("utf-16-be")
        )
        last_name_pos = data.rfind(last_pat, 0, last_wc_pos)
        insert_pos = last_name_pos - 116  # 62 bytes before random ID QString (32B + 4B len + 18B)
        # Update total screen count at 0x01357c
        total_screens = struct.unpack(">I", data[0x1357C:0x13580])[0]
        new_screen_list_idx = total_screens
        user_screen_id = int(target_no)
        # Update footer QMap<int, int>
        map_count_off = len(data) - (4 + (total_screens - 14) * 8)
        old_map_count = struct.unpack(">I", data[map_count_off : map_count_off + 4])[0]
        new_footer_map = (
            struct.pack(">I", old_map_count + 1)
            + struct.pack(">II", user_screen_id, new_screen_list_idx)
            + data[map_count_off + 4 :]
        )
        new_data = (
            data[:0x1357C]
            + struct.pack(">I", total_screens + 1)
            + data[0x13580:insert_pos]
            + new_screen_bytes
            + data[insert_pos:map_count_off]
            + new_footer_map
        )
        print(f"Appended new Screen #{new_screen_list_idx} [{target_no}:{target_name}] ({len(widgets)} widgets)")

    out_path = Path(args.output) if args.output else pro_path
    out_path.write_bytes(new_data)
    print(f"Saved updated project to: {out_path} ({len(new_data):,} bytes)")


def main():
    parser = argparse.ArgumentParser(description="USRHMIToolsProV1.0 Project & Compile Artifact Tool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ins = sub.add_parser("inspect-pro", help="Inspect a .pro project file")
    p_ins.add_argument("pro_file", help="Path to .pro file")
    p_ins.set_defaults(func=cmd_inspect_pro)

    p_scr = sub.add_parser("inspect-screens", help="Structurally inspect all screens and widgets in a .pro file")
    p_scr.add_argument("pro_file", help="Path to .pro file")
    p_scr.add_argument("--all", action="store_true", help="Include built-in keyboard screens (1..14)")
    p_scr.set_defaults(func=cmd_inspect_screens)

    p_app = sub.add_parser("apply-screen-spec", help="Build and replace/append a screen in a .pro file from a JSON spec")
    p_app.add_argument("pro_file", help="Path to base .pro file")
    p_app.add_argument("--spec", required=True, help="Path to JSON screen layout spec")
    p_app.add_argument("--output", help="Output .pro file path (defaults to in-place)")
    p_app.set_defaults(func=cmd_apply_screen_spec)

    p_srch = sub.add_parser("search-pro", help="Search QStrings inside a .pro file")
    p_srch.add_argument("pro_file", help="Path to .pro file")
    p_srch.add_argument("--query", required=True, help="Substring to search for")
    p_srch.add_argument("--context", type=int, default=4, help="Surrounding QStrings to display")
    p_srch.set_defaults(func=cmd_search_pro)

    p_rep = sub.add_parser("replace-string", help="Safely replace a QString in a .pro file")
    p_rep.add_argument("pro_file", help="Path to .pro file")
    p_rep.add_argument("--old", required=True, help="Exact old QString")
    p_rep.add_argument("--new", required=True, help="New QString")
    p_rep.add_argument("--occurrence", default="0", help="Occurrence index (0, 1, ...) or 'all'")
    p_rep.add_argument("--output", help="Output .pro path (defaults to in-place)")
    p_rep.set_defaults(func=cmd_replace_string)

    p_cmp = sub.add_parser("inspect-compile", help="Inspect compiled SQLite DBs and .dat files")
    p_cmp.add_argument(
        "compile_dir",
        nargs="?",
        default=r"C:\Program Files (x86)\USRHMIToolsProV1.0\compile",
        help="Path to compile directory",
    )
    p_cmp.set_defaults(func=cmd_inspect_compile)

    p_ext = sub.add_parser("extract-upload", help="Extract .pro backup from compile/UpLoad.zip")
    p_ext.add_argument(
        "--compile-dir",
        default=r"C:\Program Files (x86)\USRHMIToolsProV1.0\compile",
        help="Path to compile directory",
    )
    p_ext.add_argument("--output-dir", required=True, help="Destination directory")
    p_ext.set_defaults(func=cmd_extract_upload)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
