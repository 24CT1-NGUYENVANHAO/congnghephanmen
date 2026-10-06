# 🏛️ Kiến Trúc Hệ Thống SáchGóc Uni (System Architecture)

> **Tài liệu đặc tả kiến trúc phần mềm, luồng dữ liệu và thiết kế thành phần dành cho GitDiagram và các công cụ trực quan hóa mã nguồn.**

---

## 1. Tổng Quan Kiến Trúc (Architecture Overview)

Hệ thống **SáchGóc Uni** được xây dựng theo mô hình kiến trúc phân lớp chuẩn **Django MVT (Model - View - Template)** mở rộng, kết hợp cơ chế bảo mật xác thực session và phân quyền người dùng.

```mermaid
graph TB
    %% Client Layer
    subgraph Client_Tier ["🌐 Client Tier (Giao Diện Trình Duyệt)"]
        Browser["Trình duyệt Web Sinh viên / Khách"]
        Tailwind["Tailwind CSS + HTML5 Templates"]
        Browser <--> Tailwind
    end

    %% Web & Gateway Layer
    subgraph Gateway_Tier ["⚡ Gateway & Middleware Tier"]
        WSGI["core/wsgi.py / ASGI"]
        SecMiddleware["SecurityMiddleware"]
        SessionMiddleware["SessionMiddleware"]
        CsrfMiddleware["CsrfViewMiddleware"]
        AuthMiddleware["AuthenticationMiddleware"]
        
        WSGI --> SecMiddleware
        SecMiddleware --> SessionMiddleware
        SessionMiddleware --> CsrfMiddleware
        CsrfMiddleware --> AuthMiddleware
    end

    %% Controller & Routing Layer
    subgraph Routing_Tier ["🧭 Routing & Dispatcher Tier"]
        CoreURL["core/urls.py<br/>(Root Router)"]
        AdminURL["django.contrib.admin"]
        AppURL["app_main/urls.py<br/>(App Router)"]
        AuthURL["django.contrib.auth.urls"]

        CoreURL --> AdminURL
        CoreURL --> AppURL
        CoreURL --> AuthURL
    end

    %% Application Logic Tier
    subgraph Controller_Tier ["⚙️ Controller Tier (app_main/views.py)"]
        ViewHome["home()<br/>Tìm kiếm & Lọc 0đ"]
        ViewDetail["post_detail()<br/>Xem & Bình luận"]
        ViewCreate["create_post()<br/>Đăng bài & Upload ảnh"]
        ViewBuy["buy_post()<br/>Đặt mua / Nhận đồ"]
        ViewWishlist["toggle_wishlist()<br/>Thêm/Xóa yêu thích"]
        ViewMyPosts["my_posts() / toggle_sold()<br/>Quản lý tin cá nhân"]
        ViewRegister["register()<br/>Đăng ký tài khoản"]
    end

    %% Validation & Form Layer
    subgraph Form_Tier ["🛡️ Form & Validation Tier (app_main/forms.py)"]
        PostForm["PostForm<br/>Kiểm tra bài đăng & File ảnh"]
        CommentForm["CommentForm<br/>Kiểm tra nội dung bình luận"]
    end

    %% Model & Data Access Tier
    subgraph Model_Tier ["📦 Model & ORM Tier (app_main/models.py)"]
        ModelUser["django.contrib.auth.models.User"]
        ModelCategory["Category<br/>(Phân loại đồ dùng)"]
        ModelPost["Post<br/>(Sách, Đồ dùng, Quà tặng 0đ)"]
        ModelComment["Comment<br/>(Hỏi đáp / Trao đổi)"]
        ModelReview["Review<br/>(Đánh giá uy tín 1-5 sao)"]
    end

    %% Storage & Database Tier
    subgraph Storage_Tier ["🗄️ Persistence & Storage Tier"]
        Database[("MySQL / SQLite Database<br/>sachgocuni_db")]
        MediaStorage[("Media Storage<br/>/media/posts/")]
    end

    %% Connections
    Client_Tier <==>|HTTP Requests / Responses| Gateway_Tier
    Gateway_Tier ==> Routing_Tier
    AppURL --> Controller_Tier
    
    Controller_Tier --> Form_Tier
    Form_Tier --> Model_Tier
    Controller_Tier --> Model_Tier
    
    Model_Tier <==>|Django ORM SQL| Database
    Form_Tier -->|Save Image Files| MediaStorage

    classDef client fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef gateway fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef router fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef controller fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef form fill:#fffde7,stroke:#fbc02d,stroke-width:2px;
    classDef model fill:#fce4ec,stroke:#c2185b,stroke-width:2px;
    classDef storage fill:#efebe9,stroke:#5d4037,stroke-width:2px;

    class Browser,Tailwind client;
    class WSGI,SecMiddleware,SessionMiddleware,CsrfMiddleware,AuthMiddleware gateway;
    class CoreURL,AdminURL,AppURL,AuthURL router;
    class ViewHome,ViewDetail,ViewCreate,ViewBuy,ViewWishlist,ViewMyPosts,ViewRegister controller;
    class PostForm,CommentForm form;
    class ModelUser,ModelCategory,ModelPost,ModelComment,ModelReview model;
    class Database,MediaStorage storage;
```

---

## 2. Sơ Đồ Quan Hệ Thực Thể (Entity Relationship Diagram - ERD)

```mermaid
erDiagram
    USER ||--o{ POST : "seller (đăng tin)"
    USER ||--o{ COMMENT : "author (bình luận)"
    USER ||--o{ REVIEW : "reviewer / seller"
    USER }o--o{ POST : "wishlist (yêu thích)"
    CATEGORY ||--o{ POST : "chứa (phân loại)"
    POST ||--o{ COMMENT : "nhận (bình luận)"

    USER {
        int id PK
        string username
        string email
        string password
        boolean is_active
        boolean is_staff
    }

    CATEGORY {
        int id PK
        string name "Tên danh mục"
        string slug UK "Đường dẫn thân thiện"
    }

    POST {
        int id PK
        string title "Tiêu đề bài đăng"
        int seller_id FK "Người đăng"
        int category_id FK "Danh mục"
        string course_code "Mã học phần / Tên môn"
        string faculty "Khoa / Ngành"
        decimal price "Giá bán (0 nếu tặng)"
        boolean is_free "Tặng miễn phí 0đ"
        string condition "Tình trạng NEW/LIKE_NEW/GOOD/USED"
        string image "Tệp ảnh đính kèm"
        text description "Mô tả chi tiết"
        boolean is_sold "Trạng thái đã bán"
        datetime created_at "Ngày đăng tin"
    }

    COMMENT {
        int id PK
        int post_id FK "Bài đăng liên quan"
        int author_id FK "Người gửi bình luận"
        text content "Nội dung trao đổi"
        datetime created_at "Thời gian gửi"
    }

    REVIEW {
        int id PK
        int seller_id FK "Người bán được đánh giá"
        int reviewer_id FK "Người mua gửi đánh giá"
        int rating "Điểm sao (1-5)"
        text comment "Nội dung nhận xét"
        datetime created_at "Thời gian đánh giá"
    }
```

---

## 3. Luồng Xử Lý Yêu Cầu (Request Lifecycle Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor SinhVien as 👤 Sinh Viên (Client)
    participant CoreURL as 🧭 core/urls.py
    participant AppURL as 🧭 app_main/urls.py
    participant Views as ⚙️ app_main/views.py
    participant Forms as 🛡️ app_main/forms.py
    participant Models as 📦 app_main/models.py
    participant DB as 🗄️ Database (MySQL/SQLite)
    participant Template as 🎨 Template Engine

    SinhVien->>CoreURL: HTTP POST /post/create/ (Kèm file ảnh)
    CoreURL->>AppURL: Dispatch to app_main
    AppURL->>Views: Gọi create_post(request)
    
    Views->>Forms: Khởi tạo PostForm(request.POST, request.FILES)
    alt Dữ liệu hợp lệ
        Forms->>Models: form.save(commit=False)
        Views->>Models: Gán seller = request.user, is_free=(price==0)
        Models->>DB: INSERT INTO app_main_post (...)
        DB-->>Models: Thành công (post_id)
        Views-->>SinhVien: HTTP 302 Redirect to / (home)
    else Dữ liệu không hợp lệ
        Forms-->>Views: Lỗi validation (form.errors)
        Views->>Template: Render 'app_main/create_post.html' kèm lỗi
        Template-->>SinhVien: HTTP 200 OK (Hiển thị thông báo sửa)
    end
```

---

## 4. Bản Đồ Mã Nguồn & Chức Năng (Code Map)

| Đường Dẫn Tệp | Phân Lớp Kiến Trúc | Chức Năng & Trách Nhiệm Chính |
|---|---|---|
| [`core/settings.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/core/settings.py) | **Cấu hình (Config)** | Khai báo `INSTALLED_APPS`, thiết lập MySQL database, bảo mật, xác thực người dùng, Media & Static files. |
| [`core/urls.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/core/urls.py) | **Điều phối (Root Router)** | Định tuyến cấp gốc, phân phối tới `/admin/`, `app_main.urls`, `accounts/` và phục vụ media. |
| [`core/wsgi.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/core/wsgi.py) | **Cổng giao tiếp (Gateway)** | Điểm vào cho các Web Server chuẩn WSGI (Gunicorn, uWSGI). |
| [`app_main/models.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/app_main/models.py) | **Mô hình Dữ liệu (ORM)** | Định nghĩa các bảng `Category`, `Post`, `Comment`, `Review`, các mối quan hệ FK & M2M. |
| [`app_main/views.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/app_main/views.py) | **Điều khiển Logic (Controllers)** | Tiếp nhận yêu cầu HTTP, xử lý nghiệp vụ tìm kiếm, phân trang, đăng tin, mua hàng, yêu thích. |
| [`app_main/forms.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/app_main/forms.py) | **Xác thực Dữ liệu (Validation)** | Xử lý `PostForm`, tải lên file ảnh `Pillow`, xác thực `CommentForm`. |
| [`app_main/urls.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/app_main/urls.py) | **Định tuyến (App Router)** | Khai báo các endpoint con trong ứng dụng chính. |
| [`app_main/admin.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/app_main/admin.py) | **Quản trị (Admin Panel)** | Giao diện quản trị viên: lọc tin, duyệt bài, khóa/mở khóa tài khoản sinh viên vi phạm. |
| [`app_main/tests.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/app_main/tests.py) | **Kiểm thử (Unit Tests)** | Kiểm tra tính đúng đắn của Models, Views, định tuyến HTTP. |
| [`seed_data.py`](file:///d:/24CT1-NGUYEN_VAN%20HAO/seed_data.py) | **Tiện ích Khởi tạo (Seeding)** | Tự động tạo danh mục và 15+ dữ liệu mẫu ban đầu để chạy thử nghiệm. |
| [`requirements.txt`](file:///d:/24CT1-NGUYEN_VAN%20HAO/requirements.txt) | **Quản lý Thư viện (Dependencies)** | Danh mục phiên bản các gói phần mềm cần thiết: Django, Pillow, MySQL drivers. |

---

## 5. Tương Thích Với GitDiagram

Để xem sơ đồ kiến trúc động và tương tác trực tiếp trên trình duyệt bằng GitDiagram:
- **URL GitDiagram:** `https://gitdiagram.com/Hao286/congnghephanmen`
- GitDiagram sẽ tự động quét cây thư mục, tệp cấu hình `requirements.txt`, tài liệu `ARCHITECTURE.md` và `README.md` để sinh ra sơ đồ kiến trúc trực quan, tương tác và nhấp được vào từng tệp mã nguồn.
