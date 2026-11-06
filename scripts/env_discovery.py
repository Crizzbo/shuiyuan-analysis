r"""系统环境与外部工具动态发现工具库 (Environment & Executable Discovery).

消除硬编码绝对路径 (如 C:\Users\shared_user\... 与 C:\Program Files...)，
提供鲁棒的自适应探测逻辑与降级机制：
1. 优先读取环境变量 (GDRIVE_EXECUTABLE, EDGE_EXECUTABLE)；
2. 自动搜索用户目录下的 Antigravity 插件目录；
3. 搜索系统 PATH 与 Windows 常见安装目录；
4. 统一命令安全执行包装器 (带编码容错与超时保护)。
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess
from typing import List, Optional, Tuple


def get_gdrive_executable() -> Optional[str]:
    """动态探测 gdrive CLI 可执行文件路径。"""
    # 1. 显式环境变量覆盖 (支持 GDRIVE_EXECUTABLE 与 GDRIVE_EXE)
    env_path = os.getenv("GDRIVE_EXECUTABLE") or os.getenv("GDRIVE_EXE")
    if env_path and Path(env_path).is_file():
        return str(Path(env_path).resolve())

    # 2. 探测当前用户 Antigravity gdrive 插件路径
    home = Path.home()
    plugin_bin_dir = home / ".gemini" / "antigravity" / "plugin_data" / "gdrive" / "bin"
    if plugin_bin_dir.is_dir():
        candidates = list(plugin_bin_dir.glob("gdrive*.exe"))
        if candidates:
            # 选最新修改的
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return str(candidates[0].resolve())

    # 3. 探测系统 PATH
    which_path = shutil.which("gdrive")
    if which_path:
        return str(Path(which_path).resolve())

    return None


def get_edge_executable() -> Optional[str]:
    """动态探测 Microsoft Edge 或兼容 Chromium 浏览器路径以渲染 PDF。"""
    # 1. 显式环境变量覆盖 (支持 EDGE_EXECUTABLE 与 EDGE_EXE)
    env_path = os.getenv("EDGE_EXECUTABLE") or os.getenv("EDGE_EXE")
    if env_path and Path(env_path).is_file():
        return str(Path(env_path).resolve())

    # 2. 常见 Windows 安装位置
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c.resolve())

    # 3. 探测系统 PATH
    for name in ("msedge", "chrome", "chromium"):
        which_path = shutil.which(name)
        if which_path:
            return str(Path(which_path).resolve())

    return None


def get_python_executable() -> str:
    """动态探测优先使用项目内部 .venv 的 Python 解释器，避免外部环境 ABI 损坏。"""
    # 1. 显式环境变量覆盖
    env_py = os.getenv("PYTHON_EXECUTABLE")
    if env_py and Path(env_py).is_file():
        return str(Path(env_py).resolve())

    # 2. 优先项目根目录下的 .venv 虚拟环境
    root = Path(__file__).resolve().parents[1]
    venv_win = root / ".venv" / "Scripts" / "python.exe"
    if venv_win.is_file():
        return str(venv_win.resolve())
    venv_posix = root / ".venv" / "bin" / "python"
    if venv_posix.is_file():
        return str(venv_posix.resolve())

    # 3. 降级为当前 sys.executable
    import sys
    return sys.executable


def run_cmd(args: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """跨平台统一命令执行包装，提供 UTF-8 编码与 replace 容错，自动重定向 python 到项目内部解释器。"""
    final_args = list(args)
    if final_args and final_args[0] in ("python", "python3"):
        final_args[0] = get_python_executable()

    return subprocess.run(
        final_args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )

