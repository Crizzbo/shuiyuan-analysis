"""Google MCP 本地快照适配器；不联网、不填补缺失，也不推断供应商会计口径。"""
import hashlib
import math
import re
from datetime import datetime

ATTRIBUTES = ('price', 'currency', 'marketcap', 'volume', 'pe', 'eps', 'tradetime', 'datadelay', 'high52', 'low52')
UNITS = ('currency_per_share', 'currency_code', 'currency', 'shares', 'multiple', 'currency_per_share', 'provider_date_serial', 'minutes', 'currency_per_share', 'currency_per_share')
NAMES = ('最近报价', '计价币种', '市值', '成交量', '市盈率', '每股收益', '最近交易时间', '报价延迟', '52周最高价', '52周最低价')


def timestamp(value):
    """拒绝没有时区的采集/查询时间；交易时间保持原始格式，避免错误转换。"""
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('采集时间必须包含时区')
    return result


def content(result):
    if result.get('isError') or not isinstance(result.get('structuredContent'), dict):
        raise ValueError('MCP 返回失败或缺少 structuredContent')
    return result['structuredContent']


def field(cell, attribute, row):
    """只接收有效值，不解析格式化字符串；公式不匹配标为不可用。"""
    formula = cell.get('userEnteredValue', {}).get('formulaValue')
    effective = cell.get('effectiveValue', {})
    status, value = 'missing', None
    expected = f'=GOOGLEFINANCE($A{row},"{attribute}")'
    if formula is not None and formula != expected:
        status = 'formula_mismatch'
    elif 'errorValue' in effective:
        status = 'provider_error'
    elif formula == expected and effective:
        candidate = effective.get('stringValue') if attribute == 'currency' else effective.get('numberValue')
        valid = (isinstance(candidate, str) and re.fullmatch('[A-Z]{3}', candidate)) if attribute == 'currency' else (type(candidate) in (int, float) and math.isfinite(candidate))
        if valid and attribute in ('price', 'high52', 'low52', 'tradetime'):
            valid = candidate > 0
        if valid and attribute in ('marketcap', 'volume', 'datadelay'):
            valid = candidate >= 0
        status, value = ('ok', candidate) if valid else ('invalid_value', None)
    return {'attribute': attribute, 'value': value, 'unit': UNITS[ATTRIBUTES.index(attribute)],
            'status': status, 'formula': formula, 'display_value': cell.get('formattedValue'),
            'provider_error': effective.get('errorValue')}


def normalize(raw, raw_bytes, source_path, expected):
    """expected 是明确的证券/行号映射；每行身份错配会终止整批导入。"""
    observed = raw['acquired_at']
    timestamp(observed)
    meta, cells = content(raw['metadata']), content(raw['cells'])
    config_id = expected['spreadsheet_id']
    if meta['spreadsheetId'] != config_id or cells['spreadsheetId'] != config_id:
        raise ValueError('表格身份不匹配')
    name = expected['sheet_name']
    ms = next((x for x in meta['sheets'] if x['properties']['title'] == name), None)
    cs = next((x for x in cells['sheets'] if x['properties']['title'] == name), None)
    if ms is None or cs is None or ms['properties']['sheetId'] != cs['properties']['sheetId']:
        raise ValueError('标签页身份不匹配')
    lookup = {}
    for block in cs.get('data', []):
        for r, row in enumerate(block.get('rowData', []), block.get('startRow', 0) + 1):
            for c, cell in enumerate(row.get('values', []), block.get('startColumn', 0)):
                if (r, c) in lookup:
                    raise ValueError('重叠返回范围')
                lookup[r, c] = cell
    quotes, seen = [], set()
    for item in expected['securities']:
        row, ticker = item['row'], item['ticker']
        if ticker in seen or not re.fullmatch(r'[A-Z]+:[A-Za-z0-9.\-]+', ticker):
            raise ValueError('证券代码重复或无交易所前缀')
        seen.add(ticker)
        actual = lookup.get((row, 0), {}).get('effectiveValue', {}).get('stringValue')
        if actual != ticker:
            raise ValueError(f'行 {row} 证券身份不匹配')
        fields = {attr: field(lookup.get((row, i + 2), {}), attr, row) for i, attr in enumerate(ATTRIBUTES)}
        usable = fields['price']['status'] == fields['currency']['status'] == 'ok'
        quotes.append({'ticker': ticker, 'name': item['name'], 'industry_id': item.get('industry_id'),
            'market': item['market'], 'row': row, 'fields': fields,
            'quote_status': 'available' if usable else 'unavailable',
            'freshness_status': 'calendar_review_required', 'trade_timezone_status': 'unverified'})
    return {'schema_version': '1.0.0', 'source_kind': 'secondary', 'source_id': 'google_finance_sheets',
        'source_path': source_path, 'source_sha256': hashlib.sha256(raw_bytes).hexdigest(),
        'acquired_at': observed, 'spreadsheet_id': config_id, 'sheet_name': name,
        'spreadsheet_timezone': meta['properties']['timeZone'], 'quotes': quotes}


def calculation_inputs(snapshot, industry_rules, as_of):
    """连接现有估值请求格式；未校准的行业阈值始终关闭。"""
    if timestamp(snapshot['acquired_at']) > timestamp(as_of):
        raise ValueError('快照在研究时点之后，存在前视偏差')
    rules = {x['industry_id']: x for x in industry_rules['rules']}
    rows = []
    for quote in snapshot['quotes']:
        rule = rules.get(quote['industry_id'])
        fields = quote['fields']
        missing = [k for k in ('price', 'currency', 'high52', 'low52') if fields[k]['status'] != 'ok']
        # 只计算位置描述，不使用未校准的行业阈值生成深跌裁决。
        high, low, price = (fields[k]['value'] for k in ('high52', 'low52', 'price'))
        descriptor = None
        if not missing and high > low and low <= price <= high:
            descriptor = {'decline_from_52w_high': 1 - price / high,
                          'position_in_52w_range': (price - low) / (high - low)}
        range_status = 'available' if descriptor else ('missing_inputs' if missing else 'inconsistent_range')
        rows.append({'ticker': quote['ticker'], 'industry_id': quote['industry_id'],
            'price': fields['price']['value'], 'currency': fields['currency']['value'],
            'market_available': quote['quote_status'] == 'available',
            'valuation_status': 'missing_financial_inputs_and_model_selection',
            'reverse_dcf_price_binding': {'method': 'reverse_dcf', 'parameter': 'target_price', 'value': fields['price']['value']},
            'deep_decline_status': 'threshold_not_calibrated' if rule and rule['drawdown_threshold'] is None else 'industry_review_required',
            'missing_fields': missing, 'valuation_route': rule['valuation_route'] if rule else None,
            'range_descriptor': descriptor, 'range_status': range_status,
            'freshness_status': quote['freshness_status'], 'action_gate': 'blocked',
            'source_ref': {'source_path': snapshot['source_path'], 'sha256': snapshot['source_sha256'], 'row': quote['row']}})
    return {'schema_version': '1.0.0', 'as_of': as_of, 'inputs': rows}


def bind_reverse_dcf(quote, request):
    """把有证据的价格注入既有计算工具，其余参数必须来自独立的本地估值请求。"""
    if request.get('method') != 'reverse_dcf' or set(request) != {'method', 'parameters', 'ticker', 'currency'}:
        raise ValueError('仅接受显式 reverse_dcf 请求及证券/币种身份')
    if quote['quote_status'] != 'available' or quote['ticker'] != request['ticker'] or quote['fields']['currency']['value'] != request['currency']:
        raise ValueError('行情不可用或证券/币种不匹配')
    parameters = dict(request['parameters'])
    if 'target_price' in parameters:
        raise ValueError('禁止覆盖手填价格；行情由绑定提供')
    parameters['target_price'] = quote['fields']['price']['value']
    from finance_tools.service import calculate
    return calculate('reverse_dcf', parameters)
