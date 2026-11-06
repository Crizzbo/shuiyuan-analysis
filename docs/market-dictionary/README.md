# 行情数据字典目录

契约：`schemas/market-snapshot.schema.json`，版本1.0.0。标准化输出容器有 snapshot 和 calculation_inputs；schema 校验 snapshot，计算输入由固定程序生成。

| 表 | 业务粒度 | 说明文件 |
|---|---|---|
| snapshot | 一次 MCP 读取批次 | `docs/market-dictionary/snapshot.md` |
| quote | 批次内一只证券 | `docs/market-dictionary/quote.md` |
| field | 一只证券的一项供应商字段 | `docs/market-dictionary/field.md` |
| calculation_input | 一只证券的计算输入与门槛 | `docs/market-dictionary/calculation-input.md` |
| sepa_signal | 单只证券的米奈尔维尼SEPA时机与风控边界 | `docs/market-dictionary/sepa-signal.md` |

空值是未知或不可用，不表示0。供应商原值与本项目计算值分开。财报周期、复权方式及证券身份未审核时不能补造解释。
