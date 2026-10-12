"""
Sinh ảnh minh hoạ cho sản phẩm mẫu.

Vì sao cần?
------------
Dữ liệu mẫu ban đầu không có file ảnh nên mọi thẻ sản phẩm hiển thị ô trống
"Chưa có ảnh", làm giao diện kém sinh động. Script này vẽ ảnh đại diện cho
TỪNG sản phẩm bằng Pillow, gồm:
  - Nền gradient theo màu danh mục
  - Biểu tượng (emoji) của danh mục
    • Tên sản phẩm hiển thị rõ, tự co giãn cho vừa khung
    • Nhãn danh mục + tình trạng

Ảnh được lưu vào media/posts/seed/ rồi script seed_data.py gán vào bài đăng.

Cách chạy:
    python generate_images.py
"""

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / 'media' / 'posts' / 'seed'

WIDTH, HEIGHT = 1200, 900

# --- Font ---
FONT_BOLD = 'C:/Windows/Fonts/segoeuib.ttf'
FONT_SEMI = 'C:/Windows/Fonts/segoeuisl.ttf'
FONT_REGULAR = 'C:/Windows/Fonts/segoeui.ttf'
FONT_EMOJI = 'C:/Windows/Fonts/seguiemj.ttf'


# Bảng màu theo danh mục: (màu đậm, màu nhạt, màu nhấn)
CATEGORY_COLORS = {
    'Giáo trình & Sách':    ((79, 70, 229),   (129, 140, 248), (165, 180, 252)),
    'Dụng cụ học tập':      ((217, 119, 6),   (245, 158, 11), (252, 211, 77)),
    'Thiết bị điện tử':    ((2, 132, 199),   (14, 165, 233), (125, 211, 252)),
    'Đồ dùng KTX':         ((4, 120, 87),    (16, 185, 129), (110, 231, 183)),
    'Tài liệu ôn thi':      ((190, 24, 93),   (225, 29, 72),  (253, 164, 175)),
    'Thời trang sinh viên': ((126, 34, 206),  (168, 85, 247), (216, 180, 254)),
}

# Nhãn tình trạng hiển thị trên ảnh
CONDITION_LABEL = {
    'NEW': 'MỚI 100%',
    'LIKE_NEW': 'NHƯ MỚI 90-99%',
    'GOOD': 'TỐT 70-89%',
    'USED': 'CŨ DƯỚI 70%',
}

CATEGORY_EMOJI = {
    'Giáo trình & Sách': '📚',
    'Dụng cụ học tập': '✏️',
    'Thiết bị điện tử': '💻',
    'Đồ dùng KTX': '🏠',
    'Tài liệu ôn thi': '📝',
    'Thời trang sinh viên': '👕',
}


def safe_filename(text, limit=60):
    """Tạo tên file an toàn từ tiêu đề tiếng Việt (giữ nguyên chữ cái)."""
    cleaned = ''.join(c for c in text if c.isalnum() or c in ' -_')
    cleaned = cleaned.replace(' ', '-').replace('--', '-').strip('-')
    return (cleaned[:limit] or 'san-pham') + '.jpg'


def load_font(path, size):
    """Nạp font, có phương án dự phòng nếu thiếu file."""
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def hex_to_rgb(value):
    """'#4f46e5' -> (79, 70, 229)"""
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def make_gradient(size, color_start, color_end, diagonal=True):
    """Tạo nền gradient."""
    width, height = size
    base = Image.new('RGB', size, color_start)
    draw = ImageDraw.Draw(base)

    for y in range(height):
        ratio = y / max(height - 1, 1)
        row = tuple(
            int(color_start[i] + (color_end[i] - color_start[i]) * ratio)
            for i in range(3)
        )
        draw.line([(0, y), (width, y)], fill=row)

    if diagonal:
        # Lớp phủ chéo nhẹ tạo chiều sâu
        overlay = Image.new('RGBA', size, (255, 255, 255, 0))
        odraw = ImageDraw.Draw(overlay)
        for step in range(0, width + height, 6):
            odraw.line(
                [(step, 0), (step - height, height)],
                fill=(255, 255, 255, 10),
                width=5
            )
        base = Image.alpha_composite(base.convert('RGBA'), overlay)

    return base.convert('RGB')


def add_decorations(image, accent):
    """Thêm các hình tròn mờ làm điểm nhấn cho nền."""
    width, height = image.size
    circles = Image.new('RGBA', image.size, (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(circles)

    shapes = [
        (width * 0.86, height * 0.10, width * 0.30),
        (width * 0.10, height * 0.86, width * 0.26),
        (width * 0.74, height * 0.80, width * 0.16),
    ]
    for cx, cy, radius in shapes:
        cdraw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(*accent, 46)
        )

    circles = circles.filter(ImageFilter.GaussianBlur(4))
    return Image.alpha_composite(image.convert('RGBA'), circles).convert('RGB')


def wrap_text(draw, text, font, max_width):
    """Ngắt dòng văn bản cho vừa chiều rộng."""
    words = text.split()
    lines, current = [], ''

    for word in words:
        candidate = f"{current} {word}".strip()
        width = draw.textlength(candidate, font=font)
        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines


def fit_title(draw, title, max_width, max_height, start_size=76, min_size=34):
    """Chọn cỡ chữ lớn nhất mà tiêu đề vẫn nằm gọn trong khung."""
    size = start_size
    while size >= min_size:
        font = load_font(FONT_BOLD, size)
        lines = wrap_text(draw, title, font, max_width)
        line_height = size * 1.22
        if len(lines) * line_height <= max_height:
            return font, lines, line_height
        size -= 2

    font = load_font(FONT_BOLD, min_size)
    return font, wrap_text(draw, title, font, max_width), min_size * 1.22


def draw_pill(draw, xy, text, font, bg, fg=(255, 255, 255, 235)):
    """Vẽ nhãn bo tròn."""
    x, y = xy
    text_w = draw.textlength(text, font=font)
    pad_x, pad_y = 26, 12
    box = [x, y, x + text_w + pad_x * 2, y + font.size + pad_y * 2 + 4]
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=bg)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg)
    return box[3] + 24


def draw_emoji(image, emoji, center, target_height):
    """Vẽ emoji nếu font hỗ trợ, bỏ qua nếu lỗi."""
    try:
        font = ImageFont.truetype(FONT_EMOJI, target_height)
        overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.text(center, emoji, font=font, embedded_color=True, anchor='mm')
        return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    except Exception:
        return image


def build_image(title, category, condition):
    """Dựng ảnh đại diện cho một sản phẩm."""
    dark, light, accent = CATEGORY_COLORS.get(
        category, ((99, 102, 241), (129, 140, 248), (199, 210, 254))
    )

    image = make_gradient((WIDTH, HEIGHT), dark, light)
    image = add_decorations(image, accent)

    # Emoji lớn ở giữa phía trên (vẽ TRƯỚC để không che mất các nhãn bên dưới)
    image = draw_emoji(image, CATEGORY_EMOJI.get(category, '📦'),
                       (WIDTH / 2, HEIGHT * 0.33), 190)

    overlay = image.convert('RGBA')
    draw = ImageDraw.Draw(overlay)

    # Nhãn danh mục (góc trên trái) - nền tối để chữ trắng luôn nổi bật
    draw_pill(
        draw, (64, 56),
        category.upper(),
        load_font(FONT_SEMI, 28),
        (0, 0, 0, 78)
    )

    # Nhãn tình trạng (góc trên phải)
    label = CONDITION_LABEL.get(condition, '')
    if label:
        label_font = load_font(FONT_SEMI, 26)
        text_w = draw.textlength(label, font=label_font)
        box = [WIDTH - 64 - text_w - 52, 56, WIDTH - 64, 56 + 26 + 24 + 4]
        draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2,
                                fill=(0, 0, 0, 62))
        draw.text((box[0] + 26, box[1] + 12), label, font=label_font,
                  fill=(255, 255, 255, 235))

    # Tiêu đề sản phẩm
    max_width = WIDTH - 180
    max_height = 230
    font, lines, line_height = fit_title(draw, title, max_width, max_height,
                                         start_size=68)

    block_height = len(lines) * line_height
    start_y = HEIGHT * 0.60 - block_height / 2

    for index, line in enumerate(lines):
        line_w = draw.textlength(line, font=font)
        draw.text(
            ((WIDTH - line_w) / 2, start_y + index * line_height),
            line, font=font, fill=(255, 255, 255, 255)
        )

    # Đường kẻ trang trí + chữ thương hiệu
    footer_y = HEIGHT - 92
    footer_font = load_font(FONT_SEMI, 28)

    dash_font = load_font(FONT_SEMI, 28)
    brand = "SáchGóc Uni"
    brand_w = draw.textlength(brand, font=dash_font)
    draw.text(((WIDTH - brand_w) / 2, footer_y), brand,
              font=dash_font, fill=(255, 255, 255, 190))

    line_y = footer_y + 46
    draw.line([(WIDTH / 2 - 70, line_y), (WIDTH / 2 + 70, line_y)],
              fill=(255, 255, 255, 120), width=3)

    return overlay.convert('RGB')


def run():
    # Lấy danh sách sản phẩm từ seed_data để không phải khai báo trùng lặp
    from seed_data import PRODUCTS

    print("=" * 62)
    print("  SINH ẢNH MINH HOẠ CHO SẢN PHẨM MẪU")
    print("=" * 62)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Thư mục đích: {OUTPUT_DIR}")
    print(f"  Kích thước   : {WIDTH}x{HEIGHT}\n")

    created = 0
    for title, category, _price, _is_free, condition, *_rest in PRODUCTS:
        filename = safe_filename(title)
        path = OUTPUT_DIR / filename

        try:
            image = build_image(title, category, condition)
            image.save(path, 'JPEG', quality=88, optimize=True)
            created += 1
            print(f"   ✅ {filename}")
        except Exception as exc:
            print(f"   ❌ {title}: {exc}")

    print(f"\n{'=' * 62}")
    print(f"  ✅ ĐÃ TẠO {created}/{len(PRODUCTS)} ẢNH")
    print(f"  Chạy tiếp:  python seed_data.py   (để gán ảnh vào bài đăng)")
    print(f"{'=' * 62}")


if __name__ == '__main__':
    run()
