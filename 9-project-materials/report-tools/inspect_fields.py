from pathlib import Path
from docx import Document
from lxml import etree

root = Path(r"C:\Users\Lenovo\Desktop\省一改")
src = next(root.glob("项目报告书*ProMax.docx"))
doc = Document(src)
for idx in [100,103,119,163,166,183,202,215,231,234,237,242,248,254,257]:
    p = doc.paragraphs[idx]
    print("IDX", idx, "TEXT", p.text, "STYLE", p.style.style_id)
    print(etree.tostring(p._p, encoding="unicode", pretty_print=False)[:1800])
    print()
