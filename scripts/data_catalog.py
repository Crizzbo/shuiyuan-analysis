"""项目内资料目录 CLI；只读取给定的项目内文件。"""
import argparse
import json
from data_store import LocalStore, verify_backup
from validate_knowledge_structure import ROOT, local_file
from validate_research import load

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="data/catalog", help="项目根目录相对存储目录")
    subs = parser.add_subparsers(dest="command", required=True)
    reg = subs.add_parser("register-source")
    reg.add_argument("manifest")
    query = subs.add_parser("source-as-of")
    query.add_argument("source_id")
    query.add_argument("cutoff", help="含时区的 ISO 日期时间")
    save = subs.add_parser("save-research")
    save.add_argument("record")
    save.add_argument("--source-map", help="项目内证据ID到资料版本的 JSON 映射")
    read = subs.add_parser("read-research")
    read.add_argument("research_id")
    read.add_argument("--revision", type=int)
    historical = subs.add_parser("research-as-of")
    historical.add_argument("research_id")
    historical.add_argument("cutoff")
    subs.add_parser("audit")
    backup = subs.add_parser("backup")
    backup.add_argument("directory")
    verify = subs.add_parser("verify-backup")
    verify.add_argument("directory")
    args = parser.parse_args()
    store = None
    try:
        if args.command == "verify-backup":
            print(json.dumps(verify_backup(args.directory), ensure_ascii=False, indent=2))
            return
        store = LocalStore(args.store)
        if args.command == "register-source":
            result = store.register_source(load(local_file(ROOT, args.manifest)))
        elif args.command == "source-as-of":
            result = store.source_as_of(args.source_id, args.cutoff)
        elif args.command == "save-research":
            source_map = load(local_file(ROOT, args.source_map)) if args.source_map else None
            result = store.save_research(load(local_file(ROOT, args.record)), source_map)
        elif args.command == "read-research":
            result = store.get_research(args.research_id, args.revision)
        elif args.command == "research-as-of":
            result = store.research_as_of(args.research_id, args.cutoff)
        elif args.command == "backup":
            result = store.backup(args.directory)
        else:
            result = store.audit()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "audit" and not result["ok"]:
            raise SystemExit(1)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    finally:
        if store is not None:
            store.close()

if __name__ == "__main__":
    main()
