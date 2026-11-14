import subprocess
import sys
from pathlib import Path

def main():
    web_dir = Path(__file__).resolve().parent.parent / "web"
    print(f"Building React app in {web_dir}...")
    cmd = ["npm.cmd", "run", "build"] if sys.platform == "win32" else ["npm", "run", "build"]
    ret = subprocess.run(cmd, cwd=str(web_dir), capture_output=True, text=True, encoding="utf-8", errors="replace", shell=True)
    print("STDOUT:\n", ret.stdout.encode("ascii", "replace").decode("ascii"))
    if ret.stderr:
        print("STDERR:\n", ret.stderr.encode("ascii", "replace").decode("ascii"))
    sys.exit(ret.returncode)

if __name__ == "__main__":
    main()
