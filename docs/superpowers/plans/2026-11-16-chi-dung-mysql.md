# Chỉ dùng MySQL (bỏ SQLite) — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repo chỉ dùng MySQL/MariaDB: `DATABASES` luôn là MySQL, không còn cờ `USE_SQLITE`, không còn hàm dò kết nối hay đường lui sang `db.sqlite3`. Tài liệu và `.env.example` mô tả đúng hành vi mới.

**Architecture:** Xóa ba lớp dự phòng trong `core/settings.py` (`USE_SQLITE`, `_can_connect_mysql()`, `_sqlite_settings()`) và các cờ `DB_ENGINE_IN_USE`/`DB_AUTO_FALLBACK`/hàm `_warn()`. `DATABASES` gán trực tiếp từ `_mysql_settings()`. MySQL không sẵn sàng → Django báo lỗi kết nối ngay (fail-fast); `check_db.py` in engine/host/port/database để người dùng tự sửa `.env`.

**Tech Stack:** Django 5.2, MySQL/MariaDB (XAMPP cổng 3307), PyMySQL shim + mysqlclient, `django-environ`.

**Spec:** `docs/superpowers/specs/2026-11-16-chi-dung-mysql-design.md`

## Global Constraints

- Không đổi model, migration, view, template hay nghiệp vụ.
- Giữ nguyên shim `pymysql.install_as_MySQLdb()` và `OPTIONS` (`charset=utf8mb4`, `init_command`, `CONN_MAX_AGE=60`).
- Giữ `DB_PORT` mặc định trong `settings.py` là `'3306'` (mặc định chung); cấu hình chuẩn của dự án nằm ở `.env.example` = `3307`. Không đổi giá trị này trong plan.
- Không thêm probe kết nối lúc khởi động, không thêm dependency.
- Không commit/push trong lúc thực hiện; chờ xác nhận của người dùng.
- Toàn bộ chuỗi tiếng Việt giữ nguyên phong cách viết của repo (có dấu, câu ngắn).
- `grep -rni "sqlite"` phải bằng 0 trong mã nguồn, `README.md`, `.env.example` (bỏ qua `docs/superpowers/` vì đó là hồ sơ lịch sử).

## Review Focus

- Xóa `_warn()` thì `import sys` có còn dùng không → phải xóa luôn, tránh import thừa (ruff/flake8).
- `check_db.py` sau khi bỏ nhánh SQLite vẫn phải chạy được khi database rỗng (không có bảng) → chỉ in "(chưa có bảng)", không traceback.
- Không được để lại biến `DB_ENGINE_IN_USE`/`DB_AUTO_FALLBACK` — không file nào được đọc chúng (đã kiểm tra: chỉ `settings.py` định nghĩa).
- README không còn câu "bỏ qua bước tạo `.env` cũng được" — sai sự thật sau khi bỏ fallback.
- `.env.example` không còn ngụ ý app tự chuyển CSDL.

---

### Task 1: Khóa cấu hình bằng test

**Files:**
- Modify: `app_main/tests.py` (thêm import + class ở cuối file)

**Interfaces:**
- Produces: class `DatabaseConfigTests` — chạy trong `python manage.py test`, không truy vấn DB.

- [ ] **Step 1: Thêm test (đang đỏ)**

Đầu file, đổi import:

```python
from django.conf import settings
from django.test import Client, SimpleTestCase, TestCase, override_settings
```

Cuối file, thêm:

```python
class DatabaseConfigTests(SimpleTestCase):
    """Dự án chỉ dùng MySQL - không có đường lui sang SQLite."""

    def test_engine_is_mysql(self):
        self.assertEqual(
            settings.DATABASES['default']['ENGINE'],
            'django.db.backends.mysql',
        )

    def test_sqlite_switch_is_gone(self):
        self.assertFalse(hasattr(settings, 'USE_SQLITE'))
        self.assertFalse(hasattr(settings, 'DB_ENGINE_IN_USE'))
        self.assertFalse(hasattr(settings, 'DB_AUTO_FALLBACK'))
```

- [ ] **Step 2: Chạy test để thấy đỏ**

```bash
python manage.py test app_main.tests.DatabaseConfigTests -v 2
```

Kỳ vọng: `test_sqlite_switch_is_gone` FAIL (`USE_SQLITE` vẫn tồn tại). `test_engine_is_mysql` PASS (MySQL đang chạy cổng 3307).

---

### Task 2: `core/settings.py` — MySQL trực tiếp

**Files:**
- Modify: `core/settings.py`

**Interfaces:**
- Produces: `DATABASES = _mysql_settings()`; biến `USE_SQLITE`, `DB_ENGINE_IN_USE`, `DB_AUTO_FALLBACK`, `_warn`, `_can_connect_mysql`, `_sqlite_settings` không còn tồn tại.

- [ ] **Step 1: Bỏ `USE_SQLITE` khỏi khai báo `env`**

Trong `environ.Env(...)`, xóa dòng:

```python
    USE_SQLITE=(bool, False),
```

- [ ] **Step 2: Xóa `_warn()` và `import sys`**

Xóa khối:

```python
# Ghi cảnh báo vào stderr để nổi lên trước khi Django in thông báo riêng
def _warn(message):
    print(f"\n⚠️  {message}", file=sys.stderr)
```

và xóa `import sys` ở đầu file (không còn chỗ nào dùng).

- [ ] **Step 3: Thay toàn bộ khối 3 (dòng ~105–231) bằng MySQL trực tiếp**

Giữ nguyên comment giải thích, bỏ phần nói về dò/fallback:

```python
# ---------------------------------------------------------------------------
# 3. CƠ SỞ DỮ LIỆU
# ---------------------------------------------------------------------------
# Dự án chỉ dùng MySQL/MariaDB (đúng kiến trúc đồ án). Thông tin kết nối đọc
# từ .env, không có cơ chế chuyển sang CSDL khác: nếu MySQL chưa chạy, sai
# cổng hoặc database chưa tồn tại thì Django báo lỗi kết nối ngay. Chạy
# `python check_db.py` để xem app đang trỏ vào đâu rồi sửa .env.
# ---------------------------------------------------------------------------

# Cho phép dùng PyMySQL (driver thuần Python) thay cho mysqlclient
# nếu máy chưa cài thư viện C cho mysqlclient.
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:  # pragma: no cover
    pass


def _mysql_settings():
    """Cấu hình MySQL từ biến môi trường."""
    return {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            'CONN_MAX_AGE': 60,
        }
    }


DATABASES = _mysql_settings()
```

- [ ] **Step 4: Kiểm tra không còn tàn dư**

```bash
grep -n "sqlite\|USE_SQLITE\|DB_ENGINE_IN_USE\|DB_AUTO_FALLBACK\|_warn\|import sys" core/settings.py
```

Kỳ vọng: không có dòng nào.

- [ ] **Step 5: Chạy test Task 1**

```bash
python manage.py test app_main.tests.DatabaseConfigTests -v 2
```

Kỳ vọng: 2 test PASS.

---

### Task 3: `check_db.py` — bỏ nhánh SQLite

**Files:**
- Modify: `check_db.py`

**Interfaces:**
- Produces: script chỉ đọc MySQL; không có chuỗi `sqlite`; giữ phần liệt kê MySQL server ở cổng 3306/3307/3308.

- [ ] **Step 1: Bỏ khối if/else ở mục 1**

Thay:

```python
    if 'sqlite' in engine:
        print('  ⚠️  ĐANG DÙNG SQLITE, KHÔNG PHẢI MYSQL!')
        print('      Dữ liệu bạn thấy trên web KHÔNG nằm trong MySQL.')
        print('      Sửa DB_PORT / DB_PASSWORD trong .env rồi chạy lại:')
        print('          python manage.py migrate')
        print('          python seed_data.py')
        print(f'\n  File SQLite : {db["NAME"]}')

    else:
        print(f'  Host        : {db["HOST"]}')
        print(f'  Port        : {db["PORT"]}')
        print(f'  Database    : {db["NAME"]}')
        print(f'  User        : {db["USER"]}')
        print(f'  Password    : {"(rỗng)" if not db["PASSWORD"] else "***"}')
```

bằng:

```python
    print(f'  Host        : {db["HOST"]}')
    print(f'  Port        : {db["PORT"]}')
    print(f'  Database    : {db["NAME"]}')
    print(f'  User        : {db["USER"]}')
    print(f'  Password    : {"(rỗng)" if not db["PASSWORD"] else "***"}')
```

- [ ] **Step 2: Đơn giản hóa phần đếm bảng**

Thay:

```python
    with connection.cursor() as cur:
        if 'sqlite' in engine:
            cur.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        else:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s",
                [db['NAME']],
            )
        table_count = cur.fetchone()[0]
```

bằng:

```python
    with connection.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = %s",
            [db['NAME']],
        )
        table_count = cur.fetchone()[0]
```

- [ ] **Step 3: Bỏ điều kiện bọc mục 5**

Đổi `    if 'sqlite' not in engine:` (dòng ~117) thành không điều kiện: bỏ dòng `if` và giảm 4 dấu cách cho toàn bộ khối bên trong (tới hết `except ImportError: pass`).

- [ ] **Step 4: Cập nhật docstring đầu file**

Sửa câu `Rất hữu ích khi bạn không chắc dữ liệu trên web có nằm trong MySQL hay không.`
thành `Rất hữu ích khi bạn không chắc app đang nối vào MySQL server nào.`
Giữ nguyên đoạn giải thích máy có thể chạy nhiều MySQL server (3306/3307) với
database cùng tên — phần này vẫn đúng và không nhắc tới SQLite.

- [ ] **Step 5: Chạy thử**

```bash
python check_db.py
```

Kỳ vọng: `Engine : django.db.backends.mysql`, `Port : 3307`, kết nối OK, đếm bảng > 0, liệt kê 3 cổng.

---

### Task 4: `.env.example`

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Sửa header**

Thay dòng 7–8:

```text
#  ⚠️  KHÔNG cần tạo file này cũng chạy được. Nếu không kết nối được MySQL,
#  hệ thống sẽ TỰ ĐỘNG dùng SQLite và in cảnh báo giải thích cách khắc phục.
```

bằng:

```text
#  Nên tạo file này để khai báo đúng MySQL trên máy bạn. Dự án CHỈ dùng MySQL:
#  nếu chưa kết nối được, Django báo lỗi ngay (xem hướng dẫn bên dưới).
```

- [ ] **Step 2: Bỏ cảnh báo fallback và biến `USE_SQLITE`**

Xóa khối:

```text
# Nếu không kết nối được, hệ thống tự chuyển sang SQLite và vẫn chạy bình thường,
# nhưng KHI ĐÓ dữ liệu sẽ nằm trong db.sqlite3 chứ KHÔNG phải MySQL.
#

# Đặt True để ép dùng SQLite (không cần cài MySQL)
USE_SQLITE=False
```

thay bằng:

```text
# Nếu không kết nối được, Django báo lỗi ngay. Kiểm tra lại DB_PORT/DB_PASSWORD,
# bật MySQL trong XAMPP rồi chạy: python check_db.py
```

- [ ] **Step 3: Xác nhận**

```bash
grep -ni "sqlite" .env.example
```

Kỳ vọng: không có kết quả.

---

### Task 5: `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Bảng công nghệ (dòng ~84)**

Đổi `| **CSDL** | MySQL 8.0 (mặc định) hoặc SQLite | Lưu trữ dữ liệu qua ORM |`
thành `| **CSDL** | MySQL 8.0 / MariaDB | Lưu trữ dữ liệu qua ORM |`.

- [ ] **Step 2: Bước 2 — bỏ câu "bỏ qua cũng được"**

Thay:

```text
> 💡 **Bỏ qua bước này cũng được.** Dự án tự dò MySQL; nếu không kết nối
> được sẽ tự chuyển sang SQLite và in cảnh báo hướng dẫn. Xem
> [Kết nối CSDL](#-kết-nối-csdl).
```

bằng:

```text
> 💡 Dự án **chỉ dùng MySQL**. Nếu không tạo `.env`, app dùng giá trị mặc định
> trong `core/settings.py` (cổng 3306); máy chạy XAMPP của dự án cần
> `DB_PORT=3307`. Xem [Kết nối CSDL](#-kết-nối-csdl).
```

- [ ] **Step 3: Khối `.env` mẫu (dòng ~126–133)**

Xóa dòng `USE_SQLITE=False`.

- [ ] **Step 4: Bước 4b (dòng ~162)**

Đổi `mysql_tzinfo_to_sql`. Bỏ qua bước này nếu bạn dùng SQLite.`
thành `mysql_tzinfo_to_sql`.`

- [ ] **Step 5: Mục "Kết nối CSDL" (dòng ~264–287)**

Thay toàn bộ tiêu đề phụ "Cơ chế tự động" + đoạn văn + sơ đồ ASCII bằng:

```markdown
### Cơ chế

Dự án **chỉ dùng MySQL/MariaDB**. Khi khởi động, Django đọc thông tin kết nối
từ `.env` và nối thẳng vào MySQL — không có cơ chế chuyển sang CSDL khác.
Nếu MySQL chưa chạy, sai cổng hoặc database chưa tồn tại, Django báo lỗi ngay.
Chạy `python check_db.py` để biết app đang trỏ vào đâu rồi sửa `.env`.
```

- [ ] **Step 6: Bảng tham số `.env` (dòng ~293)**

Xóa dòng `| \`USE_SQLITE\` | Đặt \`True\` để ép dùng SQLite | \`False\` |`.

- [ ] **Step 7: Mục "Xem đang dùng CSDL nào" (dòng ~322–331)**

Thay phần "Kết quả" bằng:

```markdown
Kết quả mong đợi: `django.db.backends.mysql`. Nếu thấy lỗi kết nối, xem lại
`DB_HOST`/`DB_PORT`/`DB_PASSWORD` trong `.env`.
```

- [ ] **Step 8: Cây thư mục + bảng phân tầng**

- Dòng ~340: `# Đọc cấu hình từ .env, MySQL/SQLite` → `# Đọc cấu hình từ .env, cấu hình MySQL`.
- Dòng ~429: `| 🟥 **Database** | Lưu trữ dữ liệu | MySQL / SQLite |` → `| 🟥 **Database** | Lưu trữ dữ liệu | MySQL / MariaDB |`.

- [ ] **Step 9: Xác nhận**

```bash
grep -ni "sqlite" README.md
```

Kỳ vọng: không có kết quả.

---

### Task 6: Hai câu trong `app_main/models.py`

**Files:**
- Modify: `app_main/models.py`

- [ ] **Step 1: Docstring module (dòng 13)**

Đổi `Toàn bộ dữ liệu được lưu trữ qua ORM vào MySQL hoặc SQLite tuỳ cấu hình .env`
thành `Toàn bộ dữ liệu được lưu trữ qua ORM vào MySQL (cấu hình trong .env).`

- [ ] **Step 2: Comment `Order` (dòng 527)**

Đổi `không hỗ trợ partial index (chỉ SQLite/PostgreSQL mới có).`
thành `không hỗ trợ partial index (chỉ một số CSDL khác mới có).`

- [ ] **Step 3: Xác nhận**

```bash
grep -ni "sqlite" app_main/models.py
```

Kỳ vọng: không có kết quả.

---

### Task 7: Xóa `db.sqlite3`

**Files:**
- Delete: `db.sqlite3` (đang bị `.gitignore`, không tracked)

- [ ] **Step 1: Kiểm tra chưa tracked và xóa**

```bash
git ls-files --error-unmatch db.sqlite3 || echo "không tracked"
rm -f db.sqlite3
ls db.sqlite3 2>/dev/null || echo "đã xóa"
```

Kỳ vọng: "không tracked" và "đã xóa".

---

### Task 8: Kiểm chứng toàn bộ

**Files:** không sửa

- [ ] **Step 1: Django check**

```bash
python manage.py check
```

Kỳ vọng: `System check identified no issues (0 silenced).`

- [ ] **Step 2: check_db**

```bash
python check_db.py
```

Kỳ vọng: engine `django.db.backends.mysql`, port `3307`, kết nối thành công.

- [ ] **Step 3: Toàn bộ test (cần MySQL đang chạy)**

```bash
python manage.py test
```

Kỳ vọng: `Ran 140 tests` — 138 test cũ + 2 test mới — `OK`.

- [ ] **Step 4: Grep tàn dư**

```bash
grep -rni "sqlite" --include=*.py --include=*.md --include=*.example --include=*.txt . \
  | grep -v "^\./\.git/" | grep -v "^\./docs/superpowers/"
```

Kỳ vọng: không có kết quả.

- [ ] **Step 5: `git status` + báo cáo**

```bash
git status --short
```

Báo lại danh sách file thay đổi, kết quả 3 lệnh kiểm chứng, rồi **hỏi trước khi commit/push**. Nhắc: sau khi push phải regenerate GitDiagram để nút đổi thành "MySQL".
