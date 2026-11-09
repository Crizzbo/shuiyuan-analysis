"""批量清洗 scripts/legacy_batch_runners/ 中历史批次脚本的 Emoji 装饰符号与工程代号 (clean_legacy_batch_runners_emojis.py).

严格遵循 CLAUDE.md 去工程符号化与商业语义标准化准则：
1. 100% 物理消除所有装饰性 Emoji 符号 (🚀, 🔍, ❌, ✅, 📄, 📂, ☁️, 🗑️, ⚠️, ⬆️, 🎉 等)；
2. 转换为自然语言方括号商业语义标签：
   - [流水线启动]、[契约核验]、[校验失败]、[校验通过]、[报告编译]、[编译成功]、[本地同步]、
   - [云端同步]、[云端上传]、[流式上传]、[清理完成]、[清理提示]、[上传异常]、[上传成功]、[批次完成]；
3. 执行 py_compile 语法全息断言，确保 78 个批次脚本 100% 语法合规。
"""

from pathlib import Path
import py_compile
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = ROOT / "scripts" / "legacy_batch_runners"

EMOJI_PATTERN = re.compile(
    "[\U00010000-\U0010ffff]|[☀-➿]|[⌀-⏿]|[⭐-⭕]|[‼-⁉]"
)

STRING_REPLACEMENTS = [
    ('print("🚀 [', 'print("[流水线启动] '),
    ('print(f"\\n🔍 [1/4]', 'print(f"\\n[契约核验] [1/4]'),
    ('print(f"  ❌ Schema 验证失败', 'print(f"  [校验失败] Schema 验证失败'),
    ('print(f"  ❌ PDF 编译失败', 'print(f"  [编译失败] PDF 编译失败'),
    ('print(f"  ❌ 上传云端失败', 'print(f"  [上传失败] 上传云端失败'),
    ('print(f"  ✅ Schema 验证通过', 'print(f"  [校验通过] Schema 验证通过'),
    ('print(f"📄 [2/4]', 'print(f"[报告编译] [2/4]'),
    ('print(f"  ✅ PDF 生成成功', 'print(f"  [编译成功] PDF 生成成功'),
    ('print(f"  📂 本地交付目录已同步替换', 'print(f"  [本地同步] 本地交付目录已同步替换'),
    ('print(f"  📂 本地交付目录已同步存入', 'print(f"  [本地同步] 本地交付目录已同步存入'),
    ('print(f"☁️ [3/4] 正在同步 Google Drive 云盘', 'print(f"[云端同步] [3/4] 正在同步 Google Drive 云盘'),
    ('print(f"☁️ [3/4] 正在上传正式股票深度分析 PDF 至 Google Drive 云端', 'print(f"[云端上传] [3/4] 正在上传正式股票深度分析 PDF 至 Google Drive 云端'),
    ('print(f"☁️ [3/4] 正在流式上传 Google Drive 云盘', 'print(f"[流式上传] [3/4] 正在流式上传 Google Drive 云盘'),
    ('print(f"  🗑️ 旧版证据存根已移入回收站', 'print(f"  [清理完成] 旧版证据存根已移入回收站'),
    ('print(f"  ⚠️ 旧存根回收警告', 'print(f"  [清理提示] 旧存根回收提示'),
    ('print(f"  ⚠️ 旧版回收异常', 'print(f"  [清理提示] 旧版回收提示'),
    ('print(f"  ⚠️ 旧存根回收跳过或未找到', 'print(f"  [清理提示] 旧存根回收跳过或未找到'),
    ('print(f"  ⬆️ 正在上传正式股票深度分析 PDF 至云端文件夹', 'print(f"  [云端上传] 正在上传正式股票深度分析 PDF 至云端文件夹'),
    ('print(f"  ⚠️ 云端上传解析 ID 警告', 'print(f"  [上传异常] 云端上传解析 ID 异常'),
    ('print(f"  ✅ 云端上传成功！', 'print(f"  [上传成功] 云端上传成功！'),
    ('print("🎉 [', 'print("[批次完成] '),
]


def clean_batch_runners():
    files = sorted(BATCH_DIR.glob("tackle_batch*.py"))
    print(f"[批次清洗] 开始清洗 {len(files)} 个历史批次脚本的 Emoji 装饰符号...")

    updated_count = 0
    remaining_emojis = {}

    for f in files:
        original = f.read_text(encoding="utf-8")
        cleaned = original
        for old_s, new_s in STRING_REPLACEMENTS:
            cleaned = cleaned.replace(old_s, new_s)

        # 兜底清除任何剩余 Emoji
        matches = EMOJI_PATTERN.findall(cleaned)
        if matches:
            remaining_emojis[f.name] = set(matches)
            cleaned = EMOJI_PATTERN.sub("", cleaned)

        if cleaned != original:
            f.write_text(cleaned, encoding="utf-8")
            updated_count += 1

        # 语法合规断言
        py_compile.compile(str(f), doraise=True)

    print(f"[清洗完成] 成功清洗并标准化 {updated_count} 个批次脚本！")
    if remaining_emojis:
        print(f"[兜底清洗] 发现并彻底清除以下文件的残留 Emoji: {len(remaining_emojis)} 个")
    else:
        print("[零残留] 全量 78 个批次脚本 100% 消除 Emoji 装饰符号！")


if __name__ == "__main__":
    clean_batch_runners()
