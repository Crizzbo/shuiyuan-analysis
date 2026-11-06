"""单元测试: 市场行情快照解析、数据源契约、52周区间走廊与反向DCF绑定测试套件.

测试覆盖范围:
1. 【UT-SNAPSHOT-01】: 真实行情样本解析与闭合 Schema 契约验证 (Draft 2020-12)
2. 【UT-SNAPSHOT-02】: 证券身份代码错配与未登记标的物理拦截
3. 【UT-SNAPSHOT-03】: 数据源错误状态 (ErrorValue) 与真实零值的物理隔离
4. 【UT-SNAPSHOT-04】: 成交量真实零值物理保留 (Volume=0)
5. 【UT-SNAPSHOT-05】: 单元格公式错配检测与状态标记 (formula_mismatch)
6. 【UT-SNAPSHOT-06】: 前视未来时间戳输入刚性拦截 (No Look-Ahead Bias)
7. 【UT-SNAPSHOT-07】: 52 周区间跌幅与位置推导及研究闸门未校准阻断
8. 【UT-SNAPSHOT-08】: 52 周高低点端点边界与非法倒挂区间拦截 (Inconsistent Range)
9. 【UT-SNAPSHOT-09】: 越界相对路径与绝对路径越狱物理拦截 (Security Sandbox)
10. 【UT-SNAPSHOT-10】: 真实行情反向 DCF 绑定与多币种一致性校验
"""
import copy
import json
import sys
import socket
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from financial_reporting.market_snapshot import normalize, calculation_inputs, bind_reverse_dcf
from scripts.calculate_finance import local_path
from scripts.validate_research import structural, load

def deny(*args, **kwargs):
    raise AssertionError('测试禁止联网')
socket.socket.connect = deny
socket.create_connection = deny

class Tests(unittest.TestCase):
    """【单元测试】行情快照归一化、契约校验与边界防御测试."""

    def setUp(self):
        self.path = ROOT / 'data/google-finance/raw/20261011T094549Z.json'
        self.raw = load(self.path)
        self.plan = load(ROOT / 'config/google-finance-smoke-plan.json')

    def run_snapshot(self):
        return normalize(self.raw, self.path.read_bytes(), self.path.relative_to(ROOT).as_posix(), self.plan)

    def row(self):
        return self.raw['cells']['structuredContent']['sheets'][0]['data'][0]['rowData'][3]['values']

    def test_real_sample_and_closed_schema(self):
        """【UT-SNAPSHOT-01: 真实行情样本解析与闭合Schema契约验证】

        1. 测试功能与测试点:
           - 验证使用真实的离线行情原始表格底账解析出的快照对象完全满足 market-snapshot.schema.json。
           - 验证 Schema 的闭合性 (additionalProperties: false)，当注入未声明的非法字段时必须抛出校验异常。

        2. 正常函数业务边界与参数契约:
           - raw_data: 包含 Google Sheets 官方 API 结构的字典。
           - plan: 行情采纳映射规划配置。
           - 期望输出满足契约，且 price 字段值正确解析为标量浮点数。

        3. 测试数据与模拟场景说明:
           - 真实底账: 20261011T094549Z.json，标的为 MSFT (NASDAQ:MSFT)。
           - 非法注入: 在输出字典中注入 'unexpected': True 字段。

        4. 预期断言与结果验证:
           - 断言 price.value 为 336.64。
           - 断言注入未知字段后调用 structural 抛出 ValueError。
        """
        result = self.run_snapshot()
        schema = load(ROOT / 'schemas/market-snapshot.schema.json')
        structural(result, schema, schema)
        self.assertEqual(result['quotes'][0]['fields']['price']['value'], 336.64)
        result['unexpected'] = True
        with self.assertRaises(ValueError):
            structural(result, schema, schema)

    def test_wrong_identity_rejected(self):
        """【UT-SNAPSHOT-02: 证券身份代码错配刚性拦截】

        1. 测试功能与测试点:
           - 验证当表格中的证券代码与映射规划中的预期身份不一致时，归一化引擎能否主动识别并阻断。

        2. 正常函数业务边界与参数契约:
           - 单元格 stringValue 必须与 smoke-plan 中的期望 ticker 精确一致。

        3. 测试数据与模拟场景说明:
           - 篡改输入: 将单元格中的代码修改为 'NASDAQ:OTHER'。

        4. 预期断言与结果验证:
           - 断言 run_snapshot 抛出 ValueError。
        """
        self.row()[0]['effectiveValue']['stringValue'] = 'NASDAQ:OTHER'
        with self.assertRaises(ValueError): self.run_snapshot()

    def test_error_is_not_zero(self):
        """【UT-SNAPSHOT-03: 数据源错误状态与真实零值物理隔离】

        1. 测试功能与测试点:
           - 验证上游数据源返回错误（如 #N/A）时，系统绝不把错误静默回退为 0.0，而是标记为 unavailable 且值为 None。

        2. 正常函数业务边界与参数契约:
           - 错误状态字段应记录 errorValue，状态标记为 unavailable，数值为 None。

        3. 测试数据与模拟场景说明:
           - 模拟 Google Sheets 返回的错误单元格: {'errorValue': {'type': 'N_A', 'message': 'no data'}}。

        4. 预期断言与结果验证:
           - 断言 quote_status == 'unavailable' 且 price.value is None。
        """
        self.row()[2]['effectiveValue'] = {'errorValue': {'type':'N_A','message':'no data'}}
        quote = self.run_snapshot()['quotes'][0]
        self.assertEqual(quote['quote_status'], 'unavailable')
        self.assertIsNone(quote['fields']['price']['value'])

    def test_zero_volume_preserved(self):
        """【UT-SNAPSHOT-04: 成交量真实零值物理保留】

        1. 测试功能与测试点:
           - 验证停牌或无成交状态下的真实 0 成交量被完整保留，不被当作假值或缺失值处理。

        2. 正常函数业务边界与参数契约:
           - 物理数字 0 必须保留为 0，而不是转换为 None。

        3. 测试数据与模拟场景说明:
           - 设置成交量单元格为数值 0: {'numberValue': 0}。

        4. 预期断言与结果验证:
           - 断言 volume.value 精确等于 0。
        """
        self.row()[5]['effectiveValue'] = {'numberValue': 0}
        self.assertEqual(self.run_snapshot()['quotes'][0]['fields']['volume']['value'], 0)

    def test_formula_mismatch(self):
        """【UT-SNAPSHOT-05: 单元格公式错配检测与状态标记】

        1. 测试功能与测试点:
           - 验证当用户在表格中输入的公式行号与预期不匹配时，系统能够标记 formula_mismatch 状态。

        2. 正常函数业务边界与参数契约:
           - 公式字符串必须与行号绑定的规范公式一致。

        3. 测试数据与模拟场景说明:
           - 将第四行公式篡改为第 7 行公式: '=GOOGLEFINANCE($A7,"price")'。

        4. 预期断言与结果验证:
           - 断言 price.status 等于 'formula_mismatch'。
        """
        self.row()[2]['userEnteredValue']['formulaValue'] = '=GOOGLEFINANCE($A7,"price")'
        self.assertEqual(self.run_snapshot()['quotes'][0]['fields']['price']['status'], 'formula_mismatch')

    def test_forward_time_rejected(self):
        """【UT-SNAPSHOT-06: 前视未来时间戳输入刚性拦截】

        1. 测试功能与测试点:
           - 验证金融计算防前视偏差硬约束: 严禁使用晚于当前分析基准日的未来行情数据。

        2. 正常函数业务边界与参数契约:
           - snapshot.acquired_at 必须 <= as_of 时间戳。

        3. 测试数据与模拟场景说明:
           - 行情获取时间为 2026-10-11，但传入分析时间基准为早一天的 2026-10-10。

        4. 预期断言与结果验证:
           - 断言 calculation_inputs 抛出 ValueError 阻断前视计算。
        """
        with self.assertRaises(ValueError):
            calculation_inputs(self.run_snapshot(), {'rules':[]}, '2026-10-10T00:00:00Z')

    def test_positive_range_values_and_blocked_gate(self):
        """【UT-SNAPSHOT-07: 52周区间跌幅与位置推导及研究闸门未校准阻断】

        1. 测试功能与测试点:
           - 验证根据现价、52周最高价与52周最低价准确推导:
             A) 距52周高点跌幅: (High - Price) / High
             B) 52周区间相对位置: (Price - Low) / (High - Low)
           - 验证在缺乏长期大样本统计校准前，研究闸门 (action_gate) 保持 blocked 状态。

        2. 正常函数业务边界与参数契约:
           - Price=80, High=100, Low=20。
           - 跌幅 = (100 - 80) / 100 = 0.20 (20%)。
           - 位置 = (80 - 20) / (100 - 20) = 60 / 80 = 0.75 (75%)。

        3. 测试数据与模拟场景说明:
           - 构造硬件行业标的，现价 80，最高 100，最低 20。

        4. 预期断言与结果验证:
           - 断言 decline_from_52w_high 精确等于 0.2。
           - 断言 position_in_52w_range 精确等于 0.75。
           - 断言 action_gate 等于 'blocked'。
        """
        snapshot=self.run_snapshot()
        quote=snapshot['quotes'][0]
        quote['industry_id']='hardware'
        for name,value in [('price',80),('high52',100),('low52',20)]:
            quote['fields'][name].update(value=value,status='ok')
        rules={'rules':[{'industry_id':'hardware','drawdown_threshold':None,'valuation_route':'产品周期DCF'}]}
        result=calculation_inputs(snapshot,rules,snapshot['acquired_at'])['inputs'][0]
        self.assertAlmostEqual(result['range_descriptor']['decline_from_52w_high'],0.2)
        self.assertAlmostEqual(result['range_descriptor']['position_in_52w_range'],0.75)
        self.assertEqual(result['range_status'],'available')
        self.assertEqual(result['deep_decline_status'],'threshold_not_calibrated')
        self.assertEqual(result['action_gate'],'blocked')
        self.assertEqual(result['source_ref']['sha256'],snapshot['source_sha256'])

    def test_range_endpoints_invalid_ranges_and_missing(self):
        """【UT-SNAPSHOT-08: 52周高低点端点边界与非法倒挂区间拦截】

        1. 测试功能与测试点:
           - 验证端点边界极值测试 (现价恰好等于最高价、最低价)。
           - 验证非法倒挂区间拦截: 高低点相同 (50,50,50)、现价跌破最低价 (19,100,20)、现价超过最高价 (101,100,20)、最高最低倒挂 (50,20,100)。
           - 验证输入缺失时的缺失字段追踪。

        2. 正常函数业务边界与参数契约:
           - 当 Low <= Price <= High 且 High > Low 时 range_status 为 available；其余异常情况均为 inconsistent_range 或 missing_inputs。

        3. 测试数据与模拟场景说明:
           - 涵盖 6 种正常与异常价格组合，以及 low52 数据源报错场景。

        4. 预期断言与结果验证:
           - 正常端点输出正确的 (decline, position)。
           - 异常情况断言 range_status 为 'inconsistent_range' 或 'missing_inputs'。
        """
        for price,high,low,expected in [(100,100,20,(0,1)),(20,100,20,(0.8,0)),
                                       (50,50,50,None),(19,100,20,None),(101,100,20,None),(50,20,100,None)]:
            with self.subTest(price=price,high=high,low=low):
                snapshot=self.run_snapshot()
                for name,value in [('price',price),('high52',high),('low52',low)]:
                    snapshot['quotes'][0]['fields'][name].update(value=value,status='ok')
                row=calculation_inputs(snapshot,{'rules':[]},snapshot['acquired_at'])['inputs'][0]
                if expected is None:
                    self.assertIsNone(row['range_descriptor'])
                    self.assertEqual(row['range_status'],'inconsistent_range')
                else:
                    self.assertAlmostEqual(row['range_descriptor']['decline_from_52w_high'],expected[0])
                    self.assertAlmostEqual(row['range_descriptor']['position_in_52w_range'],expected[1])
        snapshot=self.run_snapshot()
        snapshot['quotes'][0]['fields']['low52'].update(status='provider_error',value=None)
        row=calculation_inputs(snapshot,{'rules':[]},snapshot['acquired_at'])['inputs'][0]
        self.assertIsNone(row['range_descriptor'])
        self.assertEqual(row['range_status'],'missing_inputs')
        self.assertIn('low52',row['missing_fields'])

    def test_path_escape(self):
        """【UT-SNAPSHOT-09: 越界相对路径与绝对路径越狱物理拦截】

        1. 测试功能与测试点:
           - 验证系统根目录安全沙箱防御，严禁通过父目录遍历 (../)、Windows绝对盘符 (C:/)、UNC网络共享 (//server) 或 URI 协议访问项目外文件。

        2. 正常函数业务边界与参数契约:
           - local_path 仅接受项目根目录内的相对路径。

        3. 测试数据与模拟场景说明:
           - 攻击注入: '../x.json', 'C:/x.json', '//server/x', 'file://x'。

        4. 预期断言与结果验证:
           - 断言上述所有越界路径均抛出 ValueError。
        """
        for name in ('../x.json', 'C:/x.json', '//server/x', 'file://x'):
            with self.assertRaises(ValueError): local_path(name)

    def test_real_reverse_dcf_binding_and_currency(self):
        """【UT-SNAPSHOT-10: 真实行情反向DCF绑定与多币种一致性校验】

        1. 测试功能与测试点:
           - 验证快照中的现价与反向 DCF 求解器入参真实绑定，杜绝模板假数据。
           - 验证跨币种错配拦截 (如美元标的与日元请求错配)。

        2. 正常函数业务边界与参数契约:
           - currency 必须与标的结算币种完全一致。

        3. 测试数据与模拟场景说明:
           - 传入现价 336.64 的 USD 行情快照，绑定反向 DCF 计算；随后切换 currency 为 'JPY' 测试拦截。

        4. 预期断言与结果验证:
           - 断言 target_price 绑定为 336.64，求解状态为 'converged' 或 'outside_bounds'。
           - 断言币种错配时抛出 ValueError。
        """
        quote = self.run_snapshot()['quotes'][0]
        request = {'method':'reverse_dcf','ticker':quote['ticker'],'currency':'USD',
            'parameters':{'cash_flow':100,'years':5,'discount_rate':0.1,'terminal_growth':0.02,'shares':10,'scope':'FCFF'}}
        result = bind_reverse_dcf(quote, request)
        self.assertEqual(result['parameters']['target_price'],336.64)
        self.assertIn(result['result']['status'], ('converged','outside_bounds'))
        request['currency']='JPY'
        with self.assertRaises(ValueError): bind_reverse_dcf(quote,request)


if __name__ == '__main__': unittest.main()
