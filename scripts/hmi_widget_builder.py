#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone QDataStream Binary Screen & Widget Synthesizer for USRHMIToolsProV1.0 (.pro files).
Loads pre-extracted binary templates from ../resources/templates/ so this skill is 100% portable
across machines without hardcoded project paths.

Supported Widgets & Screen Builders:
  - build_label          (Type 0x1C: Compound Rectangle + Text Label/Banner)
  - build_numeric_1dec   (Type 0x3F: 1-Decimal Numeric Input / Display, e.g. 88888.8)
  - build_numeric_int    (Type 0x3F: Integer Numeric Input / Display, e.g. 88)
  - build_write_button   (Type 0x26: Word-Write Constant Button)
  - build_bit_button     (Type 0x38: Bit-Write Momentary/Set/Reset Button)
  - build_jump_button    (Type 0x39: Screen-Jump Button)
  - build_bit_lamp       (Type 0x51: 2-State Bit Indicator Lamp)
  - build_screen         (Full Screen Header + Widget List Binary Block)
  - synthesize_from_spec (Declarative JSON/Dict HMI-as-Code Builder)
"""

import argparse
import json
from pathlib import Path
import struct
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TPL_DIR = Path(__file__).resolve().parent.parent / "resources" / "templates"

w_label = (TPL_DIR / "w_label.bin").read_bytes()
w_dec = (TPL_DIR / "w_dec.bin").read_bytes()
w_int = (TPL_DIR / "w_int.bin").read_bytes()
w_btn = (TPL_DIR / "w_btn.bin").read_bytes()
w_bit_btn = (TPL_DIR / "w_bit_btn.bin").read_bytes()
w_jmp = (TPL_DIR / "w_jmp.bin").read_bytes()
w_bit_lamp = (TPL_DIR / "w_bit_lamp.bin").read_bytes()
screen_hdr_tpl = (TPL_DIR / "screen_hdr.bin").read_bytes()


def qstr(s: str) -> bytes:
    b = s.encode("utf-16-be")
    return struct.pack(">I", len(b)) + b


def qcolor(r: int, g: int, b: int) -> bytes:
    return b"\x01\xff\xff" + struct.pack(">HHH", r * 257, g * 257, b * 257) + b"\x00\x00"


def build_label(
    x, y, w, h, text, font_size=24, bg_rgb=(46, 125, 50), fg_rgb=(255, 255, 255), idx=0, z_val=1001.0
) -> bytes:
    """Synthesize a Type 0x1C compound rectangle + text label widget."""
    bg = qcolor(*bg_rgb)
    fg = qcolor(*fg_rgb)
    mid = bytearray(w_label[245:783])
    struct.pack_into(">H", mid, 343 - 245, idx)
    struct.pack_into(">H", mid, 465 - 245, idx)
    return (
        w_label[0:13]
        + struct.pack(">dddd", float(x), float(y), float(x + w), float(y + h))
        + w_label[45:60]
        + bg
        + w_label[71:131]
        + struct.pack(">dddd", float(x), float(y), float(w), float(h))
        + qstr(text)
        + w_label[181:211]
        + struct.pack(">I", font_size)
        + w_label[215:234]
        + fg
        + bytes(mid)
        + bg
        + w_label[794:898]
        + fg
        + w_label[909:946]
        + qstr(str(font_size))
        + w_label[954:958]
        + qstr(text)
        + w_label[976:1014]
        + struct.pack(">d", float(z_val))
    )


def build_numeric_1dec(
    x, y, w, h, reg_num, name_str="数值输入", font_size=30,
    bg_rgb=(227, 242, 253), fg_rgb=(13, 71, 161),
    editable=True, link_name="Modbus_RTU_COM1_1", reg_type="4x",
    idx=0, z_val=1010.0,
) -> bytes:
    """Synthesize a Type 0x3F 1-decimal-place numeric input/display widget ('88888.8')."""
    bg = qcolor(*bg_rgb)
    fg = qcolor(*fg_rgb)
    bg_s = f"{bg_rgb[0]}+{bg_rgb[1]}+{bg_rgb[2]}"
    fg_s = f"{fg_rgb[0]}+{fg_rgb[1]}+{fg_rgb[2]}"
    mid1 = bytearray(w_dec[207:669])
    struct.pack_into(">H", mid1, 235 - 207, idx)
    struct.pack_into(">H", mid1, 357 - 207, idx)
    mid1[366 - 207] = 1 if editable else 0
    edit_flag = b"\x01\x00" if editable else b"\x00\x00"
    reg_full = f"[{link_name}]{reg_type}{reg_num}"
    return (
        w_dec[0:13]
        + struct.pack(">dddd", 0.0, 0.0, float(w), float(h))
        + w_dec[45:93]
        + struct.pack(">I", font_size)
        + w_dec[97:116]
        + fg
        + w_dec[127:158]
        + bg
        + w_dec[169:191]
        + struct.pack(">dd", float(x), float(y))
        + bytes(mid1)
        + qstr(name_str)
        + edit_flag
        + qstr(reg_full)
        + qstr(reg_full)
        + w_dec[795:798]
        + qstr(str(reg_num))
        + w_dec[808:2152]
        + fg
        + qstr(bg_s)
        + w_dec[2189:2219]
        + qstr(fg_s)
        + struct.pack(">I", font_size)
        + w_dec[2237:2242]
        + struct.pack(">d", float(z_val))
    )


def build_numeric_int(
    x, y, w, h, reg_num, name_str="整数输入", font_size=24,
    bg_rgb=(227, 242, 253), fg_rgb=(13, 71, 161),
    editable=True, link_name="Modbus_RTU_COM1_1", reg_type="4x",
    idx=0, z_val=1010.0,
) -> bytes:
    """Synthesize a Type 0x3F integer numeric input/display widget ('88', decimals=0)."""
    bg = qcolor(*bg_rgb)
    fg = qcolor(*fg_rgb)
    bg_s = f"{bg_rgb[0]}+{bg_rgb[1]}+{bg_rgb[2]}"
    fg_s = f"{fg_rgb[0]}+{fg_rgb[1]}+{fg_rgb[2]}"
    mid1 = bytearray(w_int[197:659])
    struct.pack_into(">H", mid1, 225 - 197, idx)
    struct.pack_into(">H", mid1, 347 - 197, idx)
    mid1[356 - 197] = 1 if editable else 0
    edit_flag = b"\x01\x00" if editable else b"\x00\x00"
    reg_full = f"[{link_name}]{reg_type}{reg_num}"
    return (
        w_int[0:13]
        + struct.pack(">dddd", 0.0, 0.0, float(w), float(h))
        + w_int[45:83]
        + struct.pack(">I", font_size)
        + w_int[87:106]
        + fg
        + w_int[117:148]
        + bg
        + w_int[159:181]
        + struct.pack(">dd", float(x), float(y))
        + bytes(mid1)
        + qstr(name_str)
        + edit_flag
        + qstr(reg_full)
        + qstr(reg_full)
        + w_int[777:780]
        + qstr(str(reg_num))
        + w_int[790:2116]
        + fg
        + qstr(bg_s)
        + w_int[2153:2183]
        + qstr(fg_s)
        + struct.pack(">I", font_size)
        + w_int[2201:2206]
        + struct.pack(">d", float(z_val))
    )


def build_write_button(
    x, y, w, h, label, font_size=28, reg_num=100, write_val=1,
    link_name="Modbus_RTU_COM1_1", reg_type="4x", idx=0, z_val=1030.0,
) -> bytes:
    """Synthesize a Type 0x26 word-write constant button widget."""
    reg_full = f"[{link_name}]{reg_type}{reg_num}"
    mid = bytearray(w_btn[302:864])
    struct.pack_into(">H", mid, 430 - 302, idx)
    struct.pack_into(">H", mid, 552 - 302, idx)
    return (
        w_btn[0:161]
        + struct.pack(">dddddd", float(x), float(y), float(w), float(h), float(x), float(y))
        + w_btn[209:222]
        + struct.pack(">dddd", float(x), float(y), float(w), float(h))
        + qstr(label)
        + w_btn[268:298]
        + struct.pack(">I", font_size)
        + bytes(mid)
        + qstr(label)
        + w_btn[878:1057]
        + qstr(str(write_val))
        + w_btn[1063:1067]
        + qstr(reg_full)
        + qstr(reg_full)
        + w_btn[1171:1174]
        + qstr(str(reg_num))
        + w_btn[1184:1437]
        + qstr(str(font_size))
        + w_btn[1445:1449]
        + qstr(label)
        + w_btn[1463:1537]
        + qstr(str(font_size))
        + w_btn[1545:1549]
        + qstr(label)
        + w_btn[1563:2006]
        + struct.pack(">d", float(z_val))
    )


def build_bit_button(
    x, y, w, h, label, bit_addr="163.0", font_size=22,
    link_name="Modbus_RTU_COM1_1", reg_type="4x_bit", idx=0, z_val=1030.0,
) -> bytes:
    """Synthesize a Type 0x38 bit-operation button widget (e.g. [Modbus_RTU_COM1_1]4x_bit163.0)."""
    reg_full = f"[{link_name}]{reg_type}{bit_addr}"
    mid = bytearray(w_bit_btn[300:868])
    struct.pack_into(">H", mid, 428 - 300, idx)
    struct.pack_into(">H", mid, 550 - 300, idx)
    # Zero out internal drag offset at 384..400
    struct.pack_into(">dd", mid, 384 - 300, 0.0, 0.0)
    return (
        w_bit_btn[0:161]
        + struct.pack(">dddddd", float(x), float(y), float(w), float(h), float(x), float(y))
        + w_bit_btn[209:222]
        + struct.pack(">dddd", float(x), float(y), float(w), float(h))
        + qstr(label)
        + w_bit_btn[266:296]
        + struct.pack(">I", font_size)
        + bytes(mid)
        + qstr(reg_full)
        + qstr(reg_full)
        + w_bit_btn[996:999]
        + qstr(str(bit_addr))
        + w_bit_btn[1013:1414]
        + qstr(str(font_size))
        + w_bit_btn[1422:1426]
        + qstr(label)
        + w_bit_btn[1438:1512]
        + qstr(str(font_size))
        + w_bit_btn[1520:1524]
        + qstr(label)
        + w_bit_btn[1536:1979]
        + struct.pack(">d", float(z_val))
    )


def build_jump_button(
    x, y, w, h, label, font_size=28, target_screen="000:画面1", target_screen_list_idx=None, idx=0, z_val=1031.0
) -> bytes:
    """Synthesize a Type 0x39 screen-jump button widget."""
    mid = bytearray(w_jmp[300:862])
    struct.pack_into(">H", mid, 428 - 300, idx)
    struct.pack_into(">H", mid, 550 - 300, idx)
    post_target = bytearray(w_jmp[905:1095])
    if target_screen_list_idx is not None:
        struct.pack_into(">I", post_target, 0, int(target_screen_list_idx))
    return (
        w_jmp[0:161]
        + struct.pack(">dddddd", float(x), float(y), float(w), float(h), float(x), float(y))
        + w_jmp[209:222]
        + struct.pack(">dddd", float(x), float(y), float(w), float(h))
        + qstr(label)
        + w_jmp[266:296]
        + struct.pack(">I", font_size)
        + bytes(mid)
        + qstr(label)
        + w_jmp[874:887]
        + qstr(target_screen)
        + bytes(post_target)
        + qstr(str(font_size))
        + w_jmp[1103:1107]
        + qstr(label)
        + w_jmp[1119:1193]
        + qstr(str(font_size))
        + w_jmp[1201:1205]
        + qstr(label)
        + w_jmp[1217:1660]
        + struct.pack(">d", float(z_val))
    )


def build_bit_lamp(
    x, y, w, h, state0_text="未到位", state1_text="已到位", bit_addr="172.0", font_size=20,
    link_name="Modbus_RTU_COM1_1", reg_type="4x_bit", idx=0, z_val=1020.0,
) -> bytes:
    """Synthesize a Type 0x51 2-state bit indicator lamp widget."""
    reg_full = f"[{link_name}]{reg_type}{bit_addr}"
    comment = f"{state0_text} / {state1_text}"
    mid = bytearray(w_bit_lamp[300:862])
    struct.pack_into(">H", mid, 428 - 300, idx)
    struct.pack_into(">H", mid, 550 - 300, idx)
    struct.pack_into(">dd", mid, 384 - 300, 0.0, 0.0)
    return (
        w_bit_lamp[0:161]
        + struct.pack(">dddddd", float(x), float(y), float(w), float(h), float(x), float(y))
        + w_bit_lamp[209:222]
        + struct.pack(">dddd", float(x), float(y), float(w), float(h))
        + qstr(state0_text)
        + w_bit_lamp[266:296]
        + struct.pack(">I", font_size)
        + bytes(mid)
        + qstr(comment)
        + qstr(reg_full)
        + qstr(reg_full)
        + w_bit_lamp[1016:1019]
        + qstr(str(bit_addr))
        + w_bit_lamp[1033:1158]
        + qstr(reg_full)
        + qstr(reg_full)
        + w_bit_lamp[1286:1289]
        + qstr(str(bit_addr))
        + w_bit_lamp[1303:1537]
        + qstr(str(font_size))
        + w_bit_lamp[1545:1549]
        + qstr(state0_text)
        + w_bit_lamp[1561:1635]
        + qstr(str(font_size))
        + w_bit_lamp[1643:1647]
        + qstr(state1_text)
        + w_bit_lamp[1659:2102]
        + struct.pack(">d", float(z_val))
    )


def build_screen(
    screen_no: str,
    screen_name: str,
    widgets: list[bytes],
    bg_rgb: tuple[int, int, int] = (197, 222, 255),
    width: float = 1024.0,
    height: float = 600.0,
) -> bytes:
    """Synthesize a complete user screen binary block (header + widget_count + concatenated widgets)."""
    bg = qcolor(*bg_rgb)
    # screen_hdr_tpl layout:
    #   0..16: 16 zero bytes
    #   16..32: >2d (width, height)
    #   32..54: bg QColor + fg QColor (22 bytes)
    #   54..90: fixed screen pre-header (36 bytes)
    #   90..104: QString('坑道1配置')
    #   104..114: QString('001')
    #   114..290: screen body metadata + 4x '000:画面1' + marker
    #   290..294: uint32_be(widget_count)
    hdr = (
        screen_hdr_tpl[0:16]
        + struct.pack(">dd", float(width), float(height))
        + bg
        + bg
        + screen_hdr_tpl[54:90]
        + qstr(screen_name)
        + qstr(screen_no)
        + screen_hdr_tpl[114:290]
        + struct.pack(">I", len(widgets))
    )
    return hdr + b"".join(widgets)


def build_widget_from_dict(wspec: dict, idx: int) -> bytes:
    """Build a single widget binary from a declarative dictionary specification."""
    wtype = wspec["type"]
    x, y, w, h = wspec["x"], wspec["y"], wspec["w"], wspec["h"]
    z = wspec.get("z", 1001.0 + idx)
    if wtype == "label":
        return build_label(
            x, y, w, h,
            text=wspec["text"],
            font_size=wspec.get("font_size", 24),
            bg_rgb=tuple(wspec.get("bg_rgb", [46, 125, 50])),
            fg_rgb=tuple(wspec.get("fg_rgb", [255, 255, 255])),
            idx=idx, z_val=z,
        )
    elif wtype == "numeric_1dec":
        return build_numeric_1dec(
            x, y, w, h,
            reg_num=wspec["reg_num"],
            name_str=wspec.get("name", "数值输入"),
            font_size=wspec.get("font_size", 30),
            bg_rgb=tuple(wspec.get("bg_rgb", [227, 242, 253])),
            fg_rgb=tuple(wspec.get("fg_rgb", [13, 71, 161])),
            editable=wspec.get("editable", True),
            link_name=wspec.get("link_name", "Modbus_RTU_COM1_1"),
            reg_type=wspec.get("reg_type", "4x"),
            idx=idx, z_val=z,
        )
    elif wtype == "numeric_int":
        return build_numeric_int(
            x, y, w, h,
            reg_num=wspec["reg_num"],
            name_str=wspec.get("name", "整数输入"),
            font_size=wspec.get("font_size", 24),
            bg_rgb=tuple(wspec.get("bg_rgb", [227, 242, 253])),
            fg_rgb=tuple(wspec.get("fg_rgb", [13, 71, 161])),
            editable=wspec.get("editable", True),
            link_name=wspec.get("link_name", "Modbus_RTU_COM1_1"),
            reg_type=wspec.get("reg_type", "4x"),
            idx=idx, z_val=z,
        )
    elif wtype == "write_button":
        return build_write_button(
            x, y, w, h,
            label=wspec["label"],
            font_size=wspec.get("font_size", 28),
            reg_num=wspec.get("reg_num", 100),
            write_val=wspec.get("write_val", 1),
            link_name=wspec.get("link_name", "Modbus_RTU_COM1_1"),
            reg_type=wspec.get("reg_type", "4x"),
            idx=idx, z_val=z,
        )
    elif wtype == "bit_button":
        return build_bit_button(
            x, y, w, h,
            label=wspec["label"],
            bit_addr=str(wspec["bit_addr"]),
            font_size=wspec.get("font_size", 22),
            link_name=wspec.get("link_name", "Modbus_RTU_COM1_1"),
            reg_type=wspec.get("reg_type", "4x_bit"),
            idx=idx, z_val=z,
        )
    elif wtype == "jump_button":
        return build_jump_button(
            x, y, w, h,
            label=wspec["label"],
            font_size=wspec.get("font_size", 28),
            target_screen=wspec.get("target_screen", "000:画面1"),
            target_screen_list_idx=wspec.get("target_screen_list_idx"),
            idx=idx, z_val=z,
        )
    elif wtype == "bit_lamp":
        return build_bit_lamp(
            x, y, w, h,
            state0_text=wspec.get("state0_text", "未到位"),
            state1_text=wspec.get("state1_text", "已到位"),
            bit_addr=str(wspec["bit_addr"]),
            font_size=wspec.get("font_size", 20),
            link_name=wspec.get("link_name", "Modbus_RTU_COM1_1"),
            reg_type=wspec.get("reg_type", "4x_bit"),
            idx=idx, z_val=z,
        )
    else:
        raise ValueError(f"Unsupported widget type: {wtype!r}")


def main():
    parser = argparse.ArgumentParser(description="Declarative HMI Screen & Widget Builder for USRHMIToolsProV1.0")
    parser.add_argument("--spec", required=True, help="Path to JSON screen spec file")
    parser.add_argument("--output-screen-bin", required=True, help="Output binary path for synthesized screen")
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    widgets = [build_widget_from_dict(w, idx) for idx, w in enumerate(spec["widgets"])]
    s_bin = build_screen(
        screen_no=spec["screen_no"],
        screen_name=spec["screen_name"],
        widgets=widgets,
        bg_rgb=tuple(spec.get("bg_rgb", [197, 222, 255])),
        width=spec.get("width", 1024.0),
        height=spec.get("height", 600.0),
    )
    Path(args.output_screen_bin).write_bytes(s_bin)
    print(f"Synthesized screen [{spec['screen_no']}:{spec['screen_name']}] with {len(widgets)} widgets ({len(s_bin):,} bytes)")


if __name__ == "__main__":
    main()
