"""只提取猫哥公开 RSS 配置的字面常量；不导入模块或读取凭据。"""
import ast
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("C:/Users/shared_user/Desktop/猫哥的股票交易指南/canyon_system/intel/intel_config.py")


def main():
    raw = SOURCE.read_bytes()
    tree = ast.parse(raw.decode("utf-8-sig"))
    feeds = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "RSS_FEEDS" for t in node.targets):
            feeds = ast.literal_eval(node.value)
            break
    if not isinstance(feeds, list):
        raise ValueError("RSS_FEEDS 不为公开字面常量，拒绝执行源文件")
    cleaned = []
    for feed in feeds:
        # 仅允许这两个公开字段；账户变量和其他配置均不复制。
        url = feed.get("url", "")
        if urlsplit(url).scheme != "https":
            continue
        cleaned.append({"name": feed.get("name", urlsplit(url).hostname), "url": url,
                        "authority": "unreviewed", "status": "candidate_not_health_checked"})
    output = {"schema_version": "1.0.0", "source_file": "猫哥系统公开 RSS 配置（未复制原文件）",
              "source_sha256": hashlib.sha256(raw).hexdigest(), "imported_fields": ["name", "url"],
              "notes": "候选库，不自动启用；须逐条核对官方身份、时效、正文使用范围和可访问性。", "feeds": cleaned}
    path = ROOT / "knowledge/sources/cat_reference/rss-candidates.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(cleaned)} public feed candidates")


if __name__ == "__main__":
    main()
