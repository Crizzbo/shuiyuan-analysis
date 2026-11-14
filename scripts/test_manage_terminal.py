# -*- coding: utf-8 -*-
"""单元与集成测试：水源分析终端进程管理中枢 (manage_terminal.py)."""

import os
from pathlib import Path
import unittest

from scripts import manage_terminal

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestManageTerminal(unittest.TestCase):
    """测试统一进程管理中枢的核心功能与安全断言."""

    def test_01_port_detection(self):
        """测试端口占用检测逻辑."""
        # 探测一个极高且大概率空闲的端口
        free_port = 59876
        self.assertFalse(manage_terminal.is_port_in_use(free_port))

    def test_02_pid_alive_check(self):
        """测试 PID 活跃检测."""
        current_pid = os.getpid()
        self.assertTrue(manage_terminal.is_pid_alive(current_pid))
        self.assertFalse(manage_terminal.is_pid_alive(-999))
        self.assertFalse(manage_terminal.is_pid_alive(9999999))

    def test_03_find_terminal_pids_does_not_contain_self(self):
        """测试扫描终端进程时排除管理脚本自身 PID."""
        pids = manage_terminal.find_terminal_pids(port=8765)
        self.assertNotIn(os.getpid(), pids)

    def test_04_query_health_on_closed_port(self):
        """测试在关闭的端口上查询健康状态安全返回 None 而不抛异常."""
        res = manage_terminal.query_health_status(port=59877)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
