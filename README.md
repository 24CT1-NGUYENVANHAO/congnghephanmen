# 📚 SáchGóc Uni - Sàn Giao Dịch & Chia Sẻ Đồ Dùng Sinh Viên

Dự án phát triển nền tảng web thương mại điện tử dành cho sinh viên trường Đại học Kiến trúc Đà Nẵng và cộng đồng sinh viên nói chung, hỗ trợ trao đổi, mua bán sách cũ, giáo trình và tặng đồ dùng học tập miễn phí (0đ).

---

## 🏗️ Sơ đồ Kiến trúc & Luồng Xử lý Tổng thể Hệ thống

GitHub hỗ trợ hiển thị trực tiếp sơ đồ kiến trúc chi tiết của dự án thông qua mã nguồn mở Mermaid dưới đây:

```mermaid
graph TD
    %% Tầng Giao diện người dùng
    subgraph Client_Layer ["1. Tầng Giao diện & Người dùng (Client Side)"]
        User([👤 Người dùng / Sinh viên]) -->|Gửi HTTP Request (GET/POST)| Browser[Trình duyệt Web <br> Tailwind CSS UI]
        Browser -->|Hiển thị Giao diện hoàn chỉnh| User
    end

    Browser -->|Truyền qua Internet| ServerCore

    %% Tầng Máy chủ & Điều hướng
    subgraph ServerCore ["2. Tầng Máy chủ & Điều phối (Django Core Server)"]
        Server[Django WSGI / ASGI Server] --> Middleware{Django Security & Session Middleware}
        
        Middleware --> RootURL[core/urls.py <br> Bộ định tuyến cấp Dự án]
        RootURL --> AppURL[app_main/urls.py <br> Bộ định tuyến cấp Ứng dụng]
        
        %% Tầng Điều khiển Logic (Views)
        AppURL --> Views{app_main/views.py <br> Bộ điều khiển Logic trung tâm}
        
        %% Phân nhánh các luồng nghiệp vụ thực tế
        subgraph Business_Modules ["3. Các Phân hệ Nghiệp vụ Chính"]
            Views -->|Xác thực tài khoản| AuthModule[Auth System <br> Đăng ký / Đăng nhập / Đăng xuất]
            Views -->|Quản lý bài đăng| PostModule[Sản phẩm & Bài đăng <br> Đăng tin, Tặng 0đ, Lọc danh mục]
            Views -->|Tương tác xã hội| SocialModule[Bình luận & Đánh giá uy tín <br> Wishlist yêu thích]
        end
        
        %% Tầng xử lý Form và Bảo mật dữ liệu
        AuthModule --> FormsCheck[app_main/forms.py <br> Kiểm tra tính hợp lệ & Xử lý File Upload]
        PostModule --> FormsCheck
        
        %% Tầng Mô hình dữ liệu ORM
        FormsCheck --> ModelsMap[app_main/models.py <br> Định nghĩa các Model & Quan hệ ORM]
    end

    %% Tầng Lưu trữ Cơ sở dữ liệu vật lý
    subgraph Storage_Layer ["4. Tầng Lưu trữ Vật lý (Database & Media)"]
        ModelsMap -->|Thực thi câu lệnh SQL| MySQLDB[(MySQL Database / db.sqlite3 <br> Lưu trữ User, Post, Category, Comment, Wishlist)]
        MySQLDB --> ModelsMap
        
        PostModule -->|Lưu tệp ảnh tải lên từ máy| MediaFolder[(Thư mục /media/posts <br> Lưu trữ hình ảnh thực tế)]
    end

    %% Tầng tổng hợp dữ liệu trả về giao diện
    ModelsMap --> TemplateEngine[Django Template Engine <br> Biên dịch HTML kết hợp Context dữ liệu]
    MediaFolder --> TemplateEngine
    AuthModule --> TemplateEngine

    TemplateEngine -->|Phản hồi HTTP Response (HTML/CSS)| Browser

    %% Định nghĩa màu sắc sinh động cho sơ đồ đồ án
    classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef server fill:#f1f8e9,stroke:#33691e,stroke-width:2px;
    classDef logic fill:#fff8e1,stroke:#ff8f00,stroke-width:2px;
    classDef db fill:#ffebee,stroke:#c62828,stroke-width:2px;

    class User,Browser client;
    class Server,Middleware,RootURL,AppURL,Views,FormsCheck,TemplateEngine server;
    class AuthModule,PostModule,SocialModule,ModelsMap logic;
    class MySQLDB,MediaFolder db;