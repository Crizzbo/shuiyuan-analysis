"""保存项目虚拟环境的精确依赖版本、许可证原文及元数据清单。"""

import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        raise RuntimeError("必须使用项目内 .venv 解释器记录依赖")
    folder = ROOT / "third_party" / "finance"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    for dist in sorted(distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = dist.metadata["Name"]
        licenses = []
        for file in dist.files or []:
            # 仅复制发行包携带的许可证，不复制外部用户资料。
            if ".dist-info" not in str(file) or not any(x in file.name.lower() for x in ("license", "copying", "notice")):
                continue
            data = Path(dist.locate_file(file)).read_bytes()
            target = folder / name / str(file).split(".dist-info/", 1)[-1]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            licenses.append({"path": target.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(data).hexdigest()})
        manifest.append({"name": name, "version": dist.version,
                         "license_metadata": dist.metadata.get("License-Expression") or dist.metadata.get("License"),
                         "license_files": licenses})
    (folder / "dependency-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    locked = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    (ROOT / "requirements-finance.lock.txt").write_text(locked, encoding="utf-8")
    print(f"记录 {len(manifest)} 个发行包与许可证；已生成完整版本锁")


if __name__ == "__main__":
    main()
