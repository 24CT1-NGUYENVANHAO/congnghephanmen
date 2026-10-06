# 📚 SáchGóc Uni - Sàn Giao Dịch & Chia Sẻ Đồ Dùng Sinh Viên

[![GitDiagram Architecture](https://img.shields.io/badge/GitDiagram-Explore%20System%20Architecture-2563eb?style=for-the-badge&logo=diagramsdotnet)](https://gitdiagram.com/24CT1-NGUYENVANHAO/congnghephanmen)
[![Django](https://img.shields.io/badge/Django-5.2%20%7C%204.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)

Dự án phát triển nền tảng web thương mại điện tử dành cho sinh viên trường Đại học Kiến trúc Đà Nẵng và cộng đồng sinh viên nói chung, hỗ trợ trao đổi, mua bán sách cũ, giáo trình và tặng đồ dùng học tập miễn phí (0đ).

> 💡 **Trực quan hóa Kiến trúc Dự án trên GitDiagram:** Bạn có thể xem và tương tác trực tiếp với sơ đồ kiến trúc mã nguồn của repository này tại: **[gitdiagram.com/24CT1-NGUYENVANHAO/congnghephanmen](https://gitdiagram.com/24CT1-NGUYENVANHAO/congnghephanmen)**

---

## 🏗️ 1. Sơ Đồ Kiến Trúc & Luồng Xử Lý Tổng Thể Hệ Thống

GitHub và GitDiagram hỗ trợ hiển thị trực quan sơ đồ kiến trúc chi tiết của dự án thông qua Mermaid:

```mermaid
graph TD
    %% Tầng Giao diện người dùng
    subgraph Client_Layer ["1. Tầng Giao diện & Người dùng (Client Side)"]
        User([👤 Người dùng / Sinh viên]) -->|Gửi HTTP Request GET / POST| Browser[Trình duyệt Web <br> Tailwind CSS UI]
        Browser -->|Hiển thị Giao diện phản hồi| User
    end

    Browser -->|Giao thức HTTP / HTTPS| ServerCore

    %% Tầng Máy chủ & Điều hướng
    subgraph ServerCore ["2. Tầng Máy chủ & Điều phối (Django Core Server)"]
        Server[Django WSGI / ASGI Server] --> Middleware{Django Security & Session Middleware}
        
        Middleware --> RootURL[core/urls.py <br> Bộ định tuyến cấp Dự án]
        RootURL --> AppURL[app_main/urls.py <br> Bộ định tuyến cấp Ứng dụng]
        RootURL --> AdminURL[django.contrib.admin <br> Bảng điều khiển Quản trị]
        
        %% Tầng Điều khiển Logic (Views)
        AppURL --> Views{app_main/views.py <br> Bộ điều khiển Logic trung tâm}
        
        %% Phân nhánh các luồng nghiệp vụ thực tế
        subgraph Business_Modules ["3. Các Phân hệ Nghiệp vụ Chính"]
            Views -->|Xác thực tài khoản| AuthModule[Auth System <br> Đăng ký / Đăng nhập / Đăng xuất]
            Views -->|Quản lý bài đăng| PostModule[Sản phẩm & Bài đăng <br> Đăng tin, Tặng 0đ, Lọc danh mục]
            Views -->|Tương tác xã hội| SocialModule[Bình luận trao đổi <br> Wishlist yêu thích]
        end
        
        %% Tầng xử lý Form và Bảo mật dữ liệu
        AuthModule --> FormsCheck[app_main/forms.py <br> Kiểm tra tính hợp lệ & Upload File]
        PostModule --> FormsCheck
        
        %% Tầng Mô hình dữ liệu ORM
        FormsCheck --> ModelsMap[app_main/models.py <br> Định nghĩa các Model & Quan hệ ORM]
    end

    %% Tầng Lưu trữ Cơ sở dữ liệu vật lý
    subgraph Storage_Layer ["4. Tầng Lưu trữ Vật lý (Database & Media)"]
        ModelsMap -->|Truy vấn SQL qua Django ORM| DB[(MySQL Database / SQLite <br> User, Post, Category, Comment, Review)]
        DB --> ModelsMap
        
        PostModule -->|Lưu trữ file ảnh tải lên| MediaFolder[(Thư mục /media/posts <br> Ảnh sản phẩm thực tế)]
    end

    %% Tầng tổng hợp dữ liệu trả về giao diện
    ModelsMap --> TemplateEngine[Django Template Engine <br> Biên dịch HTML kết hợp Context dữ liệu]
    MediaFolder --> TemplateEngine
    AuthModule --> TemplateEngine

    TemplateEngine -->|Phản hồi HTTP Response HTML/CSS| Browser

    %% Định nghĩa màu sắc sinh động
    classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef server fill:#f1f8e9,stroke:#33691e,stroke-width:2px;
    classDef logic fill:#fff8e1,stroke:#ff8f00,stroke-width:2px;
    classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px;

    class User,Browser client;
    class Server,Middleware,RootURL,AppURL,AdminURL,Views,FormsCheck,TemplateEngine server;
    class AuthModule,PostModule,SocialModule,ModelsMap logic;
    class DB,MediaFolder db;
```

---

## 📊 2. Sơ Đồ Thực Thể Cơ Sở Dữ Liệu (ERD)

```mermaid
erDiagram
    User ||--o{ Post : "đăng tin (seller)"
    User ||--o{ Comment : "bình luận (author)"
    User ||--o{ Review : "đánh giá uy tín"
    User }o--o{ Post : "yêu thích (wishlist)"
    Category ||--o{ Post : "phân loại"
    Post ||--o{ Comment : "chứa bình luận"

    Category {
        int id PK
        string name "Tên danh mục"
        string slug UK "Đường dẫn"
    }

    Post {
        int id PK
        string title "Tiêu đề sản phẩm"
        decimal price "Giá bán (VNĐ)"
        boolean is_free "Tặng miễn phí 0đ"
        string condition "Tình trạng (Mới/Cũ)"
        string image "Ảnh sản phẩm"
        boolean is_sold "Đã bán"
        datetime created_at "Ngày đăng"
    }

    Comment {
        int id PK
        text content "Nội dung trao đổi"
        datetime created_at "Thời gian"
    }

    Review {
        int id PK
        int rating "Số sao (1-5)"
        text comment "Nhận xét"
    }
```

---

## 📁 3. Cấu Trúc Thư Mục Dự Án (Project Structure)

```text
24CT1-NGUYEN_VAN HAO/
├── core/                       # Cấu hình dự án Django cấp cao nhất
│   ├── settings.py             # Cài đặt ứng dụng, Database, Media, Static
│   ├── urls.py                 # Điều phối URL gốc (Admin, App, Auth)
│   ├── wsgi.py                 # Cổng giao tiếp Web Server chuẩn WSGI
│   └── asgi.py                 # Cổng giao tiếp Asynchronous ASGI
├── app_main/                   # Ứng dụng chính của nền tảng SáchGóc Uni
│   ├── models.py               # Thực thể CSDL: Category, Post, Comment, Review
│   ├── views.py                # Xử lý logic Controller (Trang chủ, Chi tiết, Đăng tin...)
│   ├── forms.py                # Form xử lý dữ liệu và tải file ảnh (PostForm, CommentForm)
│   ├── urls.py                 # Định tuyến các trang chức năng của ứng dụng
│   ├── admin.py                # Quản trị viên Django: duyệt bài, khóa tài khoản vi phạm
│   ├── apps.py                 # Khai báo thông tin ứng dụng
│   ├── tests.py                # Bộ Unit Tests tự động kiểm tra Models & Views
│   ├── migrations/             # Lịch sử đồng bộ cấu trúc Database
│   └── templates/              # Giao diện HTML tích hợp Tailwind CSS
│       ├── app_main/           # base.html, home.html, detail.html, create_post.html, my_posts.html
│       └── registration/       # login.html, register.html
├── media/                      # Thư mục chứa hình ảnh sản phẩm người dùng upload
│   └── posts/
├── seed_data.py                # Script tự động tạo 15+ dữ liệu mẫu ban đầu
├── requirements.txt            # Danh sách các thư viện Python cần thiết
├── ARCHITECTURE.md             # Đặc tả chi tiết cấu trúc hệ thống cho GitDiagram
├── manage.py                   # Script quản lý dòng lệnh của Django
└── README.md                   # Tài liệu hướng dẫn dự án
```

---

## 🚀 4. Hướng Dẫn Cài Đặt & Khởi Chạy

### Bước 1: Cài đặt các thư viện cần thiết
```bash
pip install -r requirements.txt
```

### Bước 2: Khởi tạo Cơ sở dữ liệu
Đảm bảo dịch vụ MySQL (XAMPP/MySQL Server) đang bật tại cổng `3307` (hoặc cấu hình lại trong [`core/settings.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/core/settings.py)):
```bash
python manage.py makemigrations
python manage.py migrate
```

### Bước 3: Nạp dữ liệu mẫu ban đầu (Demo Data)
```bash
python seed_data.py
```
> Script sẽ tự động tạo tài khoản mẫu `sinhvien_demo` (mật khẩu: `123456`) cùng với các danh mục và sản phẩm mẫu sinh động.

### Bước 4: Khởi động Server
```bash
python manage.py runserver
```
Truy cập hệ thống tại: **`http://127.0.0.1:8000/`**

---

## 🌟 5. Các Tính Năng Nổi Bật
- 📖 **Mua bán & Trao đổi:** Đăng bán giáo trình, dụng cụ vẽ kỹ thuật, thiết bị điện tử giá rẻ.
- 🎁 **Tặng đồ dùng 0đ:** Chuyên mục dành riêng cho sinh viên khóa trên tặng lại đồ cho tân sinh viên.
- 🔍 **Tìm kiếm & Bộ lọc nhanh:** Lọc theo từng danh mục khoa ngành hoặc lọc nhanh đồ tặng miễn phí.
- 💬 **Hỏi đáp trực tiếp:** Tính năng bình luận ngay dưới bài đăng giúp người mua và người bán dễ dàng kết nối.
- ⭐ **Đánh giá uy tín & Wishlist:** Đánh giá điểm sao người bán và lưu lại các sản phẩm yêu thích.
- 🔒 **Quản trị toàn diện (Admin):** Kiểm duyệt bài đăng, gắn cờ sản phẩm và khóa/mở khóa tài khoản người dùng vi phạm.