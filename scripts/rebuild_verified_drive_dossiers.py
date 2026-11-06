"""从已登记事实重建云盘605份公司档案；离线生成、逐份校验，上传另用宿主MCP。"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.evidence_dossiers import build_company_dossier, validate_dossier, dossier_sections

AUDIT='data/audits/drive-deep-analysis-20261012'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',default='reports/replacements/drive-20261012')
    parser.add_argument('--limit',type=int,help='仅用于小批校验，不生成完整替换清单')
    parser.add_argument('--json-only',action='store_true',help='只验证结构，不生成PDF')
    args=parser.parse_args()
    relative=Path(args.output_dir)
    if relative.is_absolute() or '..' in relative.parts or ':' in args.output_dir or args.output_dir.startswith(('\\','/')):
        parser.error('输出目录必须在项目内')
    output=(ROOT/relative).resolve()
    if not output.is_relative_to(ROOT.resolve()) or output==ROOT.resolve(): parser.error('输出目录越界或为项目根')
    inventory=json.loads((ROOT/AUDIT/'inventory.json').read_text(encoding='utf8'))['files']
    # 原folder listing保留JP在前、US在后，精确98/507身份和总数需在审计清单中断言。
    if len(inventory)!=605 or len({f['id'] for f in inventory})!=605: raise ValueError('原始目录范围变化')
    if args.limit is not None:
        if not 1<=args.limit<=len(inventory): parser.error('limit超出范围')
        inventory=inventory[:args.limit]
    output.mkdir(parents=True,exist_ok=True)
    if (output/'manifest.json').exists(): raise ValueError('替换版本已存在，禁止覆写')
    if not args.json_only:
        import fitz
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.colors import HexColor
        # 字体由项目内PyMuPDF提供并嵌入PDF，不依赖Windows外部字体。
        font_path=ROOT/'assets/fonts/research-cjk.ttf'
        font_path.parent.mkdir(parents=True,exist_ok=True)
        if not font_path.exists(): font_path.write_bytes(fitz.Font('cjk').buffer)
        pdfmetrics.registerFont(TTFont('ResearchCJK',str(font_path)))
        body=ParagraphStyle('Body',fontName='ResearchCJK',fontSize=9,leading=14,wordWrap='CJK',spaceAfter=7)
        heading=ParagraphStyle('Heading',parent=body,fontSize=12,leading=18,textColor=HexColor('#17365D'),spaceBefore=12)
        title_style=ParagraphStyle('Title',parent=body,fontSize=16,leading=23,textColor=HexColor('#17365D'),spaceAfter=14)
    manifest=[]
    for index,file in enumerate(inventory):
        market='JP' if index<98 else 'US'
        if not isinstance(file['title'],str) or any(c in file['title'] for c in ('/','\\',':')) or not file['title'].endswith('.pdf'):
            raise ValueError('远程文件名不能作为越界输出路径')
        symbol=file['title'].split('_',1)[0]
        # 605份均为符号_名称.pdf；不从旧报告正文读取公司财务或评级。
        data=build_company_dossier(symbol,market,file['title'].removesuffix('.pdf'))
        validate_dossier(data)
        directory=output/market;directory.mkdir(parents=True,exist_ok=True)
        json_path=directory/(symbol+'.json')
        if json_path.exists(): raise ValueError('同市场证券代码重复')
        raw=(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8')
        json_path.write_bytes(raw)
        pdf_path=directory/file['title']
        item={'old_file_id':file['id'],'old_url':file['url'],'market':market,'symbol':symbol,'file_name':file['title'],
            'json_path':json_path.relative_to(ROOT).as_posix(),'json_sha256':hashlib.sha256(raw).hexdigest(),
            'pdf_path':None,'pdf_sha256':None,'facts_count':len(data['facts']),'research_status':data['research_status'],'validation_status':'checked'}
        if not args.json_only:
            story=[Paragraph(html.escape(data['display_name'])+'<br/>公司数据档案：已核实字段与待补项',title_style),
                Paragraph('制作日期：2026-10-12。旧版无来源数字已撤销；本版不宣称完成深度研究。',body)]
            for title,paragraphs in dossier_sections(data):
                story.append(Paragraph(html.escape(title),heading))
                story.extend(Paragraph(html.escape(p),body) for p in paragraphs)
            def footer(canvas,doc):
                canvas.setFont('ResearchCJK',8)
                canvas.drawString(42,25,f"{market}:{symbol} | 已核实字段与缺口 | 第{doc.page}页")
            SimpleDocTemplate(str(pdf_path),pagesize=(595.28,841.89),rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
            doc=fitz.open(pdf_path)
            text=''.join(page.get_text() for page in doc)
            if symbol not in text or '旧版无来源数字已撤销' not in text: raise ValueError('PDF文本缺失或字体错误')
            if any(bad in text for bad in ['主营旗舰业务贡献约 68%','净保留率 (NRR) 维持在 115%','前五大核心供应商采购占比约 48%']): raise ValueError('假模板事实泄漏')
            for fact in data['facts']:
                if fact['value'] not in text: raise ValueError('财务事实未完整写入PDF')
            doc.close()
            item.update(pdf_path=pdf_path.relative_to(ROOT).as_posix(),pdf_sha256=hashlib.sha256(pdf_path.read_bytes()).hexdigest())
        manifest.append(item)
    result={'schema_version':'1.0.0','created_at':datetime.now(timezone.utc).isoformat(),
        'target_folder_id':'CONFIGURE_YOUR_OWN_CLOUD_TARGET','complete_replacement_set':args.limit is None and not args.json_only,
        'count':len(manifest),'with_verified_facts':sum(bool(f['facts_count']) for f in manifest),
        'full_deep_research_completed':0,'files':manifest}
    (output/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
