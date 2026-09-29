graph TD
    %% Định nghĩa các node
    User([Người dùng / Trình duyệt]) -->|HTTP Request| Django[Django WSGI / ASGI Server]
    
    subgraph Django_Project [Hệ thống Django Core]
        Django --> RootURL[Project urls.py]
        RootURL --> AppURL[App app_main urls.py]
        
        AppURL -->|Phân phối Request| Views{views.py <br> Bộ điều khiển Logic}
        
        subgraph Xử_lý_nghiệp_vụ [Xử lý nghiệp vụ & Dữ liệu]
            Views -->|Xác thực tài khoản| Auth[Django Auth System]
            Views -->|Đọc / Ghi dữ liệu| Models[models.py <br> ORM tương tác CSDL]
            Views -->|Xử lý Form & Upload File| Forms[forms.py <br> Image / Data Validation]
        end
        
        Models -->|Truy vấn SQL| DB[(MySQL Database <br> db.sqlite3)]
        DB --> Models
        
        Views -->|Render template & context| Templates[Templates HTML + Tailwind CSS]
    end

    Templates -->|HTTP Response / Giao diện hoàn chỉnh| User

    %% Ghi chú bổ sung
    classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef core fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef db fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    
    class User client;
    class Django,RootURL,AppURL,Views,Auth,Models,Forms,Templates core;
    class DB db;