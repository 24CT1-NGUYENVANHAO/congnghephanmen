import os
import django
from django.utils.text import slugify

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from app_main.models import Post, Category

def run():
    print("🧹 Đang xóa toàn bộ dữ liệu Bài đăng và Danh mục cũ...")
    Post.objects.all().delete()
    Category.objects.all().delete()
    print("✅ Đã xóa sạch dữ liệu cũ!")

    # 1. Tạo hoặc lấy user mẫu
    user, created = User.objects.get_or_create(username='sinhvien_demo')
    if created:
        user.set_password('123456')
        user.save()

    # 2. Danh sách các Danh mục mở rộng
    categories_data = [
        "Giáo trình",
        "Dụng cụ học tập",
        "Thiết bị điện tử",
        "Đồ dùng KTX",
        "Tài liệu - Đề thi",
        "Tặng miễn phí 0đ"
    ]

    cat_map = {}
    for cat_name in categories_data:
        cat_obj, _ = Category.objects.get_or_create(
            name=cat_name,
            defaults={'slug': slugify(cat_name)}
        )
        cat_map[cat_name] = cat_obj

    # 3. Danh sách sản phẩm (Đã loại bỏ hoàn toàn image_url)
    products = [
        ("Giáo trình Triết học Mác - Lênin", cat_map["Giáo trình"], 0, True, "USED", "Giáo trình còn khá mới, tặng lại cho tân sinh viên."),
        ("Giáo trình Lập trình Python cơ bản", cat_map["Giáo trình"], 45000, False, "LIKE_NEW", "Sách viết dễ hiểu, có bài tập minh họa."),
        ("Sách Giải tích 1 & Đại số tuyến tính", cat_map["Giáo trình"], 30000, False, "GOOD", "Bộ đôi sách toán đại cương năm nhất."),
        ("Giáo trình Cơ sở dữ liệu & SQL", cat_map["Giáo trình"], 50000, False, "LIKE_NEW", "Tài liệu môn CSDL, kèm bài tập MySQL."),
        ("Sách Lập trình Web với Django", cat_map["Giáo trình"], 65000, False, "NEW", "Sách chuyên sâu về phát triển web Django."),

        ("Máy tính bỏ túi Casio FX-580VN X", cat_map["Dụng cụ học tập"], 320000, False, "LIKE_NEW", "Máy bấm nhạy, pin trâu thích hợp thi trắc nghiệm."),
        ("Combo 5 cuốn vở kẻ ngang 200 trang", cat_map["Dụng cụ học tập"], 25000, False, "NEW", "Vở giấy dày dặn, không thấm mực."),
        ("Bộ thước vẽ kỹ thuật & Bàn vẽ A3", cat_map["Dụng cụ học tập"], 80000, False, "GOOD", "Dành cho sinh viên Khoa Kiến trúc / Xây dựng."),
        ("Bảng vẽ điện tử Gaomon 1060Pro", cat_map["Dụng cụ học tập"], 280000, False, "GOOD", "Đầy đủ bút vẽ và ngòi thay thế."),
        ("Bộ bút highlight 6 màu Pastel", cat_map["Dụng cụ học tập"], 15000, False, "NEW", "Bút dạ quang màu xinh xắn đánh dấu bài học."),

        ("Chuột không dây Logitech M185", cat_map["Thiết bị điện tử"], 90000, False, "LIKE_NEW", "Kết nối USB Receiver 2.4GHz nhạy."),
        ("Tai nghe có dây kiểm âm học online", cat_map["Thiết bị điện tử"], 50000, False, "NEW", "Chất âm rõ ràng, lọc ồn tốt."),
        ("Bàn phím cơ AKKO 3087 Silent", cat_map["Thiết bị điện tử"], 450000, False, "LIKE_NEW", "Gõ êm không gây tiếng ồn trong phòng trọ."),
        ("Đế tản nhiệt Laptop 2 quạt LED", cat_map["Thiết bị điện tử"], 70000, False, "GOOD", "Giúp làm mát máy khi làm đồ án nặng."),
        ("USB 32GB Kingston Chống nước", cat_map["Thiết bị điện tử"], 60000, False, "NEW", "Lưu trữ tài liệu học tập nhỏ gọn."),

        ("Đèn học chống cận thị gấp gọn", cat_map["Đồ dùng KTX"], 60000, False, "LIKE_NEW", "Đèn LED 3 chế độ sáng, cắm cổng USB."),
        ("Balo đi học đựng Laptop 15.6 inch", cat_map["Đồ dùng KTX"], 110000, False, "GOOD", "Balo chống nước nhẹ, nhiều ngăn chứa."),
        ("Kệ để sách gỗ để bàn 3 tầng", cat_map["Đồ dùng KTX"], 70000, False, "LIKE_NEW", "Kệ gỗ lắp ghép xinh xắn giúp gọn bàn."),
        ("Quạt tích điện để bàn cổng USB", cat_map["Đồ dùng KTX"], 85000, False, "LIKE_NEW", "Cứu tinh cho mùa hè ngắt điện KTX."),
        ("Gương soi toàn thân khung gỗ", cat_map["Đồ dùng KTX"], 120000, False, "GOOD", "Gương chân đứng gập gọn cho phòng trọ."),

        ("Bộ đề thi mẫu & Đáp án CSDL", cat_map["Tài liệu - Đề thi"], 20000, False, "NEW", "Tổng hợp 10 đề thi các năm kèm đáp án chi tiết."),
        ("Tài liệu Ôn thi Tiếng Anh A2/B1", cat_map["Tài liệu - Đề thi"], 25000, False, "LIKE_NEW", "File in đẹp, tổng hợp từ vựng và ngữ pháp trọng tâm."),
        ("Sổ tay công thức Toán Cao Cấp", cat_map["Tài liệu - Đề thi"], 15000, False, "LIKE_NEW", "Tóm tắt ngắn gọn các dạng toán hay gặp."),

        ("Áo khoác Thể thao Đại học Kiến trúc", cat_map["Tặng miễn phí 0đ"], 0, True, "USED", "Tặng lại cho bạn tân sinh viên mặc mùa đông."),
        ("Combo 10 bút bi xanh Thiên Long", cat_map["Tặng miễn phí 0đ"], 0, True, "NEW", "Tặng kèm cho bạn nào ghé lấy tại KTX."),
        ("Móc treo quần áo nhựa (10 cái)", cat_map["Tặng miễn phí 0đ"], 0, True, "USED", "Dọn phòng trọ dư ra nên tặng lại."),
        ("Bình nước thuỷ tinh 500ml", cat_map["Tặng miễn phí 0đ"], 0, True, "NEW", "Quà tặng sự kiện không dùng tới."),
        ("Sách Kỹ năng mềm & Làm việc nhóm", cat_map["Tặng miễn phí 0đ"], 0, True, "NEW", "Pass 0đ cho ai thực sự cần."),
    ]

    count = 0
    for title, cat_obj, price, is_free, cond, desc in products:
        Post.objects.create(
            title=title,
            category=cat_obj,
            price=price,
            is_free=is_free,
            condition=cond,
            description=desc,
            seller=user
        )
        count += 1

    print(f"🎉 Đã tạo lại thành công {len(categories_data)} danh mục và {count} sản phẩm mẫu hoàn toàn mới!")

if __name__ == '__main__':
    run()