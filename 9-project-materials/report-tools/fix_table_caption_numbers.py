from pathlib import Path
from docx import Document

root = Path(r"C:\Users\Lenovo\Desktop\省一改")
path = root / "项目报告书-智析万卷：面向ESG报告的自适应布局分析与要素提取-专业团队ProMax-国赛专项修订版.docx"
doc = Document(path)

captions = []
for p in doc.paragraphs:
    instr = "".join(p._p.xpath(".//w:instrText/text()"))
    if "SEQ 表" in instr:
        captions.append(p)

for number, p in enumerate(captions, 1):
    separated = False
    updated = False
    for run in p.runs:
        field_types = run._r.xpath(".//w:fldChar/@w:fldCharType")
        if "separate" in field_types:
            separated = True
            continue
        if separated and "end" in field_types:
            break
        if separated and run.text and not updated:
            run.text = str(number)
            updated = True
    if not updated:
        raise RuntimeError(f"Cached SEQ result not found: {p.text}")

doc.save(path)
print(path)
print([p.text for p in captions])
