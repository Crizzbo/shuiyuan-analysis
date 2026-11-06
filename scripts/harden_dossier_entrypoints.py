"""清除旧模板与绕行入口；运行前原代码已归档，保留历史生成物待替换。"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    replacements={
      'financial_reporting/pdf_templates.py':'''"""仅渲染通过来源重建校验的档案。"""
from financial_reporting.evidence_dossiers import render_dossier_html
def render_deep_dossier_pdf_html(data): return render_dossier_html(data)
def render_daily_briefing_pdf_html(data):
    raise ValueError('旧无证据的日报评级模板已停用；使用登记的每日简报契约')
''',
      'scripts/build_full_universe.py':'''"""旧硬编码财务库构建入口停用。"""
def update_company_universe():
    raise ValueError('禁止从硬编码财务重建注册表；只能维护候选身份与登记事实')
if __name__=='__main__': update_company_universe()
''',
      'scripts/build_company_archives.py':'''"""公司归档入口委托证据驱动生成器。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.rebuild_verified_drive_dossiers import main
if __name__=='__main__': main()
'''}
    backup=ROOT/'data/audits/drive-deep-analysis-20261012/code-originals'
    for relative,text in replacements.items():
        if not (backup/Path(relative).name).exists(): raise ValueError('缺原代码审计副本')
        (ROOT/relative).write_text(text,encoding='utf8')
    for relative in ('scripts/sync_pdf_to_gdrive.py','scripts/sync_final_pdf_to_gdrive.py'):
        p=ROOT/relative;old=p.read_text(encoding='utf8')
        target=backup/p.name
        if not target.exists(): target.write_text(old,encoding='utf8')
        p.write_text('"""旧云盘同步已停用：不得按文件名跳过校验或同步旧假数据。"""\n'
            'def main():\n    raise ValueError("请使用已校验替换清单及宿主Google Drive MCP；禁止旧gdrive CLI自动上传")\n'
            'if __name__=="__main__": main()\n',encoding='utf8')
    p=ROOT/'financial_reporting/market_summary_generator.py';old=p.read_text(encoding='utf8')
    target=backup/p.name
    if not target.exists(): target.write_text(old,encoding='utf8')
    p.write_text('"""无证据的宏观新闻和自动股票推荐模板停用。"""\n'
        'def render_market_summary_briefing_html(*args,**kwargs):\n    raise ValueError("仅能使用已登记新闻和行情生成每日简报")\n',encoding='utf8')
    # 资产负债率必须使用总负债，不能把有息债务冒充总负债。
    p=ROOT/'financial_reporting/generic_metrics.py';old=p.read_text(encoding='utf8')
    if not (backup/p.name).exists(): (backup/p.name).write_text(old,encoding='utf8')
    old=old.replace('if "total_debt" in d and "total_assets" in d:\n            safe_compute("debt_to_assets", cls.debt_to_assets, d["total_debt"], d["total_assets"])',
        'if "total_liabilities" in d and "total_assets" in d:\n            safe_compute("debt_to_assets", cls.debt_to_assets, d["total_liabilities"], d["total_assets"])')
    p.write_text(old,encoding='utf8')

if __name__=='__main__': main()
