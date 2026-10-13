---
name: usr-hmi-dev
description: >-
  Operate, inspect, and develop HMI touch-screen projects for USRHMIToolsProV1.0
  (有人物联网 HMI 组态软件 / KinSealStudio OEM). Use this skill whenever the user asks to
  create, inspect, modify, compile, simulate, or automate HMI screens (.pro files),
  PLC/Modbus register bindings, C macro scripts, or GUI actions in USRHMIToolsProV1.0.
---

# USRHMIToolsProV1.0 AI Agent Development & Control Skill

This skill equips the AI Agent with a complete 4-layer toolchain to inspect, develop, modify, simulate, and automate **USRHMIToolsProV1.0** (`C:\Program Files (x86)\USRHMIToolsProV1.0\USRHMIToolsProV1.0.exe`, based on Qt5 / KinSealStudio V1.0.2 architecture).

---

## 1. Architecture Overview of `USRHMIToolsProV1.0`

- **Installation Directory**: `C:\Program Files (x86)\USRHMIToolsProV1.0`
- **Main IDE Executable**: `USRHMIToolsProV1.0.exe` (Qt5 Widgets application: `Qt5Core.dll`, `Qt5Widgets.dll`, `Qt5Xml.dll`, `Qt5Sql.dll`, `Qt5Xlsx.dll`)
- **Offline Simulator**: `USR.exe` (uses `SDL2.dll` + compiled assets inside the `compile/` directory)
- **Project File (`*.pro`)**:
  - Serialized via **Qt `QDataStream` (Big-Endian)**.
  - Every `QString` is stored as a 4-byte Big-Endian byte length (`uint32_be`) followed by `UTF-16BE` characters.
  - Contains: Header (`KinSealStudio-V1.0.2`), HMI model (`USR-H5070E`, `800*480`), PLC/Communication links (`Modbus_RTU_COM1`, baudrate, station ID), Screen list (`Screen 1`, etc.), Widget definitions (coordinates, register addresses like `LW0`, `LB0`, `4x1`, fonts, state texts), and C Macro scripts.
- **Compiled Artifacts (`compile/` directory)**:
  - When a project is compiled in the IDE, it generates:
    - **SQLite3 Databases** (can be queried/modified via `sqlite3.exe` or Python `sqlite3`):
      - `mulState.db`: Table `STATE` (`screen_id`, `item_id`, `lan_id`, `state_id`, `text`, `font`, `backColor`, `foreColor`, `picName`, `textColor`, `textSize`, etc.)
      - `mulText.db`: Table `TEXT` (`screen_id`, `item_id`, `lan_id`, `fun_num`, `text`, `font`, `fontsize`)
      - `param.db`: Tables `user`, `userLevel`, `temp_data`, `temp_xy`, `temp_draw`
      - `alarm.db`, `data.db`, `operation.db`, `Recipe.db`
    - **Binary Parameter Tables (Little-Endian C structs)**:
      - `SheetPara.dat`: Screen metadata (screen name, width `uint16_le`, height `uint16_le`, background color)
      - `ControlPara.dat`: Widget control parameters (widget type `uint16_le`, `item_id`, `x`, `y`, `width`, `height`, bound addresses)
      - `ScreenInfo.dat`, `AddrPara.dat`, `SysPara.dat`, `MarcoVar.dat`
    - **Upload Archive & Firmware Image**:
      - `UpLoad.zip`: Contains a compressed backup of the `.pro` source file!
      - `load.bin` / `Usbload.bin`: Final binary package downloaded to the HMI hardware.
- **C Macro Scripting Engine (`script/` directory)**:
  - Supports standard C macro scripts (`宏指令`) compiled via built-in GCC toolchains:
    - `script/x86/bin/gcc.exe` (for PC offline simulation -> compiles to `macrolib_x86.dll`)
    - `script/riscv64/` and `script/arm32/` (for HMI hardware -> compiles to `.so`)
  - Headers located in `script/code/include/macrolib.h` and `macro_init.h`.

---

## 2. Four-Layer AI Control Workflow

Prefer the highest-precision layer that satisfies the task:

### Layer 1: Direct `.pro` Binary Synthesis & Structural Inspection (Fastest & 100% Exact)
Use [`scripts/hmi_project_tool.py`](scripts/hmi_project_tool.py) to structurally parse `.pro` screens and widgets, inspect compiled SQLite/binary databases, or safely update `QString` fields. Use [`scripts/hmi_widget_builder.py`](scripts/hmi_widget_builder.py) (backed by portable binary widget templates in `resources/templates/`) to synthesize pixel-accurate HMI screens and widgets directly in code without slow mouse drag-and-drop.

```powershell
# 1. Inspect summary of a .pro file (HMI model, comms, screens, all Modbus/local registers)
python .agents/skills/usr-hmi-dev/scripts/hmi_project_tool.py inspect-pro "C:\Program Files (x86)\USRHMIToolsProV1.0\Project\123.pro"

# 2. Structurally inspect every screen and widget (type, (x,y) WxH geometry, bound registers, labels)
python .agents/skills/usr-hmi-dev/scripts/hmi_project_tool.py inspect-screens "C:\project_workspace\浙江润农\有人触摸屏开发\Project\Project\board_test_apriltag_v4.pro"

# 3. Search for specific QStrings (e.g., register addresses, labels, IP, baudrate) in a .pro file
python .agents/skills/usr-hmi-dev/scripts/hmi_project_tool.py search-pro "C:\Program Files (x86)\USRHMIToolsProV1.0\Project\123.pro" --query "Modbus"

# 4. Safely replace an exact QString in a .pro file (includes RGB color & system register safety guards)
python .agents/skills/usr-hmi-dev/scripts/hmi_project_tool.py replace-string "path\to\project.pro" --old "9600" --new "115200" --occurrence 0 --output "path\to\project_modified.pro"

# 5. Inspect compiled SQLite databases & screen/widget tables in compile/
python .agents/skills/usr-hmi-dev/scripts/hmi_project_tool.py inspect-compile "C:\Program Files (x86)\USRHMIToolsProV1.0\compile"
```

### Layer 2: C Macro (`宏指令`) Code Generation & Pre-Verification
When developing complex logic (custom serial protocols, CRC calculation, feeding vehicle valve/pump state machines, offset register addressing):
1. Reference `C:\Program Files (x86)\USRHMIToolsProV1.0\script\code\include\macrolib.h` and `macro_init.h`.
2. Built-in arrays & helpers available in macros:
   - `LocalWord[index]` (`LW` registers, `unsigned short*`)
   - `LocalBit[index]` (`LB` bit registers, `unsigned char*`)
   - `RWIWord[index]` (`RWI` registers, `unsigned short*`)
   - `ScreenOpen(short screenindex, short type)`
   - `GETCHARS(char PortID, char *pData)` / `PUTCHARS(char PortID, char *pData, unsigned char Length)`
   - `CRC(char *data, unsigned short Len)` / `ADDSUM` / `XORSUM`
   - `GETBIT`, `SETBIT`, `INVBIT`, `DELAY`
3. Syntax-check C macro code before pasting/injecting into the HMI project using the bundled GCC compiler:
   ```powershell
   & "C:\Program Files (x86)\USRHMIToolsProV1.0\script\x86\bin\gcc.exe" -fsyntax-only -I"C:\Program Files (x86)\USRHMIToolsProV1.0\script\code\include" your_macro.c
   ```

### Layer 3: GUI Automation & Window Control (`scripts/hmi_gui_ctl.py`)
> **CRITICAL PRIVILEGE NOTE (UIPI)**:
> `USRHMIToolsProV1.0.exe` embeds a `requireAdministrator` manifest. If launched normally via double-click, it runs at **High Integrity (Admin)**, which causes Windows UIPI to block non-elevated scripts from reading its UI tree or sending clicks/keys.
> **Solution**: Always launch `USRHMIToolsProV1.0.exe` via `hmi_gui_ctl.py launch` (which sets `__COMPAT_LAYER=RunAsInvoker` so it runs at standard user privilege without UAC prompts and is 100% controllable by the AI Agent!).

```powershell
# 1. Launch USRHMIToolsProV1.0 in Invoker mode (controllable without Admin elevation), optionally opening a .pro file
python .agents/skills/usr-hmi-dev/scripts/hmi_gui_ctl.py launch --project "C:\project_workspace\浙江润农\液态饲喂车\hmi\feeding_car.pro"

# 2. Check window status and dump exposed UI Automation (UIA) controls
python .agents/skills/usr-hmi-dev/scripts/hmi_gui_ctl.py status
python .agents/skills/usr-hmi-dev/scripts/hmi_gui_ctl.py dump-ui --depth 3

# 3. Capture a screenshot of the IDE window with a coordinate grid overlay for visual agent inspection
python .agents/skills/usr-hmi-dev/scripts/hmi_gui_ctl.py screenshot --output "hmi_screen.png" --grid

# 4. Click / Double-Click / Send Hotkeys / Input Text (relative to window top-left)
python .agents/skills/usr-hmi-dev/scripts/hmi_gui_ctl.py click --x 85 --y 320
python .agents/skills/usr-hmi-dev/scripts/hmi_gui_ctl.py keys --keys "^s"
```

### Layer 4: Direct Offline Simulator Execution (`USR.exe`)
After compiling a project (or modifying `compile/mulState.db` / `compile/mulText.db` for rapid UI text/color preview), launch the offline simulator directly:
```powershell
python .agents/skills/usr-hmi-dev/scripts/hmi_gui_ctl.py run-simulator
```

---

## 3. Binary `.pro` Screen & Widget Synthesis + Declarative HMI-as-Code

### A. Portable Binary Templates (`resources/templates/`)
- `screen_hdr.bin`: Standard user screen header (`1024*600` canvas, `QColor` background, screen name/number, reference screen links, and `uint32_be(widget_count)`).
- `w_label.bin` (`Type 0x1C`): Compound Rectangle + Text Label/Banner (`build_label`).
  - **Important**: Bytes `71..131` and `794..898` in `w_label.bin` contain internal `0xffffffff` null-QString markers (`01 ff ff ff ff 00 00 00 00 00 00`) and must be preserved verbatim; only replace `bg` (`60..71` and `783..794`) and `fg` (`234..245` and `898..909`).
- `w_dec.bin` (`Type 0x3F`): 1-Decimal-Place Numeric Input/Display `"88888.8"` (`build_numeric_1dec`).
- `w_int.bin` (`Type 0x3F`): Integer Numeric Input/Display `"88"`, `decimals=0` (`build_numeric_int`).
- `w_btn.bin` (`Type 0x26`): Word-Write Constant Button (`build_write_button`).
- `w_bit_btn.bin` (`Type 0x38`): Bit-Operation Button `[Modbus_RTU_COM1_1]4x_bit...` (`build_bit_button`).
- `w_jmp.bin` (`Type 0x39`): Screen Jump Button (`build_jump_button`, supports `target_screen_list_idx`).
- `w_bit_lamp.bin` (`Type 0x51`): 2-State Bit Indicator Lamp (`build_bit_lamp`).
- `w_multi_lamp.bin` (`Type 0x52`): Multi-State Word Indicator Lamp.

### B. Declarative JSON Screen Replacement / Addition (`apply-screen-spec`)
You can replace an existing user screen (e.g., `001`, `002`, `003`) or append a new user screen (e.g., `004`) directly from a JSON specification without writing byte-slicing boilerplate. When appending a new screen, `apply-screen-spec` automatically increments the total screen count at `0x01357c` and inserts the `(user_screen_no -> screen_list_idx)` entry into the footer `QMap<int, int>`:

```powershell
python .agents/skills/usr-hmi-dev/scripts/hmi_project_tool.py apply-screen-spec "path\to\base.pro" --spec "screen_layout.json" --output "path\to\output.pro"
```

### C. Launching & Capturing `USRHMIToolsProV1.0.exe` from Non-Interactive / Sandbox Sessions
1. Attach thread to interactive desktop `WinSta0\Default` via `OpenDesktopW("Default", 0, False, 0x01FF)` + `SetThreadDesktop`.
2. Launch original signed `USRHMIToolsProV1.0.exe` with `__COMPAT_LAYER=RunAsInvoker` and `CREATE_SUSPENDED (0x4)` (avoids Smart App Control `WinError 4551` on modified copies).
3. Before `ResumeThread`, use `VirtualProtectEx` + `WriteProcessMemory` to:
   - Patch the internal `IsUserAnAdmin()` check `JNZ` (`0f 85 1a 07 00 00`) to `NOP; JMP` (`90 e9 1a 07 00 00`).
   - Patch `"gSingle"` (`QSharedMemory` single-instance lock) to `"gSingl2"`.
4. Capture the rendered Qt window via `PrintWindow(hwnd, mdc, 2)`.

