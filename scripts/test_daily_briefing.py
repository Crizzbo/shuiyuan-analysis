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

ROOT = Path(__file__).resolve().parents[1]
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
        """【FT-BRIEFING-01: 每日早报JSON契约Schema校验、根字段全息加载与防御性状态校验】

        1. 测试功能与测试点:
           - 验证 build_daily_briefing.load_and_validate 函数读取早报数据并执行 JSON Schema 强校验。
           - 契约完备性断言: 检查 10 大必填根字段全部具备 (date, issue_number, tactical_status, macro_pulse, hot_events, capital_flows, conviction_buys, conviction_avoids, tactical_checklist, audit_disclosures)。
           - 战术状态断言: 检验仓位控制与现金占比契约。

        2. 正常函数业务边界与参数契约:
           - 输入为存在且符合 schemas/daily_briefing.schema.json 的 JSON 文件路径。
           - 返回校验成功的 Python dict。

        3. 测试数据与模拟场景说明:
           - 读取真实物理样本 data/briefings/2026-10-11/briefing_input.json。

        4. 预期断言与结果验证:
           - 断言 date == '2026-10-11' 且 issue_number == 284。
           - 断言 10 大根字段集合为 data.keys() 的子集。
           - 断言 tactical_status['state'] == '轻仓防御' 且 cash_ratio_pct == 75。
           - 断言 conviction_buys 推荐买入池非空。
        """
        data = load_and_validate(self.sample_input_path)
        self.assertEqual(data["date"], "2026-10-11")
        self.assertEqual(data["issue_number"], 284)
        required_keys = {
            "date", "issue_number", "tactical_status", "macro_pulse",
            "hot_events", "capital_flows", "conviction_buys",
            "conviction_avoids", "tactical_checklist", "audit_disclosures",
        }
        self.assertTrue(required_keys.issubset(set(data.keys())), "早报根数据必须完整包含所有核心业务字段")
        self.assertEqual(data["tactical_status"]["state"], "轻仓防御")
        self.assertEqual(data["tactical_status"]["cash_ratio_pct"], 75)
        self.assertGreater(len(data["conviction_buys"]), 0, "推荐买入池不能为空")

    def test_load_and_validate_missing_field(self):
        """【UT-BRIEFING-02: 每日早报核心必选模块(tactical_status)缺失异常阻断】

        1. 测试功能与测试点:
           - 验证当早报输入数据中缺失战略仓位状态模块 (tactical_status) 时，Schema 校验引擎的刚性拦截。
           - 杜绝残缺数据流入下游 Markdown 与 HTML 渲染器。

        2. 正常函数业务边界与参数契约:
           - 缺失必选键抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 深拷贝样本数据并物理删除 'tactical_status' 字段，写入临时文件。

        4. 预期断言与结果验证:
           - 断言抛出 ValueError。
           - 异常信息中包含 'tactical_status'。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_data = copy.deepcopy(self.sample_data)
            del bad_data["tactical_status"]  # 删除必选模块
            bad_path = Path(tmp_dir) / "invalid.json"
            bad_path.write_text(json.dumps(bad_data, ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                load_and_validate(bad_path)
            self.assertIn("tactical_status", str(ctx.exception))

    def test_load_and_validate_invalid_type(self):
        """【UT-BRIEFING-03: 每日早报日期格式非标(非YYYY-MM-DD)异常阻断】

        1. 测试功能与测试点:
           - 验证 Schema 针对日期字段的 ISO 格式正则校验。
           - 当 date 取值为非法格式 (如 'invalid-date') 时刚性拦截。

        2. 正常函数业务边界与参数契约:
           - date 必须满足 ^\\d{4}-\\d{2}-\\d{2}$ 正则。

        3. 测试数据与模拟场景说明:
           - 将 date 替换为 'invalid-date' 并写入临时文件。

        4. 预期断言与结果验证:
           - 断言抛出 ValueError。
           - 异常信息中包含 'date'。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_data = copy.deepcopy(self.sample_data)
            bad_data["date"] = "invalid-date"  # 日期格式不符合 YYYY-MM-DD
            bad_path = Path(tmp_dir) / "invalid_date.json"
            bad_path.write_text(json.dumps(bad_data, ensure_ascii=False), encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                load_and_validate(bad_path)
            self.assertIn("date", str(ctx.exception))

    def test_render_markdown(self):
        """【FT-BRIEFING-04: Markdown多模态早报多章节渲染、日美双币种精度保真与买方卡片嵌入】

        1. 测试功能与测试点:
           - 验证 render_markdown 函数渲染的投委会早报完整性。
           - 覆盖 7 大必选业务章节标题。
           - 货币与美分/日元格式保真: 日股东证标的符合千分位 (如 '10,732 円')，美股保留两位小数 (如 '159.00')。
           - 推荐股票必须以买方决策卡呈现，包含三态走廊估值分析。

        2. 正常函数业务边界与参数契约:
           - 输入合法早报字典，输出非空字符串。

        3. 测试数据与模拟场景说明:
           - 包含任天堂 (TYO: 7974 现价 10,732 円) 与 USD/JPY 159.00。

        4. 预期断言与结果验证:
           - 断言包含大标题及跨资产宏观、今日热点、资金图谱、情绪钟摆、推荐池、危险池、风控清单、数据核验等 7 大章节。
           - 正则断言日元价格匹配 r"\\b10,732\\s*円"。
           - 正则断言汇率匹配 r"USD/JPY\\s*=\\s*159\\.00"。
           - 包含估值三态走廊关键词。
        """
        import re

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

        # 1. 核心标的与日股/美股货币符号及精度保真校验
        self.assertIn("任天堂", md_text)
        self.assertIn("TYO: 7974", md_text)
        # 日股日元格式检验: 包含千分位与円符号
        self.assertRegex(md_text, r"\b10,732\s*円", "日股价格必须符合标准日元千分位展示")
        # 美股美元美分精度保真检验: 必须保留精确两位小数
        self.assertRegex(md_text, r"USD/JPY\s*=\s*159\.00", "外汇汇率必须严格保全两位小数，严禁截断为 159")

        # 2. 检查推荐池中是否具备完备买方决策卡逻辑 (悲观底/公允/乐观靶心与买点触发事件)
        self.assertTrue(
            any(kw in md_text for kw in ["悲观底", "防线", "安全边际", "击球区", "内在价值"]),
            "早报必须包含基于三态走廊的买方估值分析",
        )

    def test_render_html(self):
        """【FT-BRIEFING-05: 交互式暗色HTML仪表盘编译、自包含离线纯净性与标签封闭性】

        1. 测试功能与测试点:
           - 验证 render_html 函数编译现代暗色系买方 HTML 仪表盘的合规性。
           - 标签完整性与自包含: 必须以 <!DOCTYPE html> 开头，以 </html> 闭合，内嵌 head 与 body。
           - 离线网络隔离保障: 严禁引入在线第三方 CDN 外部脚本 (如 jsdelivr, unpkg, cdnjs)。

        2. 正常函数业务边界与参数契约:
           - 输入样本数据，输出完整 HTML 文本。

        3. 测试数据与模拟场景说明:
           - 渲染完整仪表盘。

        4. 预期断言与结果验证:
           - 断言 html_text.startswith('<!DOCTYPE html>') 且 endswith('</html>')。
           - 断言包含 '10,732 円' 与 'USD/JPY = 159.00'。
           - 断言不包含任何在线 CDN 脚本链接。
        """
        import re

        html_text = render_html(self.sample_data)
        self.assertIsInstance(html_text, str)
        self.assertTrue(html_text.startswith("<!DOCTYPE html>"))
        self.assertTrue(html_text.strip().endswith("</html>"))
        self.assertIn("<head>", html_text)
        self.assertIn("<body", html_text)
        self.assertIn("水源全球金融商业早报", html_text)
        self.assertIn("TYO: 7974", html_text)

        # 校验日元和美元的展示保真度
        self.assertIn("10,732 円", html_text)
        self.assertIn("USD/JPY = 159.00", html_text)

        # 验证离线独立性：严禁加载在线 CDN 外部脚本
        self.assertNotIn("https://cdn.jsdelivr.net", html_text)
        self.assertNotIn("https://unpkg.com", html_text)
        self.assertNotIn("https://cdnjs.cloudflare.com", html_text)

    def test_build_briefing_end_to_end(self):
        """【IT-BRIEFING-06: 每日早报端到端构建流水线(JSON输入->MD+HTML双模物理落盘)】

        1. 测试功能与测试点:
           - 验证 build_briefing 端到端主编排管线。
           - 输入 JSON 真实文件，同时生成物理落盘的 Markdown 备忘录与 HTML 仪表盘。
           - 验证生成文件物理存在且文件体积充实 (MD > 5KB, HTML > 15KB)。

        2. 正常函数业务边界与参数契约:
           - 返回状态为 'success'。

        3. 测试数据与模拟场景说明:
           - 输出至临时目录。

        4. 预期断言与结果验证:
           - 断言 result['status'] == 'success'。
           - 断言 md_path.exists() 且大小 > 5000 字节。
           - 断言 html_path.exists() 且大小 > 15000 字节。
        """
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
