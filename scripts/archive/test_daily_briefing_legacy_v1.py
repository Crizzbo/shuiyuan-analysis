"""每日金融商业早报构建程序回归测试 (Daily Briefing Builder Test Suite)

覆盖范围：
1. Schema 严格合规性检查（有效数据校验通过、缺项与非法格式精确阻断）；
2. 纯文本 Markdown 早报格式与核心模块渲染完整性；
3. 现代暗色交互式 HTML 仪表盘编译、标签封闭性与自包含特征；
4. 全流程端到端构建功能（输入 JSON -> 输出 MD + HTML 文件）；
5. 离线网络隔离保障（严禁任何网络外联）。
"""

import copy
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# 严禁任何网络连接
def deny_network(*args, **kwargs):
    raise AssertionError("测试执行过程中禁止网络访问")

socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network

from scripts.build_daily_briefing import (
    load_and_validate,
    render_markdown,
    render_html,
    build_briefing,
)


class DailyBriefingTests(unittest.TestCase):
    """早报构建脚本与契约单元测试。"""

    def setUp(self):
        self.sample_input_path = ROOT / "data/briefings/2026-10-11/briefing_input.json"
        self.assertTrue(self.sample_input_path.exists(), "样本早报输入文件不存在")
        self.sample_data = json.loads(self.sample_input_path.read_text(encoding="utf-8"))

    def test_load_and_validate_success(self):
        """测试合规数据能正常加载并通过 Schema 校验。"""
        data = load_and_validate(self.sample_input_path)
        self.assertEqual(data["date"], "2026-10-11")
        self.assertEqual(data["issue_number"], 284)
        self.assertIn("tactical_status", data)
        self.assertIn("macro_pulse", data)
        self.assertIn("hot_events", data)
        self.assertIn("capital_flows", data)
        self.assertIn("conviction_buys", data)
        self.assertIn("conviction_avoids", data)
        self.assertIn("tactical_checklist", data)
        self.assertIn("audit_disclosures", data)

    def test_load_and_validate_missing_field(self):
        """测试缺少必选字段时抛出明确异常。"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_data = copy.deepcopy(self.sample_data)
            del bad_data["tactical_status"]  # 删除必选模块
            bad_path = Path(tmp_dir) / "invalid.json"
            bad_path.write_text(json.dumps(bad_data, ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                load_and_validate(bad_path)
            self.assertIn("tactical_status", str(ctx.exception))

    def test_load_and_validate_invalid_type(self):
        """测试字段类型或取值不合法时抛出校验异常。"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_data = copy.deepcopy(self.sample_data)
            bad_data["date"] = "invalid-date"  # 日期格式不符合 YYYY-MM-DD
            bad_path = Path(tmp_dir) / "invalid_date.json"
            bad_path.write_text(json.dumps(bad_data, ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                load_and_validate(bad_path)
            self.assertIn("date", str(ctx.exception))

    def test_render_markdown(self):
        """测试 Markdown 文本渲染完整度与关键内容。"""
        md_text = render_markdown(self.sample_data)
        self.assertIsInstance(md_text, str)
        self.assertIn("# 水源全球金融商业早报", md_text)
        self.assertIn("## 跨资产宏观脉搏（Cross-Asset Pulse）", md_text)
        self.assertIn("## 一、 今日热点商业事件与产业链博弈穿透", md_text)
        self.assertIn("## 二、 机构主力与微观资金图谱", md_text)
        self.assertIn("## 三、 市场情绪钟摆与博弈特征", md_text)
        self.assertIn("## 四、 高确信度推荐股票池", md_text)
        self.assertIn("## 五、 高确信度危险股票池", md_text)
        self.assertIn("## 六、 战术资产配置与买入前风控清单", md_text)
        self.assertIn("## 七、 数据真实性核验与数据转换处理规范披露", md_text)

        # 检查核心标的与日股日元本币展示
        self.assertIn("任天堂", md_text)
        self.assertIn("TYO: 7974", md_text)
        self.assertIn("10,732 円", md_text)
        self.assertIn("希捷科技", md_text)
        self.assertIn("STX", md_text)
        self.assertIn("美光科技", md_text)
        self.assertIn("159.00", md_text)

    def test_render_html(self):
        """测试 HTML 渲染结构有效性与离线自包含属性。"""
        html_text = render_html(self.sample_data)
        self.assertIsInstance(html_text, str)
        self.assertTrue(html_text.startswith("<!DOCTYPE html>"))
        self.assertTrue(html_text.strip().endswith("</html>"))
        self.assertIn("<head>", html_text)
        self.assertIn("<body", html_text)
        self.assertIn("水源全球金融商业早报", html_text)
        self.assertIn("TYO: 7974", html_text)
        self.assertIn("10,732 円", html_text)
        self.assertIn("USD/JPY = 159.00", html_text)

        # 验证离线独立性：严禁加载在线 CDN 外部脚本
        self.assertNotIn("https://cdn.jsdelivr.net", html_text)
        self.assertNotIn("https://unpkg.com", html_text)
        self.assertNotIn("https://cdnjs.cloudflare.com", html_text)

    def test_build_briefing_end_to_end(self):
        """测试构建端到端流程（生成文件并返回正确元数据）。"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir)
            result = build_briefing(self.sample_input_path, output_dir=out_dir)

            self.assertEqual(result["status"], "success")
            self.assertEqual(result["date"], "2026-10-11")
            self.assertEqual(result["issue_number"], 284)

            md_path = Path(result["markdown_path"])
            html_path = Path(result["html_path"])

            self.assertTrue(md_path.exists())
            self.assertTrue(html_path.exists())
            self.assertGreater(md_path.stat().st_size, 5000)
            self.assertGreater(html_path.stat().st_size, 15000)


if __name__ == "__main__":
    unittest.main()
