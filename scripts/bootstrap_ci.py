"""创建项目内 Python 3.10 验证环境并安装固定依赖。"""

import os
from pathlib import Path
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """隔离安装依赖，最后核对包之间的依赖约束。"""
    if sys.version_info[:2] != (3, 10):
        print("请使用 Python 3.10 运行此验证环境初始化入口", file=sys.stderr)
        return 1
    destination = ROOT / ".venv-ci"
    executable = destination / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        venv.EnvBuilder(with_pip=True).create(destination)
    environment = dict(os.environ)
    environment["PIP_CONFIG_FILE"] = os.devnull
    environment["PIP_NO_INPUT"] = "1"
    installation = subprocess.run(
        [str(executable), "-m", "pip", "--disable-pip-version-check", "install",
         "--index-url", "https://pypi.org/simple", "--cache-dir", str(ROOT / ".cache/pip"),
         "-r", str(ROOT / "requirements-ci.lock.txt")],
        cwd=ROOT, env=environment, check=False,
    )
    if installation.returncode:
        return installation.returncode
    return subprocess.run(
        [str(executable), "-m", "pip", "check"], cwd=ROOT, env=environment, check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
