# usr-hmi-dev — AI Agent Skill for USRHMIToolsProV1.0 (有人物联网触摸屏组态软件)

An AI Agent Skill & Binary `.pro` Synthesis Toolchain for **USRHMIToolsProV1.0** (KinSealStudio V1.0.2 OEM HMI IDE).

Instead of relying on fragile mouse drag-and-drop GUI automation to draw HMI screens, `usr-hmi-dev` combines **direct Qt `QDataStream` (`.pro`) binary screen/widget synthesis** with **in-memory Admin/SingleInstance bypass & visual capture**, enabling AI Agents to inspect, build, and verify industrial touch-screen interfaces in milliseconds.

---

## Key Features

1. **Direct `.pro` Binary Screen & Widget Synthesis (`scripts/hmi_widget_builder.py`)**
   - Built on 9 portable binary templates (`resources/templates/`) with zero external path dependencies:
     - `build_label` (`Type 0x1C`): Compound Rectangle + Text Label/Banner
     - `build_numeric_1dec` (`Type 0x3F`): 1-Decimal-Place Numeric Input / Display (`"88888.8"`)
     - `build_numeric_int` (`Type 0x3F`): Integer Numeric Input / Display (`"88"`, `decimals=0`)
     - `build_write_button` (`Type 0x26`): Word-Write Constant Button (`[Modbus_RTU_COM1_1]4x...`)
     - `build_bit_button` (`Type 0x38`): Bit-Operation Button (`[Modbus_RTU_COM1_1]4x_bit...`)
     - `build_jump_button` (`Type 0x39`): Screen Jump Button (`000:画面1`, etc.)
     - `build_bit_lamp` (`Type 0x51`): 2-State Bit Indicator Lamp
     - `build_screen`: Synthesizes a complete screen header + widget array block
2. **Structural `.pro` AST Parser & Declarative HMI-as-Code (`scripts/hmi_project_tool.py`)**
   - `inspect-pro`: Extract HMI model, communication links, screen list, and all referenced Modbus/local registers.
   - `inspect-screens`: Parse every screen and widget with exact `(x, y) WxH` geometry, widget type, register bindings, and text labels.
   - `apply-screen-spec`: Compile a declarative JSON screen specification directly into an existing `.pro` file (replaces an existing screen or appends a new screen while updating the footer `QMap<int, int>` screen table).
   - `replace-string`: Safely update `QString` entries with automatic `uint32_be` UTF-16BE length recalculation and RGB color string protection.
   - `inspect-compile`: Inspect compiled `mulState.db`, `mulText.db`, `SheetPara.dat`, and `ControlPara.dat`.
3. **GUI Automation & Sandbox-Safe IDE Launcher (`scripts/hmi_gui_ctl.py`)**
   - Launches `USRHMIToolsProV1.0.exe` on `WinSta0\Default` with `__COMPAT_LAYER=RunAsInvoker` and in-memory patches (`IsUserAnAdmin` check + `gSingle` shared-memory lock bypass) so AI Agents can open `.pro` projects and capture rendered screenshots via `PrintWindow` without UAC elevation blocks.

---

## Directory Structure

```text
usr-hmi-dev/
├── SKILL.md                        # AI Agent skill instructions & binary format reference
├── README.md                       # Repository documentation
├── examples/
│   └── apriltag_screen_spec.json   # Example declarative JSON screen layout (4x4 AprilTag feeding grid)
├── resources/
│   └── templates/                  # Portable binary templates for screen & widget synthesis
│       ├── screen_hdr.bin
│       ├── w_label.bin
│       ├── w_dec.bin
│       ├── w_int.bin
│       ├── w_btn.bin
│       ├── w_bit_btn.bin
│       ├── w_jmp.bin
│       ├── w_bit_lamp.bin
│       └── w_multi_lamp.bin
└── scripts/
    ├── hmi_project_tool.py         # .pro parser, structural screen inspector & JSON spec compiler
    ├── hmi_widget_builder.py       # QDataStream binary screen & widget synthesizer
    └── hmi_gui_ctl.py              # USRHMIToolsProV1.0 process launcher, screenshot & hotkey controller
```

---

## Quick Start

### 1. Install as an AI Agent Skill
Clone this repository into your workspace or global skills folder:
```bash
git clone https://github.com/xychenzhicheng/usr-hmi-dev.git .agents/skills/usr-hmi-dev
```

### 2. Inspect an Existing `.pro` Project
```powershell
python .agents/skills/usr-hmi-dev/scripts/hmi_project_tool.py inspect-pro "path\to\project.pro"
python .agents/skills/usr-hmi-dev/scripts/hmi_project_tool.py inspect-screens "path\to\project.pro"
```

### 3. Build or Replace a Screen from a Declarative JSON Spec
```powershell
python .agents/skills/usr-hmi-dev/scripts/hmi_project_tool.py apply-screen-spec "path\to\base.pro" `
  --spec ".agents/skills/usr-hmi-dev/examples/apriltag_screen_spec.json" `
  --output "path\to\output.pro"
```

### 4. Launch in `USRHMIToolsProV1.0` & Capture Verification Screenshot
```powershell
python .agents/skills/usr-hmi-dev/scripts/hmi_gui_ctl.py launch --project "path\to\output.pro"
python .agents/skills/usr-hmi-dev/scripts/hmi_gui_ctl.py screenshot --output "preview.png" --grid
```
