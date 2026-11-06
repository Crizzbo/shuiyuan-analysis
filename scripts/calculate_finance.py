"""本地 JSON 计算入口：项目路径隔离、禁止计算过程中发起网络连接。"""

import argparse
import json
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ["MPLCONFIGDIR"] = str(ROOT / ".cache" / "matplotlib")
sys.path.insert(0, str(ROOT))
from finance_tools.service import calculate, scenarios, sensitivity, research_record


def local_path(value):
    """所有读写文件必须为项目内相对路径，并检查符号链接后的真实位置。"""
    path = Path(value)
    if path.is_absolute() or ":" in value or "\\" in value or ".." in path.parts:
        raise ValueError("仅允许项目内相对路径，统一使用正斜杠")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError("文件越界")
    return resolved


def main():
    parser = argparse.ArgumentParser(description="本地金融计算工具")
    parser.add_argument("request", help="项目内请求 JSON")
    parser.add_argument("--output", help="新输出文件，不覆盖已有记录")
    args = parser.parse_args()
    # 复用项目严格 JSON 读取器，拒绝重复键以及非有限数值。
    from validate_research import load
    request = load(local_path(args.request))
    if not isinstance(request, dict):
        raise ValueError("请求必须为 JSON 对象")

    def deny_network(*args, **kwargs):
        raise RuntimeError("计算过程禁止网络访问，只能使用本地输入")

    # CLI 是独立进程；阻止库的可选下载路径，不改变用户其他进程。
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.create_connection = deny_network
    mode = request.get("mode", "calculate")
    allowed = {"calculate": {"mode", "method", "parameters", "research_mapping"},
               "scenarios": {"mode", "method", "cases"},
               "sensitivity": {"mode", "parameters", "discount_rates", "terminal_growth_rates"}}
    if mode not in allowed or set(request) - allowed[mode]:
        raise ValueError("未知 mode 或请求字段")
    if mode == "calculate":
        result = calculate(request["method"], request["parameters"])
        if "research_mapping" in request:
            result["research_record"] = research_record(result, **request["research_mapping"])
    elif mode == "scenarios":
        result = scenarios(request["method"], request["cases"])
    elif mode == "sensitivity":
        result = sensitivity(request["parameters"], request["discount_rates"], request["terminal_growth_rates"])
    else:
        raise ValueError("未知 mode")
    text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        target = local_path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        # 研究与计算记录只追加：同名输出文件已存在则报错。
        with target.open("x", encoding="utf-8") as stream:
            stream.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
