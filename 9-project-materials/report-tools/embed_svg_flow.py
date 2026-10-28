from __future__ import annotations

import os
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(r"C:\Users\Lenovo\Desktop\省一改")
DOCX = ROOT / "项目报告书-智析万卷：面向ESG报告的自适应布局分析与要素提取-专业团队ProMax-国赛专项修订版.docx"
ASSET_DIR = ROOT / "tmp" / "report_assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)
SVG = ASSET_DIR / "企业端到端交付闭环图.svg"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def make_svg() -> str:
    boxes = [
        (110, 190, "1", "批量上传PDF", "标准输入", "green"),
        (625, 190, "2", "文件校验与去重", "准入控制", "green"),
        (1140, 190, "3", "异步任务处理", "状态可查询", "green"),
        (1655, 190, "4", "60字段结构化输出", "证据可追溯", "green"),
        (365, 480, "5", "低可信字段复核", "人机协同", "blue"),
        (885, 480, "6", "JSON接口 / CSV导出", "标准化交付", "blue"),
        (1405, 480, "7", "跨企业指标对比", "分析应用", "blue"),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="2200" height="920" viewBox="0 0 2200 920">',
        '<defs><style><![CDATA[',
        '.title{font:700 58px "Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#2F7D64}',
        '.box-title{font:700 32px "Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#20332B}',
        '.sub{font:400 26px "Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#5F6B66}',
        '.num{font:700 32px "Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#fff;text-anchor:middle;dominant-baseline:middle}',
        '.footer{font:400 26px "Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#8C5A1E}',
        ']]></style>',
        '<marker id="arrowG" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 Z" fill="#8AA89B"/></marker>',
        '<marker id="arrowB" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L12,6 L0,12 Z" fill="#477FA8"/></marker>',
        '</defs>',
        '<rect width="2200" height="920" fill="#FFFFFF"/>',
        '<text x="1100" y="90" class="title" text-anchor="middle">ESGMiner企业端到端交付闭环</text>',
        '<line x1="160" y1="130" x2="2040" y2="130" stroke="#4F9A78" stroke-width="5"/>',
    ]
    for x, y, n, title, sub, palette in boxes:
        if palette == "green":
            fill, stroke = "#EAF5F0", "#2F7D64"
        else:
            fill, stroke = "#EAF2F8", "#477FA8"
        parts += [
            f'<rect x="{x}" y="{y}" width="430" height="178" rx="25" fill="{fill}" stroke="{stroke}" stroke-width="4"/>',
            f'<circle cx="{x+52}" cy="{y+55}" r="30" fill="{stroke}"/>',
            f'<text x="{x+52}" y="{y+57}" class="num">{n}</text>',
            f'<text x="{x+102}" y="{y+57}" class="box-title">{title}</text>',
            f'<text x="{x+102}" y="{y+130}" class="sub">{sub}</text>',
        ]
    parts += [
        '<path d="M550 279 H610" stroke="#8AA89B" stroke-width="7" fill="none" marker-end="url(#arrowG)"/>',
        '<path d="M1065 279 H1125" stroke="#8AA89B" stroke-width="7" fill="none" marker-end="url(#arrowG)"/>',
        '<path d="M1580 279 H1640" stroke="#8AA89B" stroke-width="7" fill="none" marker-end="url(#arrowG)"/>',
        '<path d="M1870 378 V430 H580 V465" stroke="#8AA89B" stroke-width="7" fill="none" marker-end="url(#arrowG)"/>',
        '<path d="M805 569 H870" stroke="#477FA8" stroke-width="7" fill="none" marker-end="url(#arrowB)"/>',
        '<path d="M1325 569 H1390" stroke="#477FA8" stroke-width="7" fill="none" marker-end="url(#arrowB)"/>',
        '<rect x="170" y="765" width="1860" height="105" rx="22" fill="#FFF7EA" stroke="#D38A36" stroke-width="4"/>',
        '<text x="1100" y="830" class="footer" text-anchor="middle">异常闭环：准入跳过 ｜ 解析降级 ｜ 检索回退 ｜ 预算耗尽标记 ｜ 低可信结果复核</text>',
        '</svg>',
    ]
    return "".join(parts)


svg_text = make_svg()
SVG.write_text(svg_text, encoding="utf-8")

with zipfile.ZipFile(DOCX, "r") as zin:
    names = zin.namelist()
    document_xml = ET.fromstring(zin.read("word/document.xml"))
    rels_xml = ET.fromstring(zin.read("word/_rels/document.xml.rels"))
    types_xml = ET.fromstring(zin.read("[Content_Types].xml"))

    body = document_xml.find(f"{{{W}}}body")
    children = list(body)
    caption_idx = None
    for i, el in enumerate(children):
        text = "".join(t.text or "" for t in el.iter(f"{{{W}}}t"))
        if "企业端到端交付闭环图" in text:
            caption_idx = i
            break
    if caption_idx is None or caption_idx == 0:
        raise RuntimeError("Flow diagram caption not found")
    drawing_p = children[caption_idx - 1]
    blip = drawing_p.find(f".//{{{A}}}blip")
    if blip is None:
        raise RuntimeError("Flow diagram drawing relationship not found")
    rid = blip.get(f"{{{R}}}embed")
    if not rid:
        raise RuntimeError("Flow diagram relationship id is empty")

    rel_el = None
    for rel in rels_xml.findall(f"{{{REL}}}Relationship"):
        if rel.get("Id") == rid:
            rel_el = rel
            break
    if rel_el is None:
        raise RuntimeError(f"Relationship {rid} not found")
    old_target = rel_el.get("Target")
    new_target = "media/enterprise_delivery_flow.svg"
    rel_el.set("Target", new_target)

    for nv in drawing_p.findall(f".//{{{PIC}}}cNvPr"):
        nv.set("name", "企业端到端交付闭环图.svg")
        nv.set("descr", "ESGMiner企业端到端交付闭环")

    if not any(x.get("Extension", "").lower() == "svg" for x in types_xml.findall(f"{{{CT}}}Default")):
        default = ET.Element(f"{{{CT}}}Default")
        default.set("Extension", "svg")
        default.set("ContentType", "image/svg+xml")
        types_xml.append(default)

    # The user does not require directory refresh; remove the auto-refresh flag added during generation.
    settings_xml = ET.fromstring(zin.read("word/settings.xml"))
    for update in list(settings_xml.findall(f"{{{W}}}updateFields")):
        settings_xml.remove(update)

    referenced_old = [r for r in rels_xml.findall(f"{{{REL}}}Relationship") if r.get("Target") == old_target]
    old_zip_name = "word/" + old_target.replace("\\", "/")
    temp_docx = DOCX.with_suffix(".svg.tmp.docx")
    with zipfile.ZipFile(temp_docx, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            if name == "word/document.xml":
                data = ET.tostring(document_xml, encoding="utf-8", xml_declaration=True)
            elif name == "word/_rels/document.xml.rels":
                data = ET.tostring(rels_xml, encoding="utf-8", xml_declaration=True)
            elif name == "[Content_Types].xml":
                data = ET.tostring(types_xml, encoding="utf-8", xml_declaration=True)
            elif name == "word/settings.xml":
                data = ET.tostring(settings_xml, encoding="utf-8", xml_declaration=True)
            elif name == old_zip_name and not referenced_old:
                continue
            else:
                data = zin.read(name)
            zout.writestr(name, data)
        zout.writestr("word/" + new_target, svg_text.encode("utf-8"))

os.replace(temp_docx, DOCX)
print(DOCX)
print(SVG)
print("RELATIONSHIP", rid, old_target, "->", new_target)
