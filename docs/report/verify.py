# -*- coding: utf-8 -*-
"""Xuất .docx → PDF bằng Word COM rồi render từng trang ra PNG để tự kiểm tra.

Chạy: python docs/report/verify.py [--save] [đường-dẫn.docx]
Mặc định: docs/BaoCao_GiuaKy_CNPM_SachGocUni.docx

``--save`` ghi lại chính file .docx sau khi Word cập nhật mục lục — python-docx
dựng mục lục dưới dạng trường (field) nên số trang chỉ có sau khi mở bằng Word;
không lưu thì lần mở sau mục lục lại hiện "Error! Bookmark not defined".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "docs" / "report" / "verify"
DEFAULT_DOCX = ROOT / "docs" / "BaoCao_GiuaKy_CNPM_SachGocUni.docx"


def to_pdf(docx: Path, pdf: Path, update_fields: bool = True, save: bool = False) -> None:
    import win32com.client  # pywin32

    pdf.parent.mkdir(parents=True, exist_ok=True)
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        # Chỉ mở ở chế độ chỉ-đọc khi không cần ghi lại — mở read-only rồi Save sẽ lỗi.
        document = word.Documents.Open(str(docx), False, ReadOnly=not save)
        try:
            if update_fields:
                document.Fields.Update()
                for index in range(1, document.TablesOfContents.Count + 1):
                    document.TablesOfContents(index).Update()
                document.Repaginate()
            if save:
                document.Save()
            document.ExportAsFixedFormat(str(pdf), 17)  # 17 = wdExportFormatPDF
        finally:
            document.Close(False)
    finally:
        word.Quit()


def render(pdf: Path, outdir: Path, dpi: int = 110) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("page-*.png"):
        old.unlink()
    paths = []
    with pymupdf.open(pdf) as document:
        for number, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(dpi=dpi)
            target = outdir / f"page-{number:02d}.png"
            pixmap.save(target)
            paths.append(target)
    return paths


def main(argv: list[str]) -> int:
    # --save là cờ, phần còn lại (không bắt đầu bằng "--") mới là đường dẫn .docx.
    save = "--save" in argv
    paths = [a for a in argv[1:] if not a.startswith("--")]
    docx = Path(paths[0]) if paths else DEFAULT_DOCX
    docx = docx.resolve()  # Word COM giải đường dẫn tương đối theo thư mục của nó
    pdf = OUTDIR / "report.pdf"
    to_pdf(docx, pdf, save=save)
    pages = render(pdf, OUTDIR)
    print(f"PDF: {pdf}")
    print(f"số trang: {len(pages)}")
    with pymupdf.open(pdf) as document:
        for number, page in enumerate(document, start=1):
            text = page.get_text().strip().split("\n")
            head = " / ".join(line for line in text[:2] if line.strip())
            print(f"  {number:02d}  {head[:90]}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv))
