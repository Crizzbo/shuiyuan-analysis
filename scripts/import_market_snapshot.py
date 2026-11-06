"""离线标准化已归档的 Google MCP 返回；记录只追加，禁止自动联网。"""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_research import load, structural
from scripts.calculate_finance import local_path
from financial_reporting.market_snapshot import normalize, calculation_inputs, bind_reverse_dcf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw')
    parser.add_argument('plan')
    parser.add_argument('--output', required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--valuation-request', help='项目内反向DCF请求，财务参数由独立本地证据提供')
    args = parser.parse_args()
    raw_path = local_path(args.raw)
    snapshot = normalize(load(raw_path), raw_path.read_bytes(), args.raw, load(local_path(args.plan)))
    schema = load(ROOT / 'schemas/market-snapshot.schema.json')
    structural(snapshot, schema, schema)
    result = {'snapshot': snapshot, 'calculation_inputs': calculation_inputs(snapshot, load(ROOT / 'knowledge/taxonomy/industry_rules.json'), args.as_of)}
    if args.valuation_request:
        request = load(local_path(args.valuation_request))
        quote = next((x for x in snapshot['quotes'] if x['ticker'] == request.get('ticker')), None)
        if quote is None:
            raise ValueError('估值请求证券不在行情批次内')
        # 计算成功不解除独立财务证据、时效与研究门槛。
        result['valuation_calculation'] = bind_reverse_dcf(quote, request)
    output = local_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(f'已标准化 {len(snapshot["quotes"])} 只证券；交易日历与时区核验未完成，交易裁决保持 blocked')


if __name__ == '__main__':
    main()
