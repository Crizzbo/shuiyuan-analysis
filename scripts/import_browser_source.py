"""将 AI 浏览器实际下载的公开原文归档到项目；不发请求、不读取凭据。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import io

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_ingestion.core import Archive, encode, project_path, public_url, utcnow


def import_document(download, receipt, archive):
    """输入路径须由当次浏览器下载返回；来源身份依靠审核过的 receipt 记录。"""
    required = {"id", "entity_id", "search_url", "page_url", "document_url", "format", "published_date", "publication_precision", "verification_notes"}
    if not isinstance(receipt, dict) or set(receipt) != required or not receipt["verification_notes"]:
        raise ValueError("浏览器来源登记字段或核对说明不完整")
    config = json.loads((ROOT / "data/ingestion-sources.json").read_text(encoding="utf-8"))
    hosts = config["sources"]["issuer_ir"]["hosts"] + config["sources"]["tdnet"]["hosts"]
    public_url(receipt["page_url"], hosts)
    public_url(receipt["document_url"], hosts)
    if receipt["publication_precision"] not in ("date", "unknown"):
        raise ValueError("本版发布时间只登记已核对日期或未知，不臆造精确时刻")
    if (receipt["publication_precision"] == "unknown") != (receipt["published_date"] is None):
        raise ValueError("发布日期与精度不一致")
    if receipt["published_date"] is not None:
        from datetime import date
        date.fromisoformat(receipt["published_date"])
    path = Path(download)
    if not path.is_file():
        raise ValueError("浏览器返回的下载文件不存在")
    raw = path.read_bytes()
    if len(raw) > 100 * 1024 * 1024:
        raise ValueError("原文超过 100 MiB")
    if receipt["format"] == "zip":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            members = z.namelist()
        if not members:
            raise ValueError("ZIP 无原始文件")
    elif receipt["format"] == "pdf":
        if not raw.startswith(b"%PDF"):
            raise ValueError("下载不是 PDF")
        members = []
    else:
        raise ValueError("当前浏览器下载导入支持 PDF/ZIP")
    identity = hashlib.sha256(encode([receipt["id"], receipt["document_url"], hashlib.sha256(raw).hexdigest()])).hexdigest()
    artifact = archive.save("ai_browser", identity, raw, {
        "origin_url": receipt["document_url"], "source_kind": "primary", "dataset_kind": "financial",
        "published_at": None, "quality_status": "unreviewed",
        "raw_transport": "browser_download", "browser_receipt": receipt})
    result = {"schema_version": "1.0.0", "id": receipt["id"], "status": "archived",
              "artifact": artifact, "zip_members": members,
              "quality_notes": ["官方页面及文件链接由 AI 浏览器核对，原文已归档", "发布日期精度保留为日期；精确可得时刻未知，使用本项目观察时刻", "原始 XBRL/PDF 尚未转换为经财务口径审核的指标事实"]}
    target = project_path("data/browser-search/receipts")
    target.mkdir(parents=True, exist_ok=True)
    output = target / (hashlib.sha256(encode(result)).hexdigest() + ".json")
    output.write_bytes(encode(result) + b"\n")
    return {"status": "archived", "source_path": artifact["source_path"], "sha256": artifact["sha256"],
            "receipt_path": output.relative_to(ROOT).as_posix(), "zip_member_count": len(members)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("download", help="本次浏览器返回的实际下载文件路径，不扫描目录")
    parser.add_argument("receipt", help="项目内浏览器来源核对登记 JSON")
    args = parser.parse_args()
    archive = Archive()
    try:
        receipt = json.loads(project_path(args.receipt).read_text(encoding="utf-8"))
        print(json.dumps(import_document(args.download, receipt, archive), ensure_ascii=False, indent=2))
    finally:
        archive.close()


if __name__ == "__main__":
    main()
