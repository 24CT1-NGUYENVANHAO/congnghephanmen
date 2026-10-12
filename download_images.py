"""
Tải ảnh THẬT cho sản phẩm mẫu từ Openverse.

Vì sao dùng Openverse?
----------------------
Openverse là API tìm kiếm ảnh mở, quét các nguồn như Flickr, Wikimedia Commons.
Mọi ảnh đều kèm giấy phép Creative Commons nên dùng cho đồ án là hợp lệ.
API miễn phí, không cần đăng ký khoá.

Cách chạy:
    python download_images.py              # tải ảnh còn thiếu
    python download_images.py --force      # tải lại tất cả
    python download_images.py --only "Bàn" # chỉ tải cho sản phẩm chứa "Bàn"

Ảnh sau khi tải sẽ được cắt/căn về đúng khung 1200x900 (4:3) và lưu lại
ĐÚNG TÊN FILE như generate_images.py tạo ra, nên seed_data.py không phải
sửa gì thêm.

Nếu tải lỗi, ảnh vẽ do generate_images.py tạo sẽ được giữ nguyên.
"""

import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / 'media' / 'posts' / 'seed'
TARGET_SIZE = (1200, 900)

OPENVERSE_API = 'https://api.openverse.org/v1/images/'
HEADERS = {
    'User-Agent': 'SachGocUni/1.0 (Django project - student assignment)',
}

# Từ khoá tìm ảnh cho từng sản phẩm (tiếng Anh cho kết quả tốt hơn)
KEYWORDS = {
    "Giáo trình Triết học Mác - Lênh (bản còn mới)": "philosophy book stack",
    "Giáo trình Lập trình Python cơ bản (có bài tập)": "computer programming textbook",
    "Bộ sách Giải tích 1 & Đại số tuyến tính": "mathematics textbook books",
    "Giáo trình Cơ sở dữ liệu & SQL (bản tiếng Việt)": "database server technology",
    "Sách Lập trình Web với Django (bản mới nhất)": "html css website code screen",
    "Sách Phân tích thiết kế hệ thống (UML)": "software architecture diagram",
    "Sách Marketing căn bản (tặng)": "advertising marketing office",
    "Máy tính Casio FX-580VN X (pin mới)": "pocket calculator handheld",
    "Combo 5 cuốn vở kẻ ngang 200 trang (A4)": "notebooks stationery desk",
    "Bộ thước vẽ kỹ thuật & bàn vẽ A3": "architect drafting technical drawing",
    "Bàn vẽ điện tử Gaomon 1060Pro": "graphics tablet stylus",
    "Bộ bút highlight 6 màu pastel dịu": "highlighters markers pens",
    "Máy tính khoa học Casio fx-991ES Plus": "casio calculator mathematics",
    "Chuột không dây Logitech M185": "computer mouse desk",
    "Tai nghe có dây chống nhiễu cho học online": "headphones earphones student",
    "Bàn phím cơ AKKO 3087 Silent ( switches Brown)": "mechanical keyboard",
    "Đế tản nhiệt laptop 2 quạt LED": "laptop cooling pad fan",
    "USB 32GB Kingston chống nước": "usb flash drive memory",
    "Laptop Dell Inspiron 15 (i5, 8GB RAM)": "dell laptop notebook computer",
    "Router Wi-Fi TP-Link TP-LINK TL-WR841N": "wifi router network",
    "Đèn học chống cận thị gấp gọn 3 chế độ": "desk lamp study light",
    "Balo đựng laptop 15.6 inch chống nước": "backpack laptop bag student",
    "Kệ để sách gỗ lắp ghép 3 tầng": "wooden bookshelf books",
    "Quạt tích điện để bàn cổng USB": "portable electric fan",
    "Bàn học gỗ chân sắt (80x60cm)": "wooden desk study room",
    "Bộ đề thi CSDL 10 năm kèm đáp án chi tiết": "exam papers test documents",
    "Tài liệu ôn thi Tiếng Anh A2/B1 (in sẵn)": "english language dictionary",
    "Sổ tay công thức Toán cao cấp": "notebook notes mathematics",
    "Flashcard ôn thi tiếng Anh (300 từ)": "flashcards study revision",
    "Áo khoác thể thao Đại học Kiến trúc (tặng)": "sports jacket clothing",
    "Balo trường logo Đại học Kiến trúc (tặng)": "school bag campus backpack",
    "Móc treo quần áo nhựa (combo 10 cái)": "clothes hangers wardrobe",
    "Bàn vẽ điện tử HXS100 (đã bán)": "drawing tablet pen tablet",
    "Bộ sách Vật lý đại cương (đã tặng)": "physics textbooks books",
}

# Bộ từ khoá bị LOẠI khi tìm ảnh - tránh ảnh sai chủ đề.
# Ví dụ từ khoá "calculator" dễ ra ảnh mạch điện tử, ảnh hồ sơ thuế...
BLACKLIST_KEYWORDS = [
    # ảnh mạch/bo mạch hay bị trả về khi tìm đồ điện tử
    'circuit', 'pcb', 'teardown', 'disassembly', 'board',
    'teardown', 'internals', 'schematic', 'wiring',
    # ảnh giấy tờ/tài liệu hành chính
    'tax return', 'tax form', 'invoice', 'receipt',
    # ảnh không liên quan
    'coffee', 'beer', 'wine', 'cigarette', 'toy',
    'map', 'diagram of', 'chart of', 'logo',
]

# Từ khoá BẮT BUỘC phải xuất hiện trong tiêu đề ảnh (tăng độ tin cậy)
TITLE_HINT_KEYWORDS = {
    'Giáo trình Triết học Mác - Lênh (bản còn mới)': ['book'],
    'Giáo trình Lập trình Python cơ bản (có bài tập)': ['book', 'python'],
    'Bộ sách Giải tích 1 & Đại số tuyến tính': ['book', 'mathemat'],
    'Giáo trình Cơ sở dữ liệu & SQL (bản tiếng Việt)': ['book', 'database', 'sql'],
    'Sách Lập trình Web với Django (bản mới nhất)': ['book', 'web', 'code', 'laptop'],
    'Sách Phân tích thiết kế hệ thống (UML)': ['book', 'software', 'architect'],
    'Sách Marketing căn bản (tặng)': ['book', 'marketing'],
    'Máy tính Casio FX-580VN X (pin mới)': ['calculator', 'casio'],
    'Combo 5 cuốn vở kẻ ngang 200 trang (A4)': ['notebook', 'notepad', 'paper'],
    'Bộ thước vẽ kỹ thuật & bàn vẽ A3': ['drawing', 'architect', 'draft', 'technical'],
    'Bàn vẽ điện tử Gaomon 1060Pro': ['tablet', 'stylus', 'pen', 'graphics'],
    'Bộ bút highlight 6 màu pastel dịu': ['marker', 'highlight', 'pen'],
    'Máy tính khoa học Casio fx-991ES Plus': ['calculator', 'casio'],
    'Chuột không dây Logitech M185': ['mouse'],
    'Tai nghe có dây chống nhiễu cho học online': ['headphone', 'earphone', 'headset'],
    'Bàn phím cơ AKKO 3087 Silent ( switches Brown)': ['keyboard'],
    'Đế tản nhiệt laptop 2 quạt LED': ['laptop', 'cooler', 'cooling', 'fan'],
    'USB 32GB Kingston chống nước': ['usb', 'flash', 'memory', 'stick'],
    'Laptop Dell Inspiron 15 (i5, 8GB RAM)': ['laptop', 'notebook', 'dell'],
    'Router Wi-Fi TP-Link TP-LINK TL-WR841N': ['router', 'wifi', 'wi-fi'],
    'Đèn học chống cận thị gấp gọn 3 chế độ': ['lamp', 'light', 'desk'],
    'Balo đựng laptop 15.6 inch chống nước': ['backpack', 'bag', 'rucksack'],
    'Kệ để sách gỗ lắp ghép 3 tầng': ['bookshelf', 'shelf', 'bookcase'],
    'Quạt tích điện để bàn cổng USB': ['fan'],
    'Bàn học gỗ chân sắt (80x60cm)': ['desk', 'table'],
    'Bộ đề thi CSDL 10 năm kèm đáp án chi tiết': ['exam', 'test', 'paper'],
    'Tài liệu ôn thi Tiếng Anh A2/B1 (in sẵn)': ['english', 'dictionary', 'language'],
    'Sổ tay công thức Toán cao cấp': ['notebook', 'notes', 'formula'],
    'Flashcard ôn thi tiếng Anh (300 từ)': ['flashcard', 'card'],
    'Áo khoác thể thao Đại học Kiến trúc (tặng)': ['jacket', 'coat', 'clothing', 'hoodie'],
    'Balo trường logo Đại học Kiến trúc (tặng)': ['backpack', 'bag', 'school'],
    'Móc treo quần áo nhựa (combo 10 cái)': ['hanger', 'clothes', 'wardrobe'],
    'Bàn vẽ điện tử HXS100 (đã bán)': ['tablet', 'stylus', 'pen'],
    'Bộ sách Vật lý đại cương (đã tặng)': ['physics', 'book'],
}

# Từ khoá dự phòng theo danh mục khi sản phẩm không có trong bảng trên
CATEGORY_KEYWORDS = {
    'Giáo trình & Sách': 'textbook books study',
    'Dụng cụ học tập': 'stationery school supplies',
    'Thiết bị điện tử': 'computer electronics device',
    'Đồ dùng KTX': 'dormitory room furniture',
    'Tài liệu ôn thi': 'study documents notes',
    'Thời trang sinh viên': 'clothing apparel student',
}


def safe_filename(text, limit=60):
    """Tên file an toàn - dùng chung với generate_images.py."""
    cleaned = ''.join(c for c in text if c.isalnum() or c in ' -_')
    cleaned = cleaned.replace(' ', '-').replace('--', '-').strip('-')
    return (cleaned[:limit] or 'san-pham') + '.jpg'


def http_get(url, timeout=25):
    """Tải nội dung URL với User-Agent đúng chuẩn."""
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def search_images(keyword, limit=10):
    """Tìm ảnh trên Openverse theo từ khoá."""
    params = urllib.parse.urlencode({
        'q': keyword,
        'page_size': limit,
        'license_type': 'all-cc',
        'mature': 'false',
    })
    try:
        data = json.loads(http_get(f'{OPENVERSE_API}?{params}'))
        return data.get('results', [])
    except Exception:
        return []


def score_image(item, title_hints):
    """
    Chấm điểm ảnh để chọn ảnh ĐÚNG chủ đề.

    Openverse tìm theo metadata nên rất dễ trả về ảnh sai (ví dụ tìm
    "calculator" lại ra mạch điện tử). Vì vậy cần lọc theo tiêu đề ảnh.
    """
    title = (item.get('title') or '').lower()
    width = item.get('width') or 0
    height = item.get('height') or 0
    score = 0

    # 1. Loại ảnh có từ khoá đen ngay lập tức
    for bad in BLACKLIST_KEYWORDS:
        if bad in title:
            return -1

    # 2. Cộng điểm nếu tiêu đề chứa từ khoá kỳ vọng
    for hint in title_hints:
        if hint in title:
            score += 10

    # 3. Ưu tiên ảnh ngang (hợp với khung 4:3)
    if width and height and width >= height:
        score += 3

    # 4. Ưu tiên ảnh đủ lớn, không quá to
    if width >= 900:
        score += 3
    elif width >= 700:
        score += 1

    # 5. Ảnh quá dài/thẹp thường là ảnh ghép, ưu tiên ảnh gần tỉ lệ 4:3
    if width and height:
        ratio = width / height
        if 1.0 <= ratio <= 2.0:
            score += 2

    return score


def pick_candidate(results, title_hints):
    """Chọn ảnh điểm cao nhất sau khi lọc, loại ảnh trùng lặp."""
    scored = []
    seen_urls = set()

    for item in results:
        url = item.get('url') or ''
        if not url.lower().split('?')[0].endswith(('.jpg', '.jpeg', '.png', '.webp')):
            continue

        # Openverse hay trả về cùng một ảnh nhiều lần ở các kích thước khác nhau
        clean_url = url.split('?')[0]
        if clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)

        points = score_image(item, title_hints)
        if points > 0:
            scored.append((points, item))

    # Điểm cao hơn đứng trước
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for points, item in scored]


def fetch_square_ish(url, attempts=3):
    """Tải ảnh, cắt theo tỉ lệ 4:3 rồi đưa về đúng kích thước."""
    for attempt in range(attempts):
        try:
            raw = http_get(url, timeout=30)
            image = Image.open(io.BytesIO(raw))
            image.load()

            # Chuyển sang RGB (bỏ kênh alpha, xử lý ảnh grayscale)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Cắt giữa theo tỉ lệ 4:3
            target_ratio = TARGET_SIZE[0] / TARGET_SIZE[1]
            width, height = image.size
            current_ratio = width / height

            if current_ratio > target_ratio:
                new_width = int(height * target_ratio)
                left = (width - new_width) // 2
                image = image.crop((left, 0, left + new_width, height))
            else:
                new_height = int(width / target_ratio)
                top = (height - new_height) // 2
                image = image.crop((0, top, width, top + new_height))

            return image.resize(TARGET_SIZE, Image.LANCZOS)
        except Exception:
            if attempt < attempts - 1:
                time.sleep(1.5)
    return None


def run(force=False, only=None):
    from seed_data import PRODUCTS  # lấy danh sách sản phẩm

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("  TẢI ẢNH THẬT TỪ OPENVERSE (Creative Commons)")
    print("=" * 64)
    print("  Nguồn : Flickr • Wikimedia Commons • ...")
    print(f"  Thư mục: {OUTPUT_DIR}")
    print(f"  Kích thước: {TARGET_SIZE[0]}x{TARGET_SIZE[1]}\n")

    downloaded = failed = skipped = 0

    for index, product in enumerate(PRODUCTS, start=1):
        title, category = product[0], product[1]
        filename = safe_filename(title)
        path = OUTPUT_DIR / filename

        if only and only.lower() not in title.lower():
            continue
        if path.exists() and not force:
            print(f"  {index:>2}/{len(PRODUCTS)} ⏭  {title[:44]} (đã có)")
            skipped += 1
            continue

        title_hints = TITLE_HINT_KEYWORDS.get(title, [])
        # Thử từ khoá chính, nếu không ra ảnh nào thì thử từ khoá gợi ý
        search_terms = [KEYWORDS.get(title) or CATEGORY_KEYWORDS.get(category, 'study')]
        search_terms += [hint for hint in title_hints[:2]]

        saved = False
        for term in dict.fromkeys([t for t in search_terms if t]):
            results = search_images(term)
            candidates = pick_candidate(results, title_hints)
            if not candidates:
                continue

            print(f"  {index:>2}/{len(PRODUCTS)} 🔍 \"{term}\" "
                  f"({len(candidates)} ảnh phù hợp)")

            for candidate in candidates[:3]:
                image = fetch_square_ish(candidate['url'])
                if image is None:
                    continue
                image.save(path, 'JPEG', quality=88, optimize=True)
                credit = candidate.get('creator') or 'Unknown'
                license_name = (candidate.get('license') or '').upper()
                print(f"       ✅ {filename[:38]}  ·  CC {license_name} · {credit[:20]}")
                downloaded += 1
                saved = True
                break

            if saved:
                break
            time.sleep(0.4)

        if not saved:
            print(f"  {index:>2}/{len(PRODUCTS)} ⚠️  {title[:40]} - giữ ảnh cũ")
            failed += 1

        time.sleep(0.8)  # tôn trọng API, không dồn request

    print("\n" + "=" * 64)
    print(f"  ✅ Tải mới : {downloaded}")
    print(f"  ⏭  Bỏ qua  : {skipped} (đã có ảnh)")
    print(f"  ⚠️  Lỗi     : {failed} (giữ ảnh vẽ cũ)")
    print(f"{'=' * 64}")
    print("  Chạy tiếp:  python seed_data.py   (để nạp lại vào database)")
    print("=" * 64)


if __name__ == '__main__':
    force = '--force' in sys.argv
    only = None
    if '--only' in sys.argv:
        only = sys.argv[sys.argv.index('--only') + 1]
    run(force=force, only=only)
