"""深度档案仅消费本地已审核证据；不读取调用方的未登记财务或宏观默认值。"""
from financial_reporting.evidence_dossiers import build_company_dossier


def build_deep_dossier_data(company, macro=None):
    return build_company_dossier(
        company["ticker"].split(":")[-1],
        company["market"],
        company.get("name_zh") or company.get("name") or company["ticker"],
    )


def build_daily_briefing_data(company, macro=None):
    raise ValueError("旧自动评级日报路径已停用；使用已登记行情与新闻契约生成日报")
