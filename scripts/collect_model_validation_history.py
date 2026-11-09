"""按显式来源配置下载免费公开历史文件，原文先归档再由本地工具登记。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from scripts.data_store import LocalStore


def validate_url(url, allowed_hosts):
    """仅允许配置列出的HTTPS主机，不发送认证信息。"""
    p = urlparse(url)
    if p.scheme != "https" or p.hostname not in allowed_hosts or p.username or p.password:
        raise ValueError("下载地址不在公开来源白名单中")


def main():
    config_path = ROOT / "config/model_history_sources.json"
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    folder = ROOT / "data/history/model_validation" / stamp
    (folder / "raw").mkdir(parents=True, exist_ok=False)
    (folder / "manifests").mkdir()
    (folder / "protocol.json").write_bytes(config_bytes)
    collection = {"schema_version": "1.0.0", "capture_id": stamp,
                  "config_sha256": hashlib.sha256(config_bytes).hexdigest(), "sources": [], "failures": []}
    store = LocalStore("data/catalog")
    try:
        for source in config["sources"]:
            key, url = source["id"], source["url"]
            try:
                validate_url(url, config["allowed_hosts"])
                request = Request(url, headers={"User-Agent": "ShuiyuanLocalResearch/1.0", "Accept": "*/*"})
                with urlopen(request, timeout=30) as response:
                    validate_url(response.url, config["allowed_hosts"])
                    raw = response.read(config["max_download_bytes"] + 1)
                    final_url = response.url
                    content_type = response.headers.get("Content-Type", "")
                if len(raw) > config["max_download_bytes"] or not raw:
                    raise ValueError("文件为空或超过大小限制")
                if source["format"] == "zip" and not raw.startswith(b"PK"):
                    raise ValueError("下载结果不是ZIP原始文件")
                if source["format"] == "html" and b"<html" not in raw[:2000].lower():
                    raise ValueError("下载结果不是HTML原文")
                acquired = datetime.now(timezone.utc).isoformat()
                path = folder / "raw" / (key + "." + source["format"])
                path.write_bytes(raw)
                manifest = {
                    "schema_version": "1.1.0", "source_id": f"histval-{key}-{stamp}", "revision": 1,
                    "source_path": path.relative_to(ROOT).as_posix(), "source_kind": source["source_kind"],
                    "dataset_kind": source["dataset_kind"], "published_at": None,
                    "available_at": acquired, "acquired_at": acquired, "effective_period": None,
                    "license_notes": source["license_notes"], "quality_notes": [source["notes"], f"来源URL：{final_url}",
                    "本次归档时间不等于历史首次可用时间；不用于证明严格point-in-time回测。"],
                    "supersedes_revision": None, "published_date": None, "publication_precision": "unknown"}
                manifest_path = folder / "manifests" / (key + ".json")
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                registered = store.register_source(manifest)
                collection["sources"].append({**source, "path": path.relative_to(ROOT).as_posix(),
                    "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "acquired_at": acquired,
                    "final_url": final_url, "content_type": content_type,
                    "manifest": manifest_path.relative_to(ROOT).as_posix(), "catalog": registered})
                print("ARCHIVED", key, len(raw), flush=True)
            except Exception as exc:
                collection["failures"].append({"id": key, "url": url, "error": f"{type(exc).__name__}: {exc}"})
                print("FAILED", key, type(exc).__name__, flush=True)
            (folder / "collection.json").write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        store.close()
    assert config_path.read_bytes() == config_bytes, "采集期间协议被修改"
    print(json.dumps({"collection": (folder / "collection.json").relative_to(ROOT).as_posix(),
                      "archived": len(collection["sources"]), "failed": len(collection["failures"])}, ensure_ascii=False))
    return int(bool(collection["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
