"""仅渲染通过来源重建校验的档案。"""
from financial_reporting.evidence_dossiers import render_dossier_html
def render_deep_dossier_pdf_html(data): return render_dossier_html(data)
def render_daily_briefing_pdf_html(data):
    raise ValueError('旧无证据的日报评级模板已停用；使用登记的每日简报契约')
