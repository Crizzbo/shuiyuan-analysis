# 六步分析数据契约

- [公司证据封套2.0](company-evidence-dossier.schema.json) 与 [公司证据索引2.0](company-archive.schema.json)：假数据修复后的公司档案契约。数值必须通过登记原文重建校验，形状校验不能证明事实成立；旧版强制评级和无来源财务字段已撤销。

- [行业输入绑定方案契约](industry-input-binding-plans.schema.json)：动态中文槽位、期间与显式输入角色；生成器和台账读取入口均强制校验。详细业务约束见 [绑定方案说明](../docs/industry-input-binding-plans-contract.md)。

- [完整研究 JSON Schema](research.schema.json)：Draft 2020-12，包含共同结构和六步专用 `$defs`。
- [资料登记 Schema](source-manifest.schema.json)：项目内来源与修订契约。
- [字段与流程说明](../docs/03-六步分析Schema与流程规则.md)
- [Schema 配套说明书](../docs/05-Schema配套说明书.md)
- [逐字段数据字典](../docs/05a-Schema逐字段数据字典.md)
- [机器可读字段指南](schema-field-guide.json)
- [待填研究模板](../knowledge/templates/research.pending.json)
- [完成流程合成示例](../examples/completed.synthetic.json)
- [证据不足合成示例](../examples/blocked.synthetic.json)
- [待启动合成示例](../examples/pending.synthetic.json)

所有 `$ref` 均为单文件内部引用。`$schema` 标准 URI 和 `$id` URN 仅为标识，项目校验器不联网解析。不依赖第三方 JSON Schema 库。

在项目根目录执行：

```powershell
python scripts/validate_research.py examples/completed.synthetic.json
python scripts/test_research_contract.py
python scripts/validate_knowledge_structure.py
```

校验器仅支持当前 Schema 使用的关键字，新增不支持关键字会拒绝，不会静默略过。它不是通用 JSON Schema 实现。

构建入口是项目内 `scripts/build_research_schema.py`。需要修改契约时先修改构建源，再生成并回归；版本升级须制定迁移方案。示例构建脚本只用于合成 fixtures，不执行真实研究。

财报契约：`financial-report.schema.json`；正式财务事实封套：`registered-financial-fact.schema.json`。各自由 `scripts/build_financial_schema.py`、`scripts/build_registered_fact_schema.py` 生成。[财报数据字典](../docs/14a-财报数据字典.md)包含逐表说明。

研究及资料登记契约均支持 1.0.0/1.1.0：旧版仍强制精确 published_at，新版允许未知时刻，必填 published_date 与 publication_precision；不允许用午夜补造时刻。新研究模板采用 1.1.0，既有 1.0.0 实例继续可读。[升级与迁移说明](../docs/15-研究证据时间契约升级与迁移.md)。

行业专属[采集规格 Schema](industry-specific-specifications.schema.json)由 `scripts/build_industry_specific_specs.py` 生成，使用项目内 jsonschema 校验。配套[统一目录与独立数据字典](../knowledge/metrics/industry-specific/README.md)覆盖 41 行业和 123 个父驱动；父驱动中的复合字段逐项指定单位和统计期间。
