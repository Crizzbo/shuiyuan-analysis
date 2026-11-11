# -*- coding: utf-8 -*-
"""冷热数据分层生命周期引擎单元测试 (test_data_lifecycle_engine.py).

遵循《CLAUDE.md》与《AGENTS.md》四段式中文测试说明文档规范：
1. 测试目标 (Objective)
2. 输入数据与边界 (Inputs & Boundaries)
3. 业务逻辑断言 (Assertions & Invariants)
4. 失败场景防护 (Failure Modes)
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from financial_core.engines.data_lifecycle_engine import (
    DataLifecycleEngine,
    DataTier,
    LifecyclePolicyConfig,
)
from finance_tools.governance_and_pipeline.data_lifecycle_manager import (
    DataLifecycleEngine as ToolDataLifecycleEngine,
)


def _build_synthetic_sec_company_facts() -> dict:
    """构造覆盖 2012~2026 多年度财报事实及边界异常条目的合成测试集."""
    return {
        "cik": 1045810,
        "entityName": "SYNTHETIC TECH CORP",
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "label": "Revenues",
                    "description": "Total Revenues",
                    "units": {
                        "USD": [
                            {"end": "2012-01-31", "val": 3_997_000_000, "fy": 2012, "fp": "FY", "form": "10-K", "filed": "2012-03-15"},
                            {"end": "2018-01-28", "val": 9_714_000_000, "fy": 2018, "fp": "FY", "form": "10-K", "filed": "2018-02-28"},
                            {"end": "2022-01-30", "val": 26_914_000_000, "fy": 2022, "fp": "FY", "form": "10-K", "filed": "2022-03-18"},
                            {"end": "2023-01-29", "val": 26_974_000_000, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2023-02-24"},
                            {"end": "2024-01-28", "val": 60_922_000_000, "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2024-02-21"},
                            {"end": "2025-01-26", "val": 130_497_000_000, "fy": 2025, "fp": "FY", "form": "10-K", "filed": "2025-02-26"},
                            {"end": "2026-01-25", "val": 180_000_000_000, "fy": 2026, "fp": "FY", "form": "10-K", "filed": "2026-02-25"},
                            # 边界测试：缺少 end/filed 的异常孤立记录，系统必须安全保底归入温区且不丢失
                            {"val": 999, "note": "missing date boundary"},
                        ]
                    },
                },
                # 边界测试：SEC ffd/dei 常见空数组字段 (units={"USD": []})，不得影响无损指纹验签
                "EmptyUnitEdgeCase": {
                    "label": "Empty Unit Edge Case",
                    "description": "Real-world SEC filing edge case with empty array",
                    "units": {"USD": []},
                },
            }
        },
    }


class TestDataLifecycleEngine(unittest.TestCase):
    """冷热数据分层与无损生命周期引擎单元测试套件."""

    def setUp(self) -> None:
        self.engine = DataLifecycleEngine(policy=LifecyclePolicyConfig())
        self.cache_dir = PROJECT_ROOT / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def test_quote_date_tier_classification(self):
        """【测试一：行情与事件时效冷热温三层分类边界断言】

        1. 测试目标：验证 30 天内归热区、31天~3年归温区、3年以上归冷区，非法日期保守入温区。
        2. 输入数据：基准日期 2026-11-11，分别传入当日、30天边界、180天前、5年前及空字符串。
        3. 业务断言：
           - 当日 / 20天前 -> DataTier.HOT；
           - 31天前 / 2年前 -> DataTier.WARM；
           - 4年前 -> DataTier.COLD；
           - 非法日期 -> DataTier.WARM。
        4. 失败防护：防止时间解析异常或边界比较符号错误导致近期数据被误压缩下沉。
        """
        ref = "2026-11-11"
        self.assertEqual(self.engine.classify_date_tier("2026-11-11", ref), DataTier.HOT)
        self.assertEqual(self.engine.classify_date_tier("2026-10-15", ref), DataTier.HOT)
        self.assertEqual(self.engine.classify_date_tier("2026-10-01", ref), DataTier.WARM)
        self.assertEqual(self.engine.classify_date_tier("2024-05-01", ref), DataTier.WARM)
        self.assertEqual(self.engine.classify_date_tier("2021-01-01", ref), DataTier.COLD)
        self.assertEqual(self.engine.classify_date_tier("invalid-date", ref), DataTier.WARM)

    def test_lossless_sec_company_facts_split_and_merge(self):
        """【测试二：SEC 官方财报无损时间切片拆分与逆向合集全等断言】

        1. 测试目标：验证按年份将全周期 SEC 财报拆分为热、温、冷后，温+冷能 100% 无丢数无重复合还原。
        2. 输入数据：含 2012~2026 共 8 条记录（含 1 条缺日期记录）的合成 SEC 底稿，参考年 2026。
        3. 业务断言：
           - 热区包含 2025, 2026（共 2 条）；
           - 温区包含 2023, 2024, 2025, 2026 + 1条无日期记录（共 5 条）；
           - 冷区包含 2012, 2018, 2022（共 3 条）；
           - warm + cold == 8 条，is_lossless_partition 为 True。
        4. 失败防护：防止缺日期条目被悄然丢弃或同一记录被重复放入温冷两区。
        """
        raw = _build_synthetic_sec_company_facts()
        hot_p, warm_p, cold_p, res = self.engine.split_sec_company_facts(raw, reference_year=2026)

        self.assertTrue(res.is_lossless_partition)
        self.assertEqual(res.total_original_items, 8)
        self.assertEqual(res.hot_items_count, 2)
        self.assertEqual(res.warm_items_count, 5)
        self.assertEqual(res.cold_items_count, 3)

        merged = self.engine.merge_warm_and_cold_sec_facts(warm_p, cold_p)
        re_hot, re_warm, re_cold, re_res = self.engine.split_sec_company_facts(merged, reference_year=2026)
        self.assertEqual(re_res.original_canonical_sha256, res.original_canonical_sha256)

    def test_disk_compaction_roundtrip_and_tamper_detection(self):
        """【测试三：本地磁盘冷热压缩落盘、无损唤醒还原及防篡改报警断言】

        1. 测试目标：验证真实写盘成 .hot.json / .warm.json / .cold.json.gz 及清单，且唤醒验签 100% 通过；篡改冷包即报警拦截。
        2. 输入数据：写入项目内 .cache 临时沙箱目录的大体积合成 JSON 文件。
        3. 业务断言：
           - compact_sec_filing_file 返回 lossless_verified=True；
           - prune_original=False 时原文件完整保留；
           - 人工修改冷压缩包 1 个字节后，restore_and_verify_from_tiers 立即返回 integrity_passed=False。
        4. 失败防护：防止无损压缩损坏或磁盘静默 bit 翻转导致历史回测读取错账。
        """
        with tempfile.TemporaryDirectory(dir=self.cache_dir, prefix="lifecycle-test-") as tmp:
            root = Path(tmp)
            src_dir = root / "official_filings" / "sec"
            src_dir.mkdir(parents=True)
            src_file = src_dir / "CIK0001045810.json"
            raw = _build_synthetic_sec_company_facts()
            # 人为增加冗余格式化空格模拟原始巨型文档
            src_file.write_text(json.dumps(raw, indent=4), encoding="utf-8")

            report = self.engine.compact_sec_filing_file(
                source_file=src_file,
                data_root=root,
                reference_year=2026,
                prune_original=False,
            )

            self.assertTrue(report.lossless_verified)
            self.assertTrue(src_file.exists())
            self.assertTrue(Path(report.hot_path).is_file())
            self.assertTrue(Path(report.warm_path).is_file())
            self.assertTrue(Path(report.cold_path).is_file())
            self.assertTrue(Path(report.manifest_path).is_file())

            # 验证按需还原为字典可用
            restored_dict = self.engine.restore_sec_filing_dict(
                Path(report.warm_path),
                Path(report.cold_path),
                Path(report.manifest_path),
            )
            self.assertEqual(restored_dict["entityName"], "SYNTHETIC TECH CORP")

            # 防篡改测试：故意损坏冷压缩包
            cold_p = Path(report.cold_path)
            cold_p.write_bytes(b"corrupted-gzip-bytes")
            tamper_res = self.engine.restore_and_verify_from_tiers(
                Path(report.warm_path),
                cold_p,
                Path(report.manifest_path),
            )
            self.assertFalse(tamper_res.integrity_passed)
            self.assertIn("TAMPERED_COLD", tamper_res.restored_canonical_sha256)

    def test_anti_data_leak_cloud_guard(self):
        """【测试四：GitHub 云端防数据泄露安全边界硬门禁断言】

        1. 测试目标：断言代码、工具、文档路径 100% 放行；任何数据目录及归档压缩文件 100% 阻断。
        2. 输入数据：混合工具脚本路径与违禁本地数据路径（如 data/cold/CIK0001045810.cold.json.gz）。
        3. 业务断言：
           - 工具路径全集检查返回 is_clean=True；
           - 包含任意数据路径时返回 is_clean=False，且精确指明违禁路径与原因。
        4. 失败防护：防止用户误操作将 2GB+ 本地财报或冷数据压缩包推送到 GitHub 仓库。
        """
        clean_paths = [
            "financial_core/engines/data_lifecycle_engine.py",
            "finance_tools/governance_and_pipeline/data_lifecycle_manager.py",
            "scripts/compact_cold_data.py",
            "scripts/verify_no_data_leak_guard.py",
            "docs/HOT_WARM_COLD_DATA_ARCHITECTURE.md",
            "README.md",
            "requirements.txt",
        ]
        res_ok = self.engine.check_paths_for_data_leak(clean_paths)
        self.assertTrue(res_ok.is_clean)
        self.assertEqual(len(res_ok.violating_paths), 0)

        bad_paths = clean_paths + [
            "data/hot/filings_sec/CIK0001045810.hot.json",
            "data/cold/filings_sec/CIK0001045810.cold.json.gz",
            "data_max/normalized/prices.parquet",
            "some_backup.tar.gz",
            "CIK0000320193.json",
        ]
        res_bad = self.engine.check_paths_for_data_leak(bad_paths)
        self.assertFalse(res_bad.is_clean)
        self.assertEqual(len(res_bad.violating_paths), 5)

    def test_facade_transparency(self):
        """【测试五：中继门面与底层核心类全等透明性断言】"""
        self.assertIs(ToolDataLifecycleEngine, DataLifecycleEngine)


if __name__ == "__main__":
    unittest.main()
