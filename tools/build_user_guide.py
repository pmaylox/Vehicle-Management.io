"""Build the versioned tester guide using the bundled PDF runtime."""
from pathlib import Path
import json
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    ListFlowable, ListItem,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "docs/milesage_1_4_10_guide.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs/MileSage_1_4_10_Phone_and_Desktop_User_Guide.pdf"
pdfmetrics.registerFont(TTFont("Guide", "C:/Windows/Fonts/segoeui.ttf"))
pdfmetrics.registerFont(TTFont("GuideBold", "C:/Windows/Fonts/segoeuib.ttf"))
pdfmetrics.registerFontFamily("Guide", normal="Guide", bold="GuideBold")
INK = colors.HexColor("#292724")
MUTED = colors.HexColor("#6B655E")
ACCENT = colors.HexColor("#B65C3A")
body = ParagraphStyle("Body", fontName="Guide", fontSize=10.6, leading=14.4,
                      textColor=INK, spaceAfter=7)
intro = ParagraphStyle("Intro", parent=body, fontSize=11.1, leading=15.3, spaceAfter=12)
h1 = ParagraphStyle("Title", fontName="GuideBold", fontSize=22, leading=26,
                    textColor=colors.black, spaceAfter=10, keepWithNext=True)
h2 = ParagraphStyle("Heading", fontName="GuideBold", fontSize=12.4, leading=16,
                    textColor=colors.black, spaceBefore=9, spaceAfter=5, keepWithNext=True)
cell = ParagraphStyle("Cell", parent=body, fontSize=9.7, leading=12.7, spaceAfter=0)
headcell = ParagraphStyle("HeadCell", parent=cell, fontName="GuideBold")

def para(text, style=body):
    return Paragraph(escape(text), style)

def footer(canvas, doc):
    width, height = letter
    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.setFont("GuideBold", 9)
    canvas.drawString(46, height - 30, "MileSage")
    canvas.setFont("Guide", 8.4)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - 46, height - 30, "by Red Dirt Coding | " + DATA["version"])
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1)
    canvas.line(46, 40, width - 46, 40)
    canvas.setFont("Guide", 8)
    canvas.drawString(46, 26, "Tester guide | November 25 2026 | Android and Windows desktop")
    canvas.drawRightString(width - 46, 26, f"{doc.page} / {len(DATA['pages'])}")
    canvas.restoreState()

story = []
html = ["<!doctype html><html><head><meta charset='utf-8'><title>" + DATA["title"] +
        "</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:800px;margin:24px auto;padding:0 18px;color:#292724}h1,h2,h3{color:#000}table{border-collapse:collapse;width:100%}td,th{padding:8px;border:1px solid #DDD5CD;text-align:left}th{background:#F1DDD2}section{margin-bottom:40px}</style></head><body>",
        "<h1>" + DATA["title"] + "</h1><p>" + DATA["version"] + " | " + DATA["date"] + "</p>"]
for index, page in enumerate(DATA["pages"]):
    if index:
        story.append(PageBreak())
    if index == 0:
        story.append(para(DATA["title"], h1))
        story.append(para(page["title"], h2))
    else:
        story.append(para(page["title"], h1))
    story.append(para(page["intro"], intro))
    html.append("<section><h2>" + escape(page["title"]) + "</h2><p>" + escape(page["intro"]) + "</p>")
    for section in page["sections"]:
        story.append(para(section["heading"], h2))
        html.append("<h3>" + escape(section["heading"]) + "</h3>")
        if "text" in section:
            story.append(para(section["text"]))
            html.append("<p>" + escape(section["text"]) + "</p>")
        for key, kind in [("steps", "1"), ("bullets", "bullet")]:
            if key in section:
                story.append(ListFlowable([ListItem(para(text)) for text in section[key]],
                                          bulletType=kind, leftIndent=16,
                                          bulletFontName="Guide", bulletFontSize=10,
                                          spaceAfter=3))
                tag = "ol" if key == "steps" else "ul"
                html.append("<"+tag+">"+"".join("<li>"+escape(text)+"</li>" for text in section[key])+"</"+tag+">")
        if "table" in section:
            rows = [[para(text, headcell if row == 0 else cell) for text in values]
                    for row, values in enumerate(section["table"])]
            table = Table(rows, colWidths=[125, 395], hAlign="LEFT", repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1DDD2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), .35, colors.HexColor("#DDD5CD")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(table)
            html.append("<table>"+"".join("<tr>"+"".join("<"+("th" if i == 0 else "td")+">"+escape(t)+"</"+("th" if i == 0 else "td")+">" for t in row)+"</tr>" for i,row in enumerate(section["table"]))+"</table>")
    html.append("</section>")
html.append("</body></html>")
(ROOT / "docs/MileSage_1_4_10_Phone_and_Desktop_User_Guide.html").write_text("\n".join(html), encoding="utf-8")
doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=46, rightMargin=46,
                        topMargin=50, bottomMargin=52, title=DATA["title"],
                        author="Red Dirt Coding", subject=DATA["version"])
doc.build(story, onFirstPage=footer, onLaterPages=footer)
from pypdf import PdfReader
reader = PdfReader(str(OUT))
assert len(reader.pages) == len(DATA["pages"]), f"Unexpected page count: {len(reader.pages)}"
for page, expected in zip(reader.pages, DATA["pages"]):
    assert expected["title"] in page.extract_text()
print(f"Created {len(reader.pages)} pages: {OUT}")
