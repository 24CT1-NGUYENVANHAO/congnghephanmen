"""Nạp dữ liệu mẫu cố định để chụp ảnh giao diện cho báo cáo giữa kỳ.

Cách chạy (từ thư mục gốc dự án):

    set USE_SQLITE=True
    python manage.py migrate
    python docs/report/seed_demo.py

Script chỉ dùng ``get_or_create`` nên chạy lại nhiều lần vẫn không sinh dữ
liệu trùng. Sau khi chạy, danh sách khoá chính được ghi ra
``docs/report/seed_ids.json`` để script chụp ảnh biết phải mở trang nào.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.utils import timezone  # noqa: E402

from app_main.models import Category, Order, Post, Report  # noqa: E402

IDS_FILE = Path(__file__).resolve().parent / "seed_ids.json"
SEED_IMAGES = "posts/seed"

#: Mật khẩu dùng chung cho các tài khoản demo (khớp gợi ý ở trang đăng nhập).
STUDENT_PASSWORD = "123456"
ADMIN_PASSWORD = "admin123"

USERS = [
    {
        "key": "admin",
        "username": "admin",
        "email": "admin@sachgocuni.edu.vn",
        "password": ADMIN_PASSWORD,
        "first_name": "Ban Quản trị",
        "last_name": "",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "key": "hao",
        "username": "hao.nguyen24@gmail.com",
        "email": "hao.nguyen24@gmail.com",
        "password": STUDENT_PASSWORD,
        "first_name": "Nguyễn Văn Hảo",
        "last_name": "",
        "student_id": "2451220056",
        "faculty": "Khoa Công nghệ thông tin",
        "phone": "0905123456",
    },
    {
        "key": "lan",
        "username": "lan.tran24@gmail.com",
        "email": "lan.tran24@gmail.com",
        "password": STUDENT_PASSWORD,
        "first_name": "Trần Thị Lan",
        "last_name": "",
        "student_id": "2451000123",
        "faculty": "Khoa Công nghệ thông tin",
        "phone": "0912345678",
    },
    {
        "key": "minh",
        "username": "minh.pham24@gmail.com",
        "email": "minh.pham24@gmail.com",
        "password": STUDENT_PASSWORD,
        "first_name": "Phạm Hoàng Minh",
        "last_name": "",
        "student_id": "2451000456",
        "faculty": "Khoa Kinh tế",
        "phone": "0987654321",
    },
]

CATEGORIES = [
    ("giao-trinh", "Giáo trình & Sách", "📚", "Giáo trình, sách tham khảo, tài liệu ôn thi."),
    ("dung-cu", "Dụng cụ học tập", "✏️", "Balo, bút, thước, máy tính, đồ dùng học tập."),
    ("do-dien-tu", "Đồ điện tử", "💻", "Laptop, bàn phím, chuột, phụ kiện công nghệ."),
]

POSTS = [
    {
        "key": "csdl",
        "title": "Giáo trình Cơ sở dữ liệu SQL bản tiếng Việt",
        "description": (
            "Giáo trình Cơ sở dữ liệu do thầy cô trong khoa biên soạn, bản tiếng Việt, "
            "còn nguyên bìa và không viết vở. Sách gồm phần lý thuyết chuẩn hóa, đại số "
            "quan hệ và hơn 40 bài tập SQL mẫu. Phù hợp cho sinh viên năm 2 chuẩn bị "
            "thi giữa kỳ môn Cơ sở dữ liệu."
        ),
        "seller": "hao",
        "category": "giao-trinh",
        "course_code": "INT2203",
        "faculty": "Khoa Công nghệ thông tin",
        "price": 65000,
        "condition": Post.Condition.LIKE_NEW,
        "location": "Khu giảng đường A, Đại học Kiến trúc Đà Nẵng",
        "image": "Giáo-trình-Cơ-sở-dữ-liệu-SQL-bản-tiếng-Việt.jpg",
        "status": Post.Status.ACTIVE,
        "view_count": 48,
    },
    {
        "key": "python",
        "title": "Giáo trình Lập trình Python cơ bản (có bài tập)",
        "description": (
            "Sách Lập trình Python cơ bản kèm bài tập thực hành theo từng chương. "
            "Mình đã học xong môn nên để lại cho bạn nào cần, sách sạch, chỉ ghi tên "
            "ở trang đầu. Có thể giao tại thư viện vào các buổi chiều."
        ),
        "seller": "lan",
        "category": "giao-trinh",
        "course_code": "INT2204",
        "faculty": "Khoa Công nghệ thông tin",
        "price": 70000,
        "condition": Post.Condition.GOOD,
        "location": "Thư viện trường, tầng 2",
        "image": "Giáo-trình-Lập-trình-Python-cơ-bản-có-bài-tập.jpg",
        "status": Post.Status.ACTIVE,
        "view_count": 36,
    },
    {
        "key": "de-thi",
        "title": "Bộ đề thi CSDL 10 năm kèm đáp án chi tiết",
        "description": (
            "Tặng miễn phí bộ đề thi Cơ sở dữ liệu của 10 năm gần nhất, có đáp án và "
            "thang điểm chi tiết do sinh viên khoá trước tổng hợp. Bản in A4 đóng ghim, "
            "bạn nào cần ôn thi thì nhắn mình hẹn giờ lấy."
        ),
        "seller": "hao",
        "category": "giao-trinh",
        "course_code": "INT2203",
        "faculty": "Khoa Công nghệ thông tin",
        "price": 0,
        "condition": Post.Condition.GOOD,
        "location": "Căn tin khu B",
        "image": "Bộ-đề-thi-CSDL-10-năm-kèm-đáp-án-chi-tiết.jpg",
        "status": Post.Status.ACTIVE,
        "view_count": 112,
    },
    {
        "key": "ban-phim",
        "title": "Bàn phím cơ AKKO 3087 Silent switches Brown",
        "description": (
            "Bàn phím cơ AKKO 3087 layout 87 phím, switch Brown gõ êm, đã vệ sinh "
            "và thay keycap mới. Kết nối USB-C ổn định, đèn nền còn đủ màu. Mình "
            "nâng cấp lên bàn phím khác nên để lại, bảo hành 7 ngày tại trường."
        ),
        "seller": "lan",
        "category": "do-dien-tu",
        "course_code": "",
        "faculty": "Khoa Công nghệ thông tin",
        "price": 450000,
        "condition": Post.Condition.LIKE_NEW,
        "location": "KTX khu A",
        "image": "Bàn-phím-cơ-AKKO-3087-Silent-switches-Brown.jpg",
        "status": Post.Status.ACTIVE,
        "view_count": 79,
    },
    {
        "key": "balo",
        "title": "Balo đựng laptop 15.6 inch chống nước",
        "description": (
            "Balo chống nước, ngăn laptop có đệm lót dày phù hợp máy 15.6 inch. "
            "Nhiều ngăn phụ, quai đeo êm, đã dùng một học kỳ nên màu hơi cũ nhưng "
            "khóa kéo còn tốt. Bán để đổi sang balo nhỏ hơn."
        ),
        "seller": "minh",
        "category": "dung-cu",
        "course_code": "",
        "faculty": "Khoa Kinh tế",
        "price": 180000,
        "condition": Post.Condition.GOOD,
        "location": "Khu 3, đường Ngu Hành Sơn",
        "image": "Balo-đựng-laptop-156-inch-chống-nước.jpg",
        "status": Post.Status.ACTIVE,
        "view_count": 25,
    },
    {
        "key": "but-highlight",
        "title": "Bộ bút highlight 6 màu pastel dịu",
        "description": (
            "Tặng bộ 6 bút highlight màu pastel, mực còn gần đầy, đầu bút không tòe. "
            "Mình mua theo set nhưng chỉ dùng 2 cây, phần còn lại để lại cho bạn nào "
            "cần ghi chú bài. Nhận tại sân trường giờ nghỉ trưa."
        ),
        "seller": "minh",
        "category": "dung-cu",
        "course_code": "",
        "faculty": "Khoa Kinh tế",
        "price": 0,
        "condition": Post.Condition.LIKE_NEW,
        "location": "Sân trường, cạnh nhà xe",
        "image": "Bộ-bút-highlight-6-màu-pastel-dịu.jpg",
        "status": Post.Status.ACTIVE,
        "view_count": 64,
    },
    {
        "key": "pending",
        "title": "Sách Phân tích thiết kế hệ thống UML (bản dịch)",
        "description": (
            "Sách Phân tích và thiết kế hệ thống theo hướng đối tượng, bản dịch tiếng "
            "Việt, kèm nhiều ví dụ biểu đồ use case và biểu đồ lớp. Sách còn mới, "
            "mình muốn bán lại với giá sinh viên."
        ),
        "seller": "minh",
        "category": "giao-trinh",
        "course_code": "INT2205",
        "faculty": "Khoa Công nghệ thông tin",
        "price": 90000,
        "condition": Post.Condition.NEW,
        "location": "Khu 3, đường Ngu Hành Sơn",
        "image": "Sách-Phân-tích-thiết-kế-hệ-thống-UML.jpg",
        "status": Post.Status.PENDING,
        "view_count": 0,
    },
    {
        "key": "casio",
        "title": "Máy tính Casio FX-580VN X pin mới",
        "description": (
            "Máy tính Casio FX-580VN X đã thay pin mới, phím bấm nhạy, màn hình "
            "không xước. Phù hợp cho các môn Toán cao cấp và Xác suất thống kê."
        ),
        "seller": "hao",
        "category": "dung-cu",
        "course_code": "",
        "faculty": "Khoa Công nghệ thông tin",
        "price": 250000,
        "condition": Post.Condition.LIKE_NEW,
        "location": "Khu giảng đường A",
        "image": "Máy-tính-Casio-FX-580VN-X-pin-mới.jpg",
        "status": Post.Status.SOLD,
        "view_count": 91,
    },
]

#: Số phút trước đây mỗi bài được đăng, để danh sách trông tự nhiên
#: thay vì toàn bộ cùng một thời điểm.
POST_AGES = {
    "csdl": 185,
    "python": 305,
    "de-thi": 55,
    "ban-phim": 725,
    "balo": 26,
    "but-highlight": 9,
    "pending": 40,
    "casio": 3 * 24 * 60 + 120,
}

REPORT = {
    "post": "balo",
    "reporter": "lan",
    "reason": Report.Reason.INAPPROPRIATE,
    "detail": (
        "Ảnh sản phẩm có logo của một shop bán balo, mình nghi bài đăng lấy ảnh "
        "của người khác nên báo để admin kiểm tra lại."
    ),
}


def upsert_user(spec: dict) -> User:
    user, created = User.objects.get_or_create(
        username=spec["username"],
        defaults={
            "email": spec["email"],
            "first_name": spec["first_name"],
            "last_name": spec["last_name"],
            "is_staff": spec.get("is_staff", False),
            "is_superuser": spec.get("is_superuser", False),
            "is_active": True,
        },
    )
    changed = created
    for field in ("email", "first_name", "last_name", "is_staff", "is_superuser"):
        if field in spec and getattr(user, field) != spec[field]:
            setattr(user, field, spec[field])
            changed = True
    if changed:
        user.save()
    # Luôn đặt lại mật khẩu để lần chạy sau vẫn đăng nhập được.
    user.set_password(spec["password"])
    user.save(update_fields=["password"])

    profile = user.profile
    profile.student_id = spec.get("student_id", "")
    profile.faculty = spec.get("faculty", "")
    profile.phone = spec.get("phone", "")
    profile.bio = spec.get("bio", "Thành viên SáchGóc Uni.")
    profile.save()
    return user


def main() -> None:
    users: dict[str, User] = {spec["key"]: upsert_user(spec) for spec in USERS}

    categories: dict[str, Category] = {}
    for order, (slug, name, icon, description) in enumerate(CATEGORIES, start=1):
        category, _ = Category.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "icon": icon, "description": description, "order": order},
        )
        categories[slug] = category

    posts: dict[str, Post] = {}
    for spec in POSTS:
        post, _ = Post.objects.get_or_create(
            title=spec["title"],
            defaults={
                "description": spec["description"],
                "seller": users[spec["seller"]],
                "category": categories[spec["category"]],
                "course_code": spec["course_code"],
                "faculty": spec["faculty"],
                "price": spec["price"],
                "condition": spec["condition"],
                "location": spec["location"],
                "image": f"{SEED_IMAGES}/{spec['image']}",
                "status": spec["status"],
                "view_count": spec["view_count"],
            },
        )
        posts[spec["key"]] = post

    # Giãn thời điểm đăng để cột "x phút trước" trên trang chủ có ý nghĩa.
    now = timezone.now()
    for key, post in posts.items():
        Post.objects.filter(pk=post.pk).update(
            created_at=now - timedelta(minutes=POST_AGES[key])
        )
        post.refresh_from_db(fields=["created_at"])

    pending_order, _ = Order.objects.get_or_create(
        post=posts["ban-phim"],
        buyer=users["hao"],
        seller=users["lan"],
        defaults={
            "price_snapshot": posts["ban-phim"].price,
            "message": "Mình muốn lấy bàn phím chiều thứ 4, khoảng 15h được không ạ?",
            "contact": "0905123456",
            "status": Order.Status.PENDING,
        },
    )
    completed_order, _ = Order.objects.get_or_create(
        post=posts["casio"],
        buyer=users["minh"],
        seller=users["hao"],
        defaults={
            "price_snapshot": posts["casio"].price,
            "message": "Mình chuyển khoản trước, hẹn gặp ở cổng trường nhé.",
            "contact": "0987654321",
            "status": Order.Status.COMPLETED,
            "seller_note": "Đã giao máy và nhận đủ tiền.",
        },
    )

    report, _ = Report.objects.get_or_create(
        post=posts[REPORT["post"]],
        reporter=users[REPORT["reporter"]],
        defaults={
            "reason": REPORT["reason"],
            "detail": REPORT["detail"],
            "status": Report.Status.PENDING,
        },
    )

    ids = {
        "base_url": "http://127.0.0.1:8011",
        "credentials": {
            "student": {"username": users["hao"].email, "password": STUDENT_PASSWORD},
            "admin": {"username": users["admin"].email, "password": ADMIN_PASSWORD},
        },
        "users": {key: user.pk for key, user in users.items()},
        "categories": {key: category.pk for key, category in categories.items()},
        "posts": {key: post.pk for key, post in posts.items()},
        "orders": {"pending": pending_order.pk, "completed": completed_order.pk},
        "reports": {"pending": report.pk},
        "screens": {
            "detail_pk": posts["python"].pk,
            "buy_pk": posts["python"].pk,
            "order_pk": pending_order.pk,
        },
    }
    IDS_FILE.write_text(json.dumps(ids, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    active = Post.objects.filter(status=Post.Status.ACTIVE).count()
    print("Đã nạp dữ liệu demo:")
    print(f"  người dùng : {User.objects.count()} (staff: {User.objects.filter(is_staff=True).count()})")
    print(f"  bài đăng   : {Post.objects.count()} (đang hiển thị: {active})")
    print(f"  đơn hàng   : {Order.objects.count()} (chờ: {Order.objects.filter(status=Order.Status.PENDING).count()})")
    print(f"  báo cáo    : {Report.objects.count()}")
    print(f"  khoá chính : {IDS_FILE}")


if __name__ == "__main__":
    main()
