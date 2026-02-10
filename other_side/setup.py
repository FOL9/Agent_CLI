import os
import stat
import subprocess
import platform
from pathlib import Path

SYSTEM = platform.system()
HOME = Path.home()
PROJECT_PATH = HOME / "agent" / "other_side"

print(f"🖥 Detected system: {SYSTEM}")

# =========================
# 🐧 LINUX / MACOS
# =========================
if SYSTEM in ("Linux", "Darwin"):
    BIN_PATH = HOME / "bin"
    v_FILE = BIN_PATH / "v"

    # 1️⃣ إنشاء ~/bin
    BIN_PATH.mkdir(parents=True, exist_ok=True)

    # 2️⃣ إنشاء أمر v
    with open(v_FILE, "w") as f:
        f.write(f"""#!/usr/bin/env bash

cd "{PROJECT_PATH}" || exit 1
exec source .venv/bin/activate

""")

    # 3️⃣ جعله قابل للتنفيذ
    v_FILE.chmod(v_FILE.stat().st_mode | stat.S_IXUSR)

    # 4️⃣ إضافة ~/bin إلى PATH
    bashrc_path = HOME / ".bashrc"
    if bashrc_path.exists():
        bashrc = bashrc_path.read_text()
    else:
        bashrc = ""

    export_line = 'export PATH="$HOME/bin:$PATH"'
    if export_line not in bashrc:
        with open(bashrc_path, "a") as f:
            f.write(f"\n{export_line}\n")

    print("✅ Linux setup complete! Restart terminal or run: source ~/.bashrc")
    print("👉 You can now run: v")


# =========================
# 🪟 WINDOWS
# =========================
elif SYSTEM == "Windows":
    BIN_PATH = HOME / "bin"
    v_FILE = BIN_PATH / "v.bat"

    # 1️⃣ إنشاء bin
    BIN_PATH.mkdir(parents=True, exist_ok=True)

    # 2️⃣ إنشاء v.bat
    with open(v_FILE, "w") as f:
        f.write(f"""@echo off
cd /d "{PROJECT_PATH}"
python main.py %*
""")

    # 3️⃣ إضافة bin إلى PATH (User PATH)
    current_path = os.environ.get("PATH", "")
    bin_str = str(BIN_PATH)

    if bin_str.lower() not in current_path.lower():
        subprocess.run(
            f'setx PATH "{bin_str};%PATH%"',
            shell=True
        )

    print("✅ Windows setup complete!")
    print("⚠ Restart terminal to apply PATH changes")
    print("👉 You can now run: v")


# =========================
# ❌ UNKNOWN SYSTEM
# =========================
else:
    print("❌ Unsupported operating system")
