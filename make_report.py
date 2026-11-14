# -*- coding: utf-8 -*-
"""Dựng file báo cáo giữa kỳ môn Công nghệ Phần mềm — dự án SáchGóc Uni.

Chạy:  python make_report.py                 # toàn bộ báo cáo
       python make_report.py --only front    # chỉ phần đầu (kiểm tra bố cục)

Nội dung bám khung 2 chương của giảng viên; định dạng bám file mẫu
``Báo_Cáo_CNPM.docx`` (A4, Times New Roman 14 pt, giãn dòng 1.15).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.enum.text import (
    WD_ALIGN_PARAGRAPH,
    WD_BREAK,
    WD_LINE_SPACING,
    WD_TAB_ALIGNMENT,
    WD_TAB_LEADER,
)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "docs" / "report" / "assets"
LOGO = ROOT / "docs" / "logo-dau.png"
DEFAULT_OUT = ROOT / "docs" / "BaoCao_GiuaKy_CNPM_SachGocUni.docx"

FONT = "Times New Roman"
BODY_PT = 14
TEXT_WIDTH_CM = 15.0  # 21 - 3.5 - 2.5
BLACK = RGBColor(0, 0, 0)

#: Thông tin bìa.
COVER = {
    "school": "TRƯỜNG ĐẠI HỌC KIẾN TRÚC ĐÀ NẴNG",
    "faculty": "KHOA CÔNG NGHỆ THÔNG TIN",
    "kind": "BÁO CÁO GIỮA KÌ",
    "course": "HỌC PHẦN CÔNG NGHỆ PHẦN MỀM",
    "topic": "Xây dựng website trao đổi sách và đồ dùng học tập "
             "cho sinh viên — SáchGóc Uni",
    "teacher": "PGS. TS. PHẠM THỊ DUNG",
    "student": "Nguyễn Văn Hảo",
    "student_id": "2451220056",
    "class": "24CT1",
    "place_date": "Đà Nẵng, ngày 15 tháng 11 năm 2026",
}


# --------------------------------------------------------------- tiện ích XML

def _set_font(run_or_style, name: str = FONT, size_pt: float | None = None) -> None:
    """Gán font cho cả ba hệ chữ (ascii/hAnsi/cs) và font phương Đông."""
    font = run_or_style.font
    font.name = name
    if size_pt is not None:
        font.size = Pt(size_pt)
    element = run_or_style.element
    if not hasattr(element, "get_or_add_rPr"):
        return
    rpr = element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), name)


def _shade(paragraph, fill: str) -> None:
    """Tô nền một đoạn văn (dùng cho khối mã nguồn)."""
    ppr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    ppr.append(shd)


def _field(paragraph, instruction: str, placeholder: str = "") -> None:
    """Chèn một field Word (PAGE, TOC…) vào đoạn văn."""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, separate, text, end):
        run._r.append(node)


def _logo_stream():
    """Logo đặt trên nền trắng để không lộ khung xám của tệp gốc."""
    import io

    from PIL import Image

    image = Image.open(LOGO).convert("RGBA")
    flat = Image.new("RGBA", image.size, (255, 255, 255, 255))
    flat.alpha_composite(image)
    buffer = io.BytesIO()
    flat.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------- bộ dựng docx

class Doc:
    """Bọc python-docx để dựng báo cáo theo đúng quy ước trình bày."""

    def __init__(self) -> None:
        self.doc = Document()
        self.fig_no = 0
        self.tab_no = 0
        self.chapter = 0
        self._body_started = False
        self._first_h1 = True
        self.setup_page()

    # -- thiết lập chung ---------------------------------------------------

    def setup_page(self) -> None:
        section = self.doc.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.5)
        section.right_margin = Cm(2.5)
        section.header_distance = Cm(1.5)
        section.footer_distance = Cm(1.5)

        normal = self.doc.styles["Normal"]
        _set_font(normal, FONT, BODY_PT)
        fmt = normal.paragraph_format
        fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        fmt.line_spacing = 1.15
        fmt.space_after = Pt(6)
        fmt.space_before = Pt(0)

        self._style_heading("Heading 1", centered=True, page_break=True, size=14)
        self._style_heading("Heading 2", size=14)
        self._style_heading("Heading 3", italic=True, size=14)

    def _style_heading(
        self,
        name: str,
        *,
        centered: bool = False,
        italic: bool = False,
        page_break: bool = False,
        size: float = BODY_PT,
    ) -> None:
        style = self.doc.styles[name]
        _set_font(style, FONT, size)
        style.font.bold = True
        style.font.italic = italic
        style.font.color.rgb = BLACK
        fmt = style.paragraph_format
        fmt.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.LEFT
        )
        fmt.page_break_before = page_break
        fmt.keep_with_next = True
        fmt.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        fmt.line_spacing = 1.15
        fmt.space_before = Pt(0 if centered else 12)
        fmt.space_after = Pt(12 if centered else 6)
        fmt.first_line_indent = Cm(0)

    # -- khối văn bản ------------------------------------------------------

    def h1(self, text: str) -> None:
        match = re.match(r"CHƯƠNG\s+(\d+)", text.upper())
        if match:
            # Đánh số hình/bảng theo đúng số chương: Hình 1.1, Bảng 2.3, ... Nhờ vậy
            # dựng riêng một chương để kiểm tra vẫn ra đúng số thứ tự.
            self.chapter = int(match.group(1))
            self.fig_no = 0
            self.tab_no = 0
        paragraph = self.doc.add_paragraph(text, style="Heading 1")
        if self._first_h1:
            # Chương 1 đã nằm ngay sau section của mục lục, không cần ngắt trang nữa.
            self._first_h1 = False
            paragraph.paragraph_format.page_break_before = False

    def _number(self, kind: str, value: int) -> str:
        """Trả về ``Hình 1.2`` / ``Bảng 2.1`` theo chương hiện tại."""
        return f"{kind} {self.chapter}.{value}" if self.chapter else f"{kind} {value}"

    def h2(self, text: str) -> None:
        self.doc.add_paragraph(text, style="Heading 2")

    def h3(self, text: str) -> None:
        self.doc.add_paragraph(text, style="Heading 3")

    @staticmethod
    def _runs(paragraph, text: str, bold: bool = False, italic: bool = False) -> None:
        """Thêm chữ, hiểu cú pháp ``**đậm**``, ``*nghiêng*`` và ```mã```."""
        import re

        for chunk in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", text):
            if not chunk:
                continue
            is_bold, is_italic, is_code = bold, italic, False
            if chunk.startswith("**") and chunk.endswith("**") and len(chunk) > 4:
                chunk = chunk[2:-2]
                is_bold = True
            elif chunk.startswith("`") and chunk.endswith("`") and len(chunk) > 2:
                chunk = chunk[1:-1]
                is_code = True
            elif chunk.startswith("*") and chunk.endswith("*") and len(chunk) > 2:
                chunk = chunk[1:-1]
                is_italic = True
            run = paragraph.add_run(chunk)
            run.bold = is_bold or None
            run.italic = is_italic or None
            if is_code:
                _set_font(run, "Consolas", BODY_PT - 2)

    def p(self, text: str = "", *, bold: bool = False, italic: bool = False,
          align: str = "justify", indent: bool = True, space_after: float = 6):
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.alignment = {
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
        }[align]
        paragraph.paragraph_format.first_line_indent = Cm(1.0) if indent else Cm(0)
        paragraph.paragraph_format.space_after = Pt(space_after)
        self._runs(paragraph, text, bold=bold, italic=italic)
        return paragraph

    def bullets(self, items: list[str]) -> None:
        for item in items:
            paragraph = self.doc.add_paragraph()
            fmt = paragraph.paragraph_format
            fmt.left_indent = Cm(1.0)
            fmt.first_line_indent = Cm(-0.5)
            fmt.space_after = Pt(3)
            fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            self._runs(paragraph, f"•\t{item}")

    def numbered(self, items: list[str], *, align: str = "justify") -> None:
        for index, item in enumerate(items, start=1):
            paragraph = self.doc.add_paragraph()
            fmt = paragraph.paragraph_format
            fmt.left_indent = Cm(1.0)
            fmt.first_line_indent = Cm(-0.5)
            fmt.space_after = Pt(3)
            fmt.alignment = {
                "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                "left": WD_ALIGN_PARAGRAPH.LEFT,
            }[align]
            self._runs(paragraph, f"{index}.\t{item}")

    def code(self, text: str, size: float = 10.0) -> None:
        """Khối mã nguồn: Consolas, nền xám, không giãn dòng.

        ``size`` cho phép hạ cỡ chữ với những đoạn trích dài: ở 9 pt, một dòng
        rộng 15 cm chứa được khoảng 85 ký tự nên ít phải ngắt dòng.
        """
        lines = text.strip("\n").split("\n")
        for index, line in enumerate(lines):
            paragraph = self.doc.add_paragraph()
            fmt = paragraph.paragraph_format
            fmt.left_indent = Cm(0.9)
            # Thụt lề treo: dòng đầu bắt đầu ở 0,4 cm, còn phần bị Word ngắt
            # xuống dòng được đẩy vào 0,9 cm để thấy rõ đó là phần nối tiếp của
            # cùng một dòng mã, không phải một câu lệnh mới.
            fmt.first_line_indent = Cm(-0.5)
            fmt.space_before = Pt(0)
            fmt.space_after = Pt(0 if index < len(lines) - 1 else 8)
            fmt.line_spacing_rule = WD_LINE_SPACING.SINGLE
            # Giữ cả khối trên cùng một trang: mỗi dòng níu dòng kế tiếp, trừ
            # dòng cuối. Nếu không, Word có thể chẻ khối qua hai trang và để
            # lại đúng một dòng mồ côi ở trang sau.
            fmt.keep_with_next = index < len(lines) - 1
            _shade(paragraph, "F4F4F5")
            run = paragraph.add_run(line if line.strip() else " ")
            _set_font(run, "Consolas", size)

    def _caption(self, text: str, above: bool) -> None:
        paragraph = self.doc.add_paragraph()
        fmt = paragraph.paragraph_format
        fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fmt.first_line_indent = Cm(0)
        fmt.space_before = Pt(2)
        fmt.space_after = Pt(4 if above else 12)
        fmt.keep_with_next = above
        run = paragraph.add_run(text)
        run.italic = True
        run.font.size = Pt(12)

    def figure(self, path: Path | str, caption: str, width_cm: float = 15.0) -> None:
        path = Path(path)
        assert path.exists(), f"thiếu hình: {path}"
        paragraph = self.doc.add_paragraph()
        fmt = paragraph.paragraph_format
        fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fmt.first_line_indent = Cm(0)
        fmt.space_before = Pt(6)
        fmt.space_after = Pt(2)
        fmt.keep_with_next = True
        paragraph.add_run().add_picture(str(path), width=Cm(width_cm))
        self.fig_no += 1
        self._caption(f"{self._number('Hình', self.fig_no)}. {caption}", above=False)

    def table(self, headers: list[str], rows: list[list[str]], caption: str,
              widths: list[float] | None = None, font_pt: float = 12,
              keep_together: bool = False) -> None:
        self.tab_no += 1
        self._caption(f"{self._number('Bảng', self.tab_no)}. {caption}", above=True)
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        # Bố cục cố định để Word tôn trọng đúng bề rộng cột đã khai báo.
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        table._tbl.tblPr.append(layout)
        if widths:
            for column, width in enumerate(widths):
                table.columns[column].width = Cm(width)
        for column, header in enumerate(headers):
            cell = table.rows[0].cells[column]
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(2)
            run = paragraph.add_run(header)
            run.bold = True
            run.font.size = Pt(font_pt)
            _shade(paragraph, "E7EEF8")
        for row in rows:
            cells = table.add_row().cells
            for column, value in enumerate(row):
                cells[column].text = ""
                paragraph = cells[column].paragraphs[0]
                paragraph.paragraph_format.alignment = (
                    WD_ALIGN_PARAGRAPH.CENTER if column == 0 or len(str(value)) <= 12
                    else WD_ALIGN_PARAGRAPH.LEFT
                )
                paragraph.paragraph_format.space_after = Pt(2)
                paragraph.paragraph_format.first_line_indent = Cm(0)
                self._runs(paragraph, str(value))
                for run in paragraph.runs:
                    run.font.size = Pt(font_pt)
        if widths:
            for row in table.rows:
                for column, width in enumerate(widths):
                    row.cells[column].width = Cm(width)
        # Hàng tiêu đề lặp lại ở trang sau và không hàng nào bị cắt giữa hai trang.
        head_props = table.rows[0]._tr.get_or_add_trPr()
        repeat = OxmlElement("w:tblHeader")
        repeat.set(qn("w:val"), "true")
        head_props.append(repeat)
        for row in table.rows:
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        # Hàng tiêu đề luôn đi kèm ít nhất một hàng dữ liệu, không đứng trơ ở đáy trang.
        for cell in table.rows[0].cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.keep_with_next = True
        if keep_together:
            for row in table.rows[:-1]:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        paragraph.paragraph_format.keep_with_next = True
        # Dòng ngăn cách sau bảng.
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(0)
        spacer.paragraph_format.line_spacing = Pt(6)

    def page_break(self) -> None:
        """Ngắt trang bằng một kí tự break ở cuối đoạn cuối (không sinh trang trắng)."""
        body = self.doc.element.body
        last = body[-2] if body[-1].tag == qn("w:sectPr") else body[-1]
        if last.tag == qn("w:p"):
            paragraph = Paragraph(last, self.doc)
        else:  # phần tử cuối là bảng: cần một đoạn mới để gắn break
            paragraph = self.doc.add_paragraph()
        paragraph.add_run().add_break(WD_BREAK.PAGE)

    # -- phần đầu ----------------------------------------------------------

    def _centered(self, text: str, *, size: float = BODY_PT, bold: bool = True,
                  space_after: float = 0, space_before: float = 0, italic: bool = False):
        paragraph = self.doc.add_paragraph()
        fmt = paragraph.paragraph_format
        fmt.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fmt.first_line_indent = Cm(0)
        fmt.space_before = Pt(space_before)
        fmt.space_after = Pt(space_after)
        run = paragraph.add_run(text)
        run.bold = bold or None
        run.italic = italic or None
        run.font.size = Pt(size)
        return paragraph

    def _blank(self, count: int = 1, size: float = BODY_PT) -> None:
        for _ in range(count):
            paragraph = self.doc.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(" ")
            run.font.size = Pt(size)

    def cover(self) -> None:
        self._blank(1)
        self._centered(COVER["school"], size=15)
        self._centered(COVER["faculty"], size=15)
        self._blank(1)
        logo = self.doc.add_paragraph()
        logo.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        logo.paragraph_format.space_after = Pt(0)
        logo.add_run().add_picture(_logo_stream(), width=Cm(3.5))
        self._blank(2)
        self._centered(COVER["kind"], size=20)
        self._centered(COVER["course"], size=16, space_before=4)
        self._blank(3)
        self._centered("ĐỀ TÀI:", size=14)
        self._blank(1)
        self._centered(COVER["topic"], size=17)
        self._blank(6)
        for label, value in (
            ("Người hướng dẫn:", COVER["teacher"]),
            ("Sinh viên thực hiện:", COVER["student"]),
            ("Mã số sinh viên:", COVER["student_id"]),
            ("Lớp:", COVER["class"]),
        ):
            paragraph = self.doc.add_paragraph()
            fmt = paragraph.paragraph_format
            fmt.left_indent = Cm(2.0)
            fmt.space_after = Pt(4)
            fmt.first_line_indent = Cm(0)
            fmt.tab_stops.add_tab_stop(Cm(6.3), WD_TAB_ALIGNMENT.LEFT)
            run = paragraph.add_run(f"{label}\t{value}")
            run.font.size = Pt(14)
        self._blank(5)
        self._centered(COVER["place_date"], size=14, bold=False, italic=True)
        self.page_break()

    def _dot_lines(self, count: int = 12) -> None:
        for _ in range(count):
            paragraph = self.doc.add_paragraph()
            fmt = paragraph.paragraph_format
            fmt.space_after = Pt(10)
            fmt.first_line_indent = Cm(0)
            fmt.tab_stops.add_tab_stop(
                Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
            )
            paragraph.add_run("\t")

    def _score_box(self) -> None:
        self._blank(1)
        table = self.doc.add_table(rows=2, cols=1)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.columns[0].width = Cm(9.0)
        for index, text in enumerate(("ĐIỂM", " ")):
            cell = table.rows[index].cells[0]
            cell.width = Cm(9.0)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_before = Pt(6)
            paragraph.paragraph_format.space_after = Pt(6)
            run = paragraph.add_run(text.strip() or " ")
            run.bold = index == 0
            run.font.size = Pt(14)
        table.rows[1].height = Cm(1.6)
        table.rows[1].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST

    def remark_page(self, title: str) -> None:
        self._centered(title, space_after=14)
        self._dot_lines(12)
        self._score_box()

    def summary(self) -> None:
        self._centered("TÓM TẮT", space_after=12)
        self.p(
            "**Tên đề tài:** Xây dựng website trao đổi sách và đồ dùng học tập "
            "cho sinh viên — SáchGóc Uni. **Sinh viên thực hiện:** Nguyễn Văn Hảo. "
            "**Mã số sinh viên:** 2451220056. **Lớp:** 24CT1.",
            space_after=8,
        )
        self.p(
            "Báo cáo trình bày quá trình thiết kế và xây dựng website SáchGóc Uni "
            "bằng framework Django trên nền ngôn ngữ Python. Website giải quyết một "
            "vấn đề quen thuộc của sinh viên: sau mỗi học kì, sách giáo trình, tài "
            "liệu và đồ dùng học tập còn rất tốt nhưng không còn dùng tới, trong khi "
            "sinh viên khóa sau lại phải mua mới với chi phí cao. SáchGóc Uni tạo một "
            "không gian tập trung để sinh viên đăng tin tặng hoặc bán lại những món đồ "
            "ấy, tìm kiếm theo danh mục và môn học, liên hệ trực tiếp với người bán "
            "trong cùng trường.",
        )
        self.p(
            "Hệ thống gồm hai khối chức năng. Khối dành cho sinh viên cho phép đăng "
            "ký, đăng nhập, đăng tin kèm nhiều ảnh, tìm kiếm và lọc theo danh mục, "
            "lưu bài yêu thích, bình luận, gửi yêu cầu đặt mua và theo dõi trạng thái "
            "đơn, đánh giá người bán và báo cáo bài đăng không phù hợp. Khối quản trị "
            "gồm bảng điều khiển riêng tại đường dẫn /quan-tri/ để duyệt bài chờ, xử "
            "lý báo cáo, theo dõi đơn hàng, cùng trang quản trị mặc định của Django "
            "dùng để quản lý dữ liệu gốc.",
        )
        self.p(
            "Về kĩ thuật, đề tài sử dụng kiến trúc MTV của Django, ORM ánh xạ mười "
            "bảng dữ liệu, hệ thống xác thực và phân quyền sẵn có, template kế thừa "
            "theo khối và Tailwind CSS cho giao diện. Toàn bộ quá trình phát triển "
            "được quản lý bằng Git, đặc tả giao diện bằng Figma, vẽ sơ đồ tuần tự và "
            "sơ đồ mạng PERT bằng Draw.io.",
        )
        self.p(
            "Kết quả thực nghiệm cho thấy website chạy ổn định trên bộ kiểm thử tự "
            "động 134 trường hợp, các luồng đăng ký, đăng nhập, đăng tin và đặt mua "
            "hoạt động đúng như sơ đồ tuần tự đã đặc tả. Báo cáo cũng phân tích đường "
            "găng của kế hoạch thực hiện dự án là 35 ngày và đề xuất hướng phát triển "
            "tiếp theo như thanh toán trực tuyến, nhắn tin trong ứng dụng và ứng dụng "
            "di động.",
        )

    def preface(self) -> None:
        self._centered("LỜI NÓI ĐẦU", space_after=12)
        self.p(
            "Sinh viên sau mỗi học kì thường có một chồng sách giáo trình, tài liệu "
            "photo và đồ dùng học tập vẫn còn dùng tốt nhưng không còn nhu cầu. Phần "
            "lớn số đó bị xếp vào góc tủ, bỏ đi thì tiếc mà giữ lại thì không còn chỗ. "
            "Ở chiều ngược lại, sinh viên khóa sau bước vào cùng những học phần ấy lại "
            "phải mua sách mới, trong khi nguồn sách cũ trong trường không hề thiếu. "
            "Khoảng cách giữa người có và người cần vốn chỉ cần một nơi để gặp nhau, "
            "nhưng việc trao đổi hiện vẫn diễn ra rời rạc trên các nhóm mạng xã hội, "
            "tin đăng trôi mất sau vài ngày và không có cách nào kiểm chứng người bán.",
        )
        self.p(
            "Từ quan sát đó, em chọn đề tài “Xây dựng website trao đổi sách và đồ dùng "
            "học tập cho sinh viên — SáchGóc Uni”. Sản phẩm hướng tới một nơi tập "
            "trung duy nhất, nơi mỗi tin đăng có danh mục, môn học, ảnh chụp và trạng "
            "thái rõ ràng; người mua gửi yêu cầu ngay trong hệ thống; người bán xác "
            "nhận hoặc từ chối; và cả hai để lại đánh giá sau khi giao dịch kết thúc.",
        )
        self.p(
            "Mục tiêu của đề tài gồm ba điểm. Thứ nhất, xây dựng một website hoàn chỉnh "
            "chạy được với đầy đủ luồng nghiệp vụ cốt lõi của một sàn trao đổi đồ cũ "
            "trong phạm vi trường học. Thứ hai, vận dụng có hệ thống kiến thức của học "
            "phần Công nghệ Phần mềm: phân tích yêu cầu, đặc tả bằng sơ đồ tuần tự, lập "
            "kế hoạch tiến độ bằng sơ đồ mạng PERT, thiết kế cơ sở dữ liệu và kiểm "
            "thử. Thứ ba, rèn luyện cách làm việc có kỉ luật với Git, Figma và môi "
            "trường phát triển Django.",
        )
        self.p("Thông qua việc thực hiện đề tài này, em mong muốn:", space_after=4)
        self.numbered([
            "Vận dụng kiến thức về lập trình web, cơ sở dữ liệu quan hệ và thiết kế "
            "giao diện vào một sản phẩm chạy được.",
            "Hiểu rõ quy trình phát triển một hệ thống thông tin hoàn chỉnh, từ phân "
            "tích yêu cầu, đặc tả thiết kế, lập kế hoạch tiến độ đến kiểm thử.",
            "Tạo ra một công cụ thiết thực cho sinh viên trong trường, góp phần giảm "
            "chi phí học tập và kéo dài vòng đời sử dụng của sách.",
        ])
        self.p(
            "Báo cáo gồm hai chương: Chương 1 tổng quan cơ sở lý thuyết về framework "
            "Django, ngôn ngữ Python, công cụ và thư viện; Chương 2 trình bày thực "
            "nghiệm gồm bốn sơ đồ tuần tự, sơ đồ mạng PERT với đường găng 35 ngày, "
            "demo bốn chức năng và thiết kế cơ sở dữ liệu kèm dữ liệu thực nghiệm.",
            space_after=0,
        )

    def thanks(self) -> None:
        self._centered("LỜI CẢM ƠN", space_after=12)
        self.p(
            "Em xin gửi lời cảm ơn chân thành và sâu sắc nhất đến cô Phạm Thị Dung, "
            "giảng viên hướng dẫn học phần Công nghệ Phần mềm tại Trường Đại học Kiến "
            "trúc Đà Nẵng. Trong suốt quá trình học tập và thực hiện đề tài, cô đã tận "
            "tình hướng dẫn, góp ý và định hướng cho em từ những buổi đầu còn mơ hồ "
            "về phạm vi đề tài cho đến khi sản phẩm hoàn thiện.",
        )
        self.p(
            "Nhờ sự chỉ bảo tận tâm và tinh thần trách nhiệm của cô, em không chỉ nắm "
            "vững kiến thức về phát triển phần mềm mà còn học được cách làm việc khoa "
            "học: đặt câu hỏi đúng, đặc tả rõ ràng trước khi viết mã, và kiểm chứng "
            "kết quả thay vì tin vào cảm giác. Những nhận xét thẳng thắn của cô về "
            "cách trình bày sơ đồ và cách lập kế hoạch tiến độ đã giúp em nhìn ra "
            "những lỗi mà tự em khó thấy.",
        )
        self.p(
            "Em cũng xin gửi lời cảm ơn đến Ban Giám hiệu Nhà trường, Khoa Công nghệ "
            "Thông tin cùng toàn thể quý thầy cô Trường Đại học Kiến trúc Đà Nẵng đã "
            "tạo điều kiện học tập thuận lợi và cung cấp môi trường để em có thể thực "
            "hành những kiến thức đã học. Xin cảm ơn các bạn trong lớp 24CT1 đã chia "
            "sẻ tài liệu, góp ý giao diện và dùng thử sản phẩm trong những ngày cuối.",
        )
        self.p(
            "Một lần nữa, em xin bày tỏ lòng biết ơn sâu sắc đến cô Phạm Thị Dung vì "
            "sự quan tâm và hướng dẫn chu đáo trong suốt học phần. Em kính chúc cô "
            "luôn mạnh khỏe, hạnh phúc và gặt hái nhiều thành công trong sự nghiệp "
            "giảng dạy. Do thời gian và kinh nghiệm còn hạn chế, báo cáo khó tránh "
            "khỏi thiếu sót; em rất mong nhận được nhận xét của cô để hoàn thiện hơn.",
            space_after=0,
        )

    def toc(self) -> None:
        self._centered("MỤC LỤC", space_after=12)
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        # python-docx chỉ chèn được trường TOC rỗng; số trang do Word tính khi mở.
        # Bước cuối của quy trình dựng báo cáo chạy verify.py --save để Word cập
        # nhật rồi ghi lại, nhờ vậy file giao nộp đã có sẵn số trang.
        _field(paragraph, r'TOC \o "1-3" \h \z \u',
               "Mục lục sẽ được cập nhật tự động khi mở bằng Word.")

    # -- chuyển sang phần thân ---------------------------------------------

    def start_body(self) -> None:
        """Sang trang mới, đánh số trang lại từ 1 cho phần thân."""
        if self._body_started:
            return
        self._body_started = True
        section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.5)
        section.right_margin = Cm(2.5)
        section.footer_distance = Cm(1.5)

        numbering = OxmlElement("w:pgNumType")
        numbering.set(qn("w:start"), "1")
        section._sectPr.append(numbering)

        footer = section.footer
        footer.is_linked_to_previous = False
        paragraph = footer.paragraphs[0]
        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(0)
        _field(paragraph, "PAGE", "1")
        for run in paragraph.runs:
            run.font.name = FONT
            run.font.size = Pt(12)

    # -- xuất file ---------------------------------------------------------

    def save(self, path: Path | str = DEFAULT_OUT) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(path))
        return path


# ------------------------------------------------------------ các phần báo cáo

def build_front(doc: Doc) -> None:
    doc.cover()
    doc.remark_page("LỜI NHẬN XÉT CỦA NGƯỜI HƯỚNG DẪN")
    doc.page_break()
    doc.remark_page("NHẬN XÉT CỦA NGƯỜI PHẢN BIỆN")
    doc.page_break()
    doc.summary()
    doc.page_break()
    doc.preface()
    doc.page_break()
    doc.thanks()
    doc.page_break()
    doc.toc()


def build_ch1(doc: Doc) -> None:
    """CHƯƠNG 1 — cơ sở lý thuyết: framework, ngôn ngữ, công cụ, thư viện."""

    doc.h1("CHƯƠNG 1: TỔNG QUAN CƠ SỞ LÝ THUYẾT")

    # ---------------------------------------------------------------- 1.1
    doc.h2("1.1. Giới thiệu đề tài")
    doc.p(
        "Mỗi học kỳ kết thúc, sinh viên thường để lại một khối lượng lớn sách giáo "
        "trình, tài liệu ôn thi và đồ dùng học tập đã qua sử dụng: giáo trình của môn "
        "vừa học xong, đề cương của các môn đại cương, máy tính cầm tay, bàn phím rời, "
        "đèn bàn hay balô. Phần lớn số này vẫn còn dùng tốt nhưng không còn phù hợp với "
        "lịch học của người sở hữu, trong khi sinh viên khoá sau lại đang cần đúng những "
        "đầu sách và thiết bị đó. Nếu không có kênh trao đổi phù hợp, tài liệu hoặc bị bỏ "
        "xó cho đến khi hết giá trị, hoặc được bán với giá rất thấp cho người thu mua "
        "phế liệu."
    )
    doc.p(
        "Hiện nay sinh viên chủ yếu trao đổi qua các nhóm Facebook, trang rao vặt hoặc "
        "hỏi trực tiếp bạn bè cùng lớp. Các kênh này bộc lộ nhiều hạn chế: tin đăng trôi "
        "rất nhanh theo dòng thời gian, không phân loại được theo ngành học hay theo môn "
        "học, người mua không biết người bán có cùng trường hay không, còn người bán "
        "không có cách nào xác nhận một yêu cầu mua là nghiêm túc. Kết quả là chi phí "
        "tìm kiếm tăng lên và niềm tin giữa hai bên giảm xuống."
    )
    doc.p(
        "Từ bối cảnh đó, em chọn đề tài **“Xây dựng website trao đổi sách và đồ dùng học "
        "tập SáchGóc Uni”** — một sàn trao đổi thu nhỏ, giới hạn trong phạm vi một "
        "trường, chỉ phục vụ nhu cầu mua bán, tặng lại sách và đồ dùng học tập. Phạm vi "
        "hẹp giúp việc kiểm duyệt nội dung dễ dàng và phù hợp với thời lượng của học "
        "phần. Mục tiêu cụ thể của đề tài gồm bốn điểm:"
    )
    doc.numbered([
        "Xây dựng chức năng tài khoản cho phép sinh viên đăng ký, đăng nhập và quản lý "
        "thông tin cá nhân ngay trong hệ thống, không phụ thuộc mạng xã hội bên ngoài.",
        "Cho phép đăng tin bán hoặc tặng sách, tài liệu, đồ dùng học tập kèm hình ảnh, "
        "giá, tình trạng sử dụng và khu vực nhận hàng.",
        "Cung cấp công cụ tìm kiếm, lọc theo danh mục và khoảng giá, xem chi tiết tin "
        "đăng và theo dõi tin đã đăng.",
        "Hỗ trợ quy trình giao dịch: người mua gửi yêu cầu mua, người bán xác nhận hoặc "
        "từ chối, hai bên theo dõi trạng thái đơn, đồng thời có kênh báo cáo tin vi phạm "
        "cho quản trị viên.",
    ])
    doc.p(
        "Phạm vi của đề tài được giới hạn như sau: sản phẩm gồm bốn nhóm chức năng nêu "
        "trên, chạy trên môi trường phát triển cục bộ với cơ sở dữ liệu MariaDB; các "
        "bước thanh toán và vận chuyển được thực hiện trực tiếp giữa người mua và người "
        "bán nên không nằm trong phạm vi xây dựng; dữ liệu sử dụng trong báo cáo là dữ "
        "liệu thử nghiệm do em tự tạo, không chứa thông tin thật của sinh viên."
    )

    # ---------------------------------------------------------------- 1.2
    doc.h2("1.2. Framework Django")

    doc.h3("1.2.1. Tổng quan về Django")
    doc.p(
        "Django là framework phát triển ứng dụng web mã nguồn mở, được viết hoàn toàn "
        "bằng Python. Dự án ra đời năm 2003 tại toà soạn báo Lawrence Journal-World nhằm "
        "đáp ứng nhu cầu xây dựng nhanh các trang tin có lưu lượng lớn, được công bố công "
        "khai năm 2005 và hiện do Django Software Foundation bảo trợ. Django được thiết "
        "kế theo hướng “pin thứ cần thiết vào sẵn” (*batteries included*): những thành "
        "phần mà một ứng dụng web luôn cần như xử lý biểu mẫu, xác thực người dùng, quản "
        "trị nội dung, phân trang hay bảo mật đều có sẵn trong framework thay vì phải lắp "
        "ghép từ nhiều thư viện rời."
    )
    doc.p(
        "Ba nguyên tắc định hình cách Django tổ chức mã nguồn là: không lặp lại chính "
        "mình (*Don't Repeat Yourself*), quy ước rõ ràng thay cho cấu hình rườm rà "
        "(*Convention over Configuration*) và ưu tiên sự tường minh (*Explicit is better "
        "than implicit*). Nhờ vậy một dự án Django luôn có bố cục thư mục dễ đoán, người "
        "mới đọc mã nguồn vẫn nắm được luồng xử lý. Phiên bản được sử dụng trong đề tài "
        "là Django 4.2.30, một bản phát hành dài hạn (LTS) công bố tháng 4 năm 2023."
    )

    doc.h3("1.2.2. Kiến trúc MTV (Model – Template – View)")
    doc.p(
        "Django tổ chức ứng dụng theo kiến trúc MTV, một biến thể của mô hình MVC trong "
        "đó thành phần điều khiển được framework đảm nhiệm thay cho lập trình viên. Ba "
        "thành phần chính gồm:"
    )
    doc.bullets([
        "**Model** — lớp Python mô tả cấu trúc dữ liệu và ánh xạ tới một bảng trong cơ "
        "sở dữ liệu. Mỗi lớp con của `models.Model` tương ứng với một bảng, mỗi thuộc "
        "tính tương ứng với một cột. Tầng ORM của Django sinh câu lệnh SQL từ các thao "
        "tác Python nên lập trình viên hầu như không phải viết SQL thủ công.",
        "**Template** — tệp HTML có chèn cú pháp của Django Template Language, chịu "
        "trách nhiệm trình bày dữ liệu do View truyền vào. Template hỗ trợ kế thừa "
        "(`{% extends %}`), nhúng thành phần dùng lại (`{% include %}`) và tự động "
        "escape ký tự HTML để hạn chế lỗi XSS.",
        "**View** — hàm hoặc lớp nhận đối tượng `HttpRequest`, thực hiện nghiệp vụ, truy "
        "vấn dữ liệu qua Model rồi trả về `HttpResponse` hoặc render một Template. Toàn "
        "bộ phần điều phối giữa ba thành phần do framework thực hiện.",
    ])
    doc.p(
        "Khi người dùng mở một địa chỉ, yêu cầu HTTP được chuyển tới bảng định tuyến "
        "(`urls.py`) để tìm hàm View phù hợp. View truy vấn dữ liệu qua Model, Model "
        "sinh câu lệnh SQL gửi xuống cơ sở dữ liệu và nhận kết quả trả lại. View đóng gói "
        "kết quả thành ngữ cảnh (context), chuyển cho Template render thành HTML, rồi trả "
        "về trình duyệt dưới dạng `HttpResponse`. Hình 1.1 minh hoạ chu trình này."
    )
    doc.figure(ASSETS / "mtv.png",
               "Kiến trúc MTV của Django và luồng xử lý một yêu cầu HTTP",
               width_cm=15.0)

    doc.h3("1.2.3. Các đặc điểm nổi bật")
    doc.bullets([
        "**ORM mạnh và độc lập hệ quản trị** — cùng một đoạn mã Python có thể chạy trên "
        "SQLite khi phát triển và MariaDB khi triển khai, chỉ cần đổi cấu hình kết nối.",
        "**Django Admin** — giao diện quản trị được sinh tự động từ khai báo Model, cho "
        "phép duyệt, tìm kiếm, sửa và xoá bản ghi mà gần như không phải viết thêm mã.",
        "**Hệ thống xác thực tích hợp** — quản lý người dùng, nhóm quyền, phiên đăng "
        "nhập; mật khẩu được băm bằng PBKDF2 kèm muối ngẫu nhiên nên không lưu dạng "
        "văn bản thuần.",
        "**Cơ chế bảo mật mặc định** — mỗi biểu mẫu có token CSRF, truy vấn CSDL được "
        "tham số hoá nên chặn được SQL injection, Template tự escape HTML, cấu hình "
        "cookie và tiêu đề bảo mật có sẵn.",
        "**Migration** — thay đổi cấu trúc dữ liệu được ghi lại thành tệp migration và "
        "áp dụng tuần tự, nhờ đó cấu trúc CSDL luôn đồng bộ với mã nguồn và có thể tái "
        "tạo trên máy khác.",
        "**Hỗ trợ đa ngôn ngữ và múi giờ** — chuỗi giao diện có thể dịch qua tệp `.po`, "
        "thời gian được chuyển đổi theo múi giờ cấu hình.",
    ])

    doc.h3("1.2.4. Vai trò của Django trong đề tài")
    doc.p(
        "Trong dự án SáchGóc Uni, Django đảm nhận toàn bộ phần máy chủ. Thư mục `core/` "
        "chứa cấu hình chung gồm kết nối cơ sở dữ liệu, danh sách ứng dụng, thiết lập "
        "ngôn ngữ tiếng Việt và vùng chứa tệp tải lên. Ứng dụng `app_main/` chứa toàn bộ "
        "nghiệp vụ: mười mô hình dữ liệu khai báo trong `models.py`; các hàm xử lý trong "
        "`views.py`; biểu mẫu đăng ký, đăng nhập, đăng tin trong `forms.py`; bảng tuyến "
        "đường dẫn trong `urls.py`; bốn tệp migration đã áp dụng lên cơ sở dữ liệu. "
        "Phần giao diện gồm mười bốn template nghiệp vụ cùng các thành phần dùng chung "
        "như thanh điều hướng, chân trang và thẻ hiển thị tin đăng."
    )
    doc.p(
        "Hai cơ chế của Django được tận dụng trực tiếp. Thứ nhất là tín hiệu `post_save` "
        "trên mô hình `User`: mỗi khi một tài khoản được tạo, một bản ghi `Profile` tương "
        "ứng được sinh tự động để lưu ảnh đại diện và thông tin bổ sung. Thứ hai là "
        "Django Admin: quản trị viên dùng giao diện có sẵn để duyệt tin chờ, xem báo cáo "
        "vi phạm, trong khi trang quản trị riêng tại đường dẫn `/quan-tri/` cung cấp số "
        "liệu tổng hợp và các thao tác nhanh cho công việc hằng ngày."
    )

    # ---------------------------------------------------------------- 1.3
    doc.h2("1.3. Ngôn ngữ lập trình Python")

    doc.h3("1.3.1. Giới thiệu")
    doc.p(
        "Python là ngôn ngữ lập trình bậc cao, thông dịch, kiểu động, do Guido van Rossum "
        "khởi tạo và công bố lần đầu năm 1991. Ngôn ngữ được thiết kế với mục tiêu hàng "
        "đầu là mã nguồn dễ đọc, cho phép một người vừa học lập trình đã có thể hiểu được "
        "đoạn mã của người khác. Trải qua hơn ba thập kỷ, Python trở thành một trong "
        "những ngôn ngữ phổ biến nhất, được dùng trong phát triển web, phân tích dữ liệu, "
        "học máy, tự động hoá hệ thống và tính toán khoa học. Đề tài sử dụng Python "
        "3.11.9, phiên bản ổn định có hỗ trợ tối ưu hoá tốc độ thực thi."
    )

    doc.h3("1.3.2. Các đặc điểm nổi bật")
    doc.bullets([
        "**Cú pháp ngắn gọn, dựa trên thụt lề** — khối lệnh được xác định bằng khoảng "
        "trắng thay vì cặp ngoặc nhọn, buộc mã nguồn phải trình bày thống nhất và dễ đọc.",
        "**Kiểu động kèm chú thích kiểu** — biến không cần khai báo kiểu, nhưng từ Python "
        "3.5 có thể ghi chú kiểu (`str`, `int`, `list[Post]`) để công cụ kiểm tra tĩnh và "
        "trình soạn thảo hỗ trợ tốt hơn.",
        "**Thư viện chuẩn phong phú** — xử lý chuỗi, tệp, ngày giờ, mạng, JSON, kiểm thử "
        "đều có sẵn, giảm số thư viện bên ngoài phải cài đặt.",
        "**Hỗ trợ đa mô hình lập trình** — lập trình hướng đối tượng, hàm bậc cao, xử lý "
        "bất đồng bộ đều dùng được trong cùng một dự án.",
        "**Chạy trên nhiều nền tảng** — cùng một mã nguồn chạy được trên Windows, Linux và "
        "macOS, thuận lợi khi nhóm phát triển dùng nhiều hệ điều hành khác nhau.",
        "**Hệ sinh thái và cộng đồng lớn** — kho gói `pip` có hàng trăm nghìn thư viện, "
        "tài liệu và câu trả lời cho hầu hết lỗi thường gặp.",
    ])

    doc.h3("1.3.3. Lý do lựa chọn Python cho đề tài")
    doc.p(
        "Django được viết bằng Python nên việc chọn Python là điều kiện bắt buộc nếu dùng "
        "framework này. Ngoài ra, cú pháp gọn giúp các hàm xử lý trong `views.py` dễ đọc "
        "và dễ sửa về sau: một hàm hoàn chỉnh cho chức năng đăng tin chỉ chiếm khoảng bốn "
        "mươi dòng nhưng vẫn thể hiện rõ các bước kiểm tra quyền, kiểm tra dữ liệu, lưu "
        "bản ghi và thông báo kết quả. Việc đọc mã nguồn của người khác cũng thuận lợi "
        "nhờ quy ước trình bày thống nhất, điều này quan trọng với một đồ án được chấm "
        "theo tiêu chí khả năng bảo trì."
    )
    doc.p(
        "Công cụ đi kèm của Python cũng phù hợp với quy mô đồ án: `pip` và tệp "
        "`requirements.txt` giúp cố định phiên bản thư viện để môi trường của giảng viên "
        "chấm bài trùng với môi trường phát triển; `unittest` có sẵn để viết kiểm thử "
        "tự động; môi trường ảo (`venv`) giữ các gói của dự án tách khỏi hệ thống."
    )

    # ---------------------------------------------------------------- 1.4
    doc.h2("1.4. Công cụ hỗ trợ")

    doc.h3("1.4.1. Visual Studio Code – soạn thảo và gỡ lỗi")
    doc.p(
        "Visual Studio Code 1.94.0 là trình soạn thảo mã nguồn chính của đề tài. Trình "
        "soạn thảo cung cấp tô màu cú pháp cho Python và HTML, gợi ý hoàn thiện mã, điều "
        "hướng tới định nghĩa hàm, cửa sổ dòng lệnh tích hợp để chạy `manage.py` và công "
        "cụ gỡ lỗi đặt điểm dừng ngay trong mã nguồn. Việc gỡ lỗi trực tiếp trong trình "
        "soạn thảo giúp rút ngắn thời gian tìm nguyên nhân khi một hàm xử lý trả về kết "
        "quả không như mong đợi."
    )

    doc.h3("1.4.2. XAMPP và MariaDB – máy chủ cơ sở dữ liệu")
    doc.p(
        "XAMPP được dùng để khởi chạy máy chủ cơ sở dữ liệu cục bộ. Bộ cài đặt đi kèm "
        "MariaDB 10.4.32, một hệ quản trị cơ sở dữ liệu quan hệ tương thích với MySQL. "
        "Trong đề tài, MariaDB được cấu hình chạy trên cổng 3307 thay cho cổng mặc định "
        "3306 nhằm tránh xung đột với các dịch vụ khác đang chiếm cổng trên máy phát "
        "triển. Django kết nối tới MariaDB qua driver `mysqlclient`; phần mềm còn khai "
        "báo một cấu hình dự phòng sang SQLite để có thể chạy thử khi MariaDB chưa bật."
    )

    doc.h3("1.4.3. Git và GitHub – quản lý phiên bản")
    doc.p(
        "Git 2.52.0 được dùng để quản lý phiên bản mã nguồn, mỗi lần hoàn thành một chức "
        "năng được ghi lại thành một commit kèm mô tả thay đổi. Kho mã nguồn được đẩy lên "
        "GitHub tại địa chỉ `congnghephanmen`, đóng vai trò bản sao lưu và là nơi nộp sản "
        "phẩm. Nhờ Git, em có thể quay lại trạng thái trước đó khi một thay đổi gây lỗi, "
        "đồng thời theo dõi được tiến độ thực hiện qua lịch sử commit."
    )

    doc.h3("1.4.4. Figma – thiết kế giao diện")
    doc.p(
        "Figma là công cụ thiết kế giao diện chạy trên trình duyệt. Bốn luồng giao diện "
        "chính của đề tài gồm đăng ký, đăng nhập, đăng tin và đặt mua đều được dựng "
        "thành khung dây (wireframe) trước khi viết mã. Việc thiết kế trước giúp thống "
        "nhất bố cục, kích thước nút và thứ tự trường nhập liệu, nhờ đó phần template về "
        "sau chỉ còn việc chuyển thiết kế thành HTML thay vì phải sửa đi sửa lại."
    )

    doc.h3("1.4.5. Draw.io – vẽ sơ đồ")
    doc.p(
        "Draw.io được dùng để phác thảo sơ đồ tuần tự và sơ đồ mạng PERT trình bày trong "
        "Chương 2. Công cụ cho phép kéo thả các khối, nối mũi tên có nhãn và xuất ảnh độ "
        "phân giải cao, phù hợp để đưa vào báo cáo in."
    )

    doc.h3("1.4.6. Chrome và DevTools – kiểm tra giao diện")
    doc.p(
        "Google Chrome 157.0.8103.38, kèm bộ công cụ DevTools, được dùng để kiểm tra giao "
        "diện ở nhiều kích thước màn hình, quan sát yêu cầu mạng và đọc lỗi trong bảng "
        "điều khiển. Đây cũng là công cụ chụp ảnh giao diện trong Chương 2 để bảo đảm "
        "hình minh hoạ đúng là sản phẩm đang chạy."
    )

    doc.h3("1.4.7. Bảng tổng hợp công cụ")
    doc.p(
        "Bảng 1.1 tổng hợp lại sáu công cụ nêu trên kèm phiên bản và vai trò của từng "
        "công cụ, làm căn cứ để tái lập môi trường phát triển khi cần."
    )
    doc.table(
        ["Công cụ", "Phiên bản", "Mục đích sử dụng trong đề tài"],
        [
            ["Visual Studio Code", "1.94.0",
             "Soạn thảo mã nguồn, gỡ lỗi, chạy lệnh quản lý dự án"],
            ["XAMPP + MariaDB", "10.4.32",
             "Máy chủ cơ sở dữ liệu quan hệ, cổng 3307"],
            ["Git và GitHub", "2.52.0",
             "Quản lý phiên bản, sao lưu mã nguồn lên `congnghephanmen`"],
            ["Figma", "Bản web",
             "Thiết kế khung dây cho bốn luồng giao diện chính"],
            ["Draw.io", "Bản web",
             "Vẽ sơ đồ tuần tự và sơ đồ mạng PERT"],
            ["Google Chrome", "157.0.8103.38",
             "Kiểm tra giao diện, đọc lỗi và chụp ảnh minh hoạ"],
        ],
        "Các công cụ hỗ trợ được sử dụng trong quá trình xây dựng",
        widths=[4.2, 3.2, 7.6],
        font_pt=12,
        keep_together=True,
    )

    # ---------------------------------------------------------------- 1.5
    doc.h2("1.5. Thư viện sử dụng và cấu trúc dự án")

    doc.h3("1.5.1. Thư viện sử dụng")
    doc.p(
        "Ngoài Django, dự án chỉ dùng thêm sáu thư viện, tất cả đều được khai báo trong "
        "tệp `requirements.txt` kèm giới hạn phiên bản tối thiểu. Bảng 1.2 liệt kê phiên "
        "bản thực tế đang cài trên máy phát triển và vai trò của từng thư viện."
    )
    doc.table(
        ["Thư viện", "Phiên bản", "Vai trò trong dự án"],
        [
            ["Django", "4.2.30",
             "Framework chính: định tuyến, ORM, template, xác thực, quản trị"],
            ["django-environ", "0.14.0",
             "Đọc biến môi trường từ tệp `.env` (khoá bí mật, thông số CSDL)"],
            ["Pillow", "12.3.0",
             "Xử lý ảnh cho trường `ImageField` (ảnh đại diện, ảnh tin đăng)"],
            ["mysqlclient", "2.2.8",
             "Driver kết nối Django với MariaDB"],
            ["PyMySQL", "1.2.0",
             "Driver dự phòng, dùng khi môi trường thiếu thư viện biên dịch"],
            ["django-crispy-forms", "2.7",
             "Kết xuất biểu mẫu Django theo cấu trúc HTML gọn và thống nhất"],
            ["Tailwind CSS", "3.4.16",
             "Bộ tiện ích CSS dùng để dựng giao diện, lưu cục bộ trong `static/js/`"],
        ],
        "Các thư viện chính và phiên bản đang sử dụng",
        widths=[4.2, 2.8, 8.0],
        font_pt=12,
        keep_together=True,
    )

    doc.h3("1.5.2. Cấu trúc thư mục dự án")
    doc.p(
        "Dự án được chia thành hai phần rõ ràng: thư mục `core/` giữ cấu hình chung và "
        "thư mục `app_main/` giữ toàn bộ nghiệp vụ. Giao diện tập trung trong "
        "`templates/`, tài nguyên tĩnh trong `static/`, tệp người dùng tải lên trong "
        "`media/`, còn tài liệu và sơ đồ trong `docs/`. Cách chia này tuân theo bố cục "
        "chuẩn của Django nên khi cần mở rộng chỉ việc tạo thêm ứng dụng mới mà không "
        "phải sửa cấu trúc hiện có. Hình 1.2 mô tả cây thư mục rút gọn của dự án."
    )
    doc.figure(ASSETS / "tree.png",
               "Cấu trúc thư mục rút gọn của dự án SáchGóc Uni",
               width_cm=15.0)
    doc.p(
        "Có thể đọc cây thư mục theo ba nhóm. Nhóm thứ nhất là mã nguồn Python: tệp "
        "`manage.py` ở gốc là điểm vào của mọi lệnh quản lý dự án; thư mục `core/` chỉ "
        "chứa bốn tệp cấu hình; toàn bộ nghiệp vụ nằm trong `app_main/` với `models.py` "
        "khai báo mười mô hình, `views.py` chứa các hàm xử lý, `forms.py` chứa biểu mẫu "
        "và bốn tệp migration đã áp dụng. Nhóm thứ hai là giao diện và tài nguyên: "
        "`templates/` gồm khung chung `base.html`, thư mục `partials/` chứa thanh điều "
        "hướng, chân trang và thẻ tin đăng dùng lại ở nhiều trang, cùng mười bốn "
        "template nghiệp vụ; `static/` chứa CSS và JavaScript tự viết. Nhóm thứ ba là "
        "dữ liệu: `media/` nhận ảnh người dùng tải lên, `docs/` giữ sơ đồ và báo cáo, "
        "`db.sqlite3` là cơ sở dữ liệu dự phòng khi MariaDB chưa khởi động."
    )
    doc.p(
        "Cách chia này giữ phần cấu hình gần như không thay đổi trong suốt quá trình "
        "phát triển: tính năng mới chỉ được thêm vào `app_main/` và "
        "`templates/app_main/`, không phải sửa `core/`. Khi cần tách một nhóm chức năng "
        "thành ứng dụng riêng, chỉ việc tạo thư mục mới, khai báo trong `INSTALLED_APPS` "
        "và thêm một dòng vào `core/urls.py`."
    )


def build_ch2_head(doc: Doc) -> None:
    """Mở đầu CHƯƠNG 2 — phần thực nghiệm."""

    doc.h1("CHƯƠNG 2: THỰC NGHIỆM")
    doc.p(
        "Nếu chương 1 trả lời câu hỏi “dựng website bằng gì”, chương 2 trả lời câu hỏi "
        "“đã dựng như thế nào và kết quả ra sao”. Bốn phần của chương đi theo đúng thứ "
        "tự của một vòng phát triển: mô hình hoá tương tác giữa các thành phần, lập kế "
        "hoạch thời gian, hiện thực giao diện và cuối cùng là tổ chức dữ liệu phía sau."
    )
    doc.p(
        "Phần 2.1 trình bày bốn sơ đồ tuần tự của bốn chức năng trụ cột, kèm bảng thông "
        "điệp để đọc được từng bước xử lý mà không phải phóng to hình. Phần 2.2 lập "
        "lịch dự án bằng sơ đồ mạng PERT và xác định đường găng. Phần 2.3 là phần demo: "
        "mỗi chức năng được trình bày theo ba bước thiết kế — luồng người dùng, bố cục "
        "phác thảo và giao diện hoàn thiện — rồi đối chiếu với ảnh chụp ứng dụng đang "
        "chạy và đoạn mã xử lý tương ứng. Phần 2.4 mô tả thiết kế cơ sở dữ liệu và "
        "thống kê dữ liệu thực nghiệm đang có trong hệ thống."
    )
    doc.p(
        "Toàn bộ số liệu trong chương được lấy từ chính dự án đang chạy trên máy phát "
        "triển, không phải số liệu giả định: cơ sở dữ liệu MariaDB `sachgocuni.db`, "
        "ảnh chụp màn hình chụp trực tiếp từ Chrome ở kích thước 1440 điểm ảnh, còn "
        "các hình vẽ được sinh từ mã nguồn của chính báo cáo để bảo đảm sơ đồ và bảng "
        "số liệu luôn khớp nhau."
    )


def _message_table(doc: Doc, key: str, caption: str) -> None:
    """Bảng thông điệp của một sơ đồ tuần tự, đọc từ ``SEQUENCES``.

    Dùng lại đúng dữ liệu đã vẽ hình nên nội dung bảng và hình luôn khớp nhau.
    """
    from make_report_assets import MESSAGE_KINDS, SEQUENCES

    spec = SEQUENCES[key]
    rows = []
    for index, (src, dst, text, kind) in enumerate(spec["messages"], start=1):
        rows.append([
            str(index),
            f"{spec['actors'][src]} → {spec['actors'][dst]}",
            text,
            MESSAGE_KINDS[kind],
        ])
    doc.table(
        ["STT", "Nguồn → Đích", "Thông điệp", "Loại"],
        rows,
        caption,
        widths=[1.35, 4.6, 7.0, 2.05],
        font_pt=11,
        # Bảng luôn nằm trọn một trang: cắt đôi bảng mười hai dòng chỉ để lại
        # một trang gần trống, trong khi bảng vừa đúng một trang giấy.
        keep_together=True,
    )


def build_ch2_1(doc: Doc) -> None:
    """2.1 — bốn sơ đồ tuần tự của các chức năng chính."""

    doc.h2("2.1. Sơ đồ tuần tự (Sequence Diagram)")
    doc.p(
        "Sơ đồ tuần tự mô tả một kịch bản sử dụng theo trục thời gian: mỗi tác nhân "
        "có một đường sống riêng, các mũi tên nối hai đường sống là thông điệp trao "
        "đổi giữa chúng, thứ tự từ trên xuống dưới là thứ tự xảy ra trong thực tế. "
        "Nhờ vậy sơ đồ trả lời được câu hỏi mà sơ đồ use case không trả lời được: khi "
        "người dùng bấm một nút, hệ thống lần lượt gọi những hàm nào, truy vấn cơ sở dữ "
        "liệu ở bước nào và trả về cái gì."
    )
    doc.p(
        "Bốn chức năng được chọn để vẽ là bốn chức năng mà mọi luồng khác của "
        "SáchGóc Uni đều đi qua: đăng ký, đăng nhập, đăng tin sản phẩm và đặt mua. "
        "Trong sơ đồ, mũi tên nét liền là lời gọi hàm, mũi tên nét đứt là giá trị trả "
        "về, đường gấp khúc quay lại chính đường sống là đoạn xử lý nội bộ của một đối "
        "tượng. Mỗi sơ đồ mở đầu bằng băng tiêu đề xanh nhạt ghi tên chức năng; bên "
        "dưới là hộp tiêu đề của từng tác nhân, ghi đúng đường dẫn tệp giao diện và tệp "
        "xử lý trong dự án, riêng cơ sở dữ liệu được vẽ thành hình trụ kèm tên CSDL và "
        "các bảng liên quan. Mỗi sơ đồ có đúng một khung *alt* — khung rẽ nhánh lớn "
        "nhất — chia luồng thành hai toán hạng: điều kiện thành công ở trên và điều "
        "kiện thất bại ở dưới, ngăn cách bởi đường kẻ đứt ghi nhãn `[else]`. Nhãn điều "
        "kiện được đặt trong ngoặc vuông ngay sau chữ *alt*, theo đúng quy ước của UML. "
        "Riêng sơ đồ đăng tin còn có thêm một khung *opt* lồng bên trong khung *alt*, "
        "đánh dấu phần chỉ chạy khi người đăng có tải thêm ảnh phụ."
    )
    doc.p(
        "Mỗi hình đi kèm một bảng thông điệp đánh số đúng như số thứ tự trên hình, nhờ "
        "vậy người đọc tra được tên hàm và tên bảng mà không phải phóng to hình. Cột "
        "“Loại” trong bảng lặp lại đúng ba kiểu nét vẽ: *Gọi hàm* cho mũi tên nét liền, "
        "*Trả về* cho mũi tên nét đứt và *Tự xử lý* cho đoạn xử lý nội bộ vẽ bằng đường "
        "gấp khúc. Hình giữ vai trò tổng quan, bảng giữ vai trò tra cứu chi tiết — cách "
        "trình bày này cũng là quy ước của tài liệu thiết kế phần mềm."
    )

    # ------------------------------------------------------------ 2.1.1
    doc.h3("2.1.1. Đăng ký tài khoản")
    doc.p(
        "Người dùng mở `/dang-ky/`, view `register()` dựng biểu mẫu trống rồi trả về "
        "trình duyệt. Khi biểu mẫu được gửi đi, `RegisterForm` kiểm tra tính hợp lệ của "
        "từng trường — trong đó có ràng buộc chỉ chấp nhận địa chỉ email `@gmail.com` "
        "hoặc email của trường (`*.edu.vn`). Nếu hợp lệ, view gọi "
        "`User.objects.create_user()` để tạo bản ghi trong bảng `auth_user`; mật khẩu "
        "được băm bằng PBKDF2 trước khi ghi nên không lưu dạng đọc được. Ngay sau khi "
        "bản ghi được lưu, tín hiệu `post_save` tự động tạo một `Profile` rỗng gắn với "
        "người dùng vừa tạo, nhờ vậy các bước sau không phải kiểm tra profile có tồn "
        "tại hay không. Cuối cùng view gọi `login()` để tạo phiên làm việc và chuyển "
        "hướng về trang chủ kèm lời chào."
    )
    doc.p(
        "Nhánh `[else]` của khung *alt* mô tả trường hợp ngược lại: nếu `is_valid()` "
        "trả về `False`, view bỏ qua toàn bộ phần tạo người dùng — không có bản ghi "
        "`auth_user` nào được ghi, không có `Profile` nào được tạo — mà render lại "
        "`register.html` kèm thông báo lỗi ngay dưới từng trường sai."
    )
    doc.figure(ASSETS / "seq-dang-ky.png",
               "Sơ đồ tuần tự chức năng đăng ký tài khoản")
    _message_table(doc, "dang-ky",
                   "Các thông điệp của luồng đăng ký tài khoản")

    # ------------------------------------------------------------ 2.1.2
    doc.h3("2.1.2. Đăng nhập")
    doc.p(
        "Luồng đăng nhập có thêm một bước kiểm tra trước khi xác thực: view "
        "`user_login()` gọi `_is_allowed_email()` để chặn các tên đăng nhập không thuộc "
        "miền email được phép. Đây là quy ước của phạm vi đề tài — sàn chỉ phục vụ sinh "
        "viên trong trường — nên được kiểm tra ngay ở tầng view. Tiếp theo "
        "`AuthenticationForm` gọi `authenticate()`, hàm này băm mật khẩu vừa nhập rồi "
        "so sánh với giá trị đã lưu; kết quả là đối tượng người dùng hoặc `None`. Nếu "
        "xác thực thành công, `login()` ghi mã định danh phiên vào cookie và view "
        "chuyển hướng về tham số `next` nếu có, ngược lại về trang chủ. Nhánh `[else]` "
        "của sơ đồ là đường thất bại: khi `authenticate()` trả về `None`, view không "
        "gọi `login()` mà render lại `login.html` kèm biến `login_error` để hiện thông "
        "báo, nhờ vậy người dùng biết sai ở đâu và thử lại được ngay trên biểu mẫu."
    )
    doc.figure(ASSETS / "seq-dang-nhap.png",
               "Sơ đồ tuần tự chức năng đăng nhập")
    _message_table(doc, "dang-nhap",
                   "Các thông điệp của luồng đăng nhập")

    # ------------------------------------------------------------ 2.1.3
    doc.h3("2.1.3. Đăng tin sản phẩm")
    doc.p(
        "Đăng tin là chức năng tự chọn thứ nhất. Vì người chưa đăng nhập không được "
        "phép đăng bài, view `create_post()` được bọc bởi `login_required`: yêu cầu "
        "chưa xác thực bị chuyển sang trang đăng nhập kèm tham số `next`. Khi biểu mẫu "
        "được gửi, `PostForm` nhận cả `request.POST` và `request.FILES` để đọc được tệp "
        "ảnh. Hàm `Post.save()` được viết đè để tự sinh `slug` duy nhất từ tiêu đề và "
        "tự đặt `is_free = True` khi giá nhập vào bằng 0 — nhờ vậy một tin “tặng lại” "
        "không cần thêm thao tác riêng. Nếu người dùng chọn thêm ảnh phụ, mỗi ảnh sinh "
        "một bản ghi `PostImage` trỏ tới bài vừa tạo (khung *opt* lồng bên trong khung "
        "*alt*). Cuối cùng view chuyển hướng tới trang chi tiết của bài mới. Nếu "
        "`PostForm` báo lỗi thì nhánh `[else]` được chạy: view không ghi gì vào cơ sở "
        "dữ liệu mà render lại `post_form.html` kèm lỗi từng trường, và ảnh phụ đã "
        "chọn cũng không được lưu."
    )
    doc.figure(ASSETS / "seq-dang-tin.png",
               "Sơ đồ tuần tự chức năng đăng tin sản phẩm")
    _message_table(doc, "dang-tin",
                   "Các thông điệp của luồng đăng tin sản phẩm")

    # ------------------------------------------------------------ 2.1.4
    doc.h3("2.1.4. Đặt mua và xác nhận đơn")
    doc.p(
        "Đặt mua là chức năng tự chọn thứ hai và là luồng duy nhất có hai tác nhân "
        "người dùng. Trước khi dựng biểu mẫu, `buy_post()` kiểm tra ba điều kiện: người "
        "mua không phải chủ bài, sản phẩm còn ở trạng thái bán được và người mua chưa "
        "có đơn nào đang mở trên bài đó. Ba điều kiện này chặn cùng lúc việc tự mua bài "
        "của mình, việc mua một món đã bán và việc một người gửi nhiều yêu cầu trùng "
        "nhau. Khi biểu mẫu hợp lệ, view gán `post`, `buyer`, `seller` và chép giá hiện "
        "tại vào `price_snapshot` rồi mới ghi đơn với `status = PENDING`; chép giá là "
        "cần thiết vì người bán có thể sửa giá sau đó mà đơn đã chốt phải giữ nguyên "
        "con số hai bên đã thoả thuận. Nhánh `[else]` của khung *alt* là đường từ chối: "
        "khi vi phạm một trong ba điều kiện, view ghi thông báo lỗi rồi chuyển hướng "
        "về trang sản phẩm — hoặc về `my_orders` nếu lỗi là đơn đã tồn tại — thay vì "
        "tạo đơn mới. Ở nửa dưới của sơ đồ, người bán gọi "
        "`accept_order()` để chuyển đơn sang `CONFIRMED`, hoàn tất giao dịch."
    )
    doc.figure(ASSETS / "seq-dat-mua.png",
               "Sơ đồ tuần tự chức năng đặt mua và xác nhận đơn")
    _message_table(doc, "dat-mua",
                   "Các thông điệp của luồng đặt mua và xác nhận đơn")


def build_ch2_2(doc: Doc) -> None:
    """2.2 — sơ đồ mạng PERT và đường găng."""

    from make_report_assets import PERT_EDGES, pert_times

    doc.h2("2.2. Sơ đồ PERT và đường găng")
    doc.p(
        "Sơ đồ mạng PERT (Program Evaluation and Review Technique) biểu diễn dự án "
        "thành một mạng có hướng: mỗi đỉnh là một sự kiện (một mốc hoàn thành), mỗi "
        "cung là một công việc có thời lượng. Hai lượt duyệt trên mạng cho ra hai con "
        "số cho từng đỉnh: thời điểm sớm nhất có thể đạt tới đỉnh và thời điểm muộn "
        "nhất còn kịp để không kéo dài dự án. Hiệu của hai con số là thời gian dự trữ; "
        "công việc có dự trữ bằng 0 nằm trên **đường găng** — chuỗi công việc quyết "
        "định toàn bộ thời gian hoàn thành dự án."
    )
    doc.p(
        "Mạng PERT dưới đây giữ nguyên cấu trúc và thời lượng của bài nhận thức số 3; "
        "cột “Công việc dự án” được bổ sung để nối từng công việc trừu tượng A–J với "
        "một đầu việc cụ thể của SáchGóc Uni. Ba cung B′, C′ và E′ có thời lượng 0 là "
        "**cung giả**: chúng không tốn thời gian mà chỉ dùng để biểu diễn quan hệ phụ "
        "thuộc, tránh cho hai công việc bị biểu diễn bằng cùng một cung."
    )

    # ------------------------------------------------------------ 2.2.1
    doc.h3("2.2.1. Danh sách công việc")
    mapping = {
        "A": "Khảo sát nhu cầu, phân tích yêu cầu chức năng",
        "B": "Thiết kế cơ sở dữ liệu và sơ đồ ERD",
        "C": "Thiết kế bốn luồng giao diện trên Figma",
        "D": "Khởi tạo dự án Django, cấu hình `settings.py`, tách `app_main`",
        "B'": "Quan hệ phụ thuộc: mô hình ORM chỉ chốt sau khi có ERD",
        "E": "Xây dựng mười mô hình ORM và bốn migration",
        "C'": "Quan hệ phụ thuộc: template dùng chung chờ xong giao diện",
        "F": "Dựng `base.html`, thanh điều hướng và Tailwind cục bộ",
        "E'": "Quan hệ phụ thuộc: biểu mẫu chờ xong mô hình ORM",
        "H": "Lập trình chức năng tài khoản và đăng tin sản phẩm",
        "I": "Viết `forms.py`, kiểm tra dữ liệu đầu vào",
        "G": "Lập trình đặt mua, bình luận, báo cáo và kiểm thử",
        "J": "Hoàn thiện giao diện, kiểm thử trên trình duyệt",
    }
    before = {
        "A": "—", "B": "—", "C": "—", "D": "A", "B'": "B", "E": "B", "C'": "C",
        "F": "C", "E'": "E", "H": "D", "I": "E", "G": "H, I", "J": "F",
    }
    rows = []
    for name, start, end, dur in PERT_EDGES:
        duration = "0 (giả)" if dur == 0 else f"{dur}"
        rows.append([name, mapping[name], before[name], duration])
    doc.p(
        "Bảng dưới đây liệt kê toàn bộ cung của mạng, kể cả ba cung giả. Thời lượng "
        "tính theo ngày; tổng thời gian hoàn thành theo đường găng là 35 ngày, tương "
        "ứng với thời lượng của học phần."
    )
    doc.table(
        ["Mã", "Công việc dự án SáchGóc Uni", "Trước", "Thời lượng (ngày)"],
        rows,
        "Danh sách công việc của dự án",
        widths=[1.5, 8.3, 2.2, 3.0],
        font_pt=11,
    )

    # ------------------------------------------------------------ 2.2.2
    doc.h3("2.2.2. Sơ đồ mạng PERT")
    doc.p(
        "Hình dưới đây vẽ mạng PERT với chín đỉnh đánh số từ 0 đến 8. Mỗi đỉnh ghi hai "
        "con số dạng *sớm/muộn*; các đỉnh và cung thuộc đường găng được tô đậm để dễ "
        "đối chiếu với phần tính toán tiếp theo."
    )
    doc.figure(ASSETS / "pert.png",
               "Sơ đồ mạng PERT của dự án", width_cm=15.0)

    # ------------------------------------------------------------ 2.2.3
    doc.h3("2.2.3. Thời điểm sớm nhất, muộn nhất và dự trữ")
    doc.p(
        "Lượt duyệt xuôi tính thời điểm sớm nhất: một đỉnh chỉ đạt được khi mọi công "
        "việc đi vào nó đã xong, nên thời điểm sớm nhất của đỉnh là giá trị lớn nhất "
        "trong các tổng *thời điểm sớm nhất của đỉnh trước* cộng *thời lượng cung*. "
        "Lượt duyệt ngược bắt đầu từ đỉnh kết thúc với thời điểm muộn bằng tổng thời "
        "gian dự án, rồi lùi dần: thời điểm muộn của một đỉnh là giá trị nhỏ nhất trong "
        "các hiệu *thời điểm muộn của đỉnh sau* trừ *thời lượng cung*."
    )
    doc.p("`ES(j) = max { ES(i) + t(i, j) }` với i chạy qua mọi đỉnh có cung đi vào j.")
    doc.p("`LS(i) = min { LS(j) − t(i, j) }` với j chạy qua mọi đỉnh có cung đi ra từ i.")
    doc.p(
        "Sau hai lượt duyệt, dự trữ của từng đỉnh là `LS − ES`. Đỉnh nào có dự trữ "
        "bằng 0 thì mọi đường đi qua nó đều không được phép chậm, tức là nó nằm trên "
        "đường găng."
    )
    times = pert_times()
    events = {
        0: "Khởi đầu dự án",
        1: "Xong A — khảo sát, phân tích yêu cầu",
        2: "Xong B — thiết kế cơ sở dữ liệu",
        3: "Xong C — thiết kế giao diện Figma",
        4: "Xong D — khởi tạo dự án Django",
        5: "Xong E — mười mô hình ORM",
        6: "Xong F — khung template chung",
        7: "Xong H, I — tài khoản và đăng tin",
        8: "Kết thúc — xong G, J",
    }
    rows = []
    for node in range(len(times["es"])):
        slack = times["slack"][node]
        rows.append([
            str(node),
            events[node],
            str(times["es"][node]),
            str(times["ls"][node]),
            str(slack),
            "Có" if slack == 0 else "Không",
        ])
    doc.table(
        ["Đỉnh", "Sự kiện", "ES", "LS", "Dự trữ", "Găng"],
        rows,
        "Thời điểm sớm nhất, muộn nhất và dự trữ của từng đỉnh",
        widths=[1.3, 6.8, 1.3, 1.3, 1.8, 2.5],
        font_pt=11,
        keep_together=True,
    )

    # ------------------------------------------------------------ 2.2.4
    doc.h3("2.2.4. Kết luận về đường găng")
    doc.p(
        "Các đỉnh có dự trữ bằng 0 là 0, 1, 4, 7 và 8. Đường găng vì thế là "
        "`0 → 1 → 4 → 7 → 8`, tương ứng với bốn công việc `A → D → H → G`. Thời gian "
        "hoàn thành dự án bằng tổng thời lượng của bốn công việc này:"
    )
    doc.p("`T = 9 + 5 + 9 + 12 = 35` ngày.")
    doc.p(
        "Bốn công việc trên không có dự trữ, nên mọi chậm trễ ở A, D, H hoặc G đều "
        "đẩy ngày hoàn thành lùi đúng bằng số ngày chậm. Ngược lại, công việc C có dự "
        "trữ 13 ngày và công việc E có dự trữ 7 ngày: thiết kế giao diện và viết mô "
        "hình ORM có thể chậm trong phạm vi đó mà không ảnh hưởng tới mốc cuối. Kết "
        "quả này khớp với thực tế triển khai — phần khảo sát và phần lập trình nghiệp "
        "vụ là hai chặng chiếm nhiều thời gian nhất, còn khâu dựng khung giao diện "
        "thường hoàn tất sớm và được chỉnh dần về sau."
    )


def source_excerpt(path: str, ranges: list[tuple[int, int]],
                   need: tuple[str, ...] = ()) -> str:
    """Cắt nguyên văn vài đoạn dòng của một tệp nguồn để in vào báo cáo.

    ``ranges`` là các cặp ``(dòng đầu, dòng cuối)`` tính từ 1 và bao gồm cả hai
    đầu. Những đoạn không liền nhau được nối bằng một dòng ``# ...`` để người
    đọc biết phần giữa đã lược bớt. ``need`` là các chuỗi bắt buộc phải xuất
    hiện trong đoạn trích: nhờ vậy nếu mã nguồn bị sửa tới mức đoạn cắt không
    còn chứa nội dung cần trình bày thì báo cáo báo lỗi ngay khi dựng, thay vì
    lặng lẽ in nhầm dòng.
    """
    lines = (ROOT / path).read_text(encoding="utf-8").split("\n")
    chunks = []
    for start, end in ranges:
        assert 1 <= start <= end <= len(lines), (
            f"{path}: đoạn {start}–{end} vượt quá {len(lines)} dòng"
        )
        chunks.append("\n".join(lines[start - 1:end]).rstrip())
    text = "\n# ...\n".join(chunks)
    for needle in need:
        assert needle in text, f"{path}: đoạn cắt không còn chứa {needle!r}"
    return text


def _demo_steps(doc: Doc, steps: list[str]) -> None:
    """Năm bước của luồng người dùng, in thành danh sách đánh số."""
    doc.numbered(steps)


def build_ch2_3(doc: Doc) -> None:
    """2.3 — demo bốn chức năng theo ba bước thiết kế."""

    doc.h2("2.3. Demo bốn chức năng")
    doc.p(
        "Bốn chức năng dưới đây là bốn chức năng đã chạy được trọn vẹn trong bản "
        "dựng: đăng ký, đăng nhập, đăng tin sản phẩm và đặt mua. Mỗi chức năng được "
        "trình bày theo cùng một khuôn gồm bốn lớp thông tin, đi từ ý tưởng tới sản "
        "phẩm: luồng người dùng, bố cục phác thảo, giao diện hoàn thiện và kết quả "
        "thực hiện."
    )
    doc.p(
        "Hai lớp giữa lấy từ board thiết kế Figma của dự án. Board gốc có ba cột: "
        "cột một là luồng người dùng, cột hai là bố cục phác thảo dạng wireframe, cột "
        "ba là giao diện hoàn thiện dạng mockup chi tiết. Cột một được trình bày lại "
        "bằng danh sách năm bước thay vì ảnh, vì cột này rất cao và chữ trong ảnh "
        "không đủ lớn khi in ở khổ A4. Hai cột còn lại được cắt chung thành một hình: "
        "bên trái là bản phác thảo, bên phải là bản hoàn thiện, để người đọc so sánh "
        "được cái gì được giữ nguyên và cái gì được thêm vào ở bước sau."
    )
    doc.p(
        "Lớp cuối cùng là bằng chứng chức năng đã chạy thật: một ảnh chụp màn hình "
        "ứng dụng đang chạy trên máy phát triển cùng đoạn mã xử lý chính. Ảnh chụp "
        "được cắt sát nội dung nên không có phần thừa của thanh địa chỉ trình duyệt; "
        "đoạn mã được trích nguyên văn từ tệp nguồn `app_main/views.py`, không viết "
        "lại cho đẹp."
    )

    # ------------------------------------------------------------ 2.3.1
    doc.h3("2.3.1. Chức năng đăng ký tài khoản")
    doc.p(
        "Đăng ký là chức năng duy nhất sinh ra dữ liệu gốc của hệ thống: một bản ghi "
        "`User` và hồ sơ `Profile` đi kèm. Trang nằm ở đường dẫn `/dang-ky/` và dùng "
        "form `RegisterForm` với bảy trường. Luồng người dùng gồm năm bước:"
    )
    _demo_steps(doc, [
        "Từ trang chủ hoặc trang đăng nhập, người dùng bấm liên kết **Đăng ký miễn "
        "phí**; hệ thống chuyển tới `/dang-ky/` và hiển thị form trống.",
        "Người dùng điền họ tên, email sinh viên, khoa, mã sinh viên, mật khẩu và ô "
        "xác nhận mật khẩu, rồi tick ô đồng ý điều khoản sử dụng.",
        "Khi rời mỗi ô, giao diện kiểm tra nhanh tại chỗ: email phải có đuôi "
        "`@gmail.com`, mật khẩu tối thiểu 8 ký tự và có ít nhất một chữ hoa cùng một "
        "chữ số.",
        "Người dùng bấm **Tạo tài khoản**. `RegisterForm` kiểm tra lại toàn bộ ở phía "
        "máy chủ: email đúng miền và chưa có người dùng, hai mật khẩu trùng nhau, mật "
        "khẩu không chứa họ tên hay phần trước dấu `@` của email.",
        "Nếu hợp lệ, form tạo `User`, điền khoa và mã sinh viên vào `Profile`, gọi "
        "`login()` để đăng nhập luôn rồi chuyển về trang chủ kèm lời chào; nếu không, "
        "lỗi hiện ngay dưới trường sai và dữ liệu đã nhập được giữ nguyên.",
    ])
    doc.figure(
        ASSETS / "figma-dang-ky-pair.png",
        "Bố cục phác thảo (trái) và giao diện hoàn thiện (phải) của chức năng đăng ký",
    )
    doc.p(
        "Ở bản phác thảo, toàn bộ nội dung nằm trong một thẻ trắng duy nhất đặt trên "
        "nền sáng: tiêu đề, dòng phụ, cặp nút chuyển giữa Đăng ký và Đăng nhập, bốn ô "
        "nhập xếp thành hai hàng đôi, ô tick điều khoản và nút hành động chính ở cuối. "
        "Cách chia này giữ được thứ tự đọc tự nhiên và không cần cuộn trang trên màn "
        "hình máy tính."
    )
    doc.p(
        "Bản hoàn thiện giữ nguyên bố cục đó và bổ sung ba thứ. Thứ nhất là nhận diện: "
        "logo, tên SáchGóc Uni, khẩu hiệu và huy hiệu thành viên ở góc phải. Thứ hai "
        "là tín hiệu kiểm tra: trường bắt buộc có dấu `*` đỏ, trường đã hợp lệ có dấu "
        "`✓` xanh ngay trong ô. Thứ ba là dải thông tin tin cậy ở chân thẻ, nêu ba lợi "
        "ích ngắn để người dùng yên tâm bấm nút."
    )
    doc.p(
        "**Kết quả thực hiện.** Trang đang chạy giữ đúng thứ tự trường và cách chia "
        "hai cột của bản vẽ, chỉ thay cặp màu đỏ đô bằng tím chàm của bảng màu giao "
        "diện hiện hành. Ngoài các trường trong bản vẽ, form còn in dòng gợi ý ngay "
        "dưới ô mật khẩu để người dùng biết trước quy tắc trước khi bị báo lỗi."
    )
    doc.figure(
        ASSETS / "app-register.png",
        "Trang đăng ký đang chạy trên máy phát triển",
        width_cm=7.0,
    )
    doc.p(
        "Hàm xử lý đăng ký không tự kiểm tra từng trường — việc đó đã nằm trong "
        "form. Hàm chỉ quyết định ba việc: người đã đăng nhập thì đưa về trang chủ, "
        "form hợp lệ thì tạo tài khoản và đăng nhập luôn, còn lại thì trả về trang "
        "đăng ký kèm lỗi. Đoạn trích dưới in đúng những dòng đó."
    )
    doc.code(
        source_excerpt(
            "app_main/views.py",
            [(802, 820)],
            need=("form.save()", "login(request, user)"),
        ),
        size=9,
    )

    # ------------------------------------------------------------ 2.3.2
    doc.h3("2.3.2. Chức năng đăng nhập")
    doc.p(
        "Đăng nhập dùng `AuthenticationForm` có sẵn của Django nhưng mở rộng thêm một "
        "đường vào: người dùng có thể nhập **email** thay vì tên đăng nhập. Đây là "
        "thay đổi cần thiết vì tên đăng nhập được sinh tự động từ email lúc đăng ký, "
        "người dùng không nhất thiết nhớ nó. Luồng gồm năm bước:"
    )
    _demo_steps(doc, [
        "Người dùng mở `/dang-nhap/`, hoặc bị chuyển tới đây kèm tham số `next` khi "
        "cố vào một trang cần đăng nhập.",
        "Người dùng nhập một trong hai dạng định danh — email Gmail, email trường "
        "`@edu.vn`, hoặc tên đăng nhập — rồi nhập mật khẩu.",
        "Nếu chuỗi định danh có dấu `@`, hệ thống kiểm tra miền trước: chỉ `gmail.com` "
        "và các đuôi `.edu.vn` được chấp nhận, email ngoài danh sách bị từ chối ngay "
        "mà không cần truy vấn cơ sở dữ liệu.",
        "Với email hợp lệ, hệ thống tra bản ghi `User` theo email (không phân biệt "
        "chữ hoa thường) rồi dựng lại `AuthenticationForm` bằng tên đăng nhập tìm "
        "được; mật khẩu vẫn do Django kiểm tra như bình thường.",
        "Đăng nhập thành công thì chuyển tới `next` nếu có, không thì về trang chủ; "
        "thất bại thì hiện thông báo chung “Tên đăng nhập hoặc mật khẩu không chính "
        "xác” để không tiết lộ tài khoản nào có thật.",
    ])
    doc.figure(
        ASSETS / "figma-dang-nhap-pair.png",
        "Bố cục phác thảo (trái) và giao diện hoàn thiện (phải) của chức năng đăng nhập",
    )
    doc.p(
        "Bản phác thảo đặt hai trường nhập trong cùng một thẻ với cặp nút chuyển Đăng "
        "ký — Đăng nhập ở trên, hai liên kết phụ “Ghi nhớ đăng nhập” và “Quên mật "
        "khẩu?” ở hai mép dưới. Bản hoàn thiện giữ nguyên vị trí các thành phần, chỉ "
        "đổi nhãn trường thành “Email Gmail hoặc Tên đăng nhập” cho đúng nghiệp vụ, "
        "thêm dấu kiểm tra hợp lệ và thêm dải bảo mật ở chân thẻ."
    )
    doc.p(
        "**Kết quả thực hiện.** Form đang chạy có hai trường, nút đăng nhập chiếm trọn "
        "chiều ngang và liên kết đăng ký ở cuối; thông báo lỗi được in phía trên form "
        "nên người dùng thấy ngay mà không phải cuộn lên."
    )
    doc.figure(
        ASSETS / "app-login.png",
        "Trang đăng nhập đang chạy trên máy phát triển",
        width_cm=7.0,
    )
    doc.p(
        "Đoạn mã dưới là phần lõi của hàm `user_login`: nhánh xử lý khi người dùng "
        "nhập email và bước kiểm tra mật khẩu. Hàm phụ `_is_allowed_email` chỉ dài "
        "một dòng nên được mô tả ở đây thay vì in kèm: nó tra miền của email trong "
        "danh sách cho phép và chấp nhận thêm mọi miền kết thúc bằng `.edu.vn`."
    )
    doc.code(
        source_excerpt(
            "app_main/views.py",
            [(856, 878)],
            need=("_is_allowed_email", "email__iexact"),
        ),
        size=9,
    )

    # ------------------------------------------------------------ 2.3.3
    doc.h3("2.3.3. Chức năng đăng tin sản phẩm")
    doc.p(
        "Đăng tin là chức năng tạo ra nội dung của sàn. Trang nằm ở `/dang-tin/`, dùng "
        "`PostForm` cho phần chữ và `PostImageForm` cho ảnh đại diện. Luồng gồm năm "
        "bước:"
    )
    _demo_steps(doc, [
        "Người dùng đã đăng nhập bấm nút **+ Đăng tin** trên thanh điều hướng; hệ "
        "thống mở form đăng tin mới.",
        "Người dùng nhập tiêu đề theo mẫu gợi ý (tên sách hoặc thiết bị kèm tình "
        "trạng), chọn danh mục và tình trạng, rồi nhập giá bán.",
        "Nếu muốn tặng thay vì bán, người dùng tick ô **Tặng miễn phí (0đ)**; giá "
        "được đặt về 0 và tin sẽ xuất hiện trong mục Tặng 0đ.",
        "Người dùng viết mô tả chi tiết và chọn một ảnh đại diện (tối đa 5 MB, nhận "
        "JPG, PNG, WEBP hoặc GIF), rồi bấm **Đăng tin ngay**.",
        "Hàm `create_post` gán người bán là người đang đăng nhập, đặt trạng thái "
        "`ACTIVE` để tin hiện ngay trên sàn, lưu bản ghi rồi chuyển tới trang chi tiết "
        "của tin vừa đăng.",
    ])
    doc.figure(
        ASSETS / "figma-dang-tin-pair.png",
        "Bố cục phác thảo (trái) và giao diện hoàn thiện (phải) của chức năng đăng tin",
    )
    doc.p(
        "Bản phác thảo xếp vùng chọn ảnh lên đầu để người dùng thấy ngay việc đầu tiên "
        "cần làm là chuẩn bị ảnh, sau đó mới tới tiêu đề, cặp danh mục — giá bán và mô "
        "tả. Bản hoàn thiện thêm phần xem trước ảnh kèm dung lượng và một dấu kiểm tra "
        "độ nét, đổi nút thành “Xuất bản bài đăng ngay” và thêm dải cam kết về thời "
        "điểm hiển thị của tin."
    )
    doc.p(
        "**Kết quả thực hiện.** Form đang chạy bám sát bản vẽ nhưng bổ sung hai trường "
        "mà bản phác thảo chưa có: **Tình trạng** (năm mức, từ “Như mới 90–99%” tới "
        "“Cần sửa chữa”) và ô tick **Tặng miễn phí (0đ)**, vì giá và tình trạng là hai "
        "tiêu chí lọc mà người mua dùng nhiều nhất. Tiêu đề trang, thanh điều hướng có "
        "số tin đang chờ duyệt và phần chân trang là khung chung của toàn ứng dụng nên "
        "xuất hiện trong mọi ảnh chụp."
    )
    doc.figure(
        ASSETS / "app-create-post.png",
        "Trang đăng tin đang chạy, đã điền sẵn dữ liệu mẫu",
    )
    doc.p(
        "Đoạn mã dưới là nguyên văn hàm `create_post`. Điểm đáng chú ý là "
        "`form.save(commit=False)`: bản ghi được dựng trong bộ nhớ trước, hai trường "
        "do hệ thống quyết định là người bán và trạng thái được gán sau, rồi mới ghi "
        "xuống cơ sở dữ liệu. Cách này tránh phải thêm hai trường đó vào form và tránh "
        "việc người dùng tự sửa được chúng."
    )
    doc.code(
        source_excerpt(
            "app_main/views.py",
            [(252, 264)],
            need=("post.status = Post.Status.ACTIVE",),
        ),
        size=9,
    )

    # ------------------------------------------------------------ 2.3.4
    doc.h3("2.3.4. Chức năng đặt mua và xác nhận đơn")
    doc.p(
        "Đặt mua là chức năng khép vòng giao dịch: nó nối người mua với người bán qua "
        "một bản ghi `Order` có năm trạng thái — chờ xác nhận, đã xác nhận, hoàn tất, "
        "từ chối và đã huỷ. Trang nằm ở `/san-pham/<pk>/dat-mua/`. Luồng gồm năm bước:"
    )
    _demo_steps(doc, [
        "Từ trang chi tiết của một sản phẩm còn hiển thị, người mua bấm **Đặt mua**; "
        "nút này không xuất hiện với chủ của tin đăng.",
        "Trang đặt mua hiển thị lại thẻ sản phẩm — tiêu đề, người bán, giá — để người "
        "mua chắc chắn đang mua đúng món, phía dưới là hai trường cần điền.",
        "Người dùng nhập thông tin liên hệ (số điện thoại, Zalo hoặc email) và lời "
        "nhắn ghi rõ thời gian, địa điểm hẹn gặp, rồi bấm **Xác nhận gửi yêu cầu đặt "
        "mua**.",
        "Hàm `buy_post` chặn ba trường hợp trước khi ghi dữ liệu: mua tin của chính "
        "mình, mua sản phẩm đã bán, và gửi trùng khi đã có đơn đang mở cho cùng sản "
        "phẩm.",
        "Nếu qua được ba cửa kiểm tra, hệ thống tạo `Order` ở trạng thái chờ xác nhận, "
        "chốt giá tại thời điểm đặt mua rồi chuyển người mua tới trang đơn hàng của "
        "mình; người bán xác nhận, hoàn tất hoặc từ chối từ trang quản lý tin.",
    ])
    doc.figure(
        ASSETS / "figma-dat-mua-pair.png",
        "Bố cục phác thảo (trái) và giao diện hoàn thiện (phải) của chức năng đặt mua",
    )
    doc.p(
        "Bản phác thảo đặt thẻ sản phẩm ngay dưới tiêu đề để người mua nhìn thấy món "
        "đang mua trước khi điền bất cứ thứ gì, sau đó mới tới hai trường và nút gửi. "
        "Bản hoàn thiện giữ nguyên trật tự này, tô màu giá bằng đỏ để nhấn mạnh con số "
        "quan trọng nhất, đổi nhãn trường thành “Số điện thoại / Zalo nhận tin” cho sát "
        "thói quen liên hệ của sinh viên và thêm dải cam kết ba điểm: giao dịch trực "
        "tiếp, không phí trung gian, dành cho sinh viên."
    )
    doc.p(
        "**Kết quả thực hiện.** Trang đang chạy cho thấy các bước kiểm tra phía máy chủ "
        "đã có hiệu lực: một sản phẩm đã bán không còn nút đặt mua trên trang chi tiết, "
        "còn người đã gửi yêu cầu thì được đưa về trang đơn hàng kèm cảnh báo thay vì "
        "tạo thêm bản ghi trùng."
    )
    doc.figure(
        ASSETS / "app-buy-post.png",
        "Trang đặt mua đang chạy, đã điền sẵn dữ liệu mẫu",
    )
    doc.p(
        "Đoạn mã dưới trích hai phần của hàm `buy_post`: phần mở đầu với hai cửa "
        "kiểm tra đầu tiên, và nhánh tạo đơn. Phần kiểm tra đơn trùng nằm giữa hai "
        "đoạn này nên được lược bớt, ký hiệu bằng dòng `# ...`. Điều kiện “một đơn mở "
        "cho mỗi sản phẩm” được kiểm tra bằng truy vấn chứ không dùng ràng buộc duy "
        "nhất có điều kiện của cơ sở dữ liệu, vì MariaDB không hỗ trợ loại ràng buộc "
        "đó."
    )
    doc.code(
        source_excerpt(
            "app_main/views.py",
            [(448, 465), (481, 490)],
            need=("post.is_available", "price_snapshot = post.price"),
        ),
        size=9,
    )


#: Số bản ghi đo được trên cơ sở dữ liệu thật ngày 15/11/2026, sau khi chạy
#: ``docs/report/seed_demo.py``. Ghi cứng thay vì truy vấn lúc dựng báo cáo để
#: con số trong báo cáo luôn khớp với ảnh chụp cùng ngày — máy khác mở dự án
#: hoặc thêm dữ liệu sau đó sẽ không làm lệch bảng thống kê.
#: Truy vấn: ``SELECT '<bảng>', COUNT(*) FROM <bảng>`` trên từng bảng của
#: ``app_main`` và ``auth_user``; riêng ``app_main_post`` đếm thêm theo trạng thái.
DB_STATS: list[tuple[str, int, str]] = [
    ("auth_user", 11, "Tài khoản: 1 quản trị, 10 sinh viên"),
    ("app_main_profile", 11, "Mỗi tài khoản có đúng một hồ sơ"),
    ("app_main_category", 6, "Giáo trình, dụng cụ, thiết bị, đồ án, văn phòng phẩm, khác"),
    ("app_main_post", 35, "32 đang hiển thị, 3 đã bán; 5 tin tặng miễn phí"),
    ("app_main_postimage", 0, "Ảnh phụ chưa dùng, mỗi tin mới có một ảnh đại diện"),
    ("app_main_comment", 118, "Bình luận và trả lời dưới các tin"),
    ("app_main_favorite", 47, "Lượt yêu thích, không trùng cặp người dùng – tin"),
    ("app_main_review", 9, "Đánh giá 1–5 sao sau giao dịch"),
    ("app_main_report", 0, "Chưa có báo cáo vi phạm nào"),
    ("app_main_order", 4, "2 đơn hoàn tất, 1 đang chờ, 1 đã huỷ"),
]


def build_ch2_4(doc: Doc) -> None:
    """2.4 — thiết kế cơ sở dữ liệu và dữ liệu thực nghiệm."""

    doc.h2("2.4. Cơ sở dữ liệu")
    doc.p(
        "Phần lưu trữ được trình bày theo ba lớp: sơ đồ quan hệ giữa các bảng, mô tả chi "
        "tiết trường của ba bảng nhiều ràng buộc nhất, và số liệu thật đang nằm trong cơ "
        "sở dữ liệu sau khi chạy bộ dữ liệu mẫu. Toàn bộ bảng do Django ORM sinh ra từ "
        "tệp `app_main/models.py` qua bốn migration, chạy trên XAMPP + MariaDB 10.4.32 "
        "với kiểu bảng InnoDB và bộ ký tự `utf8mb4`."
    )

    # ------------------------------------------------------------ 2.4.1
    doc.h3("2.4.1. Thiết kế các bảng và sơ đồ quan hệ")
    doc.p(
        "Hệ thống có mười bảng: chín bảng em tự thiết kế trong `app_main` và bảng "
        "`auth_user` do Django cung cấp sẵn. Bảng `auth_user` giữ những gì liên quan "
        "tới đăng nhập — tên đăng nhập, email, mật khẩu đã băm, cờ quản trị — nên em "
        "không sửa cấu trúc của nó mà mở rộng bằng bảng `Profile` quan hệ một-một, "
        "chứa những thông tin riêng tư mà trang cá nhân cần: mã sinh viên, khoa, số "
        "điện thoại, ảnh đại diện."
    )
    doc.p(
        "Bảng trung tâm là `Post`. Mỗi tin đăng thuộc về đúng một người bán và có thể "
        "thuộc một danh mục; xung quanh nó là bốn bảng tương tác cùng trỏ về bằng khoá "
        "ngoại: `PostImage` (một-nhiều, ảnh phụ), `Comment` (một-nhiều, tự tham chiếu "
        "để trả lời lồng một cấp), `Favorite` (nhiều-nhiều qua bảng nối) và `Review` "
        "(đánh giá người bán sau giao dịch). Hai bảng còn lại — `Report` và `Order` — "
        "ghi nhận hai nghiệp vụ riêng: kiểm duyệt và mua bán."
    )
    doc.figure(
        ASSETS / "erd.png",
        "Sơ đồ quan hệ thực thể của cơ sở dữ liệu",
        width_cm=15.0,
    )
    doc.p(
        "Sơ đồ trên vẽ mười bảng cùng mười bốn quan hệ. Nhãn trên mỗi đường nối ghi "
        "bội số của hai đầu, đọc theo hướng từ bảng chứa khoá ngoại sang bảng được "
        "tham chiếu. Bảng dưới đây tóm tắt vai trò của từng bảng và các liên kết của nó."
    )
    doc.table(
        ["Bảng", "Vai trò", "Liên kết chính"],
        [
            ["auth_user", "Tài khoản đăng nhập do Django quản lý",
             "Được 7 bảng khác tham chiếu"],
            ["Profile", "Hồ sơ sinh viên: mã sinh viên, khoa, số điện thoại, ảnh",
             "1-1 với auth_user"],
            ["Category", "Danh mục sản phẩm kèm biểu tượng và thứ tự hiển thị",
             "1-n với Post"],
            ["Post", "Tin đăng bán hoặc tặng, có giá, tình trạng, khu vực giao dịch",
             "n-1 tới auth_user, Category"],
            ["PostImage", "Ảnh phụ của tin đăng, sắp theo thứ tự",
             "n-1 với Post"],
            ["Comment", "Bình luận hỏi đáp, trả lời lồng một cấp",
             "n-1 với Post, auth_user; tự tham chiếu"],
            ["Favorite", "Danh sách yêu thích, có mốc thời gian",
             "n-1 với auth_user, Post; duy nhất theo cặp"],
            ["Review", "Đánh giá 1–5 sao người bán sau khi giao dịch",
             "n-1 với auth_user (2 lần), Post"],
            ["Report", "Báo cáo vi phạm để quản trị viên kiểm duyệt",
             "n-1 với Post, auth_user"],
            ["Order", "Đơn đặt mua với giá chốt và năm trạng thái",
             "n-1 với Post, auth_user (2 lần)"],
        ],
        "Vai trò và liên kết của mười bảng trong cơ sở dữ liệu",
        widths=[3.2, 7.6, 4.2],
        font_pt=11,
        keep_together=True,
    )
    doc.p(
        "Ba quyết định thiết kế đáng chú ý. Thứ nhất, `Favorite` là bảng nối tự viết "
        "chứ không dùng `ManyToManyField` trực tiếp, vì mục “Yêu thích gần đây” cần "
        "mốc thời gian mà bảng nối do Django tự sinh không có. Thứ hai, `Order` chép "
        "lại `seller` từ tin đăng thay vì suy ra qua `post.seller`: đơn hàng là ảnh "
        "chụp của giao dịch tại thời điểm đặt, nên nếu sau này tin đăng bị xoá hoặc "
        "đổi chủ, đơn cũ vẫn còn đủ hai bên để đối chiếu. Thứ ba, `Review` ràng buộc "
        "duy nhất theo cặp *người được đánh giá – người đánh giá*, để một sinh viên "
        "không thể tự nâng điểm uy tín của mình bằng nhiều lượt đánh giá."
    )

    # ------------------------------------------------------------ 2.4.2
    doc.h3("2.4.2. Mô tả trường của các bảng chính")
    doc.p(
        "Ba bảng dưới đây được mô tả tới từng trường vì chúng quyết định phần lớn hành "
        "vi của hệ thống: `Post` là bảng rộng nhất và có hàm `save()` tự xử lý, `Order` "
        "là bảng có nhiều ràng buộc nghiệp vụ nhất, còn `Report` là bảng nhỏ nhưng "
        "quyết định toàn bộ luồng kiểm duyệt của quản trị viên. Cột “Ràng buộc” ghi "
        "đúng những gì migration tạo ra trong MariaDB, không chỉ những gì khai báo "
        "trong mã nguồn."
    )
    doc.table(
        ["Trường", "Kiểu dữ liệu", "Ràng buộc", "Mô tả"],
        [
            ["title", "varchar(200)", "NOT NULL",
             "Tiêu đề tin đăng, hiện trên thẻ sản phẩm"],
            ["slug", "varchar(220)", "UNIQUE",
             "Đường dẫn thân thiện, tự sinh từ tiêu đề nếu bỏ trống"],
            ["seller_id", "bigint", "FK → auth_user",
             "Người đăng; xoá tài khoản thì tin đăng xoá theo"],
            ["category_id", "bigint", "FK → Category, NULL",
             "Danh mục; xoá danh mục thì tin vẫn còn, chỉ mất phân loại"],
            ["price", "decimal(10,0)", "DEFAULT 0",
             "Giá bán; bằng 0 thì `save()` tự bật cờ tặng miễn phí"],
            ["condition", "varchar(20)", "4 lựa chọn",
             "Tình trạng: mới 100%, như mới, tốt, cũ dưới 70%"],
            ["location", "varchar(120)", "có thể trống",
             "Khu vực giao dịch, ghi theo khuôn viên trường"],
            ["status", "varchar(20)", "INDEX, DEFAULT ACTIVE",
             "Năm trạng thái: chờ duyệt, đang hiển thị, đã bán, bị từ chối, đã ẩn"],
            ["is_sold", "boolean", "DEFAULT false",
             "Cờ nhanh; `save()` đồng bộ hai chiều với `status`"],
            ["view_count", "int unsigned", "DEFAULT 0",
             "Lượt xem, tăng bằng biểu thức `F('view_count') + 1`"],
            ["created_at", "datetime", "INDEX, auto",
             "Ngày đăng; khoá sắp xếp mặc định của mọi danh sách"],
            ["updated_at", "datetime", "auto",
             "Ngày cập nhật gần nhất"],
        ],
        "Các trường của bảng Post",
        widths=[2.9, 2.9, 3.7, 5.5],
        font_pt=10,
        keep_together=True,
    )
    doc.table(
        ["Trường", "Kiểu dữ liệu", "Ràng buộc", "Mô tả"],
        [
            ["post_id", "bigint", "FK → Post",
             "Sản phẩm được đặt mua"],
            ["buyer_id", "bigint", "FK → auth_user",
             "Người mua"],
            ["seller_id", "bigint", "FK → auth_user",
             "Người bán, chép từ tin đăng lúc tạo đơn"],
            ["price_snapshot", "decimal(10,0)", "DEFAULT 0",
             "Giá chốt tại thời điểm đặt; người bán sửa giá sau đó cũng không ảnh hưởng"],
            ["message", "varchar(500)", "có thể trống",
             "Lời nhắn: thời gian và địa điểm hẹn gặp"],
            ["contact", "varchar(120)", "có thể trống",
             "Số điện thoại, Zalo hoặc email nhận tin"],
            ["status", "varchar(20)", "INDEX, DEFAULT PENDING",
             "Năm trạng thái: chờ xác nhận, đã xác nhận, hoàn tất, từ chối, đã huỷ"],
            ["seller_note", "varchar(300)", "có thể trống",
             "Ghi chú của người bán khi xác nhận hoặc từ chối"],
            ["created_at", "datetime", "auto",
             "Thời gian người mua gửi yêu cầu"],
            ["updated_at", "datetime", "auto",
             "Lần đổi trạng thái gần nhất"],
        ],
        "Các trường của bảng Order",
        widths=[2.9, 2.9, 3.7, 5.5],
        font_pt=10,
        keep_together=True,
    )
    doc.table(
        ["Trường", "Kiểu dữ liệu", "Ràng buộc", "Mô tả"],
        [
            ["post_id", "bigint", "FK → Post",
             "Bài đăng bị báo cáo"],
            ["reporter_id", "bigint", "FK → auth_user",
             "Người gửi báo cáo"],
            ["reason", "varchar(20)", "5 lựa chọn",
             "Lý do: spam, thông tin sai lệch, không phù hợp, trùng lặp, khác"],
            ["detail", "varchar(500)", "có thể trống",
             "Mô tả thêm của người báo cáo"],
            ["status", "varchar(20)", "INDEX, DEFAULT PENDING",
             "Chờ xử lý, đã xử lý hoặc bỏ qua"],
            ["created_at", "datetime", "auto",
             "Thời gian gửi báo cáo"],
        ],
        "Các trường của bảng Report",
        widths=[2.9, 2.9, 3.7, 5.5],
        font_pt=10,
        keep_together=True,
    )
    doc.p(
        "Ràng buộc “mỗi người mua chỉ có một đơn đang mở cho mỗi sản phẩm” không nằm "
        "trong ba bảng trên mà nằm ở hàm `buy_post`, vì MariaDB không hỗ trợ chỉ mục "
        "một phần — loại ràng buộc duy nhất có điều kiện (`UNIQUE … WHERE status IN "
        "(…)`) chỉ có trên SQLite và PostgreSQL. Đây là ví dụ cho thấy ràng buộc "
        "nghiệp vụ đôi khi phải chuyển từ tầng dữ liệu lên tầng ứng dụng."
    )

    # ------------------------------------------------------------ 2.4.3
    doc.h3("2.4.3. Dữ liệu thực nghiệm")
    doc.p(
        "Để kiểm chứng thiết kế, em chạy bộ dữ liệu mẫu trong "
        "`docs/report/seed_demo.py` — kịch bản này tạo tài khoản, tin đăng, bình luận, "
        "lượt yêu thích, đánh giá và đơn hàng theo đúng thứ tự phụ thuộc khoá ngoại, "
        "chạy lại nhiều lần vẫn không sinh bản ghi trùng. Bảng dưới đây là số bản ghi "
        "đếm được trên cơ sở dữ liệu sau khi nạp, không phải số liệu giả định."
    )
    doc.table(
        ["Bảng", "Số bản ghi", "Ghi chú"],
        [[name, str(count), note] for name, count, note in DB_STATS],
        "Số bản ghi thực tế trong cơ sở dữ liệu sau khi nạp dữ liệu mẫu",
        widths=[4.4, 2.6, 8.0],
        font_pt=11,
        keep_together=True,
    )
    doc.p(
        "Cộng lại, cơ sở dữ liệu đang giữ 241 bản ghi. Con số đáng chú ý là 35 tin "
        "đăng, chia thành 32 tin đang hiển thị và 3 tin đã bán — đúng bằng số bản ghi "
        "mà trang chủ liệt kê khi không lọc gì. Trong 35 tin có 5 tin giá 0 đồng, và "
        "cả 5 đều được đánh dấu tặng miễn phí, xác nhận rằng hàm `save()` của `Post` "
        "đồng bộ đúng hai trường `price` và `is_free`. Phân bố theo danh mục là 9, 7, "
        "7, 5, 4 và 3 tin; ba danh mục đầu chiếm hai phần ba số tin, khớp với thực tế "
        "nhu cầu giáo trình và dụng cụ học tập của sinh viên."
    )
    doc.p(
        "Hai bảng rỗng — `app_main_postimage` và `app_main_report` — không phải lỗi "
        "thiết kế. Ảnh phụ chỉ xuất hiện khi người đăng tải thêm ảnh thứ hai, còn bộ "
        "dữ liệu mẫu chỉ gắn một ảnh đại diện cho mỗi tin; bảng báo cáo rỗng vì chưa "
        "có ai bấm nút báo cáo vi phạm. Cả hai bảng đều đã được kiểm thử ở tầng chức "
        "năng: luồng tải nhiều ảnh và luồng gửi báo cáo chạy đúng, chỉ là dữ liệu mẫu "
        "chưa sinh ra bản ghi nào."
    )
    doc.p(
        "Hình dưới đây là ảnh chụp trang quản trị đang đọc chính cơ sở dữ liệu đó — "
        "cùng một bộ số liệu nhưng nhìn từ phía người vận hành: số tin chờ duyệt, số "
        "đơn đang mở và danh sách tin mới nhất kèm trạng thái."
    )
    doc.figure(
        ASSETS / "app-dashboard.png",
        "Dữ liệu mẫu hiển thị trên trang quản trị",
        width_cm=15.0,
    )



def build_back(doc: Doc) -> None:
    """KẾT LUẬN và TÀI LIỆU THAM KHẢO — phần sau hai chương bắt buộc."""

    doc.h1("KẾT LUẬN")
    doc.p(
        "Báo cáo dừng ở hai chương theo đề cương: chương 1 trình bày cơ sở lý thuyết và "
        "bộ công cụ, chương 2 trình bày phần thực nghiệm trên chính dự án SáchGóc Uni. "
        "Phần này nhìn lại toàn bộ kết quả, nói rõ những gì còn thiếu và vạch hướng "
        "phát triển tiếp theo."
    )

    doc.h2("Đánh giá và phân tích kết quả")
    doc.p(
        "Về mặt chức năng, website đã chạy được trọn vẹn vòng giao dịch của một sàn "
        "trao đổi đồ dùng học tập: đăng ký, đăng nhập, đăng tin kèm ảnh, tìm và lọc "
        "theo danh mục, bình luận, yêu thích, báo cáo vi phạm, đặt mua và xác nhận "
        "đơn, cùng một trang quản trị riêng cho người vận hành. Bốn chức năng trọng "
        "tâm ở mục 2.3 được trình bày đủ bốn lớp — luồng dùng, phác thảo, giao diện "
        "hoàn thiện và ảnh chạy thật kèm mã nguồn — nên kết quả nêu ra đều kiểm chứng "
        "được, không phải mô tả dự kiến. Phần mã nguồn hiện có 134 bài kiểm thử tự "
        "động ở tầng mô hình và tầng xử lý, tất cả đều chạy qua trước mỗi lần dựng "
        "báo cáo."
    )
    doc.p(
        "Về mặt phương pháp, ba bài học rút ra từ quá trình làm. Thứ nhất, việc vẽ mô "
        "hình dữ liệu trước khi viết giao diện tiết kiệm hơn nhiều so với sửa bảng "
        "sau khi đã có dữ liệu: mười bảng ở mục 2.4 chỉ phải đổi cấu trúc hai lần, cả "
        "hai đều phát hiện từ sơ đồ chứ không từ lỗi khi chạy. Thứ hai, sơ đồ PERT ở "
        "mục 2.2 buộc phải ước lượng thời gian cho từng đầu việc thay vì đoán tổng "
        "thời gian; kết quả 35 ngày với đường găng A → D → H → G cho thấy chậm một "
        "ngày ở khâu kiểm thử hoặc khâu đóng gói là chậm đúng một ngày nộp, còn chậm "
        "ở các việc có dự trữ thì không ảnh hưởng. Thứ ba, không phải ràng buộc nào "
        "cũng đặt được ở tầng dữ liệu: MariaDB không có chỉ mục một phần nên ràng "
        "buộc “mỗi người mua chỉ có một đơn đang mở cho mỗi sản phẩm” phải chuyển "
        "lên hàm xử lý, và đó là chỗ dễ sinh lỗi nhất khi bảo trì."
    )
    doc.p(
        "Về mặt hạn chế, hệ thống còn năm điểm chưa làm. Chưa có thanh toán trực "
        "tuyến — người mua và người bán vẫn phải gặp nhau, đúng với mô hình trao đổi "
        "trong khuôn viên trường nhưng chưa khép kín được giao dịch từ xa. Chưa có "
        "thông báo đẩy: đơn mới chỉ hiện khi người bán mở trang đơn hàng. Tìm kiếm "
        "dùng `icontains` trên tiêu đề và mô tả nên chưa xếp hạng được kết quả và sẽ "
        "chậm dần khi số tin tăng. Ảnh đang lưu trên đĩa của máy chủ, chưa đưa lên "
        "dịch vụ lưu trữ nên khó triển khai nhiều máy. Cuối cùng, kiểm thử mới dừng ở "
        "tầng mô hình và tầng xử lý, chưa có kiểm thử giao diện tự động."
    )

    doc.h2("Hướng phát triển")
    doc.p(
        "Sáu việc dưới đây được xếp theo thứ tự ưu tiên, việc đầu tiên là điều kiện "
        "cần để đưa website ra dùng thật:"
    )
    doc.bullets([
        "Tích hợp cổng thanh toán nội địa (VNPay hoặc MoMo) và ví điện tử, kèm bước "
        "đối soát trạng thái đơn khi cổng trả kết quả về.",
        "Bổ sung thông báo thời gian thực bằng Django Channels: có đơn mới, có bình "
        "luận mới hoặc tin đăng được duyệt thì chuông trên thanh điều hướng báo ngay.",
        "Thay tìm kiếm `icontains` bằng chỉ mục toàn văn của MariaDB hoặc "
        "Elasticsearch, thêm lọc theo khoảng giá, theo khoa và theo tình trạng sản phẩm.",
        "Mở kênh chat trong ứng dụng giữa người mua và người bán để hai bên không "
        "phải trao đổi số điện thoại ngay từ lần đầu liên hệ.",
        "Đưa ảnh lên dịch vụ lưu trữ đối tượng (S3 hoặc Cloudinary) và nén ảnh ngay "
        "trên trình duyệt trước khi tải lên, giảm dung lượng và thời gian chờ.",
        "Đóng gói bằng Docker, dựng quy trình tích hợp tự động trên GitHub Actions "
        "chạy 134 bài kiểm thử hiện có trước khi triển khai, rồi bổ sung kiểm thử "
        "giao diện để bắt lỗi hiển thị.",
    ])

    doc.h2("Kết luận chung")
    doc.p(
        "Đề tài đã hoàn thành mục tiêu đề ra: một website Django chạy được, có cơ sở "
        "dữ liệu quan hệ đúng chuẩn hoá, có phân quyền ba vai trò và có kiểm thử tự "
        "động cho phần xử lý. Giá trị thực tiễn nằm ở chỗ sinh viên trong trường có "
        "một chỗ đăng bán hoặc tặng lại giáo trình, dụng cụ cũ thay vì để chúng nằm "
        "im trong ký túc xá, và người mua tìm được đúng món cần chỉ trong vài thao "
        "tác. Giá trị học tập nằm ở quy trình: đi từ yêu cầu, vẽ mô hình dữ liệu, "
        "ước lượng thời gian bằng PERT, dựng giao diện, viết mã nguồn rồi kiểm thử — "
        "đúng thứ tự mà một dự án phần mềm thật đòi hỏi. Những hạn chế đã nêu là danh "
        "sách công việc cho giai đoạn tiếp theo, không phải lý do để dừng lại."
    )

    # ------------------------------------------------------------ tham khảo
    doc.h1("TÀI LIỆU THAM KHẢO")
    doc.numbered([
        "Django Software Foundation. *Django Documentation*, phiên bản 4.2. "
        "https://docs.djangoproject.com/en/4.2/",
        "Python Software Foundation. *Python 3.11 Documentation*. "
        "https://docs.python.org/3.11/",
        "Tailwind Labs. *Tailwind CSS Documentation*, phiên bản 3.4. "
        "https://tailwindcss.com/docs",
        "MariaDB Foundation. *MariaDB Server Documentation*, phiên bản 10.4. "
        "https://mariadb.com/kb/en/documentation/",
        "Mozilla. *MDN Web Docs — HTML, CSS và JavaScript*. "
        "https://developer.mozilla.org/",
        "Figma. *Figma Help Center*. https://help.figma.com/",
        "diagrams.net. *draw.io Documentation*. https://www.drawio.com/doc/",
        "Sommerville, I. (2016). *Software Engineering*, 10th edition. Pearson.",
    ], align="left")


PARTS: dict[str, callable] = {
    "front": build_front,
    "ch1": build_ch1,
    "ch2": build_ch2_head,
    "ch2-1": build_ch2_1,
    "ch2-2": build_ch2_2,
    "ch2-3": build_ch2_3,
    "ch2-4": build_ch2_4,
    "back": build_back,
}


def build(parts: list[str]) -> Doc:
    doc = Doc()
    if "front" in parts:
        build_front(doc)
        # Mục lục kết thúc phần đầu; phần thân sang trang mới và đánh số lại từ 1.
        doc.start_body()
    for name in parts:
        if name == "front":
            continue
        PARTS[name](doc)
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dựng báo cáo giữa kỳ SáchGóc Uni")
    parser.add_argument("--only", default="", help="chỉ dựng phần này (vd: front)")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="đường dẫn file .docx")
    args = parser.parse_args(argv)

    parts = [p.strip() for p in args.only.split(",") if p.strip()] or list(PARTS)
    for name in parts:
        if name not in PARTS:
            parser.error(f"phần chưa dựng: {name}")

    doc = build(parts)
    path = doc.save(args.out)
    print(f"đã ghi {path}")
    print(f"hình: {doc.fig_no}, bảng: {doc.tab_no}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
