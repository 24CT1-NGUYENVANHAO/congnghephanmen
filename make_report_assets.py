"""Sinh toàn bộ hình ảnh cho báo cáo giữa kỳ SáchGóc Uni.

Cách dùng:
    python make_report_assets.py --smoke     # kiểm tra helper render
    python make_report_assets.py            # sinh toàn bộ hình vào docs/report/assets

Phụ thuộc: Chrome (headless), Pillow. Không cần LibreOffice/pandoc/graphviz.
"""

from __future__ import annotations

import base64
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "docs" / "report" / "assets"

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]

# Khổ rộng mặc định của ảnh chụp (px). Báo cáo in ở 15.5 cm nên 1440 px cho ~236 dpi.
SHOT_WIDTH = 1440


def chrome_binary() -> Path:
    for path in CHROME_CANDIDATES:
        if path.exists():
            return path
    raise RuntimeError(
        "Không tìm thấy Chrome/Edge. Cài Chrome hoặc thêm đường dẫn vào CHROME_CANDIDATES."
    )


def _run_chrome(url: str, out_png: Path, width: int, height: int, full_page: bool, scale: int = 1) -> Path:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    if out_png.exists():
        out_png.unlink()
    with tempfile.TemporaryDirectory(prefix="shot-") as profile:
        args = [
            str(chrome_binary()),
            # Chromium cũ (--headless trần) chụp toàn bộ trang; headless=new chỉ chụp viewport.
            "--headless" if full_page else "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
            "--allow-file-access-from-files",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            f"--force-device-scale-factor={scale}",
            "--virtual-time-budget=3000",
            f"--screenshot={out_png}",
            url,
        ]
        proc = subprocess.run(args, capture_output=True, text=True, timeout=180)
    if not out_png.exists():
        raise RuntimeError(
            f"Chrome không sinh được ảnh cho {url}\nSTDOUT: {proc.stdout[-800:]}\nSTDERR: {proc.stderr[-1500:]}"
        )
    return out_png


def _file_url(path: Path) -> str:
    return path.resolve().as_uri()


def render_html(
    url_or_path: str,
    out_png: Path,
    width: int = SHOT_WIDTH,
    height: int = 900,
    full_page: bool = False,
    scale: int = 1,
) -> Path:
    """Chụp một trang HTML (đường dẫn file hoặc URL http/https) ra PNG."""
    text = str(url_or_path)
    if text.startswith(("http://", "https://", "file://", "data:")):
        url = text
    else:
        url = _file_url(Path(text))
    return _run_chrome(url, Path(out_png), width, height, full_page, scale)


_SVG_SIZE = re.compile(r'<svg[^>]*?width=["\']([\d.]+)["\'][^>]*?height=["\']([\d.]+)["\']', re.S)
_SVG_SIZE_ALT = re.compile(r'<svg[^>]*?height=["\']([\d.]+)["\'][^>]*?width=["\']([\d.]+)["\']', re.S)


def svg_size(svg: str) -> tuple[int, int]:
    match = _SVG_SIZE.search(svg)
    if match:
        return int(float(match.group(1))), int(float(match.group(2)))
    match = _SVG_SIZE_ALT.search(svg)
    if match:
        return int(float(match.group(2))), int(float(match.group(1)))
    raise ValueError("Không đọc được width/height của thẻ <svg>")


def render_svg(svg: str, out_png: Path, width: int = 1600) -> Path:
    """Render chuỗi SVG ra PNG. Nếu `width` khác bề rộng gốc của SVG thì scale đều."""
    svg_w, svg_h = svg_size(svg)
    height = int(round(svg_h * width / svg_w))
    wrapped = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:#fff;}"
        f"svg{{display:block;width:{width}px;height:{height}px;}}</style></head><body>"
        f"{svg}</body></html>"
    )
    with tempfile.TemporaryDirectory(prefix="svg-") as tmp:
        html_path = Path(tmp) / "doc.html"
        html_path.write_text(wrapped, encoding="utf-8")
        return _run_chrome(_file_url(html_path), Path(out_png), width, height, full_page=False)


def svg_to_data_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


# ------------------------------------------------------- biểu đồ tuần tự

DIAGRAM_FONT = "Segoe UI, Arial, Helvetica, sans-serif"
INK = "#111827"
CALL_COLOR = "#1f2937"
RETURN_COLOR = "#64748b"
FRAG_COLOR = "#1e3a8a"

#: Bảng màu bám mẫu tham chiếu: băng tiêu đề xanh nhạt, hộp tác nhân viền
#: mảnh nền trắng, cơ sở dữ liệu vẽ thành hình trụ.
BANNER_FILL = "#dbeafe"
BANNER_LINE = "#93c5fd"
BANNER_INK = "#0b2c52"
BOX_LINE = "#334155"
DB_FILL = "#eef2f7"


def _wrap_text(text: str, max_width: float, font_size: float,
               char_factor: float = 0.52) -> list[str]:
    """Ngắt dòng tham lam theo bề rộng ước lượng (không cần font metrics).

    ``char_factor`` là bề rộng trung bình của một ký tự tính theo đơn vị em.
    Nhãn thông điệp dùng chữ nhỏ nên hệ số thực tế thấp hơn phần đầu mục.
    """
    max_chars = max(6, int(max_width / (font_size * char_factor)))
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    lines = lines or [""]
    # Số thứ tự ("7.") không bao giờ đứng một mình trên dòng: gộp vào dòng sau.
    merged: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.fullmatch(r"\d+\.", line) and index + 1 < len(lines):
            merged.append(f"{line} {lines[index + 1]}")
            index += 2
            continue
        merged.append(line)
        index += 1
    return merged


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class SequenceDiagram:
    """Dựng sơ đồ tuần tự bám mẫu tham chiếu bằng SVG thuần.

    Mỗi tác nhân có một hộp tiêu đề riêng ghi đường dẫn tệp thật của dự án
    (riêng cơ sở dữ liệu vẽ thành hình trụ), phía trên là băng tiêu đề xanh
    nhạt và hộp "Tên chức năng" ở góc phải. Toạ độ tính theo "đơn vị điểm":
    480 đơn vị in ra 15 cm, nên cỡ chữ 10 đơn vị tương đương 8,9 pt trên giấy.
    """

    WIDTH = 480.0
    MESSAGE_FONT = 10.0
    LINE_H = 14.0
    HEAD_FONT = 7.0
    CAPTION_FONT = 6.6
    HEAD_LINE_H = 9.2
    HEAD_TOP = 58.0
    BANNER_TOP = 6.0
    BANNER_H = 40.0
    LEGEND_W = 136.0

    def __init__(self, headers: list[dict], banner: str, legend: str,
                 width: float | None = None):
        self.headers = headers
        self.banner = banner
        self.legend = legend
        self.width = width or self.WIDTH
        self.messages: list[dict] = []
        self.fragments: list[dict] = []
        self.frag_rects: list[dict] = []
        # Hộp tác nhân chia đều bề rộng, luôn chừa khe 8 đơn vị giữa các hộp.
        self.box_w = (self.width - 16) / len(headers) - 6
        edge = self.box_w / 2 + 4
        step = (self.width - 2 * edge) / max(1, len(headers) - 1)
        self.xs = [edge + index * step for index in range(len(headers))]
        self.font = self.MESSAGE_FONT
        self.line_h = self.LINE_H
        self.blocks: list[dict] = []
        self.header_h = 0.0
        self.header_bottom = 0.0

    def msg(self, src: int, dst: int, label: str, kind: str = "call",
            num: str | None = None) -> int:
        """Thêm một thông điệp; ``num`` cho phép đánh số kiểu ``8a``/``9b``.

        Không truyền ``num`` thì thông điệp mang số thứ tự tuần tự của nó, đúng
        như bảng thông điệp. Các bước nằm trong khung ``alt`` được đánh số theo
        nhánh (``8a``, ``9a`` cho nhánh đầu; ``8b``, ``9b`` cho nhánh ``else``)
        để người đọc đối chiếu được hai nhánh song song.
        """
        self.messages.append({"src": src, "dst": dst, "label": label,
                              "kind": kind, "num": num})
        return len(self.messages) - 1

    def fragment(self, kind: str, guard: str, first: int, last: int,
                 split: int | None = None, else_guard: str = "") -> None:
        """Thêm một khung alt/opt.

        ``split`` là chỉ số thông điệp cuối cùng của toán hạng thứ nhất; khi có
        ``split`` khung được vẽ thành ``alt`` hai nhánh, nhánh thứ hai mở đầu
        bằng đường kẻ đứt và nhãn ``[else ...]``. Không truyền ``split`` thì
        khung chỉ có một nhánh (``opt``).
        """
        self.fragments.append({
            "kind": kind, "guard": guard, "first": first, "last": last,
            "split": split, "else_guard": else_guard,
        })

    # -- phần đầu sơ đồ ----------------------------------------------
    def _header_blocks(self) -> list[dict]:
        """Chia chữ trong từng hộp tiêu đề và đo chiều cao cần thiết."""
        blocks = []
        for header in self.headers:
            kind = header.get("kind", "box")
            body: list[str] = []
            for line in header.get("lines", []):
                body.extend(item for item in _wrap_text(line, self.box_w - 10, self.HEAD_FONT) if item)
            caption = header.get("caption", "")
            if isinstance(caption, str):
                caption = [
                    item for item in
                    _wrap_text(caption, self.box_w - 12, self.CAPTION_FONT) if item
                ]
            name: list[str] = []
            if kind == "actor":
                name = [
                    item for item in
                    _wrap_text(header.get("label", ""), self.box_w - 6, self.HEAD_FONT + 0.6)
                    if item
                ]
                height = 27 + 5 + len(name) * self.HEAD_LINE_H
            elif kind == "db":
                height = 11 + (len(caption) + len(body)) * self.HEAD_LINE_H + 8
            else:
                height = 7 + (len(caption) + len(body)) * self.HEAD_LINE_H + 6
            blocks.append({
                "kind": kind,
                "caption": caption,
                "body": body,
                "name": name,
                "height": height,
            })
        return blocks

    # -- bố cục ------------------------------------------------------
    def _layout(self) -> tuple[list[float], list[float], float]:
        self.blocks = self._header_blocks()
        self.header_h = max(block["height"] for block in self.blocks)
        self.header_bottom = self.HEAD_TOP + self.header_h + 4
        x_bounds = self._fragment_x_bounds()
        start_marks = {frag["first"]: frag for frag in self.fragments}
        split_marks = {
            frag["split"] + 1 for frag in self.fragments
            if frag["split"] is not None and frag["split"] + 1 < len(self.messages)
        }
        ys: list[float] = []
        heights: list[float] = []
        y = self.header_bottom + 16
        for index, message in enumerate(self.messages):
            if index in start_marks:
                y += 24  # chừa chỗ cho tab và nhãn điều kiện của khung
            if index in split_marks:
                y += 20  # chừa chỗ cho đường kẻ đứt và nhãn [else]
            ys.append(y)
            src_x = self.xs[message["src"]]
            dst_x = self.xs[message["dst"]]
            # Khung hẹp nhất chứa thông điệp (nếu có) quyết định vùng được viết:
            # nhãn phải nằm gọn trong khung thay vì tràn sang cột tác nhân bên
            # phải. Thông điệp ngoài khung vẫn dùng hết bề rộng hình.
            holders = [rect for rect in x_bounds
                       if rect["first"] <= index <= rect["last"]]
            holder = (min(holders, key=lambda r: r["right"] - r["left"])
                      if holders else None)
            inner_left = holder["left"] + 4 if holder else 4.0
            inner_right = holder["right"] - 4 if holder else self.width - 8
            if message["src"] == message["dst"]:
                # Đoạn tự xử lý: vòng gấp khúc quay lại chính đường sống. Nếu
                # còn ít chỗ bên phải thì vẽ vòng sang trái và đặt nhãn bên trái.
                if src_x + 34 <= inner_right:
                    message["loop_dir"] = 1
                else:
                    message["loop_dir"] = -1
                if inner_right - src_x >= 120:
                    message["anchor"] = "start"
                    x_text = src_x + 8
                    max_w = min(170.0, inner_right - x_text)
                else:
                    message["anchor"] = "end"
                    x_text = src_x - 8
                    max_w = min(170.0, max(x_text - inner_left, 70.0))
            elif dst_x > src_x:
                # Lời gọi đi sang phải: nhãn bắt đầu ngay sau đường sống nguồn
                # và kết thúc trước cạnh phải của khung bao.
                message["anchor"] = "start"
                x_text = src_x + 6
                max_w = max(inner_right - x_text - 4, 70.0)
            elif holder is not None and min(src_x, dst_x) > holder["left"]:
                # Trả về giữa hai đường sống đều nằm trong khung: nhãn buộc
                # phải ở trong khung, canh trái ngay sau đầu mũi tên, nếu
                # không nó sẽ chạy ngược qua cạnh trái và đè lên đường bao.
                message["anchor"] = "start"
                x_text = dst_x + 6
                max_w = max(inner_right - x_text - 4, 70.0)
            else:
                # Giá trị trả về đi sang trái: nhãn canh phải, kết thúc ngay
                # dưới đường sống nguồn như mẫu tham chiếu. Nhãn trả về được
                # phép vượt cạnh trái của khung để chạm tới cột giao diện,
                # nhưng phải dừng hẳn bên ngoài khung, không đè lên đường bao.
                message["anchor"] = "end"
                x_text = src_x - 6
                if holder is not None and x_text <= inner_left + 8:
                    x_text = holder["left"] - 6
                max_w = max(x_text - 8, 60.0)
            message["x_text"] = x_text
            num = message.get("num") or str(index + 1)
            lines = _wrap_text(f"{num}. {message['label']}", max_w, self.font,
                                char_factor=0.46)
            message["lines"] = lines
            if message["kind"] == "self":
                height = len(lines) * self.line_h + 34
            else:
                height = len(lines) * self.line_h + 20
            heights.append(height)
            y += height
        self.frag_rects = self._fragment_bounds(ys, heights, x_bounds)
        self._keep_loops_inside()
        return ys, heights, y + 10

    def _fragment_x_bounds(self) -> list[dict]:
        """Tính cạnh trái/phải của từng khung alt/opt từ các đường sống liên quan.

        Khung chỉ ôm các đường sống phía backend: khách (người dùng, giao diện)
        nằm ngoài khung, nhờ vậy khung rẽ nhánh trùng đúng vùng xử lý phía máy
        chủ. Các thông điệp trả kết quả về trình duyệt vẫn vẽ bình thường và đi
        ra ngoài cạnh trái của khung.
        """
        rects: list[dict] = []
        for frag in self.fragments:
            involved = set()
            for message in self.messages[frag["first"]:frag["last"] + 1]:
                involved.update((message["src"], message["dst"]))
            backend = {
                index for index in involved
                if self.headers[index].get("layer", "backend") == "backend"
            }
            if backend:
                involved = backend
            left = max(4.0, min(self.xs[i] for i in involved) - 12)
            right = min(self.width - 4, max(self.xs[i] for i in involved) + 12)
            # Khung lồng trong một khung khác phải thụt vào, nếu không hai
            # đường bao sẽ trùng nhau và không đọc được khung nào là khung nào.
            nested = any(
                other is not frag
                and other["first"] <= frag["first"] and other["last"] >= frag["last"]
                for other in self.fragments
            )
            if nested:
                left += 4
                right -= 4
            rects.append({**frag, "left": left, "right": right})
        return rects

    def _fragment_bounds(self, ys: list[float], heights: list[float],
                         x_bounds: list[dict] | None = None) -> list[dict]:
        """Bổ sung cạnh trên/dưới cho các hộp bao đã có cạnh trái/phải."""
        rects = x_bounds if x_bounds is not None else self._fragment_x_bounds()
        return [
            {
                **rect,
                "top": ys[rect["first"]] - 22,
                "bottom": ys[rect["last"]] + heights[rect["last"]] - 2,
            }
            for rect in rects
        ]

    def _keep_loops_inside(self) -> None:
        """Quay vòng tự xử lý vào trong nếu nó định vẽ ra ngoài khung bao."""
        for index, message in enumerate(self.messages):
            if message["src"] != message["dst"]:
                continue
            holders = [r for r in self.frag_rects if r["first"] <= index <= r["last"]]
            if not holders:
                continue
            rect = min(holders, key=lambda r: r["right"] - r["left"])
            src_x = self.xs[message["src"]]
            span = 44.0
            if (message["loop_dir"] > 0
                    and src_x + span + 4 > rect["right"]
                    and src_x - span - 4 >= rect["left"]):
                message["loop_dir"] = -1

    # -- các mảnh vẽ -------------------------------------------------
    def _actor(self, parts: list[str], cx: float, top: float, name_lines: list[str]) -> None:
        """Tác nhân là người: hình nhân que và tên bên dưới."""
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{top + 5:.1f}" r="4.6" fill="#ffffff" '
            f'stroke="{BOX_LINE}" stroke-width="1"/>'
            f'<line x1="{cx:.1f}" y1="{top + 9.6:.1f}" x2="{cx:.1f}" y2="{top + 19:.1f}" '
            f'stroke="{BOX_LINE}" stroke-width="1"/>'
            f'<line x1="{cx - 7:.1f}" y1="{top + 12.5:.1f}" x2="{cx + 7:.1f}" y2="{top + 12.5:.1f}" '
            f'stroke="{BOX_LINE}" stroke-width="1"/>'
            f'<line x1="{cx:.1f}" y1="{top + 19:.1f}" x2="{cx - 6:.1f}" y2="{top + 26:.1f}" '
            f'stroke="{BOX_LINE}" stroke-width="1"/>'
            f'<line x1="{cx:.1f}" y1="{top + 19:.1f}" x2="{cx + 6:.1f}" y2="{top + 26:.1f}" '
            f'stroke="{BOX_LINE}" stroke-width="1"/>'
        )
        baseline = top + 32 + 5.6
        for index, line in enumerate(name_lines):
            parts.append(
                f'<text x="{cx:.1f}" y="{baseline + index * self.HEAD_LINE_H:.1f}" '
                f'font-family="{DIAGRAM_FONT}" font-size="{self.HEAD_FONT + 0.6:.1f}" '
                f'font-weight="bold" fill="{INK}" text-anchor="middle">{_esc(line)}</text>'
            )

    def _cylinder(self, parts: list[str], left: float, top: float,
                  width: float, height: float) -> None:
        """Cơ sở dữ liệu vẽ thành hình trụ như mẫu tham chiếu."""
        radius = width / 2
        ry = 5.0
        bottom = top + height
        parts.append(
            f'<path d="M {left:.1f} {top + ry:.1f} L {left:.1f} {bottom - ry:.1f} '
            f'A {radius:.1f} {ry:.1f} 0 0 0 {left + width:.1f} {bottom - ry:.1f} '
            f'L {left + width:.1f} {top + ry:.1f} Z" fill="{DB_FILL}" '
            f'stroke="{BOX_LINE}" stroke-width="0.9"/>'
            f'<ellipse cx="{left + radius:.1f}" cy="{top + ry:.1f}" rx="{radius:.1f}" '
            f'ry="{ry:.1f}" fill="{DB_FILL}" stroke="{BOX_LINE}" stroke-width="0.9"/>'
        )

    def _header_text(self, parts: list[str], cx: float, top: float, block: dict) -> None:
        baseline = top + 5.2
        for line in block["caption"]:
            parts.append(
                f'<text x="{cx:.1f}" y="{baseline:.1f}" font-family="{DIAGRAM_FONT}" '
                f'font-size="{self.CAPTION_FONT:.1f}" font-weight="bold" fill="#475569" '
                f'text-anchor="middle">{_esc(line)}</text>'
            )
            baseline += self.HEAD_LINE_H
        for line in block["body"]:
            parts.append(
                f'<text x="{cx:.1f}" y="{baseline:.1f}" font-family="{DIAGRAM_FONT}" '
                f'font-size="{self.HEAD_FONT:.1f}" fill="{INK}" text-anchor="middle">'
                f'{_esc(line)}</text>'
            )
            baseline += self.HEAD_LINE_H

    # -- vẽ ----------------------------------------------------------
    def svg(self) -> str:
        ys, heights, height = self._layout()
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width:.0f}" height="{height:.0f}" '
            f'viewBox="0 0 {self.width:.0f} {height:.0f}">',
            "<defs>"
            '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{CALL_COLOR}"/></marker>'
            '<marker id="ah-open" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10" fill="none" stroke="{RETURN_COLOR}" stroke-width="1.5"/></marker>'
            "</defs>",
            f'<rect width="{self.width:.0f}" height="{height:.0f}" fill="#ffffff"/>',
        ]

        # băng tiêu đề + hộp "Tên chức năng"
        banner_w = self.width - self.LEGEND_W - 12
        parts.append(
            f'<rect x="4" y="{self.BANNER_TOP}" width="{banner_w:.1f}" height="{self.BANNER_H}" rx="9" '
            f'fill="{BANNER_FILL}" stroke="{BANNER_LINE}" stroke-width="1"/>'
        )
        banner_lines = _wrap_text(self.banner, banner_w - 16, 10.4)
        banner_font = 10.4
        if len(banner_lines) > 1:
            banner_lines = _wrap_text(self.banner, banner_w - 16, 9.2)
            banner_font = 9.2
        first_baseline = (
            self.BANNER_TOP + self.BANNER_H / 2 + banner_font * 0.36
            - (len(banner_lines) - 1) * banner_font * 0.62
        )
        for index, line in enumerate(banner_lines):
            parts.append(
                f'<text x="{4 + banner_w / 2:.1f}" y="{first_baseline + index * banner_font * 1.24:.1f}" '
                f'font-family="{DIAGRAM_FONT}" font-size="{banner_font:.1f}" font-weight="bold" '
                f'fill="{BANNER_INK}" text-anchor="middle">{_esc(line)}</text>'
            )
        legend_x = self.width - self.LEGEND_W - 4
        parts.append(
            f'<rect x="{legend_x:.1f}" y="{self.BANNER_TOP}" width="{self.LEGEND_W:.1f}" '
            f'height="{self.BANNER_H}" fill="#ffffff" stroke="{BOX_LINE}" stroke-width="0.9"/>'
            f'<text x="{legend_x + self.LEGEND_W / 2:.1f}" y="{self.BANNER_TOP + 15.5:.1f}" '
            f'font-family="{DIAGRAM_FONT}" font-size="7.6" font-weight="bold" fill="{INK}" '
            f'text-anchor="middle">Tên chức năng:</text>'
            f'<text x="{legend_x + self.LEGEND_W / 2:.1f}" y="{self.BANNER_TOP + 28.5:.1f}" '
            f'font-family="{DIAGRAM_FONT}" font-size="7.6" fill="{INK}" '
            f'text-anchor="middle">{_esc(self.legend)}</text>'
        )

        # lifeline
        for x in self.xs:
            parts.append(
                f'<line x1="{x:.1f}" y1="{self.header_bottom:.1f}" x2="{x:.1f}" y2="{height - 8:.1f}" '
                f'stroke="#94a3b8" stroke-width="0.9" stroke-dasharray="3 3"/>'
            )

        # hộp tiêu đề của từng tác nhân
        for index, block in enumerate(self.blocks):
            cx = self.xs[index]
            left = cx - self.box_w / 2
            top = self.HEAD_TOP
            if block["kind"] == "actor":
                self._actor(parts, cx, top, block["name"])
                continue
            block_h = block["height"]
            if block["kind"] == "db":
                self._cylinder(parts, left, top, self.box_w, block_h)
                # Nhãn phải nằm dưới vành trên của hình trụ (đỉnh + 2*ry).
                self._header_text(parts, cx, top + 13.8, block)
                continue
            parts.append(
                f'<rect x="{left:.1f}" y="{top:.1f}" width="{self.box_w:.1f}" '
                f'height="{block_h:.1f}" fill="#ffffff" stroke="{BOX_LINE}" stroke-width="0.9"/>'
            )
            self._header_text(parts, cx, top + 6.4, block)

        # khung alt/opt (hộp bao đã tính sẵn trong _layout)
        for frag in self.frag_rects:
            left, right = frag["left"], frag["right"]
            top, bottom = frag["top"], frag["bottom"]
            tab_w = 24.0
            parts.append(
                f'<rect x="{left:.1f}" y="{top:.1f}" width="{right - left:.1f}" '
                f'height="{bottom - top:.1f}" fill="none" stroke="{FRAG_COLOR}" stroke-width="1"/>'
                f'<rect x="{left:.1f}" y="{top:.1f}" width="{tab_w}" height="13" '
                f'fill="#ffffff" stroke="{FRAG_COLOR}" stroke-width="1"/>'
                f'<text x="{left + tab_w / 2:.1f}" y="{top + 9.4:.1f}" font-family="{DIAGRAM_FONT}" '
                f'font-size="7.6" font-style="italic" font-weight="bold" fill="{FRAG_COLOR}" '
                f'text-anchor="middle">{_esc(frag["kind"])}</text>'
                f'<text x="{left + tab_w + 7:.1f}" y="{top + 9.4:.1f}" font-family="{DIAGRAM_FONT}" '
                f'font-size="7.2" font-style="italic" fill="#1f2937">{_esc(frag["guard"])}</text>'
            )
            parts.append(
                f'<line x1="{left:.1f}" y1="{top + 13:.1f}" x2="{right:.1f}" y2="{top + 13:.1f}" '
                f'stroke="{FRAG_COLOR}" stroke-width="0.9"/>'
            )
            split = frag["split"]
            if split is not None:
                # Đường kẻ đứt chia hai toán hạng, kèm nhãn [else] của nhánh sau.
                div_y = ys[split + 1] - 18
                parts.append(
                    f'<line x1="{left:.1f}" y1="{div_y:.1f}" x2="{right:.1f}" y2="{div_y:.1f}" '
                    f'stroke="{FRAG_COLOR}" stroke-width="0.9" stroke-dasharray="4 3"/>'
                    f'<text x="{left + 7:.1f}" y="{div_y + 9:.1f}" font-family="{DIAGRAM_FONT}" '
                    f'font-size="7.2" font-style="italic" fill="#1f2937">'
                    f'[else] {_esc(frag["else_guard"])}</text>'
                )

        # mũi tên + nhãn
        for index, message in enumerate(self.messages):
            y = ys[index]
            src_x, dst_x = self.xs[message["src"]], self.xs[message["dst"]]
            lines = message["lines"]
            x_text = message["x_text"]
            anchor = message["anchor"]
            for line_index, line in enumerate(lines):
                parts.append(
                    f'<text x="{x_text:.1f}" y="{y + 10 + line_index * self.line_h:.1f}" '
                    f'font-family="{DIAGRAM_FONT}" font-size="{self.font:.1f}" fill="{INK}" '
                    f'stroke="#ffffff" stroke-width="2.4" stroke-linejoin="round" '
                    f'paint-order="stroke" text-anchor="{anchor}">{_esc(line)}</text>'
                )
            text_bottom = y + len(lines) * self.line_h
            if message["kind"] == "self":
                if message["loop_dir"] > 0:
                    loop_w = min(44.0, self.width - 8 - src_x)
                else:
                    loop_w = min(44.0, src_x - 8)
                end_x = src_x + message["loop_dir"] * loop_w
                loop_top = text_bottom + 3
                path = (
                    f'M {src_x:.1f} {loop_top:.1f} H {end_x:.1f} V {loop_top + 16:.1f} '
                    f'H {src_x + (2 if message["loop_dir"] > 0 else -2):.1f}'
                )
                parts.append(
                    f'<path d="{path}" fill="none" stroke="{CALL_COLOR}" stroke-width="1.05" '
                    f'marker-end="url(#ah)"/>'
                )
                continue
            arrow_y = text_bottom + 4
            dashed = message["kind"] == "return"
            color = RETURN_COLOR if dashed else CALL_COLOR
            marker = "ah-open" if dashed else "ah"
            dash_attr = ' stroke-dasharray="4 3"' if dashed else ""
            parts.append(
                f'<line x1="{src_x:.1f}" y1="{arrow_y:.1f}" x2="{dst_x:.1f}" y2="{arrow_y:.1f}" '
                f'stroke="{color}" stroke-width="1.05" marker-end="url(#{marker})"{dash_attr}/>'
            )

        parts.append("</svg>")
        return "\n".join(parts)


#: Bốn sơ đồ tuần tự của báo cáo. Mỗi mục gồm: tiêu đề, danh sách tác nhân,
#: danh sách thông điệp ``(nguồn, đích, nội dung, loại)``, tệp PNG và danh sách
#: khung ``alt``/``opt`` (đánh số thông điệp từ 1 như trên hình).
#: ``make_report.py`` đọc lại đúng dữ liệu này để sinh bảng thông điệp, nhờ vậy
#: hình và bảng không bao giờ lệch nhau.
SEQUENCES: dict[str, dict] = {
    "dang-ky": {
        "title": "Đăng ký tài khoản",
        "actors": ["Người dùng", "Giao diện đăng ký", "View register()",
                   "RegisterForm", "CSDL (User)"],
        "banner": "SƠ ĐỒ TUẦN TỰ - CHỨC NĂNG ĐĂNG KÝ TÀI KHOẢN (REGISTER)",
        "legend": "Đăng ký tài khoản",
        "headers": [
            {"kind": "actor", "label": "Người dùng", "layer": "client"},
            {"kind": "box", "layer": "client", "caption": ["Đường dẫn vào", "frontend:"],
             "lines": ["templates/", "registration/", "register.html"]},
            {"kind": "box", "caption": ["Đường dẫn vào", "file backend:"],
             "lines": ["app_main/views.py", "register()"]},
            {"kind": "box", "caption": "Biểu mẫu xử lý:",
             "lines": ["app_main/forms.py", "RegisterForm"]},
            {"kind": "db", "caption": ["Tên CSDL /", "bảng hỗ trợ:"],
             "lines": ["sachgocuni.db", "auth_user,", "app_main_profile"]},
        ],
        "messages": [
            (0, 1, "Yêu cầu mở form đăng ký (Click “Đăng ký”)", "call"),
            (1, 2, "GET /dang-ky/ → view register()", "call"),
            (2, 1, "Hiển thị form đăng ký", "return"),
            (0, 1, "Nhập đầy đủ thông tin và bấm “Đăng ký”", "call"),
            (1, 2, "Gửi thông tin đăng ký (POST /dang-ky/)", "call"),
            (2, 3, "RegisterForm(request.POST)", "call"),
            (3, 4, "SELECT 1 FROM auth_user WHERE email = ?", "call"),
            (3, 2, "Trả về lỗi từng trường", "return", "8a"),
            (2, 1, "Render lại register.html kèm thông báo lỗi", "return", "9a"),
            (2, 4, "INSERT INTO auth_user (…, mật khẩu băm PBKDF2)", "call", "8b"),
            (4, 4, "signal post_save tạo Profile", "self", "9b"),
            (4, 2, "Trả về user (pk mới)", "return", "10b"),
            (2, 1, "Chuyển hướng về trang chủ kèm lời chào", "return", "11"),
            (1, 0, "Hiển thị thông báo “Đăng ký thành công”", "return", "12"),
        ],
        "file": "seq-dang-ky.png",
        "fragments": [
            {"kind": "alt", "first": 8, "split": 9, "last": 13,
             "guard": "[Trường hợp email đã tồn tại hoặc dữ liệu không hợp lệ]",
             "else_guard": "Trường hợp dữ liệu hợp lệ và email chưa tồn tại"},
        ],
    },
    "dang-nhap": {
        "title": "Đăng nhập",
        "actors": ["Người dùng", "Giao diện đăng nhập", "View user_login()",
                   "AuthenticationForm", "CSDL (User)"],
        "banner": "SƠ ĐỒ TUẦN TỰ - CHỨC NĂNG ĐĂNG NHẬP (LOGIN)",
        "legend": "Đăng nhập",
        "headers": [
            {"kind": "actor", "label": "Người dùng", "layer": "client"},
            {"kind": "box", "layer": "client", "caption": ["Đường dẫn vào", "frontend:"],
             "lines": ["templates/", "registration/", "login.html"]},
            {"kind": "box", "caption": ["Đường dẫn vào", "file backend:"],
             "lines": ["app_main/views.py", "user_login()"]},
            {"kind": "box", "caption": "Lớp xử lý:",
             "lines": ["django.contrib.auth", "AuthenticationForm"]},
            {"kind": "db", "caption": ["Tên CSDL /", "bảng hỗ trợ:"],
             "lines": ["sachgocuni.db", "auth_user,", "django_session"]},
        ],
        "messages": [
            (0, 1, "Yêu cầu mở form đăng nhập (Click “Đăng nhập”)", "call"),
            (1, 2, "GET /dang-nhap/ → view user_login()", "call"),
            (2, 1, "Hiển thị form đăng nhập (email, mật khẩu)", "return"),
            (0, 1, "Nhập email, mật khẩu và bấm “Đăng nhập”", "call"),
            (1, 2, "Gửi thông tin đăng nhập (POST /dang-nhap/)", "call"),
            (2, 2, "_is_allowed_email(): lọc miền", "self"),
            (2, 3, "AuthenticationForm(request.POST)", "call"),
            (3, 4, "authenticate(): SELECT * FROM auth_user", "call"),
            (3, 2, "Trả về lỗi xác thực (user = None)", "return", "9a"),
            (2, 1, "Render lại login.html kèm thông báo lỗi", "return", "10a"),
            (2, 4, "login(): INSERT INTO django_session", "call", "9b"),
            (4, 2, "Trả về session_key vừa tạo", "return", "10b"),
            (2, 1, "Chuyển hướng về trang chủ kèm lời chào", "return", "11b"),
            (1, 0, "Hiển thị trang chủ", "return", "12"),
        ],
        "file": "seq-dang-nhap.png",
        "fragments": [
            {"kind": "alt", "first": 9, "split": 10, "last": 13,
             "guard": "[Trường hợp sai email hoặc sai mật khẩu]",
             "else_guard": "Trường hợp email và mật khẩu đều hợp lệ"},
        ],
    },
    "dang-tin": {
        "title": "Đăng tin sản phẩm",
        "actors": ["Người dùng", "Giao diện đăng tin", "View create_post()",
                   "PostForm", "CSDL (Post)"],
        "banner": "SƠ ĐỒ TUẦN TỰ - CHỨC NĂNG ĐĂNG TIN (CREATE POST)",
        "legend": "Đăng tin sản phẩm",
        "headers": [
            {"kind": "actor", "label": "Người dùng", "layer": "client"},
            {"kind": "box", "layer": "client", "caption": ["Đường dẫn vào", "frontend:"],
             "lines": ["templates/app_main/", "post_form.html"]},
            {"kind": "box", "caption": ["Đường dẫn vào", "file backend:"],
             "lines": ["app_main/views.py", "create_post()"]},
            {"kind": "box", "caption": "Biểu mẫu xử lý:",
             "lines": ["app_main/forms.py", "PostForm"]},
            {"kind": "db", "caption": ["Tên CSDL /", "bảng hỗ trợ:"],
             "lines": ["sachgocuni.db", "app_main_post,", "app_main_postimage"]},
        ],
        "messages": [
            (0, 1, "Yêu cầu mở form đăng tin (Click “Đăng tin”)", "call"),
            (1, 2, "GET /dang-tin/ → view create_post() (login_required)", "call"),
            (2, 1, "Hiển thị form đăng tin (post_form.html)", "return"),
            (0, 1, "Nhập tiêu đề, danh mục, giá, mô tả, ảnh và bấm “Đăng tin”", "call"),
            (1, 2, "Gửi dữ liệu bài đăng (POST FormData)", "call"),
            (2, 3, "PostForm(request.POST, request.FILES)", "call"),
            (3, 2, "Trả về lỗi từng trường", "return", "7a"),
            (2, 1, "Render lại post_form.html báo lỗi", "return", "8a"),
            (2, 4, "INSERT INTO app_main_post (…, slug, is_free)", "call", "7b"),
            (4, 2, "Trả về post.pk kèm ảnh phụ đã lưu", "return", "8b"),
            (2, 1, "Chuyển hướng tới trang chi tiết", "return", "9b"),
            (1, 0, "Hiển thị bài đăng mới", "return", "10"),
        ],
        "file": "seq-dang-tin.png",
        "fragments": [
            {"kind": "alt", "first": 7, "split": 8, "last": 11,
             "guard": "[Trường hợp dữ liệu không hợp lệ]",
             "else_guard": "Trường hợp dữ liệu hợp lệ"},
        ],
    },
    "dat-mua": {
        "title": "Đặt mua và xác nhận đơn",
        "actors": ["Người mua", "Trang sản phẩm", "View buy_post()",
                   "OrderForm / Order", "Người bán"],
        "banner": "SƠ ĐỒ TUẦN TỰ - CHỨC NĂNG ĐẶT MUA (BUY & CONFIRM)",
        "legend": "Đặt mua và xác nhận đơn",
        "headers": [
            {"kind": "actor", "label": "Người mua", "layer": "client"},
            {"kind": "box", "layer": "client", "caption": ["Đường dẫn vào", "frontend:"],
             "lines": ["templates/app_main/", "buy_post.html"]},
            {"kind": "box", "caption": ["Đường dẫn vào", "file backend:"],
             "lines": ["app_main/views.py", "buy_post()"]},
            {"kind": "box", "caption": ["Biểu mẫu /", "mô hình:"],
             "lines": ["app_main/forms.py", "OrderForm", "app_main_order"]},
            {"kind": "actor", "label": "Người bán", "layer": "client"},
        ],
        "messages": [
            (0, 1, "Yêu cầu đặt mua sản phẩm (Click “Đặt mua”)", "call"),
            (1, 2, "GET /san-pham/<pk>/dat-mua/ → view buy_post()", "call"),
            (2, 1, "Hiển thị form đặt mua (buy_post.html)", "return"),
            (0, 1, "Nhập lời nhắn, số điện thoại và bấm “Gửi yêu cầu”", "call"),
            (1, 2, "Gửi thông tin đặt mua (POST)", "call"),
            (2, 3, "SELECT 1 FROM app_main_order WHERE post_id=?", "call"),
            (2, 1, "Chuyển hướng kèm thông báo đã gửi trước đó", "return", "7a"),
            (1, 0, "Hiển thị thông báo không thể đặt mua", "return", "8a"),
            (2, 3, "INSERT INTO app_main_order", "call", "7b"),
            (2, 1, "Chuyển hướng tới my_orders", "return", "8b"),
            (4, 2, "POST accept_order(pk): người bán xác nhận", "call", "9"),
            (2, 3, "UPDATE app_main_order SET status = 'CONFIRMED'", "call", "10"),
            (2, 1, "Chuyển hướng tới order_detail", "return", "11"),
            (1, 0, "Hiển thị đơn xác nhận", "return", "12"),
        ],
        "file": "seq-dat-mua.png",
        "fragments": [
            {"kind": "alt", "first": 7, "split": 8, "last": 10,
             "guard": "[Trường hợp đã có đơn mở]",
             "else_guard": "Trường hợp chưa có đơn mở"},
        ],
    },
}

#: Nhãn tiếng Việt cho cột "Loại" của bảng thông điệp.
MESSAGE_KINDS = {
    "call": "Gọi hàm",
    "return": "Trả về",
    "self": "Tự xử lý",
}


def _render_sequence(key: str) -> Path:
    """Vẽ một sơ đồ tuần tự từ dữ liệu trong ``SEQUENCES``."""
    spec = SEQUENCES[key]
    d = SequenceDiagram(spec["headers"], spec["banner"], spec["legend"])
    for message in spec["messages"]:
        src, dst, text, kind = message[:4]
        num = message[4] if len(message) > 4 else None
        d.msg(src, dst, text, kind, num)
    for frag in spec["fragments"]:
        split = frag.get("split")
        d.fragment(
            frag.get("kind", "opt"), frag["guard"],
            frag["first"] - 1, frag["last"] - 1,
            None if split is None else split - 1,
            frag.get("else_guard", ""),
        )
    out = ASSETS / spec["file"]
    render_svg(d.svg(), out, width=1560)
    return out


def seq_dang_ky() -> Path:
    return _render_sequence("dang-ky")


def seq_dang_nhap() -> Path:
    return _render_sequence("dang-nhap")


def seq_dang_tin() -> Path:
    return _render_sequence("dang-tin")


def seq_dat_mua() -> Path:
    return _render_sequence("dat-mua")


# ------------------------------------------------------------ sơ đồ PERT

#: Mạng PERT lấy nguyên từ Bài nhận thức 3: (tên, đỉnh đầu, đỉnh cuối, thời lượng).
PERT_EDGES: list[tuple[str, int, int, int]] = [
    ("A", 0, 1, 9),
    ("B", 0, 2, 8),
    ("C", 0, 3, 6),
    ("D", 1, 4, 5),
    ("B'", 2, 4, 0),   # cung giả
    ("E", 2, 5, 4),
    ("C'", 3, 5, 0),   # cung giả
    ("F", 3, 6, 3),
    ("E'", 5, 6, 0),   # cung giả
    ("H", 4, 7, 9),
    ("I", 5, 7, 4),
    ("G", 7, 8, 12),
    ("J", 6, 8, 10),
]

PERT_NODES = 9

#: Toạ độ vẽ (đơn vị viewBox) — cột theo mức dài nhất, không theo thứ tự số đỉnh.
PERT_POS: dict[int, tuple[float, float]] = {
    0: (70, 200),
    1: (250, 80),
    2: (250, 200),
    3: (250, 320),
    4: (450, 80),
    5: (450, 200),
    6: (450, 320),
    7: (645, 150),
    8: (840, 260),
}

PERT_RADIUS = 20.0


def pert_times() -> dict:
    """Tính ES/EF/LS/LF/slack bằng hai lượt duyệt trên mạng PERT.

    Trả về dict gồm các danh sách theo đỉnh, danh sách cạnh găng và tổng thời gian T.
    """
    successors: dict[int, list[tuple[int, int, int]]] = {i: [] for i in range(PERT_NODES)}
    predecessors: dict[int, list[tuple[int, int]]] = {i: [] for i in range(PERT_NODES)}
    for _, start, end, dur in PERT_EDGES:
        successors[start].append((end, dur, 0))
        predecessors[end].append((start, dur))

    order: list[int] = []
    indegree = {node: len(predecessors[node]) for node in range(PERT_NODES)}
    queue = [node for node in range(PERT_NODES) if indegree[node] == 0]
    while queue:
        node = queue.pop(0)
        order.append(node)
        for end, _, _ in successors[node]:
            indegree[end] -= 1
            if indegree[end] == 0:
                queue.append(end)
    assert len(order) == PERT_NODES, "Mạng PERT có chu trình — không tính được"

    es = [0] * PERT_NODES
    ef = [0] * PERT_NODES
    for node in order:
        for end, dur, _ in successors[node]:
            es[end] = max(es[end], es[node] + dur)
    for node in range(PERT_NODES):
        ef[node] = max((es[start] + dur for start, dur in predecessors[node]), default=es[node])
    total = max(es)

    lf = [total] * PERT_NODES
    ls = [total] * PERT_NODES
    for node in reversed(order):
        if successors[node]:
            lf[node] = min(ls[end] - dur for end, dur, _ in successors[node])
        # Đỉnh không tốn thời gian nên LS = LF; LF = min(LS đỉnh kế - thời lượng cung).
        ls[node] = lf[node]
    slack = [ls[node] - es[node] for node in range(PERT_NODES)]
    critical_nodes = [node for node in range(PERT_NODES) if slack[node] == 0]
    critical_edges = [
        (name, start, end)
        for name, start, end, dur in PERT_EDGES
        if dur > 0 and slack[start] == 0 and slack[end] == 0 and es[start] + dur == es[end]
    ]

    assert es == [0, 9, 8, 6, 14, 12, 12, 23, 35], f"ES sai: {es}"
    assert ls == [0, 9, 14, 19, 14, 19, 25, 23, 35], f"LS sai: {ls}"
    assert critical_nodes == [0, 1, 4, 7, 8], f"đỉnh găng sai: {critical_nodes}"
    assert total == 35, f"tổng thời gian sai: {total}"

    return {
        "es": es,
        "ef": ef,
        "ls": ls,
        "lf": lf,
        "slack": slack,
        "critical_nodes": critical_nodes,
        "critical_edges": [name for name, _, _ in critical_edges],
        "total": total,
    }


def _arrow(p: tuple[float, float], q: tuple[float, float], shrink: float) -> tuple[float, float, float, float]:
    import math

    dx, dy = q[0] - p[0], q[1] - p[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    return (
        p[0] + ux * shrink,
        p[1] + uy * shrink,
        q[0] - ux * shrink,
        q[1] - uy * shrink,
    )


def render_pert() -> Path:
    """Vẽ sơ đồ PERT: đỉnh tròn ghi ES/LS, cung ghi Tên(thời lượng)."""
    import math

    info = pert_times()
    width, height = 920, 400
    critical = set(info["critical_edges"])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        "<defs>",
        '<marker id="pert-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#334155"/></marker>',
        '<marker id="pert-ah-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#b91c1c"/></marker>',
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]

    for name, start, end, dur in PERT_EDGES:
        p, q = PERT_POS[start], PERT_POS[end]
        x1, y1, x2, y2 = _arrow(p, q, PERT_RADIUS + 2)
        on_critical = name in critical
        color = "#b91c1c" if on_critical else "#334155"
        marker = "pert-ah-red" if on_critical else "pert-ah"
        dash = ' stroke-dasharray="6 4"' if dur == 0 else ""
        stroke_w = 2.4 if on_critical else 1.5
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{stroke_w}" marker-end="url(#{marker})"{dash}/>'
        )
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        dx, dy = q[0] - p[0], q[1] - p[1]
        length = math.hypot(dx, dy) or 1.0
        label = f"{name} ({dur})"
        if abs(dx) < 1e-6 or abs(dy) > 2 * abs(dx):
            # Cung gần thẳng đứng: đặt nhãn lệch phải để không đè lên nét cung.
            lx, ly, anchor = mx + 10, my + 4, "start"
        else:
            nx, ny = -dy / length, dx / length
            if ny > 0:
                nx, ny = -nx, -ny
            lx, ly, anchor = mx + nx * 18, my + ny * 18, "middle"
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-family="{DIAGRAM_FONT}" font-size="13" '
            f'font-weight="{"bold" if on_critical else "normal"}" '
            f'fill="{"#b91c1c" if on_critical else "#1f2937"}" text-anchor="{anchor}">{_esc(label)}</text>'
        )

    for node in range(PERT_NODES):
        cx, cy = PERT_POS[node]
        slack = info["slack"][node]
        fill = "#fee2e2" if slack == 0 else "#ffffff"
        stroke = "#b91c1c" if slack == 0 else "#334155"
        parts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{PERT_RADIUS:.1f}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{cy + 6:.1f}" font-family="{DIAGRAM_FONT}" font-size="16" '
            f'font-weight="bold" fill="#111827" text-anchor="middle">{node}</text>'
        )
        # Viền trắng quanh chữ ES/LS để mũi tên đi vào đỉnh không đè lên số.
        parts.append(
            f'<text x="{cx:.1f}" y="{cy - PERT_RADIUS - 7:.1f}" font-family="{DIAGRAM_FONT}" font-size="12.5" '
            f'fill="#111827" text-anchor="middle" stroke="#ffffff" stroke-width="4" paint-order="stroke">'
            f'{info["es"][node]}/{info["ls"][node]}</text>'
        )

    parts.append("</svg>")
    out = ASSETS / "pert.png"
    render_svg("\n".join(parts), out, width=1600)
    return out


# ------------------------------------------------------- ảnh board thiết kế

FIGMA_BOARDS = [
    ("dang-ky", "figma-dang-ky.png"),
    ("dang-nhap", "figma-dang-nhap.png"),
    ("dang-tin", "figma-dang-tin.png"),
    ("dat-mua", "figma-dat-mua.png"),
]


def _figma(slug: str) -> Path:
    """Chụp toàn bộ trang board thiết kế (3 bước) thành một ảnh dọc."""
    from PIL import Image

    source = ROOT / "docs" / f"figma-board-{slug}.html"
    if not source.exists():
        raise FileNotFoundError(f"Thiếu board thiết kế: {source}")
    name = dict(FIGMA_BOARDS)[slug]
    out = ASSETS / name
    # Chrome 132+ bỏ chế độ headless cũ nên --screenshot chỉ chụp viewport:
    # chụp với cửa sổ rất cao rồi cắt bớt phần nền trắng phía dưới.
    # Board rộng tối đa 1540 px: chụp ở 1600 px để không bị cắt hai bên.
    render_html(source, out, width=1600, height=6000, full_page=True)
    with Image.open(out) as img:
        rgb = img.convert("RGB")
        gray = rgb.convert("L")
        width, height = rgb.size
        # Nền trang là màu xám nhạt: cắt tại hàng cuối còn khác màu nền.
        background = rgb.getpixel((width - 4, height - 4))
        last = 0
        for y in range(height - 1, -1, -1):
            different = 0
            for x in range(0, width, 6):
                pixel = rgb.getpixel((x, y))
                if sum(abs(a - b) for a, b in zip(pixel, background)) > 18:
                    different += 1
                    if different > 4:
                        break
            if different > 4:
                last = y
                break
        cropped = rgb.crop((0, 0, width, min(height, last + 24)))
        cropped.save(out)
        size = cropped.size
        extrema = gray.getextrema()
    assert size[1] > 900, f"{name}: chiều cao {size[1]} px — chụp thiếu trang?"
    assert extrema[0] < 250, f"{name}: ảnh gần như trắng trơn {extrema}"
    print(f"    {name}: {size[0]}x{size[1]}")
    return out


def figma_dang_ky() -> Path:
    return _figma("dang-ky")


def figma_dang_nhap() -> Path:
    return _figma("dang-nhap")


def figma_dang_tin() -> Path:
    return _figma("dang-tin")


def figma_dat_mua() -> Path:
    return _figma("dat-mua")


#: Khung cắt hai cột "BƯỚC 2 · WIREFRAME" và "BƯỚC 3 · MOCKUP CHI TIẾT" trên ảnh
#: board 1600 px. Board có 3 cột: x = 60..533 / 557..1030 / 1054..1527, nên cắt từ
#: 549 (lề trái cột 2) tới 1535 (lề phải cột 3). Cạnh trên/dưới cắt sát thẻ nội
#: dung để bỏ dải header và footer trang trí: board đăng ký cao hơn vì form dài.
FIGMA_PAIR_BOXES = {
    "dang-ky": (549, 185, 1535, 890),
    "dang-nhap": (549, 187, 1535, 865),
    "dang-tin": (549, 226, 1535, 845),
    "dat-mua": (549, 229, 1535, 844),
}


def figma_pairs() -> list[Path]:
    """Cắt riêng hai cột wireframe + mockup của cả bốn board (dùng cho mục 2.3)."""
    from PIL import Image

    outputs: list[Path] = []
    for slug, box in FIGMA_PAIR_BOXES.items():
        source = ASSETS / dict(FIGMA_BOARDS)[slug]
        if not source.exists():
            raise FileNotFoundError(
                f"Thiếu ảnh board {source} — chạy generator của board trước."
            )
        out = ASSETS / f"figma-{slug}-pair.png"
        with Image.open(source) as img:
            rgb = img.convert("RGB")
            width, height = rgb.size
            x0, y0, x1, y1 = box
            assert 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height, (
                f"{out.name}: khung {box} nằm ngoài ảnh {width}x{height}"
            )
            cropped = rgb.crop(box)
            cropped.save(out)
        print(f"    {out.name}: {cropped.size[0]}x{cropped.size[1]}")
        outputs.append(out)
    return outputs


# ------------------------------------------------ sơ đồ thực thể - quan hệ

ERD_COL_X = (55, 400, 745)
ERD_ROW_Y = (50, 320, 590, 860)
ERD_W = 250
ERD_HEAD = 38
ERD_LINE = 22

#: (tên, kiểu dữ liệu, khoá) — khoá: "PK", "FK" hoặc "".
ERD_TABLES: dict[str, dict] = {
    "auth_user": {
        "title": "auth_user (Người dùng)",
        "col": 0, "row": 1,
        "fields": [
            ("id", "bigint", "PK"),
            ("username", "varchar(150)", ""),
            ("email", "varchar(254)", ""),
            ("password", "varchar(128)", ""),
            ("is_staff", "boolean", ""),
            ("date_joined", "datetime", ""),
        ],
    },
    "Profile": {
        "title": "Profile (Hồ sơ)",
        "col": 0, "row": 0,
        "fields": [
            ("id", "bigint", "PK"),
            ("user_id", "bigint", "FK"),
            ("student_id", "varchar(20)", ""),
            ("faculty", "varchar(120)", ""),
            ("phone", "varchar(15)", ""),
            ("avatar", "varchar(100)", ""),
        ],
    },
    "Category": {
        "title": "Category (Danh mục)",
        "col": 1, "row": 0,
        "fields": [
            ("id", "bigint", "PK"),
            ("name", "varchar(100)", ""),
            ("slug", "varchar(50)", ""),
            ("icon", "varchar(20)", ""),
            ("order", "int", ""),
        ],
    },
    "Post": {
        "title": "Post (Bài đăng)",
        "col": 1, "row": 1,
        "fields": [
            ("id", "bigint", "PK"),
            ("seller_id", "bigint", "FK"),
            ("category_id", "bigint", "FK"),
            ("title", "varchar(200)", ""),
            ("price", "decimal(10)", ""),
            ("status", "varchar(10)", ""),
        ],
    },
    "PostImage": {
        "title": "PostImage (Ảnh)",
        "col": 2, "row": 0,
        "fields": [
            ("id", "bigint", "PK"),
            ("post_id", "bigint", "FK"),
            ("image", "varchar(100)", ""),
            ("order", "int", ""),
        ],
    },
    "Comment": {
        "title": "Comment (Bình luận)",
        "col": 2, "row": 1,
        "fields": [
            ("id", "bigint", "PK"),
            ("post_id", "bigint", "FK"),
            ("author_id", "bigint", "FK"),
            ("content", "text", ""),
            ("created_at", "datetime", ""),
        ],
    },
    "Favorite": {
        "title": "Favorite (Yêu thích)",
        "col": 2, "row": 2,
        "fields": [
            ("id", "bigint", "PK"),
            ("user_id", "bigint", "FK"),
            ("post_id", "bigint", "FK"),
            ("created_at", "datetime", ""),
        ],
    },
    "Review": {
        "title": "Review (Đánh giá)",
        "col": 2, "row": 3,
        "fields": [
            ("id", "bigint", "PK"),
            ("post_id", "bigint", "FK"),
            ("seller_id", "bigint", "FK"),
            ("reviewer_id", "bigint", "FK"),
            ("rating", "smallint", ""),
        ],
    },
    "Report": {
        "title": "Report (Báo cáo)",
        "col": 0, "row": 3,
        "fields": [
            ("id", "bigint", "PK"),
            ("post_id", "bigint", "FK"),
            ("reporter_id", "bigint", "FK"),
            ("reason", "varchar(20)", ""),
            ("status", "varchar(10)", ""),
        ],
    },
    "Order": {
        "title": "Order (Đơn đặt mua)",
        "col": 1, "row": 2,
        "fields": [
            ("id", "bigint", "PK"),
            ("post_id", "bigint", "FK"),
            ("buyer_id", "bigint", "FK"),
            ("seller_id", "bigint", "FK"),
            ("price_snapshot", "decimal(10)", ""),
            ("status", "varchar(10)", ""),
        ],
    },
}


def erd_rect(name: str) -> tuple[int, int, int, int]:
    table = ERD_TABLES[name]
    x = ERD_COL_X[table["col"]]
    y = ERD_ROW_Y[table["row"]]
    return x, y, ERD_W, ERD_HEAD + ERD_LINE * len(table["fields"])


def erd_anchor(name: str, side: str, offset: float) -> tuple[float, float]:
    """Điểm trên cạnh hộp; ``offset`` tính từ mép trên (trái/phải) hoặc trái (trên/dưới)."""
    x, y, w, h = erd_rect(name)
    if side == "top":
        return x + offset, y
    if side == "bottom":
        return x + offset, y + h
    if side == "left":
        return x, y + offset
    if side == "right":
        return x + w, y + offset
    raise ValueError(side)


#: Mỗi quan hệ: hai đầu (bảng, cạnh, offset), danh sách điểm gấp khúc, nhãn hai đầu.
ERD_RELATIONS: list[dict] = [
    # Profile 1—1 auth_user
    {"a": ("Profile", "bottom", 75), "b": ("auth_user", "top", 75), "via": [], "la": "1", "lb": "1"},
    # Category 1—n Post
    {"a": ("Category", "bottom", 125), "b": ("Post", "top", 125), "via": [], "la": "1", "lb": "n"},
    # auth_user 1—n Post
    {"a": ("auth_user", "right", 100), "b": ("Post", "left", 100), "via": [], "la": "1", "lb": "n"},
    # Post 1—n PostImage
    {"a": ("Post", "right", 30), "b": ("PostImage", "left", 60), "via": [(672, 350), (672, 110)], "la": "1", "lb": "n"},
    # Post 1—n Comment
    {"a": ("Post", "right", 130), "b": ("Comment", "left", 130), "via": [], "la": "1", "lb": "n"},
    # Post 1—n Favorite
    {"a": ("Post", "bottom", 160), "b": ("Favorite", "left", 60),
     "via": [(560, 545), (692, 545), (692, 650)], "la": "1", "lb": "n"},
    # Post 1—n Order
    {"a": ("Post", "bottom", 80), "b": ("Order", "top", 80), "via": [], "la": "1", "lb": "n"},
    # auth_user 1—n Order (buyer + seller)
    {"a": ("auth_user", "right", 160), "b": ("Order", "left", 90),
     "via": [(375, 480), (375, 680)], "la": "1", "lb": "n"},
    # auth_user 1—n Favorite
    {"a": ("auth_user", "left", 70), "b": ("Favorite", "right", 60),
     "via": [(38, 390), (38, 12), (1032, 12), (1032, 650)], "la": "1", "lb": "n"},
    # auth_user 1—n Comment
    {"a": ("auth_user", "right", 40), "b": ("Comment", "right", 80),
     "via": [(350, 360), (350, 28), (1015, 28), (1015, 400)], "la": "1", "lb": "n"},
    # auth_user 1—n Report
    {"a": ("auth_user", "bottom", 95), "b": ("Report", "top", 95), "via": [], "la": "1", "lb": "n"},
    # Post 1—n Report
    {"a": ("Post", "left", 130), "b": ("Report", "top", 125),
     "via": [(350, 450), (350, 830), (180, 830)], "la": "1", "lb": "n"},
    # auth_user 1—n Review (seller + reviewer)
    {"a": ("auth_user", "left", 110), "b": ("Review", "bottom", 105),
     "via": [(22, 430), (22, 1040), (850, 1040)], "la": "1", "lb": "n"},
    # Post 1—n Review
    {"a": ("Post", "right", 160), "b": ("Review", "left", 40),
     "via": [(716, 480), (716, 900)], "la": "1", "lb": "n"},
]


def _erd_label(point: tuple[float, float], toward: tuple[float, float], text: str) -> str:
    """Nhãn 1/n đặt lệch khỏi đầu mút một đoạn ngắn, có quầng trắng."""
    px, py = point
    qx, qy = toward
    dx, dy = qx - px, qy - py
    length = max((dx * dx + dy * dy) ** 0.5, 1.0)
    lx = px + dx / length * 15
    ly = py + dy / length * 15 + 4
    return (
        f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle" font-size="14" '
        f'font-weight="700" fill="#b45309" stroke="#ffffff" stroke-width="3.4" '
        f'paint-order="stroke">{_esc(text)}</text>'
    )


def _erd_box(name: str) -> list[str]:
    table = ERD_TABLES[name]
    x, y, w, h = erd_rect(name)
    hub = name in ("auth_user", "Post")
    head_fill = "#0f6ecd" if hub else "#1e3a5f"
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#ffffff" '
        f'stroke="#94a3b8" stroke-width="1.6"/>',
        f'<path d="M{x} {y + 7} a7 7 0 0 1 7 -7 h{w - 14} a7 7 0 0 1 7 7 v{ERD_HEAD - 7} '
        f'h{-w} z" fill="{head_fill}"/>',
        f'<text x="{x + w / 2}" y="{y + 25}" text-anchor="middle" font-size="16" '
        f'font-weight="700" fill="#ffffff">{_esc(table["title"])}</text>',
    ]
    for i, (field, sql_type, key) in enumerate(table["fields"]):
        ty = y + ERD_HEAD + i * ERD_LINE
        cy = ty + 15
        if i:
            parts.append(
                f'<line x1="{x + 1}" y1="{ty}" x2="{x + w - 1}" y2="{ty}" '
                f'stroke="#e2e8f0" stroke-width="1"/>'
            )
        if key:
            color = "#b45309" if key == "PK" else "#0f766e"
            parts.append(
                f'<rect x="{x + 9}" y="{cy - 11}" width="26" height="15" rx="3" '
                f'fill="{color}"/>'
                f'<text x="{x + 22}" y="{cy}" text-anchor="middle" font-size="10" '
                f'font-weight="700" fill="#ffffff">{key}</text>'
            )
        else:
            parts.append(f'<circle cx="{x + 15}" cy="{cy - 4}" r="2.2" fill="#cbd5e1"/>')
        weight = "700" if key == "PK" else "400"
        parts.append(
            f'<text x="{x + 42}" y="{cy}" font-size="15" font-weight="{weight}" '
            f'fill="{INK}">{_esc(field)}</text>'
        )
        parts.append(
            f'<text x="{x + w - 10}" y="{cy}" text-anchor="end" font-size="12" '
            f'fill="#64748b">{_esc(sql_type)}</text>'
        )
    return parts


def render_erd() -> Path:
    """Vẽ sơ đồ thực thể - quan hệ 10 bảng của app_main."""
    width, height = 1050, 1120
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
             f'viewBox="0 0 {width} {height}" font-family="{DIAGRAM_FONT}">',
             f'<rect width="{width}" height="{height}" fill="#ffffff"/>']

    # Đường nối vẽ trước để hộp che lên trên; quầng trắng tạo hiệu ứng cầu vượt.
    for rel in ERD_RELATIONS:
        a_table, a_side, a_off = rel["a"]
        b_table, b_side, b_off = rel["b"]
        points = [erd_anchor(a_table, a_side, a_off), *rel["via"],
                  erd_anchor(b_table, b_side, b_off)]
        d = "M " + " L ".join(f"{px:.0f} {py:.0f}" for px, py in points)
        parts.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="6" '
                     f'stroke-linejoin="round"/>')
        parts.append(f'<path d="{d}" fill="none" stroke="#64748b" stroke-width="1.5" '
                     f'stroke-linejoin="round"/>')
        parts.append(_erd_label(points[0], points[1], rel["la"]))
        parts.append(_erd_label(points[-1], points[-2], rel["lb"]))

    for name in ERD_TABLES:
        parts.extend(_erd_box(name))

    legend_y = 1072
    parts.append(
        f'<rect x="55" y="{legend_y - 18}" width="26" height="15" rx="3" fill="#b45309"/>'
        f'<text x="68" y="{legend_y - 6}" text-anchor="middle" font-size="10" '
        f'font-weight="700" fill="#ffffff">PK</text>'
        f'<text x="92" y="{legend_y - 6}" font-size="13" fill="{INK}">khoá chính</text>'
        f'<rect x="200" y="{legend_y - 18}" width="26" height="15" rx="3" fill="#0f766e"/>'
        f'<text x="213" y="{legend_y - 6}" text-anchor="middle" font-size="10" '
        f'font-weight="700" fill="#ffffff">FK</text>'
        f'<text x="237" y="{legend_y - 6}" font-size="13" fill="{INK}">khoá ngoại</text>'
        f'<line x1="345" y1="{legend_y - 11}" x2="405" y2="{legend_y - 11}" '
        f'stroke="#64748b" stroke-width="1.5"/>'
        f'<text x="413" y="{legend_y - 6}" font-size="13" fill="{INK}">'
        f'quan hệ 1—n (một—nhiều)</text>'
    )
    parts.append(
        f'<text x="55" y="{legend_y + 24}" font-size="12" fill="#475569">'
        f'Order.buyer_id và Order.seller_id cùng tham chiếu auth_user.id; '
        f'Review.seller_id và Review.reviewer_id cùng tham chiếu auth_user.id '
        f'(mỗi cặp dùng chung một đường nối).</text>'
    )
    parts.append("</svg>")

    out = ASSETS / "erd.png"
    render_svg("".join(parts), out, width=1600)
    print(f"    erd: {svg_size(''.join(parts))}")
    return out


# ------------------------------------------- kiến trúc MTV và cây thư mục

MONO_FONT = "Consolas, 'Cascadia Mono', 'Courier New', monospace"


def _mtv_box(x: float, y: float, w: float, h: float, title: str, accent: str) -> list[str]:
    """Hộp chữ nhật bo góc có dải tiêu đề màu."""
    head = h
    radius = 8
    d = (
        f"M {x} {y + head} V {y + radius} A {radius} {radius} 0 0 1 {x + radius} {y} "
        f"H {x + w - radius} A {radius} {radius} 0 0 1 {x + w} {y + radius} "
        f"V {y + head} Z"
    )
    return [
        f'<path d="{d}" fill="{accent}"/>',
        f'<text x="{x + w / 2}" y="{y + h / 2 + 6}" text-anchor="middle" font-size="16" '
        f'font-weight="700" fill="#ffffff">{_esc(title)}</text>',
    ]


def _mtv_arrow(
    x1: float, y1: float, x2: float, y2: float, label: str,
    lx: float, ly: float, *, both: bool = False, dashed: bool = False,
) -> list[str]:
    extra = ' marker-start="url(#mtv-ah)"' if both else ""
    if dashed:
        extra += ' stroke-dasharray="6 4"'
    return [
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#64748b" stroke-width="1.6" '
        f'marker-end="url(#mtv-ah)"{extra}/>',
        f'<text x="{lx}" y="{ly}" font-size="13" fill="#334155" stroke="#ffffff" '
        f'stroke-width="4" paint-order="stroke">{_esc(label)}</text>',
    ]


def render_mtv() -> Path:
    """Vẽ kiến trúc MTV của Django và luồng xử lý một yêu cầu."""
    width, height = 780, 520
    blue, amber, green, grey, slate = "#0f6ecd", "#b45309", "#0f766e", "#64748b", "#475569"
    mx, mw, cx = 170, 250, 295      # cột chính: x, bề rộng, tâm
    rx, rcx = 500, 625              # cột phải
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{DIAGRAM_FONT}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        '<defs><marker id="mtv-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
        'markerHeight="8" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker></defs>',
    ]

    parts += _mtv_box(mx, 26, mw, 36, "Trình duyệt", grey)
    parts += _mtv_box(mx, 116, mw, 36, "URLconf (urls.py)", grey)
    parts += _mtv_box(mx, 206, mw, 36, "V — View (views.py)", blue)
    parts += _mtv_box(mx, 346, mw, 36, "T — Template (*.html)", green)
    parts += _mtv_box(mx, 456, mw, 36, "Trình duyệt nhận HTML", grey)
    parts += _mtv_box(rx, 206, 250, 36, "M — Model (models.py)", amber)
    parts += _mtv_box(rx, 346, 250, 36, "CSDL MariaDB", slate)

    parts += _mtv_arrow(cx, 62, cx, 116, "HTTP request", cx + 12, 96)
    parts += _mtv_arrow(cx, 152, cx, 206, "khớp tuyến", cx + 12, 186)
    parts += _mtv_arrow(mx + mw, 224, rx, 224, "ORM", (mx + mw + rx) / 2, 216, both=True)
    parts += _mtv_arrow(rcx, 242, rcx, 346, "SQL", rcx + 12, 302, both=True)
    parts += _mtv_arrow(cx, 242, cx, 346, "truyền context", cx + 12, 300)
    parts += _mtv_arrow(cx, 382, cx, 456, "HTTP response", cx + 12, 426, dashed=True)

    parts.append("</svg>")
    out = ASSETS / "mtv.png"
    render_svg("".join(parts), out, width=1600)
    print(f"    mtv: {svg_size(''.join(parts))}")
    return out


#: (dòng cây, chú thích) — cột chú thích bắt đầu ở kí tự thứ 31.
TREE_LINES: list[tuple[str, str]] = [
    ("SachGocUni/", "thư mục gốc của dự án"),
    ("├── manage.py", "điểm vào dòng lệnh của Django"),
    ("├── requirements.txt", "danh sách thư viện phụ thuộc"),
    ("├── .env", "cấu hình môi trường: CSDL, SECRET_KEY"),
    ("├── db.sqlite3", "CSDL dự phòng khi MariaDB không chạy"),
    ("├── core/", "cấu hình chung của dự án"),
    ("│   ├── settings.py", "thiết lập CSDL, i18n, static, media"),
    ("│   ├── urls.py", "bảng định tuyến gốc"),
    ("│   └── wsgi.py, asgi.py", "điểm vào cho máy chủ web"),
    ("├── app_main/", "ứng dụng nghiệp vụ chính"),
    ("│   ├── models.py", "10 mô hình dữ liệu"),
    ("│   ├── views.py", "các hàm xử lý nghiệp vụ"),
    ("│   ├── forms.py", "form đăng ký, đăng nhập, đăng tin"),
    ("│   ├── urls.py", "tuyến URL của ứng dụng"),
    ("│   ├── admin.py", "đăng ký mô hình với Django Admin"),
    ("│   ├── templatetags/", "bộ lọc hiển thị giá, thời gian"),
    ("│   ├── signals.py", "tự tạo Profile khi tạo User"),
    ("│   └── migrations/", "4 migration đã áp dụng"),
    ("├── templates/", "toàn bộ giao diện HTML"),
    ("│   ├── base.html", "khung chung: navbar, footer"),
    ("│   ├── partials/", "navbar, footer, post_card, ..."),
    ("│   ├── registration/", "login.html, register.html"),
    ("│   └── app_main/", "14 template nghiệp vụ"),
    ("├── static/", "css/ và js/ tự viết"),
    ("├── media/", "ảnh tải lên: avatars/, posts/"),
    ("└── docs/", "tài liệu, sơ đồ, báo cáo"),
]


def render_tree() -> Path:
    """Vẽ cây thư mục rút gọn của dự án."""
    font, row, top = 20, 27, 30
    advance = font * 0.55
    left = 40
    comment_x = round(left + 31 * advance)
    width = 900
    height = top + row * len(TREE_LINES) + 26

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{MONO_FONT}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    # Kí tự │ của font monospace để hở giữa hai dòng, nên vẽ thêm nét nối dọc
    # màu xám trung tính (nét của kí tự cũng được tô xám bằng tspan bên dưới).
    for index, (line, _) in enumerate(TREE_LINES):
        y = top + index * row
        prefix = line[: line.rfind("─") + 1]
        for column, char in enumerate(prefix):
            if char != "│":
                continue
            x = left + (column + 0.5) * advance - 0.2
            parts.append(
                f'<line x1="{x:.1f}" y1="{y - 19.5:.1f}" x2="{x:.1f}" y2="{y + 7.5:.1f}" '
                f'stroke="#94a3b8" stroke-width="1.2"/>'
            )

    for index, (line, comment) in enumerate(TREE_LINES):
        y = top + index * row
        cut = line.rfind("─") + 1
        prefix, name = line[:cut], line[cut:]
        is_dir = name.rstrip().endswith("/")
        color = "#0f6ecd" if is_dir else INK
        weight = ' font-weight="600"' if is_dir else ""
        parts.append(
            f'<text x="{left}" y="{y}" font-size="{font}" fill="{color}"{weight} '
            f'xml:space="preserve">'
            + (f'<tspan fill="#94a3b8" font-weight="400">{_esc(prefix)}</tspan>' if prefix else "")
            + f'{_esc(name)}</text>'
        )
        parts.append(
            f'<text x="{comment_x}" y="{y}" font-size="{font}" fill="#64748b" '
            f'xml:space="preserve">{_esc(comment)}</text>'
        )
    parts.append("</svg>")

    out = ASSETS / "tree.png"
    render_svg("".join(parts), out, width=1600)
    print(f"    tree: {svg_size(''.join(parts))}")
    return out


# ------------------------------------------------ ảnh chụp giao diện thật

#: Server demo phải chạy trước (xem hướng dẫn ở _check_server).
BASE_URL = os.environ.get("REPORT_BASE_URL", "http://127.0.0.1:8011")
SEED_IDS = ROOT / "docs" / "report" / "seed_ids.json"
SHOT_VIEWPORT = (1440, 1000)

#: (tên file, đường dẫn, chuỗi phải xuất hiện) theo từng phiên đăng nhập.
APP_SHOT_GROUPS: dict[str, list[dict]] = {
    "anonymous": [
        {"name": "app-home", "path": "/", "marker": "SáchGóc Uni", "clip": (0, 1440)},
        {
            "name": "app-register",
            "path": "/dang-ky/",
            "marker": "Tạo tài khoản sinh viên",
            "select": ".max-w-lg",
        },
        {"name": "app-login", "path": "/dang-nhap/", "marker": "Đăng nhập", "select": ".max-w-md"},
    ],
    "student": [
        {
            "name": "app-post-detail",
            "path": "/san-pham/{detail_pk}/",
            "marker": "Lập trình Python",
            "clip": (0, 800),
        },
        {
            "name": "app-create-post",
            "path": "/dang-tin/",
            "marker": "Đăng tin mới",
            "fill": """(() => {
                const set = (sel, value) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    const proto = el.tagName === 'TEXTAREA'
                        ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                };
                const pick = (sel, needle) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    const opt = Array.from(el.options).find(o => o.textContent.includes(needle));
                    if (!opt) return false;
                    el.value = opt.value;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                };
                set('#id_title', 'Giáo trình Giải tích 1 - Đại số tuyến tính');
                pick('#id_category', 'Giáo trình');
                pick('#id_condition', 'Như mới');
                set('#id_price', '55000');
                set('#id_description',
                    'Combo 2 cuốn Giải tích 1 và Đại số tuyến tính dùng cho học kỳ 1, '
                    + 'sách còn mới 95%, chỉ ghi tên ở trang bìa, không gạch chân. '
                    + 'Mình đã qua môn nên để lại cho bạn khoá sau, giao dịch tại thư viện trường.');
                return true;
            })()""",
        },
        {
            "name": "app-buy-post",
            "path": "/san-pham/{buy_pk}/dat-mua/",
            "marker": "Đặt mua",
            "fill": """(() => {
                const set = (sel, value) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    const proto = el.tagName === 'TEXTAREA'
                        ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                };
                set('#id_message',
                    'Chào bạn, mình muốn nhận cuốn Giáo trình Lập trình Python. '
                    + 'Chiều thứ 4 này mình có tiết ở khu A, khoảng 15h gặp nhau ở thư viện được không?');
                set('#id_contact', '0905123456');
                return true;
            })()""",
        },
        {
            "name": "app-orders",
            "path": "/don-hang/",
            "marker": "Đơn hàng của tôi",
            "clip": (0, 620),
        },
    ],
    "admin": [
        {
            "name": "app-dashboard",
            "path": "/quan-tri/",
            "marker": "Bảng điều khiển",
            # Cắt ngay dưới hàng thẻ lối tắt: chân trang tối màu và khoảng trắng
            # bên dưới không mang dữ liệu, giữ lại thì hình cao 14,7 cm và bị đẩy
            # sang trang riêng, để lại gần nửa trang trống ở cuối chương 2.
            "clip": (0, 960),
        },
        {
            "name": "app-django-admin",
            "path": "/django-admin/app_main/post/",
            "marker": "để thay đổi",
            "clip": (0, 900),
            "width": 1600,
        },
    ],
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _check_server(base_url: str) -> None:
    """Báo lỗi rõ ràng nếu server demo chưa chạy."""
    try:
        with urllib.request.urlopen(base_url + "/", timeout=5) as response:
            status = response.status
    except Exception as exc:  # noqa: BLE001 — cần bắt mọi lỗi kết nối
        raise RuntimeError(
            "Chưa chạy được server demo. Mở terminal khác và chạy:\n"
            "  set USE_SQLITE=True\n"
            "  python manage.py runserver 8011 --noreload\n"
            f"Lỗi gốc: {exc}"
        ) from exc
    if status != 200:
        raise RuntimeError(f"Server demo trả về HTTP {status} cho {base_url}/")


class _Cdp:
    """Client CDP tối giản: gửi lệnh và chờ đúng phản hồi theo id."""

    def __init__(self, ws_url: str) -> None:
        import websocket  # websocket-client

        self.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True)
        self.next_id = 0

    def call(self, method: str, params: dict | None = None, session_id: str | None = None) -> dict:
        self.next_id += 1
        payload: dict = {"id": self.next_id, "method": method, "params": params or {}}
        if session_id:
            payload["sessionId"] = session_id
        self.ws.send(json.dumps(payload))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") != self.next_id:
                continue
            if "error" in message:
                raise RuntimeError(f"CDP {method} lỗi: {message['error']}")
            return message.get("result", {})

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:  # noqa: BLE001 — đóng socket có thể lỗi, không quan trọng
            pass


class _AppChrome:
    """Một phiên Chrome headless giữ đăng nhập, dùng để chụp nhiều trang."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.profile = ""
        self.proc: subprocess.Popen | None = None
        self.cdp: _Cdp | None = None
        self.session = ""

    # --- vòng đời ---
    def __enter__(self) -> "_AppChrome":
        width, height = SHOT_VIEWPORT
        self.profile = tempfile.mkdtemp(prefix="app-shot-")
        port = _free_port()
        self.proc = subprocess.Popen(
            [
                str(chrome_binary()),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-background-networking",
                "--remote-allow-origins=*",
                f"--remote-debugging-port={port}",
                f"--user-data-dir={self.profile}",
                f"--window-size={width},{height}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        version = self._wait_debugger(port)
        self.cdp = _Cdp(version["webSocketDebuggerUrl"])
        target = self.cdp.call("Target.createTarget", {"url": "about:blank"})
        self.session = self.cdp.call(
            "Target.attachToTarget", {"targetId": target["targetId"], "flatten": True}
        )["sessionId"]
        self.cdp.call("Page.enable", session_id=self.session)
        # Ép giao diện sáng: Django admin tự đổi màu theo prefers-color-scheme.
        self.cdp.call(
            "Emulation.setEmulatedMedia",
            {"features": [{"name": "prefers-color-scheme", "value": "light"}]},
            session_id=self.session,
        )
        self.cdp.call(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": False,
            },
            session_id=self.session,
        )
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self.cdp is not None:
            self.cdp.close()
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)

    def _wait_debugger(self, port: int, timeout: float = 40.0) -> dict:
        deadline = time.time() + timeout
        url = f"http://127.0.0.1:{port}/json/version"
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise RuntimeError("Chrome thoát ngay khi khởi động (headless)")
            try:
                with urllib.request.urlopen(url, timeout=3) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception:  # noqa: BLE001 — Chrome chưa mở cổng, thử lại
                time.sleep(0.25)
        raise RuntimeError("Chrome không mở cổng remote debugging sau 40s")

    # --- thao tác trang ---
    def eval(self, expression: str) -> object:
        assert self.cdp is not None
        result = self.cdp.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
            session_id=self.session,
        )
        if "exceptionDetails" in result:
            raise RuntimeError(f"JS lỗi: {result['exceptionDetails']}")
        return result.get("result", {}).get("value")

    def _wait_ready(self, timeout: float = 40.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                state = self.eval("document.readyState")
                images = self.eval("Array.from(document.images).every(i => i.complete)")
            except RuntimeError:
                time.sleep(0.15)
                continue
            if state == "complete" and images:
                return
            time.sleep(0.15)
        raise RuntimeError("Trang không tải xong sau 40s")

    def goto(self, url: str) -> None:
        assert self.cdp is not None
        result = self.cdp.call("Page.navigate", {"url": url}, session_id=self.session)
        if result.get("errorText"):
            raise RuntimeError(f"Không mở được {url}: {result['errorText']}")
        self._wait_ready()

    def login(self, username: str, password: str) -> None:
        self.goto(self.base_url + "/dang-nhap/")
        filled = self.eval(
            """(() => {
                const user = document.getElementById('id_username');
                const pass = document.getElementById('id_password');
                if (!user || !pass) return false;
                user.value = %s;
                pass.value = %s;
                user.form.submit();
                return true;
            })()"""
            % (json.dumps(username), json.dumps(password))
        )
        if not filled:
            raise RuntimeError("Trang đăng nhập không có #id_username / #id_password")

        deadline = time.time() + 40
        while time.time() < deadline:
            try:
                ready = self.eval("document.readyState")
                path = self.eval("location.pathname") or ""
                signed_in = self.eval(
                    "document.querySelector('form[action*=\"dang-xuat\"]') !== null"
                )
            except RuntimeError:
                time.sleep(0.2)
                continue
            if ready == "complete" and path != "/dang-nhap/" and signed_in:
                return
            time.sleep(0.25)
        raise RuntimeError(f"Đăng nhập thất bại cho {username}")

    def assert_page(self, name: str, marker: str) -> None:
        text = self.eval("document.body ? document.body.innerText : ''") or ""
        title = self.eval("document.title") or ""
        for bad in (
            "Page not found",
            "Server Error",
            "Traceback (most recent call last)",
            "TemplateDoesNotExist",
            "OperationalError",
        ):
            if bad in text:
                raise RuntimeError(f"{name}: trang lỗi chứa “{bad}” — {text[:300]}")
        if marker not in title and marker not in text:
            raise RuntimeError(f"{name}: không thấy dấu hiệu “{marker}” — tiêu đề “{title}”")

    def _reset_viewport(self, width: int | None = None) -> None:
        """Trả viewport về kích thước gốc trước khi đo trang mới."""
        assert self.cdp is not None
        base_width, height = SHOT_VIEWPORT
        self.cdp.call(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width or base_width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": False,
            },
            session_id=self.session,
        )
        time.sleep(0.2)

    def shoot(
        self,
        out_png: Path,
        clip: tuple[int, int] | None = None,
        select: str | None = None,
        pad: int = 28,
        width: int | None = None,
    ) -> tuple[int, int]:
        """Chụp trang hiện tại.

        - ``select``: cắt đúng vùng của phần tử (dùng cho trang đăng nhập/đăng ký).
        - ``clip``: cắt từ đầu trang với chiều cao cho trước.
        - ``width``: bề rộng khung nhìn khác mặc định (Django admin cần rộng hơn).
        - Không truyền gì: chụp toàn bộ trang (kéo viewport theo nội dung).
        """
        assert self.cdp is not None
        width = width or SHOT_VIEWPORT[0]
        self._reset_viewport(width)

        if select:
            rect = self.eval(
                """(() => {
                    const el = document.querySelector(%s);
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return {x: r.x + window.scrollX, y: r.y + window.scrollY,
                            w: r.width, h: r.height};
                })()"""
                % json.dumps(select)
            )
            if not rect:
                raise RuntimeError(f"Không tìm thấy phần tử {select} để cắt ảnh")
            x = max(0, int(math.floor(rect["x"])) - pad)
            y = max(0, int(math.floor(rect["y"])) - pad)
            shot_w = min(width - x, int(math.ceil(rect["w"])) + 2 * pad)
            shot_h = int(math.ceil(rect["h"])) + 2 * pad
        elif clip:
            x, y = 0, 0
            shot_w = width
            shot_h = clip[1]
        else:
            content = self.cdp.call(
                "Page.getLayoutMetrics", session_id=self.session
            )["cssContentSize"]
            shot_h = max(int(math.ceil(content["height"])), 600)
            self.cdp.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": width, "height": shot_h, "deviceScaleFactor": 1, "mobile": False},
                session_id=self.session,
            )
            time.sleep(0.3)
            content = self.cdp.call(
                "Page.getLayoutMetrics", session_id=self.session
            )["cssContentSize"]
            shot_h = max(int(math.ceil(content["height"])), 600)
            x, y = 0, 0
            shot_w = width

        data = self.cdp.call(
            "Page.captureScreenshot",
            {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {"x": x, "y": y, "width": shot_w, "height": shot_h, "scale": 1},
            },
            session_id=self.session,
        )["data"]
        out_png.parent.mkdir(parents=True, exist_ok=True)
        out_png.write_bytes(base64.b64decode(data))
        return shot_w, shot_h


def app_shots() -> list[Path]:
    """Chụp 9 màn hình thật của ứng dụng (3 phiên: khách, sinh viên, quản trị)."""
    from PIL import Image

    if not SEED_IDS.exists():
        raise FileNotFoundError(
            f"Thiếu {SEED_IDS.relative_to(ROOT)} — chạy trước:\n"
            "  set USE_SQLITE=True\n"
            "  python docs/report/seed_demo.py"
        )
    ids = json.loads(SEED_IDS.read_text(encoding="utf-8"))
    base_url = os.environ.get("REPORT_BASE_URL", ids.get("base_url", BASE_URL)).rstrip("/")
    _check_server(base_url)
    screens = ids["screens"]
    credentials = ids["credentials"]

    outputs: list[Path] = []
    for group, pages in APP_SHOT_GROUPS.items():
        with _AppChrome(base_url) as chrome:
            if group != "anonymous":
                chrome.login(credentials[group]["username"], credentials[group]["password"])
            for page in pages:
                name = page["name"]
                url = base_url + page["path"].format(**screens)
                chrome.goto(url)
                chrome.assert_page(name, page["marker"])
                if page.get("fill"):
                    chrome.eval(page["fill"])
                out = ASSETS / f"{name}.png"
                width, height = chrome.shoot(
                    out, clip=page.get("clip"), select=page.get("select"), width=page.get("width")
                )
                with Image.open(out) as img:
                    size = img.size
                    extrema = img.convert("L").getextrema()
                assert size == (width, height), f"{name}: {size} khác mong đợi {(width, height)}"
                assert extrema[0] < 250, f"{name}: ảnh gần như trắng trơn {extrema}"
                print(f"    {name}: {size[0]}x{size[1]}")
                outputs.append(out)
    return outputs


# ---------------------------------------------------------------- smoke test


def _smoke() -> None:
    from PIL import Image

    ASSETS.mkdir(parents=True, exist_ok=True)
    out = ASSETS / "_smoke.png"
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='400' height='200'>"
        "<rect width='400' height='200' fill='#ffffff'/>"
        "<rect x='20' y='20' width='120' height='60' fill='#1173d4'/>"
        "<text x='40' y='140' font-family='Times New Roman' font-size='28' fill='#111'>SáchGóc Uni</text>"
        "</svg>"
    )
    render_svg(svg, out, width=400)
    with Image.open(out) as img:
        size = img.size
        corner = img.convert("RGB").getpixel((399, 199))
    print(f"smoke: size={size} corner={corner}")
    assert size == (400, 200), f"kích thước sai: {size}"
    out.unlink()
    print("smoke: OK, đã xoá ảnh thử")


def main(argv: list[str]) -> int:
    if "--smoke" in argv:
        _smoke()
        return 0
    ASSETS.mkdir(parents=True, exist_ok=True)
    generators = [
        seq_dang_ky,
        seq_dang_nhap,
        seq_dang_tin,
        seq_dat_mua,
        render_pert,
        render_erd,
        render_mtv,
        render_tree,
        figma_dang_ky,
        figma_dang_nhap,
        figma_dang_tin,
        figma_dat_mua,
        figma_pairs,
        app_shots,
    ]
    print(f"Sinh {len(generators)} hình...")
    for fn in generators:
        result = fn()
        paths = result if isinstance(result, list) else [result]
        for path in paths:
            print(f"  -> {path.relative_to(ROOT)}")
    print("Xong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
