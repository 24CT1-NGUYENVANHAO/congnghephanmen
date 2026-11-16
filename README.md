# 📚 SáchGóc Uni — Sàn Giao Dịch & Chia Sẻ Đồ Dùng Sinh Viên

[![Django](https://img.shields.io/badge/Django-4.2%20%7C%205.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Tailwind](https://img.shields.io/badge/CSS%20Design%20System-Custom-38B2AC?style=for-the-badge)](https://tailwindcss.com/)

> **Đồ án Công nghệ Phần mềm** — Nền tảng thương mại điện tử dành cho sinh viên
> Trường Đại học Kiến trúc Đà Nẵng và cộng đồng sinh viên nói chung.

Chuyên dụng cho **mua bán sách cũ, giáo trình, dụng cụ học tập** và **tặng đồ dùng 0đ**.

---

## 📑 Mục lục

1. [Tính năng](#-tính-năng)
2. [Công nghệ sử dụng](#-công-nghệ-sử-dụng)
3. [Cài đặt & chạy dự án](#-cài-đặt--chạy-dự-án)
4. [Tài khoản mẫu](#-tài-khoản-mẫu)
5. [Kết nối CSDL](#-kết-nối-csdl)
6. [Cấu trúc dự án](#-cấu-trúc-dự-án)
7. [Kiểm thử](#-kiểm-thử)
8. [Sơ đồ kiến trúc](#-sơ-đồ-kiến-trúc)
9. [Luồng xử lý chính](#-luồng-xử-lý-chính)
10. [Ghi chú kỹ thuật](#-ghi-chú-kỹ-thuật)

---

## ✨ Tính năng

### 🛒 Nghiệp vụ chính

| Tính năng | Mô tả |
|---|---|
| 📖 **Mua bán sản phẩm** | Đăng bán giáo trình, dụng cụ vẽ, thiết bị với giá tuỳ chọn |
| 🛒 **Đặt mua trong hệ thống** | Gửi yêu cầu → người bán xác nhận/từ chối → hoàn tất. Giá chốt không đổi sau khi đặt |
| 📋 **Quản lý đơn hàng** | 5 trạng thái: Chờ xác nhận, Đã xác nhận, Hoàn tất, Từ chối, Đã huỷ |
| 🎁 **Tặng miễn phí 0đ** | Chuyên mục tặng lại đồ cho tân sinh viên |
| 🔍 **Tìm kiếm thông minh** | Tìm theo tiêu đề, mô tả, mã học phần, khoa |
| 🧩 **Bộ lọc nâng cao** | Lọc theo danh mục, tình trạng, khoa, khoảng giá |
| ↕️ **5 kiểu sắp xếp** | Mới nhất, cũ nhất, giá tăng/giảm, phổ biến nhất |
| 📄 **Phân trang** | Tự động chia trang, giữ nguyên bộ lọc khi chuyển trang |

### 👥 Tương tác & niềm tin

| Tính năng | Mô tả |
|---|---|
| 💬 **Bình luận & trả lời** | Hỏi đáp trực tiếp, hỗ trợ trả lời lồng 1 cấp |
| ♡ **Wishlist** | Lưu sản phẩm yêu thích (AJAX, không tải lại trang) |
| ⭐ **Đánh giá uy tín** | Chấm điểm 1-5 sao cho người bán, mỗi người 1 lần |
| 📊 **Trang hồ sơ** | Lịch sử bán, số tin đang bán, điểm uy tín, đánh giá nhận về |
| 🚩 **Báo cáo vi phạm** | Người dùng tố bài đăng, Admin xử lý |

### 🛡️ Bảo mật & kiểm duyệt

| Tính năng | Mô tả |
|---|---|
| 🔐 **Xác thực** | Đăng nhập chỉ bằng **email đã đăng ký** (`gmail.com` hoặc email trường `@edu.vn`); tên đăng nhập do hệ thống sinh, người dùng không cần nhớ |
| 🛡️ **Chống CSRF** | Mọi hành động đổi trạng thái đều POST + CSRF token |
| 🔑 **Mật khẩu mạnh** | Tối thiểu 8 ký tự, có hoa + số, không chứa thông tin cá nhân |
| 🚫 **Phân quyền** | Chỉ chủ bài đăng được sửa/xoá; chỉ tác giả/chủ bài xoá bình luận |
| 📋 **Vòng đời bài đăng** | Đang hiển thị → Đã bán / Đã ẩn / Bị từ chối; admin ẩn hoặc từ chối kèm lý do |
| 🛡️ **Trang quản trị** | Duyệt/ẩn/từ chối bài đăng, khoá tài khoản, xử lý báo cáo |
| 🧹 **Kiểm duyệt tự động** | Trang chủ chỉ hiện bài *Đang hiển thị*; bài bị ẩn hoặc từ chối biến mất ngay |

### 🎨 Trải nghiệm người dùng

- Giao diện responsive (mobile → desktop), hiệu ứng hover mượt mà
- Thông báo toast + hộp thoại thông báo tự động biến mất
- Trạng thái rỗng (empty state) thân thiện cho mọi danh sách
- Trang lỗi 404 / 500 riêng đồng bộ giao diện
- Thư viện ảnh sản phẩm nhiều ảnh (tối đa 5 ảnh/bài)
- Đếm lượt xem bài đăng

---

## 🛠 Công nghệ sử dụng

| Lớp | Công nghệ | Vai trò |
|---|---|---|
| **Frontend** | Django Template + Tailwind CSS (bản **lưu cục bộ**) | Giao diện responsive |
| **Backend** | Django 4.2 / 5.2 (MTV) | Xử lý logic nghiệp vụ |
| **CSDL** | MySQL 8.0 / MariaDB | Lưu trữ dữ liệu qua ORM |
| **Cấu hình** | django-environ + `.env` | Quản lý bí mật, không hardcode |
| **Media** | Pillow | Xử lý & kiểm tra ảnh tải lên |

> **Về Tailwind CSS:** thư viện được tải về lưu tại `static/js/tailwind.min.js` (441KB)
> và được nạp bằng thẻ `<script>` **cục bộ**, không dùng CDN.
> Nhờ vậy dự án **vẫn hiển thị đầy đủ giao diện khi không có mạng** — điều mà
> `<script src="https://cdn.tailwindcss.com">` của bản cũ không làm được.
> Bảng màu thương hiệu được khai báo trong `templates/base.html`.
>
> Nếu muốn dùng Tailwind đúng chuẩn production, thay file trên bằng bản build
> từ Tailwind CLI (không cần mạng khi chạy web server).

`static/css/main.css` đặt **sau** Tailwind để ghi đè các component dùng chung
(`.btn`, `.card`, `.badge`, `.form-input`...) và chứa design token của dự án.

---

## 🚀 Cài đặt & chạy dự án

### Bước 1 — Cài thư viện

```bash
pip install -r requirements.txt
```

### Bước 2 — (Tuỳ chọn) Tạo file cấu hình

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

> 💡 Dự án **chỉ dùng MySQL**. Nếu không tạo `.env`, app dùng giá trị mặc định
> trong `core/settings.py` (cổng 3306); máy chạy XAMPP của dự án cần
> `DB_PORT=3307`. Xem [Kết nối CSDL](#-kết-nối-csdl).

<details>
<summary>⚙️ Chỉnh cấu hình MySQL cho đúng máy của bạn</summary>

Mở `.env` và sửa cho khớp. Cổng MySQL thay đổi tuỳ máy — xem cột **"Port(s)"**
trong XAMPP Control Panel:

```env
DB_NAME=sachgocuni_db
DB_USER=root
DB_PASSWORD=          # XAMPP để trống; MySQL riêng thì điền mật khẩu
DB_HOST=127.0.0.1
DB_PORT=3307          # Cổng MySQL XAMPP đang dùng trong dự án
```

</details>

### Bước 3 — Tạo database

Tạo database trước:

```sql
CREATE DATABASE sachgocuni_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Bước 4 — Áp dụng migration

```bash
python manage.py migrate
```

### Bước 4b — Nạp dữ liệu múi giờ vào MySQL

Bảng `mysql.time_zone_*` trên XAMPP/MySQL mới cài thường **để trống**, khiến
trang quản trị báo lỗi `Database returned an invalid datetime value`. Chạy
script này **một lần duy nhất** (tự dò đúng cấu trúc bảng MySQL 5.6 / 8.x):

```bash
python load_tzinfo.py
```

Script nạp ~598 múi giờ từ thư viện `zoneinfo` của Python, không cần
`mysql_tzinfo_to_sql`.

### Bước 5 — Chuẩn bị ảnh cho sản phẩm mẫu

```bash
python generate_images.py
```

Vẽ 34 ảnh đại diện bằng Pillow: nền gradient theo màu danh mục, biểu tượng,
tên sản phẩm (tự co giãn, hỗ trợ đầy đủ dấu tiếng Việt), nhãn danh mục và
tình trạng. Không cần mạng.

<details>
<summary>🖼️ Tuỳ chọn: dùng ảnh chụp thật thay vì ảnh vẽ</summary>

```bash
python download_images.py            # tải ảnh CC từ Openverse (Flickr, Wikimedia)
python download_images.py --force    # tải lại tất cả
python download_images.py --only "Bàn"   # chỉ một sản phẩm
```

> ⚠️ **Cảnh báo thực tế:** Openverse tìm ảnh theo *metadata*, không theo nội
> dung ảnh. Đã gặp trường hợp tiêu đề ghi *"Casio Scientific Calculator"* nhưng
> ảnh thật là **mổ ruột linh kiện** — người đăng đặt tên bài viết theo sản
> phẩm chứ không phải theo ảnh. Script có chấm điểm và danh sách loại ảnh sai,
> nhưng **vẫn phải kiểm tra bằng mắt**.
>
> Dùng `python make_contact_sheet.py` để gộp toàn bộ ảnh thành 1 tấm duy
> nhất rồi soi. Thực tế đã thử và chỉ tìm được ảnh đúng chủ đề cho **18/34**
> sản phẩm; phần còn lại không có ảnh phù hợp trên nguồn miễn phí (đồ sinh
> viên Việt Nam như Casio FX-580, sách tiếng Việt, balo trường... không có
> trên Flickr). Trộn ảnh thật với ảnh vẽ làm giao diện lệch tông, nên dự án
> **mặc định dùng ảnh vẽ** cho đồng nhất.

</details>

### Bước 6 — Nạp dữ liệu mẫu

```bash
python seed_data.py
```

Tạo 6 danh mục, 34 sản phẩm (có gán ảnh), khoảng 100 bình luận (0–4 mỗi bài,
một nửa có người bán trả lời), yêu thích, đánh giá và 4 đơn hàng mẫu đủ bốn
trạng thái. Thời gian đăng được rải rác trong 30 ngày gần nhất cho tự nhiên.

### Bước 7 — Khởi chạy

```bash
python manage.py runserver
```

Truy cập: **http://127.0.0.1:8000/**

<details>
<summary>🛡️ Trang quản trị — chi tiết</summary>

**Địa chỉ:** http://127.0.0.1:8000/django-admin/
**Tài khoản:** `admin` / `admin123`

> Django admin đăng nhập bằng **username**. Muốn vào bằng giao diện của ứng dụng
> (`/dang-nhap/`) thì dùng email `admin@sachgocuni.edu.vn` / `admin123`.

Chức năng có sẵn:

| Trang | Chức năng |
|---|---|
| **Tổng quan** | Thống kê nhanh số bài đăng, người dùng, bình luận |
| **Bài đăng** | Duyệt / ẩn / từ chối, đánh dấu đã bán, làm nổi bật (đưa lên đầu) |
| **Báo cáo vi phạm** | Xử lý hoặc bỏ qua báo cáo của người dùng |
| **Bình luận** | Xem và xoá bình luận vi phạm |
| **Danh mục** | Thêm/sửa danh mục, đặt thứ tự hiển thị |
| **Hồ sơ sinh viên** | Mã SV, khoa ngành, điểm uy tín |
| **Yêu thích** | Thống kê sản phẩm được yêu thích |
| **Đánh giá** | Xem điểm uy tín và nhận xét |
| **Người dùng** | Khoá / mở khoá tài khoản, phân quyền staff |

Tất cả thao tác kiểm duyệt đều hỗ trợ **chọn nhiều dòng rồi áp dụng hàng loạt**.

</details>

---

## 🔑 Tài khoản mẫu

Trang `/dang-nhap/` **chỉ nhận email**, không nhận tên đăng nhập. Email phải là
`@gmail.com` hoặc email trường đuôi `.edu.vn`; nhập thiếu `@`, sai miền, hay email
chưa đăng ký đều bị chặn ngay với thông báo riêng cho từng trường hợp.

| Vai trò | Email đăng nhập | Mật khẩu | Đường dẫn |
|---|---|---|---|
| 👑 Quản trị | `admin@sachgocuni.edu.vn` | `admin123` | `/dang-nhap/` · `/django-admin/` (dùng `admin`) |
| 🎓 Sinh viên | `hao.nguyen24@gmail.com` | `123456` | `/dang-nhap/` |
| 🎓 Sinh viên | `thanhhoa@gmail.com` | `123456` | `/dang-nhap/` |
| 🎓 Sinh viên | `minhthu@gmail.com` | `123456` | `/dang-nhap/` |
| 🎓 Sinh viên | `quynhanh@gmail.com` | `123456` | `/dang-nhap/` |

> Trang đăng nhập có sẵn hai nút **"Điền nhanh"** (sinh viên và quản trị) để test
> tiện hơn.

---

## 🔌 Kết nối CSDL

### Cơ chế

Dự án **chỉ dùng MySQL/MariaDB**. Django đọc thông tin kết nối từ `.env` và
nối thẳng vào MySQL — không có cơ chế chuyển sang CSDL khác. Nếu MySQL chưa
chạy, sai cổng hoặc database chưa tồn tại, ngay truy vấn đầu tiên (khi mở
trang web) Django báo lỗi kết nối. Chạy `python check_db.py` để biết app đang
trỏ vào đâu rồi sửa `.env`.

### Tham số cấu hình (file `.env`)

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `DB_NAME` | Tên database | `sachgocuni_db` |
| `DB_USER` | Tài khoản MySQL | `root` |
| `DB_PASSWORD` | Mật khẩu (XAMPP để trống) | *(rỗng)* |
| `DB_HOST` | Địa chỉ server | `127.0.0.1` |
| `DB_PORT` | Cổng MySQL; XAMPP của dự án dùng | `3307` |
| `DEBUG` | Bật chế độ gỡ lỗi | `True` |
| `ALLOWED_HOSTS` | Host được phép truy cập, cách nhau dấu phẩy | `127.0.0.1,localhost` |
| `SECRET_KEY` | Khoá ký session/CSRF — đổi khi triển khai thật | khoá mẫu trong `.env.example` |
| `MAX_UPLOAD_SIZE` | Giới hạn dung lượng mỗi ảnh (byte) | `5242880` (5 MB) |
| `POSTS_PER_PAGE` | Số bài đăng mỗi trang | `12` |

### Cổng MySQL thường gặp

Trong cấu hình dùng với XAMPP của dự án, MySQL chạy ở cổng **3307**:

| Tình huống | Cổng |
|---|---|
| XAMPP của dự án | `3307` |
| XAMPP mặc định trên một số máy | `3306` |
| MySQL cài riêng | `3306` |
| Giá trị đang ghi trong `.env.example` | `3307` |

**Cách xem cổng đang dùng:** mở XAMPP Control Panel → dòng **MySQL** cột *Port(s)*.
Nếu máy của bạn dùng XAMPP ở cổng khác, sửa `DB_PORT` trong `.env` cho đúng;
riêng cấu hình chuẩn của dự án là `DB_PORT=3307`.
Nếu phpMyAdmin vẫn vào bình thường mà app báo không kết nối được thì gần như chắc
chắn là sai cổng — chạy `python check_db.py` để biết app đang trỏ vào đâu.

### Xem đang dùng CSDL nào

```bash
python manage.py shell -c "from django.db import connection; print(connection.settings_dict['ENGINE'])"
```

Kết quả mong đợi: `django.db.backends.mysql`. Nếu thấy lỗi kết nối, xem lại
`DB_HOST`/`DB_PORT`/`DB_PASSWORD` trong `.env`.

---

## 📁 Cấu trúc dự án

```text
24CT1-NGUYEN_VAN HAO/
│
├── core/                          # Cấu hình dự án cấp cao nhất
│   ├── settings.py                # Đọc cấu hình từ .env, cấu hình MySQL
│   ├── urls.py                    # Định tuyến gốc + xử lý 404/500
│   ├── wsgi.py / asgi.py          # Cổng giao tiếp web server
│
├── app_main/                      # Ứng dụng chính
│   ├── models.py                  # 9 model: Category, Profile, Post, PostImage,
│   │                              #   Favorite, Comment, Review, Report, Order
│   ├── views.py                   # 36 view xử lý toàn bộ nghiệp vụ
│   ├── forms.py                   # Form + validation tập trung
│   ├── urls.py                    # 34 route
│   ├── admin.py                   # Trang quản trị kiểm duyệt
│   ├── signals.py                 # Tự tạo Profile khi đăng ký
│   ├── context_processors.py      # Biến dùng chung cho template
│   ├── templatetags/app_extras.py # Filter & tag tùy chỉnh
│   ├── tests.py                   # 140 test tự động
│   └── migrations/                # Lịch sử cấu trúc CSDL
│
├── templates/                     # Template dùng chung
│   ├── base.html                  # Khung trang (nav, messages, footer)
│   ├── 404.html / 500.html        # Trang lỗi
│   ├── app_main/                  # 14 trang nghiệp vụ
│   ├── registration/              # Đăng nhập / Đăng ký
│   └── partials/                  # navbar, footer, messages, card, phân trang
│
├── static/
│   ├── css/main.css               # Design token + component dùng chung
│   ├── js/tailwind.min.js         # Tailwind CSS lưu cục bộ (offline)
│   └── js/main.js                 # Menu, yêu thích AJAX, validate mật khẩu
│
├── media/                         # Ảnh tải lên trong quá trình chạy (không commit)
│   └── posts/seed/                # Ảnh sản phẩm mẫu do generate_images.py tạo
│
├── check_db.py                    # Script kiểm tra kết nối MySQL và đếm bản ghi
├── seed_data.py                   # Script nạp dữ liệu mẫu
├── generate_images.py             # Vẽ ảnh minh hoạ bằng Pillow (không cần mạng)
├── download_images.py             # Tải ảnh thật từ Openverse (CC)
├── make_contact_sheet.py          # Gộp ảnh để kiểm tra bằng mắt
├── load_tzinfo.py                 # Nạp dữ liệu múi giờ vào MySQL (chạy 1 lần)
├── requirements.txt
├── .env.example                   # Mẫu cấu hình (copy thành .env)
└── manage.py
```

---

## 🧪 Kiểm thử

```bash
python manage.py test                    # Chạy toàn bộ
python manage.py test app_main.tests.InteractionTests   # Chỉ 1 nhóm
python manage.py test --verbosity 2      # Chi tiết từng test
```

**140 test tự động** bao phủ:

| Nhóm | Số test | Nội dung |
|---|---|---|
| Model | 23 | Sinh slug, đồng bộ trạng thái, ràng buộc unique, đơn hàng |
| Form | 15 | Mật khẩu yếu, Gmail trùng, trùng username, liên hệ hợp lệ |
| Public view | 14 | Tìm kiếm, lọc, sắp xếp, phân trang |
| Auth | 12 | Đăng ký, đăng nhập **chỉ bằng email** (chặn username), đăng xuất |
| Phân quyền | 16 | Chặn truy cập trái phép, sở hữu bài đăng |
| Tương tác | 16 | Yêu thích, bình luận, đánh giá, báo cáo |
| **Đặt mua** | **18** | Đặt mua, xác nhận, từ chối, hoàn tất, huỷ, phân quyền |
| Hồ sơ | 3 | Sửa hồ sơ, đổi mật khẩu |
| Kịch bản đầu-cuối | 1 | Hành trình đầy đủ: đăng ký → đăng tin → mua → hoàn tất |
| **Quản trị** | **20** | Dashboard, duyệt/từ chối bài, xử lý báo cáo, khoá tài khoản |
| Cấu hình CSDL | 2 | Engine luôn MySQL, không còn cờ chuyển CSDL |
| **Tổng** | **140** | ✅ |

Bao gồm các test bảo mật quan trọng:

- ❌ Đổi trạng thái bằng `GET` phải bị từ chối (405) — chống CSRF
- ❌ Sửa/xoá bài đăng của người khác phải bị chặn
- ❌ Mật khẩu rỗng không gây crash (lỗi `IndexError` ở bản cũ)
- ❌ Đăng nhập bằng **tên đăng nhập** phải bị từ chối, chỉ nhận email
- ❌ Email ngoài `gmail.com` / `.edu.vn` bị chặn trước khi truy vấn CSDL
- ✅ Hành trình đầy đủ: đăng ký → đăng tin → tìm kiếm → yêu thích → bình luận → đánh giá

---

## 📊 Sơ đồ kiến trúc

### Phân tầng kiến trúc

Hệ thống chia làm **3 phần riêng biệt**, mỗi phần một màu khác nhau:

| Phần | Trách nhiệm | Công nghệ |
|---|---|---|
| 🟦 **Frontend** | Hiển thị giao diện cho người dùng | Django Template, CSS, JavaScript |
| 🟩 **Backend** | Xử lý nghiệp vụ, bảo mật | Django (Python) |
| 🟥 **Database** | Lưu trữ dữ liệu | MySQL / MariaDB |

```mermaid
flowchart TD
    User(["👤 Người dùng<br/>(sinh viên)"])

    subgraph FRONTEND ["🟦 PHẦN 1 · FRONTEND — Tầng giao diện"]
        direction TB
        T1["📄 Django Templates<br/><b>base.html + 14 trang + 5 partials</b>"]
        T2["🎨 main.css<br/><b>Design system: .btn .card .badge</b>"]
        T3["⚡ main.js<br/><b>Menu, yêu thích AJAX, validate</b>"]
        T4["🖼️ tailwind.min.js<br/><b>Tailwind lưu cục bộ (offline)</b>"]
    end

    subgraph BACKEND ["🟩 PHẦN 2 · BACKEND — Tầng ứng dụng Django"]
        direction TB
        B1["🛡️ Middleware<br/><b>Session · CSRF · Auth · Security</b>"]
        B2["🔗 urls.py<br/><b>core + app_main · 34 route</b>"]

        subgraph NGHIEPVU ["Module nghiệp vụ"]
            direction LR
            B3["🎯 views.py<br/><b>36 view</b>"]
            B4["📝 forms.py<br/><b>Validation tập trung</b>"]
            B5["🛡️ admin.py<br/><b>Kiểm duyệt hàng loạt</b>"]
        end

        B6["🗃️ models.py<br/><b>9 model ORM</b>"]
        B7["🏷️ templatetags + context_processors<br/><b>Filter & biến dùng chung</b>"]
        B8["⚡ signals.py<br/><b>Tự tạo Profile</b>"]
    end

    subgraph DATABASE ["🟥 PHẦN 3 · DATABASE — Lưu trữ"]
        direction TB
        D1[("🄽 MySQL 8.0 / MariaDB<br/><b>sachgocuni_db · 9 bảng</b>")]
        D2[("📁 media/posts/<br/><b>Ảnh sản phẩm</b>")]
        D3["⚙️ .env<br/><b>Cấu hình kết nối CSDL</b>"]
    end

    User -->|"① Gửi yêu cầu HTTP<br/>(GET / POST)"| FRONTEND
    FRONTEND -->|"② Render HTML + CSS + JS"| User

    FRONTEND ==>|"③ Request tới server"| BACKEND
    BACKEND ==>|"④ HTML đã render"| FRONTEND

    BACKEND ==>|"⑤ Truy vấn qua ORM"| D1
    BACKEND -->|"⑥ Đọc/ghi file ảnh"| D2
    D3 -.->|"đọc cấu hình"| D1

    D1 ==>|"⑦ Trả về QuerySet"| BACKEND

    classDef fe fill:#e0e7ff,stroke:#4338ca,stroke-width:2px,color:#1e1b4b
    classDef be fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef db fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d
    classDef user fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f

    class T1,T2,T3,T4 fe
    class B1,B2,B3,B4,B5,B6,B7,B8 be
    class D1,D2,D3 db
    class User user
```

**Luồng xử lý một yêu cầu (ví dụ người dùng bấm "Đăng tin"):**

```
①  Người dùng điền form  → ②  Trình duyệt gửi POST /dang-tin/
                          → ③  Middleware kiểm tra CSRF + phiên đăng nhập
                          → ④  urls.py định tuyến tới views.create_post
                          → ⑤  PostForm kiểm tra dữ liệu đầu vào
                          → ⑥  ORM ghi bảng app_main_post vào MySQL
                          → ⑦  Redirect tới trang chi tiết sản phẩm
```

### Sơ đồ quan hệ CSDL (ERD)

```mermaid
erDiagram
    User ||--|| Profile : "có hồ sơ"
    User ||--o{ Post : "đăng tin"
    User ||--o{ Comment : "viết bình luận"
    User ||--o{ Review : "được đánh giá"
    User ||--o{ Report : "gửi báo cáo"
    User ||--o{ Favorite : "yêu thích"
    Category ||--o{ Post : "phân loại"
    Post ||--o{ PostImage : "có nhiều ảnh"
    Post ||--o{ Comment : "nhận bình luận"
    Post ||--o{ Favorite : "được yêu thích"
    Post ||--o{ Report : "bị báo cáo"
    Post ||--o{ Review : "được đánh giá"
    Post ||--o{ Order : "có đơn hàng"
    User ||--o{ Order : "đặt mua / nhận đơn"
    Comment ||--o{ Comment : "trả lời"

    User {
        int id PK
        string username UK
        string email UK
        string first_name
        string last_name
        bool is_staff
        bool is_active
    }

    Profile {
        int id PK
        int user_id FK UK
        string student_id
        string faculty
        string phone
        text bio
        image avatar
    }

    Category {
        int id PK
        string name
        string slug UK
        string icon
        int order
    }

    Post {
        int id PK
        string title
        string slug UK
        text description
        int seller_id FK
        int category_id FK
        string course_code
        string faculty
        decimal price
        bool is_free
        string condition
        string location
        image image
        string status
        bool is_sold
        int view_count
        datetime created_at
    }

    PostImage {
        int id PK
        int post_id FK
        image image
        int order
    }

    Favorite {
        int id PK
        int user_id FK
        int post_id FK
        datetime created_at
    }

    Comment {
        int id PK
        int post_id FK
        int author_id FK
        int parent_id FK
        text content
        datetime created_at
    }

    Review {
        int id PK
        int seller_id FK
        int reviewer_id FK
        int post_id FK
        int rating "1-5 sao"
        text content
        datetime created_at
    }

    Report {
        int id PK
        int post_id FK
        int reporter_id FK
        string reason
        text detail
        string status
        datetime created_at
    }

    Order {
        int id PK
        int post_id FK
        int buyer_id FK
        int seller_id FK
        decimal price_snapshot
        string status
        string contact
        text message
        text seller_note
        datetime created_at
        datetime updated_at
    }
```

### Vòng đời bài đăng

```mermaid
stateDiagram-v2
    [*] --> ACTIVE: Người dùng đăng tin
    ACTIVE --> SOLD: Đánh dấu đã bán
    SOLD --> ACTIVE: Mở lại bài
    ACTIVE --> HIDDEN: Chủ bài ẩn / Admin ẩn
    HIDDEN --> ACTIVE: Mở lại
    ACTIVE --> REJECTED: Admin từ chối
    REJECTED --> ACTIVE: Sửa & lưu lại
    ACTIVE --> [*]: Xoá
    SOLD --> [*]: Xoá
```

---

## 🔄 Luồng xử lý chính

Bốn chức năng chính của ứng dụng, mỗi luồng đi qua đúng view và route dưới đây:

| # | Chức năng | View xử lý | Route |
|---|---|---|---|
| 1 | Đăng nhập | `views.user_login` | `POST /dang-nhap/` |
| 2 | Đăng ký | `views.register` | `POST /dang-ky/` |
| 3 | Đăng tin sản phẩm | `views.create_post` | `POST /dang-tin/` |
| 4 | Đặt mua | `views.buy_post` | `POST /san-pham/<pk>/dat-mua/` |

---

## 📝 Ghi chú kỹ thuật

### Vì sao bỏ cấu hình MySQL hardcode?

Bản cũ ghi cứng `PORT = '3307'` và `PASSWORD = ''`, khiến dự án **không kết nối được**
với MySQL thật. Nay mọi thông tin nhạy cảm đọc từ `.env` nên chạy được trên mọi máy.

### Vì sao mọi thay đổi trạng thái dùng POST?

Bản cũ cho phép đánh dấu "đã bán" / "yêu thích" bằng thẻ `<a href>` (GET).
Kẻ tấn công có thể chèn ảnh `<img src="...toggle-sold/1">` vào trang khác để tự ý
đổi trạng thái — đây là lỗ hổng **CSRF**. Nay dùng `@require_POST` + CSRF token.

### Vì sao có bảng `Favorite` thay vì `ManyToManyField` trực tiếp?

`ManyToManyField` không lưu thời điểm yêu thích. Bảng nối `Favorite` cho phép
hiển thị "yêu thích gần đây" và thêm ràng buộc unique `(user, post)`.

### Vì sao `STATIC_URL` phải có dấu `/` ở đầu?

Nếu đặt `STATIC_URL = 'static/'` (thiếu dấu `/`), thẻ `{% static %}` sinh ra
đường dẫn tương đối. Ở trang chủ (`/`) nó vô hại, nhưng ở trang có đường dẫn lồng
nhau (`/san-pham/1/`) trình duyệt sẽ yêu cầu `/san-pham/static/css/main.css`
→ **404, mất toàn bộ CSS**. Vì vậy bắt buộc dùng `STATIC_URL = '/static/'`.

### Hiệu năng

- Index được đặt trên `created_at`, `(status, created_at)`, `(category, status)`
- `select_related` cho seller/category, `prefetch_related` cho ảnh & bình luận
- Tăng lượt xem bằng `F()` expression, không tốn query `SELECT`
- Ảnh dùng `loading="lazy"` để tải trang nhanh hơn

---

## 📄 Giấy phép

Dự án phục vụ mục đích học tập. Đồ dùng học tập được giao dịch giữa sinh viên,
người bán tự chịu trách nhiệm về tình trạng sản phẩm và giao dịch.

---

<div align="center">

**SáchGóc Uni** — Đồ án Công nghệ Phần mềm
Trường Đại học Kiến trúc Đà Nẵng

Made with ❤️ cho cộng đồng sinh viên

</div>
