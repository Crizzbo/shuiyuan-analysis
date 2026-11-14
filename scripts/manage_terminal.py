# -*- coding: utf-8 -*-
"""水源分析终端统一进程管理中枢 (WaterSource Terminal Process Manager).

功能定位：
1. 单一事实来源 (SSOT) 管理水源分析终端的前后台生命周期 (启动/停止/重启/健康检查)；
2. 彻底解决多进程残留、端口被占、SQLite 任务锁假死与僵尸进程问题；
3. 纯 Python 标准库驱动，零第三方 pip 依赖，Windows / POSIX 原生双平台兼容；
4. 启动后自动前置探测健康检查端点 (`/api/health`) 断言，保证真实服务就绪。
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request
import webbrowser

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / ".cache" / "terminal"
PID_FILE = CACHE_DIR / "server.pid"
SERVE_SCRIPT = PROJECT_ROOT / "scripts" / "serve_watersource_terminal.py"
LOG_FILE = CACHE_DIR / "terminal_server.log"
DEFAULT_PORT = 8765
DEFAULT_HOST = "127.0.0.1"


def is_port_in_use(port: int, host: str = DEFAULT_HOST) -> bool:
    """探测指定本地 TCP 端口是否被监听占用."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            return s.connect_ex((host, port)) == 0
        except Exception:
            return False


def is_pid_alive(pid: int) -> bool:
    """检测指定 PID 是否仍在运行."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            return str(pid) in res.stdout
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def find_terminal_pids(port: int = DEFAULT_PORT) -> List[int]:
    """全盘扫描并识别与终端服务相关的进程 PID 集合 (依据 PID 文件、命令行特征及端口持有者)."""
    pids = set()

    # 1. 读取记录的 PID 文件
    if PID_FILE.exists():
        try:
            val = int(PID_FILE.read_text(encoding="utf-8").strip())
            if is_pid_alive(val):
                pids.add(val)
        except Exception:
            pass

    # 2. Windows 平台：深度检测命令行中包含 serve_watersource_terminal 的 Python 进程
    if sys.platform == "win32":
        try:
            cmd_ps = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | "
                "Where-Object { $_.CommandLine -like '*serve_watersource_terminal.py*' } | "
                "Select-Object -ExpandProperty ProcessId",
            ]
            res = subprocess.run(cmd_ps, capture_output=True, text=True, timeout=5)
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if line.isdigit() and int(line) > 0:
                    pids.add(int(line))
        except Exception:
            pass

        # 3. 检查占用该端口的持有进程 PID
        try:
            cmd_port = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess)",
            ]
            res_port = subprocess.run(cmd_port, capture_output=True, text=True, timeout=5)
            for line in res_port.stdout.strip().splitlines():
                line = line.strip()
                if line.isdigit() and int(line) > 0:
                    pids.add(int(line))
        except Exception:
            pass
    else:
        # POSIX 平台检测
        try:
            res = subprocess.run(
                ["pgrep", "-f", "serve_watersource_terminal.py"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.add(int(line))
        except Exception:
            pass

    # 排除当前管理脚本自身的 PID
    my_pid = os.getpid()
    if my_pid in pids:
        pids.remove(my_pid)

    return sorted(list(pids))


def terminate_pids(pids: List[int]) -> List[int]:
    """强力终止目标 PID 列表，返回成功终止的 PID 清单."""
    killed: List[int] = []
    my_pid = os.getpid()

    for pid in pids:
        if pid <= 0 or pid == my_pid:
            continue
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5,
                )
            else:
                os.kill(pid, signal.SIGKILL)
            killed.append(pid)
        except Exception as err:
            print(f"[警告] 终止进程 PID {pid} 失败: {err}", file=sys.stderr)

    return killed


def query_health_status(port: int = DEFAULT_PORT, host: str = DEFAULT_HOST) -> Optional[Dict[str, Any]]:
    """向终端服务查询健康状态快照."""
    url = f"http://{host}:{port}/api/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WaterSourceTerminalManager/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                body = resp.read().decode("utf-8")
                return json.loads(body)
    except Exception:
        return None
    return None


def stop_terminal(port: int = DEFAULT_PORT) -> bool:
    """优雅且彻底关闭水源分析终端服务进程."""
    print("======================================================================")
    print("【水源分析终端】执行服务关闭与残留进程清理...")
    print("======================================================================")

    pids = find_terminal_pids(port=port)
    if not pids and not is_port_in_use(port):
        print(f"[提示] 未发现运行中的终端服务 (端口 {port} 处于空闲状态)。")
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except Exception:
                pass
        return True

    print(f"[进程识别] 发现相关终端进程 PID: {pids}")
    killed = terminate_pids(pids)
    print(f"[进程清理] 已强制终止 {len(killed)} 个服务进程: {killed}")

    # 等待端口释放（最长等待 3 秒）
    released = False
    for _ in range(6):
        time.sleep(0.5)
        if not is_port_in_use(port):
            released = True
            break

    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except Exception:
            pass

    if released:
        print(f"[清理完毕] 端口 {port} 已成功完全释放，调度器排他锁已解除。")
        return True
    else:
        print(f"[警告] 端口 {port} 仍被占用，请检查是否有外部进程使用该端口。", file=sys.stderr)
        return False


def start_terminal(
    port: int = DEFAULT_PORT,
    host: str = DEFAULT_HOST,
    open_browser: bool = False,
    manual_only: bool = False,
    force_restart: bool = True,
) -> bool:
    """启动水源分析终端后台常驻服务，并前置断言健康状态."""
    print("======================================================================")
    print("【水源分析终端】启动服务进程中...")
    print("======================================================================")

    # 1. 若端口被占或存在旧进程，依策略处理
    existing_pids = find_terminal_pids(port=port)
    if existing_pids or is_port_in_use(port, host):
        if force_restart:
            print(f"[端口检测] 端口 {port} 已被占用，自动执行旧进程清理...")
            stop_terminal(port=port)
        else:
            print(f"[错误] 端口 {port} 已被占用且未指定强制重置，终止启动。", file=sys.stderr)
            return False

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 2. 组装启动命令行
    cmd = [
        sys.executable,
        str(SERVE_SCRIPT),
        "--host",
        str(host),
        "--port",
        str(port),
    ]
    if manual_only:
        cmd.append("--manual-only")

    # 3. 打开日志落盘文件
    log_fp = open(LOG_FILE, "a", encoding="utf-8")
    log_fp.write(f"\n--- [WaterSource Terminal Process Manager] 启动于 {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_fp.flush()

    # 4. 后台脱壳拉起服务
    creationflags = 0
    if sys.platform == "win32":
        # Windows: DETACHED_PROCESS (0x00000008) | CREATE_NEW_PROCESS_GROUP (0x00000200)
        creationflags = 0x00000008 | 0x00000200

    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=log_fp,
        stderr=log_fp,
        creationflags=creationflags,
        close_fds=(sys.platform != "win32"),
    )

    # 5. 写入 PID
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    print(f"[服务拉起] 已派生后台进程 (PID: {proc.pid})，正在探测就绪状态...")

    # 6. 轮询等待健康就绪 (最长等待 12 秒)
    target_url = f"http://{host}:{port}/"
    ready = False
    health_data: Optional[Dict[str, Any]] = None

    for i in range(24):
        time.sleep(0.5)
        # 若子进程在启动阶段崩溃
        if proc.poll() is not None:
            print(f"[错误] 服务进程在启动阶段提前退出 (ExitCode: {proc.returncode})，详见日志: {LOG_FILE}", file=sys.stderr)
            return False

        h = query_health_status(port=port, host=host)
        if h and h.get("ok"):
            ready = True
            health_data = h.get("data")
            break

    if ready:
        print("======================================================================")
        print("  【服务启动成功】水源分析终端已就绪并正常提供服务！")
        print(f"  - 服务地址: {target_url}")
        print(f"  - 主进程号 (PID): {proc.pid}")
        print(f"  - 运行日志: {LOG_FILE.relative_to(PROJECT_ROOT)}")
        if health_data:
            print(f"  - 系统状态: {health_data.get('status')} · 管道状态: {health_data.get('pipeline_state')}")
            print(f"  - 架构完整度: {health_data.get('architecture_integrity')}")
        print("======================================================================")

        if open_browser:
            print("[浏览器] 正在为您自动唤起默认浏览器打开终端界面...")
            webbrowser.open(target_url)

        return True
    else:
        print(f"[超时] 12 秒内服务未完成健康响应，请检查日志: {LOG_FILE}", file=sys.stderr)
        return False


def status_terminal(port: int = DEFAULT_PORT, host: str = DEFAULT_HOST) -> None:
    """查询并打印当前终端服务运行全息状态."""
    print("======================================================================")
    print("【水源分析终端】运行状态巡检")
    print("======================================================================")

    pids = find_terminal_pids(port=port)
    port_active = is_port_in_use(port, host)
    health = query_health_status(port=port, host=host)

    print(f"- 监听端口: {port} ({'正在监听' if port_active else '空闲/未监听'})")
    print(f"- 活跃服务进程 PID: {pids if pids else '无运行中进程'}")

    if health and health.get("ok"):
        data = health.get("data", {})
        print("- 健康状态: 正常在线 (HTTP 200 OK)")
        print(f"- 系统环境: 状态={data.get('status')} | 管道={data.get('pipeline_state')}")
        print(f"- 架构检测: {data.get('architecture_integrity')}")
        print(f"- 访问链接: http://{host}:{port}/")
    elif port_active:
        print("- 健康状态: 端口被占用，但健康端点未返回预期 JSON (可能是其他进程占用或服务正在启动中)")
    else:
        print("- 健康状态: 终端服务未运行 (可使用 python scripts/manage_terminal.py start 启动)")
    print("======================================================================")


def main() -> None:
    parser = argparse.ArgumentParser(description="水源分析终端统一进程管理中枢")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # start
    p_start = subparsers.add_parser("start", help="启动终端后台服务")
    p_start.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"监听端口 (默认 {DEFAULT_PORT})")
    p_start.add_argument("--host", type=str, default=DEFAULT_HOST, help=f"监听地址 (默认 {DEFAULT_HOST})")
    p_start.add_argument("--open", action="store_true", help="启动后自动打开默认浏览器")
    p_start.add_argument("--manual-only", action="store_true", help="禁用定时后台调度，仅支持手动提交任务")

    # stop
    p_stop = subparsers.add_parser("stop", help="停止所有终端服务进程并释放端口")
    p_stop.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"目标端口 (默认 {DEFAULT_PORT})")

    # restart
    p_restart = subparsers.add_parser("restart", help="重启终端服务")
    p_restart.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"监听端口 (默认 {DEFAULT_PORT})")
    p_restart.add_argument("--host", type=str, default=DEFAULT_HOST, help=f"监听地址 (默认 {DEFAULT_HOST})")
    p_restart.add_argument("--open", action="store_true", help="启动后自动打开默认浏览器")
    p_restart.add_argument("--manual-only", action="store_true", help="禁用定时后台调度")

    # status
    p_status = subparsers.add_parser("status", help="巡检终端服务运行状态")
    p_status.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"目标端口 (默认 {DEFAULT_PORT})")
    p_status.add_argument("--host", type=str, default=DEFAULT_HOST, help=f"目标地址 (默认 {DEFAULT_HOST})")

    args = parser.parse_args()

    if args.command == "start":
        ok = start_terminal(
            port=args.port,
            host=args.host,
            open_browser=args.open,
            manual_only=args.manual_only,
            force_restart=True,
        )
        sys.exit(0 if ok else 1)
    elif args.command == "stop":
        ok = stop_terminal(port=args.port)
        sys.exit(0 if ok else 1)
    elif args.command == "restart":
        stop_terminal(port=args.port)
        time.sleep(0.5)
        ok = start_terminal(
            port=args.port,
            host=args.host,
            open_browser=args.open,
            manual_only=args.manual_only,
            force_restart=True,
        )
        sys.exit(0 if ok else 1)
    elif args.command == "status":
        status_terminal(port=args.port, host=args.host)
        sys.exit(0)


if __name__ == "__main__":
    main()
