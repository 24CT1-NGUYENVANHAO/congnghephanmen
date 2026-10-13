"""
Script nạp dữ liệu mẫu cho dự án SáchGóc Uni.

Cách chạy:  python seed_data.py

Script sẽ:
  1. Xoá sạch dữ liệu sản phẩm cũ (giữ nguyên tài khoản Admin)
  2. Tạo tài khoản sinh viên mẫu
  3. Tạo danh mục, bài đăng, bình luận, đánh giá và yêu thích
  4. In ra thông tin đăng nhập để kiểm thử
"""

import os
import random
import sys
from datetime import timedelta
from pathlib import Path

import django

# Windows mặc định dùng cp1252, cần ép UTF-8 để in được emoji tiếng Việt
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from app_main.models import (  # noqa: E402
    Category, Comment, Favorite, Order, Post, Review,
)

# Thư mục chứa ảnh minh hoạ do generate_images.py tạo ra
SEED_IMAGE_DIR = Path(__file__).resolve().parent / 'media' / 'posts' / 'seed'


def seed_image_for(title):
    """
    Trả về đường dẫn ảnh tương ứng với tiêu đề sản phẩm (đã có sẵn trên đĩa).

    Dùng chung hàm đặt tên với generate_images.py để tên file luôn khớp.
    Trả về None nếu chưa chạy generate_images.py.
    """
    # Import cục bộ để tránh phụ thuộc vòng tròn với generate_images
    from generate_images import safe_filename

    path = SEED_IMAGE_DIR / safe_filename(title)
    return f'posts/seed/{path.name}' if path.exists() else None


# ---------------------------------------------------------------------------
#  DỮ LIỆU MẪU
# ---------------------------------------------------------------------------

CATEGORIES = [
    ("Giáo trình & Sách", "📚", "Sách giáo trình, tài liệu tham khảo, sách luyện tập"),
    ("Dụng cụ học tập", "✏️", "Bút, vở, thước kẻ, compa, dụng cụ vẽ kỹ thuật"),
    ("Thiết bị điện tử", "💻", "Laptop, máy tính, chuột, bàn phím, thiết bị âm thanh"),
    ("Đồ dùng KTX", "🏠", "Nội thất phòng trọ: đèn, quạt, bàn, ghế, giường"),
    ("Tài liệu ôn thi", "📝", "Đề thi, đáp án, tài liệu luyện tập, flashcard"),
    ("Thời trang sinh viên", "👕", "Áo khoác, đồ thể thao, phụ kiện"),
]

# (tiêu đề, danh mục, giá, tặng 0đ, tình trạng, khoa, mã môn, địa điểm, mô tả)
PRODUCTS = [
    # --- Giáo trình ---
    ("Giáo trình Triết học Mác - Lênnh (bản còn mới)", "Giáo trình & Sách", 45000, False, "GOOD",
     "Khoa Triết học", "POL101", "Khu 3",
     "Giáo trình Triết học Mác-Lênh dùng cho môn Triết học đại cương.\nSách đã được highlight và ghi chú ở một số chương, còn nguyên 90% nội dung.\nKhông bị rách, không ghi bìa, sạch sẽ."),

    ("Giáo trình Lập trình Python cơ bản (có bài tập)", "Giáo trình & Sách", 55000, False, "LIKE_NEW",
     "Khoa CNTT & TT", "IT001", "KTX B",
     "Sách dành cho sinh viên năm nhất ngành CNTT.\nCó đầy đủ bài tập thực hành và lời giải ở cuối mỗi chương.\nNgôn ngữ dễ hiểu, ví dụ minh hoạ rõ ràng.\nMình học xong khóa 1 nên không dùng nữa."),

    ("Bộ sách Giải tích 1 & Đại số tuyến tính", "Giáo trình & Sách", 80000, False, "GOOD",
     "Khoa Toán & Vật lý", "MATH101", "Căn cứ Mỹ Đức",
     "Bộ 2 cuối: Giải tích 1 và Đại số tuyến tính cho môn toán đại cương.\nBìa còn tốt, ruột sách đầy đủ trang.\nCó highlight ở các phần công thức quan trọng.\nBán nhanh để lấy tiền mua sách mới."),

    ("Giáo trình Cơ sở dữ liệu & SQL (bản tiếng Việt)", "Giáo trình & Sách", 60000, False, "LIKE_NEW",
     "Khoa CNTT & TT", "IT003", "KTX A",
     "Giáo trình môn Cơ sở dữ liệu với đầy đủ ví dụ về SQL.\nSách dày, in rõ nét.\nPhần bài tập truy vấn rất hữu ích cho đồ án."),

    ("Sách Lập trình Web với Django (bản mới nhất)", "Giáo trình & Sách", 95000, False, "NEW",
     "Khoa CNTT & TT", "IT007", "Khu 3",
     "Sách chuyên sâu về Django 5.x, còn nguyên trong hộp.\nChưa đọc bao nhiêu, tặng luôn cho bạn nào cần.\nRất phù hợp làm đồ án."),

    ("Sách Phân tích thiết kế hệ thống (UML)", "Giáo trình & Sách", 70000, False, "GOOD",
     "Khoa CNTT & TT", "IT005", "KTX C",
     "Giáo trình môn Phân tích thiết kế hệ thống, trình bày chuẩn về UML.\nNhiều ví dụ thực tế, phù hợp làm đồ án nhóm."),

    ("Sách Marketing căn bản (tặng)", "Giáo trình & Sách", 0, True, "USED",
     "Khoa Kinh tế", "MKT101", "Khu 3",
     "Sách marketing căn bản mình dùng để thi cuối kỳ đã xong.\nTặng lại cho bạn nào đang cần tham khảo.\nCòn nguyên, chỉ có vài chỗ highlight.\nLấy tại Khu 3 bất cứ lúc nào nhé."),

    # --- Dụng cụ học tập ---
    ("Máy tính Casio FX-580VN X (pin mới)", "Dụng cụ học tập", 320000, False, "LIKE_NEW",
     "Khoa CNTT & TT", "", "Căn cứ Mỹ Đức",
     "Máy tính bấm Casio FX-580VN X, dùng cho thi trắc nghiệm.\nĐã thay pin mới, phím bấm rất nhạy.\nMàn hình không xước, kèm cáp sạc.\nHộp đầy đủ."),

    ("Combo 5 cuốn vở kẻ ngang 200 trang (A4)", "Dụng cụ học tập", 25000, False, "NEW",
     "Khoa Kiến trúc", "ARCH101", "KTX A",
     "5 cuốn vở kẻ ngang 200 trang, giấy dày 100g không thấm mực.\nMới, chưa viết giấy nào.\nPhù hợp vẽ tay và ghi chú kiến trúc."),

    ("Bộ thước vẽ kỹ thuật & bàn vẽ A3", "Dụng cụ học tập", 95000, False, "GOOD",
     "Khoa Kiến trúc", "ARCH203", "Khu 3",
     "Bộ thước kỹ thuật gồm thước chữ E, thước tỷ lệ, compa.\nBàn vẽ A3 kèm khay đựng.\nDành riêng cho sinh viên Kiến trúc.\nĐã dùng 2 kỳ, còn rất tốt."),

    ("Bàn vẽ điện tử Gaomon 1060Pro", "Dụng cụ học tập", 280000, False, "GOOD",
     "Khoa Kiến trúc", "ARCH301", "KTX B",
     "Bàn vẽ điện tử hỗ trợ màn hình máy tính.\nBút vẽ nhạy, ngòi thay thế còn nguyên.\nVẽ đồ án môn khối rất tiện.\nBán vì chuyển sang dùng máy."),

    ("Bộ bút highlight 6 màu pastel dịu", "Dụng cụ học tập", 18000, False, "NEW",
     "", "", "",
     "Bộ 6 cây highlight màu pastel, nhẹ tay, không lem.\nMới chưa dùng hoặc dùng 2 lần.\nChuyên đánh dấu sách khi ôn thi."),

    ("Máy tính khoa học Casio fx-991ES Plus", "Dụng cụ học tập", 240000, False, "LIKE_NEW",
     "Khoa Kinh tế", "", "Căn cứ Mỹ Đức",
     "Máy tính khoa học hỗ trợ giải hệ phương trình, ma trận.\nMàn hình rõ, pin tốt.\nPhụ kiện đầy đủ."),

    # --- Thiết bị điện tử ---
    ("Chuột không dây Logitech M185", "Thiết bị điện tử", 95000, False, "LIKE_NEW",
     "", "", "KTX A",
     "Chuột không dây 2.4GHz, kết nối ổn định.\nPin tốt, nhấp nhẹ, phù hợp vẽ CAD/dựng hình.\nKèm củ USB."),

    ("Tai nghe có dây chống nhiễu cho học online", "Thiết bị điện tử", 120000, False, "NEW",
     "", "", "",
     "Tai nghe có mic, chất âm rõ ràng, lọc tiếng ồn tốt.\nDùng học online và họp nhóm không bị rè.\nMới, còn nguyên hộp."),

    ("Bàn phím cơ AKKO 3087 Silent ( switches Brown)", "Thiết bị điện tử", 480000, False, "LIKE_NEW",
     "", "", "KTX B",
     "Bàn phím cơ silent switch, gõ êm không gây tiếng ồn trong phòng trọ.\nKeycap PBT in nét, có đèn LED.\nĐủ cáp, hộp và keycap dự phòng."),

    ("Đế tản nhiệt laptop 2 quạt LED", "Thiết bị điện tử", 75000, False, "GOOD",
     "", "", "",
     "Đế tản nhiệt 2 quạt giúp laptop mát hơn khi làm đồ án nặng.\nCó 3 mức tốc độ.\nQuạt chạy êm, không gây tiếng ồn."),

    ("USB 32GB Kingston chống nướt", "Thiết bị điện tử", 62000, False, "NEW",
     "", "", "",
     "USB 3.0 tốc độ cao, thiết kế chống nướt.\nDung lượng 32GB đủ lưu tài liệu và phần mềm.\nCòn nguyên bao bì."),

    ("Laptop Dell Inspiron 15 (i5, 8GB RAM)", "Thiết bị điện tử", 6500000, False, "GOOD",
     "Khoa CNTT & TT", "", "Khu 3",
     "Laptop Dell Inspiron 15, CPU i5 thế hệ 10, RAM 8GB, SSD 256GB.\nPin còn tốt, màn hình FullHD không điểm chết.\nBàn phím tiếng Việt nguyên.\nBán do cần máy mới để làm đồ án AI."),

    ("Router Wi-Fi TP-Link TP-LINK TL-WR841N", "Thiết bị điện tử", 150000, False, "GOOD",
     "", "", "",
     "Router Wi-Fi phát cho cả khu KTX, độ phủ tốt.\nFirmware mới nhất đã cài.\nKèm cáp và adapter."),

    # --- Đồ dùng KTX ---
    ("Đèn học chống cận thị gấp gọn 3 chế độ", "Đồ dùng KTX", 65000, False, "LIKE_NEW",
     "", "", "KTX A",
     "Đèn LED 3 chế độ sáng vàng/trắng, cắm cổng USB.\nTay cứng chắc, xoay 360 độ.\nThiết kế chống cận thị, rất tốt cho mắt."),

    ("Balo đựng laptop 15.6 inch chống nước", "Đồ dùng KTX", 120000, False, "GOOD",
     "", "", "",
     "Balo chống nước, nhiều ngăn, ngăn riêng cho laptop 15.6 inch.\nCó cổng USB sạc dây.\nChất liệu dày dặn, đeo lưng không mỏi."),

    ("Kệ để sách gỗ lắp ghép 3 tầng", "Đồ dùng KTX", 75000, False, "LIKE_NEW",
     "", "", "KTX B",
     "Kệ gỗ lắp ghép không cần dụng cụ, 3 tầng chứa được nhiều sách.\nMàu tự nhiên đẹp, phù hợp phòng trọ.\nChắc chắn, không bị rung."),

    ("Quạt tích điện để bàn cổng USB", "Đồ dùng KTX", 88000, False, "LIKE_NEW",
     "", "", "KTX A",
     "Quạt tích điện 3 chế độ gió, cắm cổng USB laptop.\nCứu tinh cho mùa hè khi KTX hay mất điện.\nPin tốt, dùng được 6-8 giờ."),

    ("Bàn học gỗ chân sắt (80x60cm)", "Đồ dùng KTX", 280000, False, "GOOD",
     "", "", "",
     "Bàn học mặt gỗ ép chống nước, chân sắt chắc chắn.\nKích thước 80x60cm vừa đủ đặt laptop và sách.\nChân có đệm chống trầy sàn."),

    # --- Tài liệu ôn thi ---
    ("Bộ đề thi CSDL 10 năm kèm đáp án chi tiết", "Tài liệu ôn thi", 30000, False, "NEW",
     "Khoa CNTT & TT", "IT003", "Khu 3",
     "Tổng hợp 10 đề thi CSDL các năm kèm đáp án giải chi tiết từng câu.\nChất lượng in tốt, giấy không đục khi highlight.\nRất hữu ích cho kỳ thi cuối."),

    ("Tài liệu ôn thi Tiếng Anh A2/B1 (in sẵn)", "Tài liệu ôn thi", 25000, False, "NEW",
     "", "", "",
     "Bộ tài liệu ôn thi Tiếng Anh trình độ A2/B1.\nTổng hợp 2000 từ vựng thường gặp và ngữ pháp trọng tâm.\nBìa laminate, giấy dày, viết thoải mái."),

    ("Sổ tay công thức Toán cao cấp", "Tài liệu ôn thi", 18000, False, "LIKE_NEW",
     "Khoa Toán & Vật lý", "MATH203", "",
     "Sổ tay tóm tắt toàn bộ công thức Toán cao cấp 1 và 2.\nCó phần bài tập mẫu kèm lời giải.\nNhỏ gọn, bỏ vào túi xem nhanh rất tiện."),

    ("Flashcard ôn thi tiếng Anh (300 từ)", "Tài liệu ôn thi", 20000, False, "NEW",
     "", "", "",
     "300 flashcard từ vựng tiếng Anh thường gặp trong kỳ thi.\nChia sẻ 10 chiều, nhớ lâu hơn.\nMới, còn nguyên bộ."),

    # --- Thời trang ---
    ("Áo khoác thể thao Đại học Kiến trúc (tặng)", "Thời trang sinh viên", 0, True, "GOOD",
     "", "", "Khu 3",
     "Áo khoác thể thao mùa đông của trường, size L.\nMặc 2 mùa nên hơi xù nhẹ ở tay áo.\nTặng lại bạn nào mới vào trường cần giữ ấm.\nLấy tại Khu 3 nhé."),

    ("Balo trường logo Đại học Kiến trúc (tặng)", "Thời trang sinh viên", 0, True, "USED",
     "", "", "Khu 3",
     "Balô canvas in logo trường, dùng được vài lần.\nCòn chắc, dây kéo tốt.\nTặng cho tân sinh viên nhé, mình không dùng nữa."),

    ("Móc treo quần áo nhựa (combo 10 cái)", "Thời trang sinh viên", 0, True, "NEW",
     "", "", "",
     "Combo 10 móc treo quần áo chất liệu nhựa bền.\nMua dưa mà không dùng hết nên tặng lại.\nCòn mới nguyên trong túi."),

    # --- Đã bán (để demo trạng thái) ---
    ("Bàn vẽ điện tử HXS100 (đã bán)", "Dụng cụ học tập", 350000, False, "GOOD",
     "Khoa Kiến trúc", "", "",
     "Bàn vẽ điện tử đã bán cho bạn sinh viên khoa Kiến trúc, giao dịch thành công."),

    ("Bộ sách Vật lý đại cương (đã tặng)", "Giáo trình & Sách", 0, True, "USED",
     "Khoa Toán & Vật lý", "", "",
     "Đã tặng cho tân sinh viên khoa Toán, hẹn gặp ở khu 3. Cảm ơn bạn!"),
]

COMMENTS = [
    "Sách này còn bản PDF không bạn?",
    "Bạn có thể giao dịch ở khu 3 được không?",
    "Tình trạng sách thực tế thế nào, có bị ghi nhiều không?",
    "Mình cần sản phẩm này, còn hàng không bạn?",
    "Giá có thể bớt thêm được không ạ?",
    "Cảm ơn bạn nhiều, hôm nay mình ghé lấy nhé!",
    "Sản phẩm này còn nguyên phụ kiện không?",
    "Bạn có bán kèm cả bài tập không?",
    "Mình sinh viên năm nhất, sản phẩm này dùng được không nhỉ?",
    "Lúc nào rảnh mình đến xem trực tiếp được không?",
]

REVIEW_COMMENTS = [
    "Giao dịch nhanh gọn, người bán nhiệt tình và đúng giá. Rất hài lòng!",
    "Sản phẩm đúng như mô tả, chất lượng tốt hơn mình mong đợi. 👍",
    "Thân thiện, sẵn sàng giải đáp thắc mắc. Rất đáng tin cậy!",
    "Gặp mặt trao đổi thuận lợi, hẹn giao tại cổng trường. Cảm ơn bạn!",
    "Sách tình trạng tốt, giao hàng nhanh. Sẽ giới thiệu bạn cho bạn bè.",
    "Người bán uy tín, giá hợp lý. Rất hài lòng với giao dịch!",
]


# ---------------------------------------------------------------------------
#  HÀM CHÍNH
# ---------------------------------------------------------------------------

@transaction.atomic
def run():
    print("=" * 60)
    print("  SEED DATA - SÁCHGÓC UNI")
    print("=" * 60)

    # --- 1. Dọn dữ liệu cũ (giữ nguyên tài khoản) ---
    print("\n🧹 Đang xoá dữ liệu sản phẩm cũ...")
    Review.objects.all().delete()
    Favorite.objects.all().delete()
    Comment.objects.all().delete()
    Post.objects.all().delete()
    Category.objects.all().delete()
    print("   ✅ Đã xoá sạch.")

    # --- 2. Tạo tài khoản Admin ---
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@sachgocuni.edu.vn', 'is_staff': True, 'is_superuser': True}
    )
    if created or not admin.is_staff:
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password('admin123')
        admin.save()
    admin.profile.faculty = "Ban Quản Trị"
    admin.profile.save()

    # --- 3. Tạo tài khoản sinh viên mẫu ---
    students = [
        ("sinhvien_demo", "Nguyễn Văn Hào", "hao.nguyen24@gmail.com", "Khoa Kiến trúc", "24CT100001"),
        ("thanhhoa", "Trần Thanh Hoà", "thanhhoa@gmail.com", "Khoa CNTT & TT", "24CT100045"),
        ("minhthu", "Lê Minh Thư", "minhthu@gmail.com", "Khoa Kiến trúc", "24CT100078"),
        ("quynhanh", "Phạm Quỳnh Anh", "quynhanh@gmail.com", "Khoa CNTT & TT", "24CT100102"),
    ]

    users = []
    for username, full_name, email, faculty, student_id in students:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'first_name': full_name}
        )
        if created:
            user.set_password('123456')
            user.save()
        user.profile.faculty = faculty
        user.profile.student_id = student_id
        user.profile.bio = f"Sinh viên {faculty}. Thích chia sẻ đồ dùng học tập và giúp đỡ đàn em khóa sau. 📚"
        user.profile.save()
        users.append(user)

    print(f"   ✅ Đã tạo {len(users)} tài khoản sinh viên.")

    # --- 4. Tạo danh mục ---
    cat_map = {}
    for order, (name, icon, description) in enumerate(CATEGORIES):
        from django.utils.text import slugify
        category, _ = Category.objects.get_or_create(
            slug=slugify(name),
            defaults={'name': name, 'icon': icon, 'description': description, 'order': order}
        )
        cat_map[name] = category

    print(f"   ✅ Đã tạo {len(cat_map)} danh mục.")

    # --- 5. Tạo bài đăng ---
    created_posts = []
    for title, cat_name, price, is_free, condition, faculty, course_code, location, description in PRODUCTS:
        seller = random.choice(users)

        post = Post(
            title=title,
            description=description,
            seller=seller,
            category=cat_map.get(cat_name),
            price=price,
            is_free=is_free,
            condition=condition,
            faculty=faculty,
            course_code=course_code,
            location=location,
            status=Post.Status.ACTIVE,
        )

        # Gán ảnh minh hoạ nếu generate_images.py đã được chạy trước
        image_path = seed_image_for(title)
        if image_path:
            post.image.name = image_path

        # Đánh dấu bán cho một số sản phẩm demo
        if 'đã bán' in title.lower() or 'đã tặng' in title.lower():
            post.status = Post.Status.SOLD
            post.is_sold = True

        post.save()

        # Ngẫu nhiên lượt xem và điểm uy tín
        post.view_count = random.randint(5, 450)

        # Rải thời gian đăng trong 30 ngày gần nhất để trang chủ nhìn
        # tự nhiên hơn (thay vì tất cả đều "0 phút trước").
        # created_at là auto_now_add nên phải ghi đè bằng UPDATE.
        post.save(update_fields=['view_count'])
        days_ago = random.uniform(0.05, 30)
        published_at = timezone.now() - timedelta(days=days_ago)
        Post.objects.filter(pk=post.pk).update(
            created_at=published_at, updated_at=published_at
        )
        post.refresh_from_db(fields=['created_at'])

        created_posts.append(post)

    print(f"   ✅ Đã tạo {len(created_posts)} bài đăng.")

    # --- 6. Tạo bình luận ---
    comment_count = 0
    for post in created_posts:
        if post.is_sold:
            continue
        # Mỗi bài có 0-4 bình luận
        for _ in range(random.randint(0, 4)):
            commenter = random.choice([u for u in users if u != post.seller])
            Comment.objects.create(
                post=post,
                author=commenter,
                content=random.choice(COMMENTS)
            )
            comment_count += 1
            # Bình luận phải sau thời điểm đăng bài
            last_comment = Comment.objects.filter(
                post=post, author=commenter
            ).order_by('-created_at').first()
            if last_comment:
                Comment.objects.filter(pk=last_comment.pk).update(
                    created_at=post.created_at + timedelta(
                        minutes=random.randint(10, 4000)
                    )
                )

            # Một số bình luận có người bán trả lời
            if random.random() < 0.5:
                reply = Comment.objects.create(
                    post=post,
                    author=post.seller,
                    parent=last_comment,
                    content="Dạ mình gửi thêm cho bạn nhé! Bạn inbox mình để trao đổi chi tiết nhé."
                )
                Comment.objects.filter(pk=reply.pk).update(
                    created_at=reply.parent.created_at + timedelta(
                        hours=random.randint(1, 60)
                    )
                )
                comment_count += 1

    print(f"   ✅ Đã tạo {comment_count} bình luận.")

    # --- 7. Tạo yêu thích ---
    favorite_count = 0
    for post in created_posts:
        for _ in range(random.randint(0, 5)):
            user = random.choice(users)
            if user != post.seller:
                Favorite.objects.get_or_create(user=user, post=post)
                favorite_count += 1

    print(f"   ✅ Đã tạo {favorite_count} lượt yêu thích.")

    # --- 8. Tạo đánh giá uy tín ---
    review_count = 0
    for seller in users:
        for reviewer in users:
            if seller == reviewer or random.random() > 0.65:
                continue
            Review.objects.get_or_create(
                seller=seller,
                reviewer=reviewer,
                defaults={
                    'rating': random.choice([4, 5, 5, 5, 4, 3]),
                    'content': random.choice(REVIEW_COMMENTS),
                }
            )
            review_count += 1

    print(f"   ✅ Đã tạo {review_count} đánh giá.")

    # --- 10. Đơn hàng mẫu (đặt mua) ---
    print("\n Đơn hàng mẫu (chức năng Đặt mua)…")
    Order.objects.all().delete()
    order_count = 0

    # Kịch bản: 1 đơn cho mỗi trạng thái để minh hoạ đủ luồng
    scenarios = [
        (Order.Status.PENDING,   'Còn hàng không ạ? Mình có thể gặp tối mai.'),
        (Order.Status.CONFIRMED, 'Mình lấy sau khi thi giữa kỳ nhé.'),
        (Order.Status.COMPLETED, 'Cảm ơn bạn, giao dịch mượt lắm!'),
        (Order.Status.REJECTED,  'Xin lỗi, sản phẩm đã có người hẹn trước.'),
    ]

    # Duyệt qua các bài đăng, mỗi bài tìm người mua khác người bán
    post_cursor = 0
    for index, (status, note) in enumerate(scenarios):
        order = None

        # Tìm cặp (bài đăng, người mua) hợp lệ
        while post_cursor < len(created_posts) and order is None:
            post_obj = created_posts[post_cursor]
            post_cursor += 1
            for buyer in users:
                if buyer != post_obj.seller:
                    order = (post_obj, buyer)
                    break

        if order is None:
            break

        post_obj, buyer = order

        order = Order.objects.create(
            post=post_obj,
            buyer=buyer,
            seller=post_obj.seller,
            price_snapshot=post_obj.price,
            message='Xin chào, mình muốn mua sản phẩm này. '
                    'Có thể giao dịch vào cuối tuần này được không ạ?',
            contact=f'09{20000000 + index * 111111:08d}',
            status=status,
            seller_note=note if status in (
                Order.Status.CONFIRMED, Order.Status.REJECTED
            ) else '',
        )

        # Đơn hoàn tất thì sản phẩm chuyển sang đã bán
        if status == Order.Status.COMPLETED:
            post_obj.status = Post.Status.SOLD
            post_obj.is_sold = True
            post_obj.save(update_fields=['status', 'is_sold', 'updated_at'])

        order_count += 1

    print(f"   ✅ Đã tạo {order_count} đơn hàng.")

    # --- 10. Thống kê & thông tin đăng nhập ---
    print("\n" + "=" * 60)
    print("  ✅ HOÀN TẤT NẠP DỮ LIỆU!")
    print("=" * 60)
    print(f"""
  📊 THỐNG KÊ:
     • Danh mục     : {Category.objects.count()}
     • Bài đăng    : {Post.objects.count()} (đang hiển thị: {Post.objects.active().count()})
     • Tặng 0đ     : {Post.objects.active().free_items().count()}
     • Bình luận   : {Comment.objects.count()}
     • Yêu thích  : {Favorite.objects.count()}
     • Đánh giá    : {Review.objects.count()}
     • Đơn hàng    : {Order.objects.count()}
     • Người dùng  : {User.objects.count()}

  🔑 TÀI KHOẢN ĐĂNG NHẬP:

     Quản trị viên:
        username: admin
        password: admin123
        URL: http://127.0.0.1:8000/django-admin/

     Sinh viên demo:
        username: sinhvien_demo
        password: 123456
        (Các tài khoản: thanhhoa, minhthu, quynhanh — cùng mật khẩu 123456)

  🚀 KHỞI ĐỘNG:
        python manage.py runserver
        → http://127.0.0.1:8000/
""")


if __name__ == '__main__':
    run()
