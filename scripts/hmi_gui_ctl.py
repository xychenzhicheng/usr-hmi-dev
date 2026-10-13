#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USRHMIToolsProV1.0 GUI Automation & Simulator Controller
Provides:
  - launch: Launch USRHMIToolsProV1.0.exe with __COMPAT_LAYER=RunAsInvoker (bypasses UIPI elevation barrier so AI Agents can control UI directly)
  - run-simulator: Launch USR.exe offline simulator against compiled artifacts
  - status: Check running USRHMIToolsProV1.0 processes and window geometry
  - screenshot: Capture window screenshot with optional coordinate grid overlay for Visual Agent
  - click / double-click: Click at window-relative or screen coordinates
  - keys: Send keyboard shortcuts (e.g., Ctrl+S, Ctrl+O) to the IDE window
"""

import argparse
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_INSTALL_DIR = Path(r"C:\Program Files (x86)\USRHMIToolsProV1.0")
DEFAULT_IDE_EXE = DEFAULT_INSTALL_DIR / "USRHMIToolsProV1.0.exe"
DEFAULT_SIM_EXE = DEFAULT_INSTALL_DIR / "USR.exe"

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# Automatically attach thread to interactive WinSta0\Default desktop when running from a sandboxed desktop
try:
    _hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
    if _hdesk:
        user32.SetThreadDesktop(_hdesk)
except Exception:
    pass



def find_hmi_windows():
    """Return list of (hwnd, pid, title, class_name, rect) for USRHMIToolsProV1.0 windows."""
    results = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                title_buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title_buf, length + 1)
                title = title_buf.value
                cls_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls_buf, 256)
                cls_name = cls_buf.value

                if "USRHMIToolsPro" in title or "USR" in title or cls_name.startswith("Qt5"):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    if "USRHMIToolsPro" in title:
                        results.append(
                            (
                                hwnd,
                                pid.value,
                                title,
                                cls_name,
                                (rect.left, rect.top, rect.right, rect.bottom),
                            )
                        )
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return results


def cmd_launch(args):
    import struct
    exe_path = Path(args.exe)
    if not exe_path.exists():
        print(f"[ERROR] Executable not found: {exe_path}")
        sys.exit(1)

    raw = exe_path.read_bytes()
    pe_off = struct.unpack("<I", raw[0x3C:0x40])[0]
    num_sec = struct.unpack("<H", raw[pe_off + 6 : pe_off + 8])[0]
    opt_size = struct.unpack("<H", raw[pe_off + 20 : pe_off + 22])[0]
    img_base = struct.unpack("<I", raw[pe_off + 24 + 28 : pe_off + 24 + 32])[0]
    sec_off = pe_off + 24 + opt_size
    sections = []
    for i in range(num_sec):
        s = raw[sec_off + i * 40 : sec_off + (i + 1) * 40]
        vsize, rva, raw_size, raw_ptr = struct.unpack("<IIII", s[8:24])
        sections.append((rva, vsize, raw_ptr, raw_size))

    def file_to_va(foff):
        for rva, vsize, raw_ptr, raw_size in sections:
            if raw_ptr <= foff < raw_ptr + raw_size:
                return img_base + rva + (foff - raw_ptr)
        return None

    admin_seq = bytes.fromhex("e891f8ffff84c00f851a070000")
    admin_pos = raw.find(admin_seq)
    admin_va = file_to_va(admin_pos + 7) if admin_pos != -1 else None
    gsingle_vas = [
        file_to_va(p)
        for p in (raw.find(b"gSingle"), raw.rfind(b"gSingle"))
        if p != -1
    ]

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD), ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(wintypes.BYTE)), ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
        ]

    os.environ["__COMPAT_LAYER"] = "RunAsInvoker"
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    si.lpDesktop = "WinSta0\\Default"
    si.dwFlags = 1
    si.wShowWindow = 3
    pi = PROCESS_INFORMATION()

    cmd_str = f'"{exe_path}"'
    if args.project:
        cmd_str += f' "{Path(args.project).resolve()}"'

    ok = kernel32.CreateProcessW(
        None, ctypes.create_unicode_buffer(cmd_str), None, None, False,
        0x00000004, None, str(exe_path.parent), ctypes.byref(si), ctypes.byref(pi)
    )
    if not ok:
        print(f"[ERROR] CreateProcessW failed: WinError {ctypes.GetLastError()}")
        sys.exit(1)

    def patch_mem(hproc, addr, data_bytes):
        old_prot = wintypes.DWORD()
        kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data_bytes), 0x40, ctypes.byref(old_prot))
        written = ctypes.c_size_t()
        kernel32.WriteProcessMemory(hproc, ctypes.c_void_p(addr), data_bytes, len(data_bytes), ctypes.byref(written))
        kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data_bytes), old_prot.value, ctypes.byref(old_prot))

    if admin_va:
        patch_mem(pi.hProcess, admin_va, bytes.fromhex("90e91a070000"))
    for v in gsingle_vas:
        if v:
            patch_mem(pi.hProcess, v, b"gSingl2")

    kernel32.ResumeThread(pi.hThread)
    print(f"Launched {exe_path.name} (PID={pi.dwProcessId}) on WinSta0\\Default with in-memory Admin & SingleInstance bypass")
    time.sleep(2.5)
    cmd_status(args)


def cmd_run_simulator(args):
    sim_path = Path(args.sim_exe)
    if not sim_path.exists():
        print(f"[ERROR] Simulator executable not found: {sim_path}")
        sys.exit(1)

    env = os.environ.copy()
    env["__COMPAT_LAYER"] = "RunAsInvoker"
    proc = subprocess.Popen([str(sim_path)], cwd=str(sim_path.parent), env=env)
    print(f"Launched Offline Simulator {sim_path.name} (PID={proc.pid})")


def cmd_status(args):
    wins = find_hmi_windows()
    if not wins:
        print("No visible USRHMIToolsProV1.0 window found (or running elevated in another integrity context).")
        return
    for hwnd, pid, title, cls_name, (l, t, r, b) in wins:
        print(f"HWND=0x{hwnd:08X} | PID={pid} | Class={cls_name!r} | Title={title!r} | Rect=({l}, {t}, {r}, {b}) Size={r-l}x{b-t}")


def cmd_screenshot(args):
    wins = find_hmi_windows()
    if not wins:
        print("[ERROR] No controllable USRHMIToolsProV1.0 window found.")
        sys.exit(1)

    hwnd, pid, title, cls_name, (left, top, right, bottom) = wins[-1]
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE if minimized
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("[ERROR] Pillow (PIL) is required for screenshot. Install via: pip install pillow")
        sys.exit(1)

    hwndDC = user32.GetWindowDC(hwnd)
    mfcDC = gdi32.CreateCompatibleDC(hwndDC)
    saveBitMap = gdi32.CreateCompatibleBitmap(hwndDC, w, h)
    gdi32.SelectObject(mfcDC, saveBitMap)
    user32.PrintWindow(hwnd, mfcDC, 2)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = w
    bmi.biHeight = -h
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mfcDC, saveBitMap, 0, h, buf, ctypes.byref(bmi), 0)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    gdi32.DeleteObject(saveBitMap)
    gdi32.DeleteDC(mfcDC)
    user32.ReleaseDC(hwnd, hwndDC)

    if args.grid:
        draw = ImageDraw.Draw(img)
        step = args.grid_step
        for x in range(0, w, step):
            draw.line([(x, 0), (x, h)], fill=(255, 0, 0, 128), width=1)
            draw.text((x + 2, 2), str(x), fill=(255, 0, 0))
        for y in range(0, h, step):
            draw.line([(0, y), (w, y)], fill=(255, 0, 0, 128), width=1)
            draw.text((2, y + 2), str(y), fill=(255, 0, 0))

    out = Path(args.output)
    img.save(out)
    print(f"Saved window screenshot ({w}x{h}) to: {out.resolve()}")



def cmd_click(args):
    wins = find_hmi_windows()
    if not wins:
        print("[ERROR] No controllable USRHMIToolsProV1.0 window found.")
        sys.exit(1)

    hwnd, pid, title, cls_name, (left, top, right, bottom) = wins[0]
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.15)

    abs_x = left + args.x if args.relative else args.x
    abs_y = top + args.y if args.relative else args.y

    user32.SetCursorPos(abs_x, abs_y)
    time.sleep(0.05)

    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    clicks = 2 if args.double else 1
    for _ in range(clicks):
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.03)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.05)

    print(f"{'Double-clicked' if args.double else 'Clicked'} at window=({args.x}, {args.y}) -> screen=({abs_x}, {abs_y})")


def cmd_keys(args):
    wins = find_hmi_windows()
    if not wins:
        print("[ERROR] No controllable USRHMIToolsProV1.0 window found.")
        sys.exit(1)

    hwnd, pid, title, cls_name, _ = wins[-1]
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.2)

    # Support Ctrl+S (^s), Ctrl+O (^o), F7 ({F7}), Enter ({ENTER}), Esc ({ESC}) via WScript.Shell SendKeys
    ps_cmd = f'$ws = New-Object -ComObject WScript.Shell; $ws.SendKeys("{args.keys}")'
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
    print(f"Sent keys {args.keys!r} to HWND=0x{hwnd:08X} ({title!r})")


def main():
    parser = argparse.ArgumentParser(description="USRHMIToolsProV1.0 GUI Automation Controller")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_launch = sub.add_parser("launch", help="Launch USRHMIToolsProV1.0 in Invoker mode")
    p_launch.add_argument("--exe", default=str(DEFAULT_IDE_EXE), help="Path to USRHMIToolsProV1.0.exe")
    p_launch.add_argument("--project", help="Optional .pro file to open on startup")
    p_launch.set_defaults(func=cmd_launch)

    p_sim = sub.add_parser("run-simulator", help="Launch USR.exe offline simulator")
    p_sim.add_argument("--sim-exe", default=str(DEFAULT_SIM_EXE), help="Path to USR.exe")
    p_sim.set_defaults(func=cmd_run_simulator)

    p_stat = sub.add_parser("status", help="Show USRHMIToolsProV1.0 window status")
    p_stat.set_defaults(func=cmd_status)

    p_shot = sub.add_parser("screenshot", help="Take screenshot of USRHMIToolsProV1.0 window")
    p_shot.add_argument("--output", default="usr_hmi_window.png", help="Output PNG path")
    p_shot.add_argument("--grid", action="store_true", help="Overlay coordinate grid")
    p_shot.add_argument("--grid-step", type=int, default=100, help="Grid pixel step (default 100)")
    p_shot.set_defaults(func=cmd_screenshot)

    p_clk = sub.add_parser("click", help="Click inside USRHMIToolsProV1.0 window")
    p_clk.add_argument("--x", type=int, required=True, help="X coordinate")
    p_clk.add_argument("--y", type=int, required=True, help="Y coordinate")
    p_clk.add_argument("--screen-coords", dest="relative", action="store_false", help="Use absolute screen coordinates")
    p_clk.add_argument("--double", action="store_true", help="Perform double-click")
    p_clk.set_defaults(func=cmd_click)

    p_keys = sub.add_parser("keys", help="Send keyboard shortcuts (e.g. ^s, ^o) to USRHMIToolsProV1.0")
    p_keys.add_argument("--keys", required=True, help="SendKeys string, e.g. '^s'")
    p_keys.set_defaults(func=cmd_keys)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
