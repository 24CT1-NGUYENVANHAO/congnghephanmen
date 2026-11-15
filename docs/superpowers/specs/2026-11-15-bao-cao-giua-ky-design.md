# Thiết kế: Báo cáo giữa kỳ môn Công nghệ Phần mềm — SáchGóc Uni

Ngày: 2026-11-15
Trạng thái: chờ duyệt

## 1. Mục tiêu

Tạo file `.docx` báo cáo giữa kỳ cho dự án **SáchGóc Uni**, bám sát:
- **Khung nội dung bắt buộc** của giảng viên: 02 chương (Ch.1 lý thuyết — Ch.2 thực nghiệm).
- **Định dạng trình bày** của file mẫu `C:\Users\ACER\Downloads\Báo_Cáo_CNPM.docx`.
- **Dữ liệu thật** của mã nguồn trong repo này (model, view, form, CSDL đang chạy).

Không sao chép nội dung đề tài khác (bán đồ ăn Nhật Bản); chỉ kế thừa bố cục, font, cách đánh số hình.

## 2. Sản phẩm bàn giao

| Đường dẫn | Nội dung |
|---|---|
| `docs/BaoCao_GiuaKy_CNPM_SachGocUni.docx` | Báo cáo hoàn chỉnh (bản chính) |
| `docs/report/assets/*.png` | Toàn bộ hình sinh tự động (sơ đồ, ảnh chụp) |
| `make_report_assets.py` (root) | Sinh hình: sequence diagram, PERT, ERD, ảnh Figma, ảnh app |
| `make_report.py` (root) | Dựng file .docx từ nội dung + assets |
| `docs/report/verify/` | PDF + ảnh từng trang để tự kiểm tra bố cục (không commit) |

Quy ước script đặt ở root giống các script sẵn có (`make_sequence_diagrams.py`, `generate_images.py`, `make_contact_sheet.py`).

## 3. Thông tin bìa

| Trường | Giá trị |
|---|---|
| Trường / Khoa | TRƯỜNG ĐẠI HỌC KIẾN TRÚC ĐÀ NẴNG — KHOA CÔNG NGHỆ THÔNG TIN |
| Học phần | HỌC PHẦN CÔNG NGHỆ PHẦN MỀM |
| Đề tài | Xây dựng website trao đổi sách và đồ dùng học tập cho sinh viên — SáchGóc Uni |
| GVHD | PGS. TS. PHẠM THỊ DUNG |
| Sinh viên | Nguyễn Văn Hảo *(giả định theo tên repo — cần xác nhận)* |
| MSSV | 2451220056 |
| Lớp | 24CT1 |
| Ngày | Đà Nẵng, ngày … tháng 11 năm 2026 |

## 4. Cấu trúc báo cáo

### Phần đầu (không đánh số chương)
1. Trang bìa (logo trường lấy từ `docs/logo-dau.png`)
2. LỜI NHẬN XÉT CỦA NGƯỜI HƯỚNG DẪN — trang kẻ chấm để viết tay, khung điểm
3. TÓM TẮT (khoảng 250 từ)
4. LỜI MỞ ĐẦU
5. LỜI CẢM ƠN
6. MỤC LỤC (field TOC, cập nhật tự động bằng Word COM)

### CHƯƠNG 1: TỔNG QUAN CƠ SỞ LÝ THUYẾT
- **1.1. Giới thiệu đề tài** — bối cảnh (sách/đồ dùng học tập tồn sau mỗi kỳ), lý do chọn, mục tiêu, phạm vi.
- **1.2. Framework Django**
  - 1.2.1. Tổng quan về Django
  - 1.2.2. Kiến trúc MTV (Model – Template – View) + hình minh hoạ luồng request
  - 1.2.3. Đặc điểm nổi bật (ORM, admin, auth, template, bảo mật CSRF/SQL injection, migrations)
  - 1.2.4. Vai trò của Django trong đề tài
- **1.3. Ngôn ngữ lập trình Python**
  - 1.3.1. Giới thiệu
  - 1.3.2. Đặc điểm nổi bật
  - 1.3.3. Lý do lựa chọn Python cho đề tài
- **1.4. Công cụ hỗ trợ (Tools)**
  - 1.4.1. Visual Studio Code — soạn thảo, debug, terminal tích hợp
  - 1.4.2. XAMPP + MySQL 8.0 — máy chủ CSDL (cổng 3307 trên máy phát triển)
  - 1.4.3. Git & GitHub — quản lý phiên bản, remote `congnghephanmen`
  - 1.4.4. Figma — thiết kế 4 luồng giao diện
  - 1.4.5. Draw.io — sơ đồ tuần tự và sơ đồ mạng PERT
  - 1.4.6. Chrome DevTools — kiểm tra giao diện responsive
  - 1.4.7. Bảng tổng hợp công cụ (mục đích – phiên bản – vai trò)
- **1.5. Thư viện sử dụng và cấu trúc dự án**
  - 1.5.1. Bảng thư viện: Django 4.2/5.2, django-environ, Pillow, mysqlclient, PyMySQL, django-crispy-forms, Tailwind CSS (bản lưu cục bộ)
  - 1.5.2. Cấu trúc thư mục dự án (`core/`, `app_main/`, `templates/`, `static/`, `media/`, `docs/`)

### CHƯƠNG 2: THỰC NGHIỆM
- **2.1. Sơ đồ tuần tự (Sequence Diagram)**
  - 2.1.1. Đăng ký — `register()` → `RegisterForm` → `User` + `Profile` (signal)
  - 2.1.2. Đăng nhập — `user_login()` → `AuthenticationForm` → session
  - 2.1.3. Đăng tin sản phẩm *(tự chọn 1)* — `create_post()` → `PostForm` → `Post.save()` sinh slug
  - 2.1.4. Đặt mua & xác nhận đơn *(tự chọn 2)* — `buy_post()` → `OrderForm` → `Order` (PENDING) → người bán `accept_order()`
  - Mỗi mục: đoạn dẫn luồng xử lý + hình + bảng thông điệp (nguồn → đích, nội dung)
- **2.2. Sơ đồ PERT và đường găng**
  - 2.2.1. Bảng danh sách công việc (A–J, thời lượng, công việc trước) — **giữ nguyên cấu trúc và thời lượng của Bài nhận thức 3**, thêm cột ánh xạ sang công việc dự án SáchGóc Uni
  - 2.2.2. Sơ đồ mạng PERT (đỉnh 0–8, cung A–J + 3 cung giả)
  - 2.2.3. Bảng tính thời gian sớm nhất / muộn nhất, dự trữ của từng đỉnh
  - 2.2.4. Kết luận: đường găng `0 → 1 → 4 → 7 → 8` (A → D → H → G), thời gian hoàn thành **35 ngày**
- **2.3. Demo (3/5 bước thiết kế + kết quả thực hiện)**
  - 2.3.1. Đăng ký
  - 2.3.2. Đăng nhập
  - 2.3.3. Đăng tin sản phẩm *(tự chọn 1)*
  - 2.3.4. Đặt mua & xác nhận đơn *(tự chọn 2)*
  - Mỗi mục trình bày 3 bước chi tiết: **(1)** Luồng người dùng / use case, **(2)** Bố cục phác thảo (wireframe Figma), **(3)** Giao diện hoàn thiện; sau đó **Kết quả thực hiện thực tế**: ảnh chụp app đang chạy + mô tả mã nguồn xử lý.
- **2.4. Cơ sở dữ liệu**
  - 2.4.1. Thiết kế: 9 bảng (`auth_user`, `Category`, `Profile`, `Post`, `PostImage`, `Favorite`, `Comment`, `Review`, `Report`, `Order`) + sơ đồ ERD
  - 2.4.2. Bảng mô tả trường chính của `Post`, `Order`, `Report` (kiểu dữ liệu, ràng buộc, mô tả)
  - 2.4.3. Dữ liệu thực nghiệm: bảng thống kê từ CSDL thật (11 người dùng, 35 bài đăng: 32 ACTIVE / 3 SOLD, 4 đơn hàng, 0 báo cáo) + ảnh dữ liệu mẫu trên giao diện

### Phần cuối
- **KẾT LUẬN** — kết quả đạt được, hạn chế, hướng phát triển (1 trang)
- **TÀI LIỆU THAM KHẢO**

## 5. Định dạng giống file mẫu

| Thuộc tính | Giá trị |
|---|---|
| Khổ giấy | A4 (21 × 29.7 cm) |
| Lề | trái 3.5 cm, phải 2.5 cm, trên 2.5 cm, dưới 2.5 cm |
| Font chính | Times New Roman 14 pt, giãn dòng 1.15, khoảng cách sau 6 pt |
| Tiêu đề chương | `CHƯƠNG N: …` in đậm 14 pt, canh giữa, sang trang mới |
| Mục cấp 1 (`1.1.`) | in đậm |
| Mục cấp 2 (`1.1.1.`) | in đậm nghiêng |
| Chú thích hình | `Hình N. …` in nghiêng, canh giữa, ngay dưới hình |
| Chú thích bảng | `Bảng N. …` in nghiêng, canh giữa, ngay trên bảng |
| Đánh số trang | góc dưới giữa, bắt đầu từ Chương 1 |
| Ảnh | rộng tối đa 15.5 cm, canh giữa |

## 6. Hình ảnh cần sinh (khoảng 20 hình)

| # | Hình | Cách sinh |
|---|---|---|
| 1 | Kiến trúc MTV của Django | SVG tự vẽ → PNG (Chrome headless) |
| 2 | Cấu trúc thư mục dự án | chụp từ `tree` bằng matplotlib/SVG |
| 3–6 | 4 sơ đồ tuần tự | SVG generator (Python thuần) → PNG |
| 7 | Sơ đồ mạng PERT | SVG generator, đúng cấu trúc file bài nhận thức 3 |
| 8–19 | 4 × (wireframe Figma + giao diện thật) + ảnh CSDL/admin | Chrome headless chụp `docs/figma-board-*.html` và app đang chạy |
| 20 | Sơ đồ ERD | SVG generator (bảng + quan hệ 1-n, n-n) |

Ảnh chụp app: chạy `runserver` trên CSDL SQLite cục bộ đã seed, chụp bằng Chrome `--headless --screenshot --window-size=1440,900`.

## 7. Kiểm chứng

1. Sinh `docs/BaoCao_GiuaKy_CNPM_SachGocUni.docx`.
2. Dùng Word COM (`pywin32`) xuất PDF, cập nhật field TOC.
3. Render PDF → PNG từng trang bằng PyMuPDF, xem lại: không tràn lề, không ảnh vỡ, mục lục đúng số trang, số hình liên tục.
4. Kiểm tra số trang mục lục khớp, font không bị fallback.

## 8. Ngoài phạm vi

- Không sửa mã nguồn app (trừ khi cần seed dữ liệu demo bằng script riêng).
- Không commit/push khi chưa có xác nhận của bạn.
- Không cài thêm LibreOffice/pandoc.

## 9. Cần bạn xác nhận

1. Họ tên trên bìa: **Nguyễn Văn Hào** (theo tên repo) — đúng chưa?
2. Tự chọn 1 = **Đăng tin sản phẩm**, Tự chọn 2 = **Đặt mua & xác nhận đơn** — đúng chưa?
3. PERT: giữ nguyên mạng A–J và con số 35 ngày của bài nhận thức 3, chỉ thêm cột ánh xạ công việc dự án — đồng ý không?
4. Có thêm mục **KẾT LUẬN** ngắn ở cuối (ngoài 2 chương bắt buộc) không?
