"""
Tạo ảnh tổng hợp (contact sheet) từ các ảnh sản phẩm để KIỂM CHỨNG BẰNG MẮT.

Vì sao cần script này?
---------------------
Openverse tìm ảnh theo metadata nên rất dễ trả về ảnh SAI nội dung
(ví dụ tìm "máy tính Casio" lại ra mạch điện tử). Không có cách nào kiểm
chứng tự động chắc chắn 100%, nên cần nhìn thủ công.

Cách dùng:
    python make_contact_sheet.py            # tạo ảnh tổng hợp
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / 'media' / 'posts' / 'seed'
OUTPUT = BASE_DIR / 'contact_sheet.jpg'

THUMB_W, THUMB_H = 300, 225
COLS = 5
LABEL_H = 46
FONT_PATH = 'C:/Windows/Fonts/arialbd.ttf'


def main():
    sys.path.insert(0, str(BASE_DIR))
    from seed_data import PRODUCTS
    from download_images import safe_filename

    items = []
    for index, product in enumerate(PRODUCTS, start=1):
        path = IMAGE_DIR / safe_filename(product[0])
        if path.exists():
            items.append((index, product[0], path))

    if not items:
        print("Không tìm thấy ảnh nào trong", IMAGE_DIR)
        return

    rows = (len(items) + COLS - 1) // COLS
    sheet_w = COLS * THUMB_W
    sheet_h = rows * (THUMB_H + LABEL_H)

    sheet = Image.new('RGB', (sheet_w, sheet_h), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)

    try:
        font_num = ImageFont.truetype(FONT_PATH, 26)
        font_txt = ImageFont.truetype(FONT_PATH, 15)
    except OSError:
        font_num = font_txt = ImageFont.load_default()

    for position, (index, title, path) in enumerate(items):
        col, row = position % COLS, position // COLS
        x = col * THUMB_W
        y = row * (THUMB_H + LABEL_H)

        try:
            image = Image.open(path).convert('RGB').resize(
                (THUMB_W, THUMB_H), Image.LANCZOS
            )
            sheet.paste(image, (x, y))
        except Exception:
            draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], fill=(220, 220, 220))

        # Số thứ tự lớn ở góc để dễ đối chiếu
        draw.rectangle([x + 4, y + 4, x + 42, y + 40], fill=(0, 0, 0))
        draw.text((x + 14, y + 8), str(index), font=font_num, fill=(255, 255, 255))

        # Tên sản phẩm (cắt gọn)
        label = title if len(title) <= 34 else title[:32] + '..'
        draw.text((x + 6, y + THUMB_H + 12), label, font=font_txt, fill=(20, 20, 20))

        draw.rectangle([x, y, x + THUMB_W - 1, y + THUMB_H + LABEL_H - 1],
                       outline=(210, 210, 210), width=1)

    sheet.save(OUTPUT, 'JPEG', quality=86)
    print(f"Đã tạo contact sheet: {OUTPUT}")
    print(f"Số ảnh: {len(items)} | Kích thước: {sheet_w}x{sheet_h}")
    print("\nDanh sách để đối chiếu:")
    for index, title, _ in items:
        print(f"  {index:>2}. {title}")


if __name__ == '__main__':
    main()
