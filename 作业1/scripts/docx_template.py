"""把 Markdown 正文渲染进课程作业模板。

课程模板本身就是一个 docx：前三段是「日期 / 课程名 — 作业X / 学号 姓名 得分」，
第四段是「本次作业回答如下：」，后面的正文留给学生自己填。
模板还带了页脚和页边距设置，手工重排很容易丢掉这些。

所以这里不重做版式，而是分两步：
1. 用 ``pandoc --reference-doc=模板`` 把 Markdown 转成正文 docx。
   pandoc 会把模板的 styles.xml、页脚、页面设置原样带走，正文自动套用模板的标题/正文样式。
2. 把模板自己的表头四段插到正文最前面，并填入学号、姓名、日期、作业序号。

这样出来的文档，版式与模板一致，内容由脚本生成。
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import date
from pathlib import Path

# 模板里的样式 id。它们是模板 styles.xml 里真实存在的，直接沿用，
# 不要改成 Heading1 之类 —— 那会套用 pandoc 自己的样式，版式就和模板不一样了。
STYLE_DATE = "ac"
STYLE_TITLE = "a8"
STYLE_LINE = "1"

COURSE_NAME = "应用系统体系架构"

#: 版面可用宽度。见模板 sectPr：pgSz 11907 twips 宽，左右页边距各 1800 twips，
#: 剩下 8307 twips ≈ 14.65 cm。图片和表格都不能超过这个宽度，否则会被挤出页边。
TEXT_WIDTH_TWIPS = 11907 - 1800 - 1800
TEXT_WIDTH_EMU = int(TEXT_WIDTH_TWIPS / 1440 * 914400)  # twips -> inch -> EMU
#: 图片统一缩到 14.2 cm：贴着版心宽度在 Word 里容易顶到页边，留一点余量更稳。
IMAGE_WIDTH_EMU = int(14.2 / 2.54 * 914400)

#: pandoc 会引用一批样式名，但课程模板的 styles.xml 里没有它们。
#: 引用不存在的样式时 Word 静默套用默认值：表格没有边框、单元格字号跟着正文、
#: 行内代码不变宽。这里把缺的几个补上，表格和代码块的显示才稳定。
#: 表头加粗靠 tblStylePr + 表格自身的 firstRow 标记，不需要调 markdown。
MISSING_STYLES = """<w:style w:type="paragraph" w:customStyle="1" w:styleId="BodyText"><w:name w:val="Body Text"/><w:basedOn w:val="a"/><w:qFormat/><w:pPr><w:spacing w:before="0" w:after="120" w:line="300" w:lineRule="auto"/><w:ind w:left="0" w:right="0" w:firstLine="0"/></w:pPr></w:style><w:style w:type="paragraph" w:customStyle="1" w:styleId="FirstParagraph"><w:name w:val="First Paragraph"/><w:basedOn w:val="a"/><w:pPr><w:spacing w:before="0" w:after="120" w:line="300" w:lineRule="auto"/><w:ind w:left="0" w:right="0" w:firstLine="0"/></w:pPr></w:style><w:style w:type="paragraph" w:customStyle="1" w:styleId="Compact"><w:name w:val="Compact"/><w:basedOn w:val="a"/><w:pPr><w:spacing w:before="20" w:after="20" w:line="260" w:lineRule="auto"/><w:ind w:left="0" w:right="0" w:firstLine="0"/></w:pPr><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style><w:style w:type="character" w:customStyle="1" w:styleId="VerbatimChar"><w:name w:val="Verbatim Char"/><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:style><w:style w:type="character" w:customStyle="1" w:styleId="Emphasis"><w:name w:val="Emphasis"/><w:rPr><w:i/><w:iCs/></w:rPr></w:style><w:style w:type="table" w:customStyle="1" w:styleId="Table"><w:name w:val="Table"/><w:tblPr><w:tblW w:type="pct" w:w="5000"/><w:jc w:val="center"/><w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/></w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="60" w:type="dxa"/><w:left w:w="110" w:type="dxa"/><w:bottom w:w="60" w:type="dxa"/><w:right w:w="110" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:bCs/></w:rPr><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/></w:tcPr></w:tblStylePr></w:style>"""



def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def _run(text: str, *, underline: bool = False) -> str:
    """一个 run。rPr 的子元素顺序由 OOXML schema 固定：rFonts 在前，color 次之，u 在后。"""
    properties = '<w:rFonts w:hint="eastAsia"/><w:color w:val="auto"/>'
    if underline:
        properties += '<w:u w:val="single"/>'
    return f'<w:r><w:rPr>{properties}</w:rPr><w:t xml:space="preserve">{_escape(text)}</w:t></w:r>'


def _paragraph(style: str, runs: str, *, indented: bool = False) -> str:
    properties = f'<w:pPr><w:pStyle w:val="{style}"/>'
    if indented:
        properties += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr><w:ind w:left="360"/>'
    properties += '<w:jc w:val="both"/><w:rPr><w:color w:val="auto"/></w:rPr></w:pPr>'
    return f"<w:p>{properties}{runs}</w:p>"


def header_xml(student_id: str, student_name: str, homework_no: str, submit_date: str) -> str:
    """模板最前面的四段。"""
    blanks = " " * 8
    line = (
        _run("学号：")
        + _run(f" {student_id} ", underline=True)
        + _run("    ")
        + _run("姓名：")
        + _run(f" {student_name} ", underline=True)
        + _run("    ")
        + _run("得分：")
        + _run(blanks, underline=True)
    )
    return "".join(
        [
            _paragraph(STYLE_DATE, _run(submit_date)),
            _paragraph(STYLE_TITLE, _run(f"{COURSE_NAME} — 作业{homework_no}")),
            _paragraph(STYLE_LINE, line, indented=True),
            _paragraph(STYLE_LINE, _run("本次作业回答如下："), indented=True),
        ]
    )


#: 模板的 heading 2/3/4 只写了复杂文种字号（szCs），没写 w:sz，
#: 结果正文标题和正文一样是 11pt，层级看不出来。这里补上字号与段间距，
#: 让「一、二、」这类节标题明显大一号。heading 1 模板自己定了 13pt，
#: 而模板表头那行用的正是 heading 1，所以不动它。
HEADING_SIZES = {"2": 30, "3": 26, "4": 23}  # 半磅：30=15pt, 26=13pt, 23=11.5pt
HEADING_SPACING = {"2": (240, 120), "3": (200, 100), "4": (160, 80)}


def polish_styles(styles: str) -> str:
    """补齐缺失样式，并修掉两处会串版的地方。"""
    # 1. 补上 pandoc 引用了、模板里却没有的样式。
    if 'w:styleId="Compact"' not in styles:
        styles = styles.replace("</w:styles>", f"{MISSING_STYLES}</w:styles>", 1)

    # 2. 模板的标题样式挂着 numId=1，而 pandoc 重写了 numbering.xml，没有 1 号编号。
    #    悬空编号在 Word 里会被忽略，但不留它更干净；标题序号由 Markdown 里的「一、二、」负责。
    styles = re.sub(
        r"<w:numPr>\s*(?:<w:ilvl[^>]*/>\s*)?<w:numId w:val=\"1\"\s*/>\s*</w:numPr>", "", styles
    )

    # 3. 代码块样式：模板的 docDefaults 让段落默认左缩进 360 twips，
    #    代码块跟着缩进会挤出右边距；顺带把字号定死在 9pt。
    source_code = re.search(r'<w:style [^>]*w:styleId="SourceCode".*?</w:style>', styles, re.S)
    if source_code:
        block = source_code.group(0)
        fixed = block.replace(
            '<w:pPr><w:wordWrap w:val="off"/></w:pPr>',
            '<w:pPr><w:wordWrap w:val="off"/>'
            '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
            '<w:ind w:left="0" w:right="0" w:firstLine="0"/></w:pPr>'
            '<w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>',
        )
        styles = styles.replace(block, fixed, 1)

    # 4. 给 heading 2/3/4 补字号与段间距。
    for style_id, size in HEADING_SIZES.items():
        pattern = re.compile(r'<w:style [^>]*w:styleId="' + style_id + r'".*?</w:style>', re.S)
        found = pattern.search(styles)
        if not found:
            continue
        block = found.group(0)
        before, after = HEADING_SPACING[style_id]

        if '<w:szCs' in block:
            # rPr 里 rFonts、color 在前，sz 紧跟 szCs 之前才符合 schema 顺序。
            block = re.sub(
                r'<w:szCs w:val="\d+"\s*/>',
                f'<w:sz w:val="{size}" /><w:szCs w:val="{size}" />',
                block,
                count=1,
            )
        else:
            block = block.replace("</w:rPr>", f'<w:sz w:val="{size}" /><w:szCs w:val="{size}" /></w:rPr>', 1)

        block = re.sub(
            r'<w:spacing w:[^/]*/>',
            f'<w:spacing w:before="{before}" w:after="{after}" />',
            block,
            count=1,
        )
        styles = styles.replace(found.group(0), block, 1)

    return styles


TABLE_BORDERS = (
    "<w:tblBorders>"
    '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    "</w:tblBorders>"
)
TABLE_CELL_MARGIN = (
    "<w:tblCellMar>"
    '<w:top w:w="50" w:type="dxa"/><w:left w:w="85" w:type="dxa"/>'
    '<w:bottom w:w="50" w:type="dxa"/><w:right w:w="85" w:type="dxa"/>'
    "</w:tblCellMar>"
)
TABLE_LOOK = (
    '<w:tblLook w:firstRow="1" w:lastRow="0" w:firstColumn="0" '
    'w:lastColumn="0" w:noHBand="0" w:noVBand="0" w:val="0020" />'
)
# 表格正文 9pt、表头加粗；顺序按 OOXML 的 rPr 定义：b 在 sz 之前。
TABLE_RUN_PROPS = '<w:sz w:val="18" /><w:szCs w:val="18" />'
TABLE_HEADER_RUN_PROPS = '<w:b /><w:bCs />' + TABLE_RUN_PROPS
TABLE_CELL_SHD = '<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2" />'


def _decorate_run(run: str, *, header: bool) -> str:
    """给表格里的 run 套上字号（表头再套加粗）。

    rPr 的子元素顺序由 schema 固定，rFonts 必须排在 b / sz 之前，
    所以插入点选在 rFonts 之后；没有 rPr 的就新建一个。
    """
    props = TABLE_HEADER_RUN_PROPS if header else TABLE_RUN_PROPS

    if "<w:rPr />" in run:
        return run.replace("<w:rPr />", f"<w:rPr>{props}</w:rPr>", 1)
    if "<w:rPr>" in run:
        fonts = re.search(r"<w:rFonts[^>]*/>", run)
        if fonts:
            return run.replace(fonts.group(0), f"{fonts.group(0)}{props}", 1)
        return run.replace("<w:rPr>", f"<w:rPr>{props}", 1)
    return re.sub(
        r"<w:t(?:\s[^>]*)?>", lambda m: f"<w:rPr>{props}</w:rPr>{m.group(0)}", run, count=1
    )


def _fix_row(row: str, widths: list[int], *, header: bool) -> str:
    """按表格网格给每个单元格写死列宽，并顺手统一字号。"""
    column = 0

    def cell_width(_match: re.Match[str]) -> str:
        nonlocal column
        width = widths[column % len(widths)]
        column += 1
        shading = TABLE_CELL_SHD if header else ""
        return (
            f'<w:tcPr><w:tcW w:w="{width}" w:type="dxa" />{shading}'
            '<w:vAlign w:val="center" /></w:tcPr>'
        )

    row = re.sub(r"<w:tcPr\s*/>", cell_width, row)
    row = re.sub(r"<w:r>.*?</w:r>", lambda m: _decorate_run(m.group(0), header=header), row, flags=re.S)
    # 单元格段落不要继承 docDefaults 的左缩进，否则每格都往里缩一截。
    row = row.replace(
        '<w:pStyle w:val="Compact" />',
        '<w:pStyle w:val="Compact" /><w:ind w:left="0" w:right="0" w:firstLine="0" />',
    )
    return row


def _column_weights(table: str, column_count: int) -> list[int]:
    """按每一列里最长的单元格内容估算列宽权重。

    pandoc 给的是等宽列，长内容会被硬折成好几行（`check_inventory({"isbn": ...})`
    能折成好几行），短内容又白占地方。这里按内容长度重新分配。

    三点经验：
    - 中日韩字符按两个字宽计，否则中文列会被算得过窄；
    - 行内代码（VerbatimChar，等宽字体）每个字符比正文宽约三分之一，也要放大计；
    - 权重有上下限：下限保证「第 1 轮」这种短列不会被挤到折行，上限避免一列吃掉整张表。
    """
    weights = [0] * column_count

    for row in re.findall(r"<w:tr[ >].*?</w:tr>", table, re.S):
        for index, cell in enumerate(re.findall(r"<w:tc>.*?</w:tc>", row, re.S)):
            if index >= column_count:
                break
            total = 0.0
            for run in re.findall(r"<w:r>.*?</w:r>", cell, re.S):
                # 注意用 <w:t> / <w:t ...> 而不是 <w:t[^>]*>：后者会把 <w:tcPr> 也匹配进来。
                text = "".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", run, re.S))
                if not text:
                    continue
                mono = 'w:rStyle w:val="VerbatimChar"' in run
                total += sum(
                    2 if ord(char) > 0x2E80 else (1.35 if mono else 1.0) for char in text
                )
            weights[index] = max(weights[index], int(total + 0.5))

    return [max(min(weight, 36), 10) for weight in weights]


def _fix_table(match: re.Match[str]) -> str:
    """把一张表改成按内容分配列宽，并直接描边。

    这些格式全部写成直接格式而不是依赖表格样式：样式在不同渲染器里的支持不一致，
    直接格式则处处生效。表格样式仍然保留，作为 Word 里的兜底。
    """
    table = match.group(0)

    grid = [int(width) for width in re.findall(r'<w:gridCol w:w="(\d+)"\s*/>', table)]
    if not grid:
        return table

    weights = _column_weights(table, len(grid))
    total_weight = sum(weights) or 1
    widths = [max(1, round(TEXT_WIDTH_TWIPS * weight / total_weight)) for weight in weights]
    # 四舍五入会留下几 twips 的误差，补给最后一列，保证总宽正好等于版心。
    widths[-1] += TEXT_WIDTH_TWIPS - sum(widths)

    properties = (
        '<w:tblPr><w:tblStyle w:val="Table" />'
        f'<w:tblW w:type="dxa" w:w="{TEXT_WIDTH_TWIPS}" />'
        '<w:jc w:val="center" />'
        f"{TABLE_BORDERS}<w:tblLayout w:type=\"fixed\" />{TABLE_CELL_MARGIN}{TABLE_LOOK}</w:tblPr>"
    )
    table = re.sub(r"<w:tblPr>.*?</w:tblPr>", lambda _m: properties, table, count=1, flags=re.S)

    # 网格宽度与单元格宽度必须一致，否则固定布局下不同渲染器会各算各的。
    grid_xml = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{width}" />' for width in widths) + "</w:tblGrid>"
    table = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", lambda _m: grid_xml, table, count=1, flags=re.S)

    rows = re.findall(r"<w:tr[ >].*?</w:tr>", table, re.S)
    for index, row in enumerate(rows):
        table = table.replace(row, _fix_row(row, widths, header=index == 0), 1)
    return table


def polish_document(xml: str) -> str:
    """表格占满版心、图片不超过版心。"""
    if IMAGE_WIDTH_EMU > TEXT_WIDTH_EMU:
        raise SystemExit("配的图片宽度超过了版心宽度，会被挤出页边")

    xml = re.sub(r"<w:tbl>.*?</w:tbl>", _fix_table, xml, flags=re.S)

    # 图片按 EMU 记宽度。pandoc 会把图片放大到版心宽度，贴着页边不好看，
    # 统一缩到 14.2 cm，高度等比跟着缩。
    def clamp(match: re.Match[str]) -> str:
        cx, cy = int(match.group(1)), int(match.group(2))
        if cx <= IMAGE_WIDTH_EMU:
            return match.group(0)
        ratio = IMAGE_WIDTH_EMU / cx
        return f'<wp:extent cx="{IMAGE_WIDTH_EMU}" cy="{int(cy * ratio)}" />'

    xml = re.sub(r'<wp:extent cx="(\d+)" cy="(\d+)"\s*/>', clamp, xml)
    return xml


def render_docx(
    markdown_path: Path,
    template_path: Path,
    out_path: Path,
    *,
    student_id: str,
    student_name: str,
    homework_no: str,
    submit_date: str | None = None,
) -> Path:
    submit_date = submit_date or date.today().isoformat()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        body_docx = tmp_dir / "body.docx"

        subprocess.run(
            [
                "pandoc", str(markdown_path),
                "-f", "gfm", "-t", "docx",
                f"--reference-doc={template_path}",
                "-o", str(body_docx),
            ],
            check=True,
        )

        unpacked = tmp_dir / "unpacked"
        unpacked.mkdir()
        with zipfile.ZipFile(body_docx) as archive:
            names = archive.namelist()
            archive.extractall(unpacked)

        document = unpacked / "word" / "document.xml"
        xml = document.read_text(encoding="utf-8")
        if "<w:body>" not in xml:
            raise SystemExit("pandoc 输出的 document.xml 结构异常，找不到 <w:body>")

        header = header_xml(student_id, student_name, homework_no, submit_date)
        xml = xml.replace("<w:body>", f"<w:body>{header}", 1)
        document.write_text(polish_document(xml), encoding="utf-8")

        styles = unpacked / "word" / "styles.xml"
        styles.write_text(polish_styles(styles.read_text(encoding="utf-8")), encoding="utf-8")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            out_path.unlink()
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in names:
                archive.write(unpacked / name, name)

    return out_path


def check_template(template_path: Path) -> None:
    """确认模板里确实有我们要用的样式 id，避免静默套错样式。"""
    with zipfile.ZipFile(template_path) as archive:
        styles = archive.read("word/styles.xml").decode("utf-8")
    missing = [
        style
        for style in (STYLE_DATE, STYLE_TITLE, STYLE_LINE)
        if f'w:styleId="{style}"' not in styles
    ]
    if missing:
        raise SystemExit(f"模板缺少样式 {missing}，请确认使用的是课程的作业模版")


def zip_files(out_zip: Path, files: list[tuple[Path, str]]) -> Path:
    """按「归档内路径 -> 磁盘路径」打包，只收录显式列出的文件。"""
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in files:
            archive.write(source, arcname)
    return out_zip


def zip_tree(out_zip: Path, root: Path, include: list[str], exclude_dirs: set[str]) -> Path:
    """打包指定子目录，跳过缓存与第三方依赖。"""
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry in include:
            target = root / entry
            if target.is_file():
                archive.write(target, entry)
                continue
            for path in sorted(target.rglob("*")):
                if path.is_dir():
                    continue
                if any(part in exclude_dirs for part in path.relative_to(root).parts):
                    continue
                archive.write(path, path.relative_to(root).as_posix())
    return out_zip
