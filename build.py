import subprocess
import os

scripts = ["server.py", "user.py"]
ICON_FOLDER = os.path.join(os.getcwd(),"icons")

for script in scripts:
    print(f"Building {script}...")
    iconName = script.split(".py")[0] + ".ico"
    subprocess.run([
        "pyinstaller",
        "--onefile",
        # ignored on Linux
        f"--icon={os.path.join(ICON_FOLDER, iconName)}",
        script
    ])
