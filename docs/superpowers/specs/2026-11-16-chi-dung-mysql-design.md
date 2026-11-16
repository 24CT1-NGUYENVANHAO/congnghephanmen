# Thiết kế: Chỉ dùng MySQL (bỏ SQLite)

Ngày: 2026-11-16
Trạng thái: đã duyệt

## 1. Mục tiêu

Repo chỉ dùng **một** hệ quản trị CSDL là MySQL/MariaDB, đúng như phần mô tả
đồ án. GitDiagram (sinh từ README + mã nguồn) không còn nút "MySQL / SQLite".

Hiện tại `core/settings.py` có ba lớp dự phòng khiến SQLite xuất hiện: cờ
`USE_SQLITE`, hàm dò `_can_connect_mysql()` và `_sqlite_settings()`. Khi MySQL
không nối được, app **âm thầm** chuyển sang `db.sqlite3` và in cảnh báo.

## 2. Phạm vi

### Làm

| File | Thay đổi |
|---|---|
| `core/settings.py` | `DATABASES` luôn là MySQL; bỏ `USE_SQLITE`, `_sqlite_settings()`, `_can_connect_mysql()`, `DB_ENGINE_IN_USE`, `DB_AUTO_FALLBACK`, `_warn()`; giữ shim PyMySQL và `OPTIONS` utf8mb4 |
| `check_db.py` | Bỏ nhánh kiểm tra/in cảnh báo SQLite; vẫn in engine, host, port, database, user và đếm bản ghi |
| `.env.example` | Bỏ `USE_SQLITE`; bỏ đoạn "tự chuyển sang SQLite"; nói rõ app báo lỗi nếu MySQL chưa sẵn sàng |
| `README.md` | Bỏ dòng `USE_SQLITE` trong bảng biến; mục "Xem đang dùng CSDL nào" chỉ còn MySQL; rà hết chỗ nhắc SQLite/fallback |
| `db.sqlite3` | Xóa file cũ (đang bị ignore, chỉ còn dữ liệu của những lần chạy fallback) |

### Không làm (cố ý)

- Không đổi model, migration hay nghiệp vụ.
- Không xóa PyMySQL (`requirements.txt` giữ nguyên) — vẫn là driver dự phòng khi máy thiếu `mysqlclient`.
- Không thêm bước "dò kết nối" lúc khởi động: bỏ hẳn thay vì thay bằng probe khác.

## 3. Cách đã chọn

MySQL trực tiếp, **fail-fast**: nối được thì chạy, không nối được thì Django
báo lỗi ngay kèm thông tin host/port/database trong thông báo. Người dùng chạy
`python check_db.py` để biết đang trỏ vào đâu và sửa `.env`.

Các cách khác bị loại:

- *Chỉ sửa README cho ghi MySQL* — sơ đồ đổi nhưng code vẫn fallback, sai yêu cầu.
- *Giữ fallback nhưng ẩn khỏi tài liệu* — càng dễ gây nhầm dữ liệu đang ở đâu.

## 4. Hệ quả

1. MySQL tắt/sai cổng → app **không chạy** (trước đây vẫn chạy bằng SQLite).
   Đây là hành vi mong muốn: dữ liệu luôn nằm trong MySQL.
2. `python manage.py test` tạo database `test_sachgocuni_db` trên MySQL, nên
   **phải bật MySQL** mới chạy test.
3. Sau khi push, GitDiagram phải sinh lại sơ đồ mới thấy nút "MySQL".

## 5. Kiểm chứng

- `python manage.py check` → không lỗi.
- `python check_db.py` → engine `django.db.backends.mysql`, đúng cổng 3307.
- `python manage.py test` → 140 test pass (138 cũ + 2 test khoá cấu hình).
- `grep -ri "sqlite"` trong mã nguồn/README → 0 kết quả.
