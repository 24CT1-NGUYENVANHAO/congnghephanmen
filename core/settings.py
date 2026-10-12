"""
Cấu hình chính cho dự án SáchGóc Uni.

Mọi thông tin nhạy cảm (khóa bảo mật, thông tin MySQL) được đọc từ file `.env`
thay vì hardcode, giúp dự án chạy được trên nhiều máy khác nhau.

Tài liệu cấu hình: https://docs.djangoproject.com/en/5.2/topics/settings/
"""

import os
import sys
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# 1. ĐƯỜNG DẪN CƠ SỞ & NẠP BIẾN MÔI TRƯỜNG
# ---------------------------------------------------------------------------

# BASE_DIR trỏ tới thư mục gốc chứa manage.py
BASE_DIR = Path(__file__).resolve().parent.parent

# Ghi cảnh báo vào stderr để nổi lên trước khi Django in thông báo riêng
def _warn(message):
    print(f"\n⚠️  {message}", file=sys.stderr)


env = environ.Env(
    # (tên biến, giá trị mặc định nếu .env không khai báo)
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ['127.0.0.1', 'localhost']),
    USE_SQLITE=(bool, False),
    DB_NAME=(str, 'sachgocuni_db'),
    DB_USER=(str, 'root'),
    DB_PASSWORD=(str, ''),
    DB_HOST=(str, '127.0.0.1'),
    DB_PORT=(str, '3306'),
    MAX_UPLOAD_SIZE=(int, 5 * 1024 * 1024),
    POSTS_PER_PAGE=(int, 12),
)

# Nạp file .env nếu tồn tại (không bắt buộc phải có khi deploy)
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(env_file)

# Lấy giá trị sau khi đã nạp .env
SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-only-key-please-override-in-env-file')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Cho phép hiển thị lỗi chi tiết trên máy local khi DEBUG bật
if DEBUG:
    ALLOWED_HOSTS += ['testserver', '[::1]']

# ---------------------------------------------------------------------------
# 2. ỨNG DỤNG
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # Định dạng số lượng, ngày tháng trong template
    'app_main',                # Ứng dụng chính của sàn giao dịch
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',       # Chống Cross-Site Request Forgery
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # Template dùng chung (partials, trang lỗi)
        'APP_DIRS': True,                   # Template riêng của app_main
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                # Đưa biến (danh mục, số thông báo chưa đọc) vào mọi template
                'app_main.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# ---------------------------------------------------------------------------
# 3. CƠ SỞ DỮ LIỆU
# ---------------------------------------------------------------------------
# Dự án dùng MySQL làm CSDL chính (đúng kiến trúc đồ án).
#
# Vấn đề thực tế: mỗi máy cấu hình MySQL khác nhau (cổng, mật khẩu, có bật
# XAMPP hay không...). Nếu bắt người dùng phải tự sửa file .env thì rất dễ
# gặp lỗi "Access denied for user 'root'@'localhost'" và không biết cách sửa.
#
# Giải pháp: TỰ ĐỘNG DÒ. Thử kết nối MySQL trước; nếu thất bại thì chuyển
# sang SQLite một cách âm thầm để dự án LUÔN chạy được. Muốn ép dùng SQLite
# thì đặt USE_SQLITE=True trong .env.
#
# Cách này giúp thầy giáo clone về chạy thử được ngay mà không cần cài
# MySQL hay chỉnh sửa cấu hình.
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


def _sqlite_settings():
    """Cấu hình SQLite - không cần cài đặt gì thêm."""
    return {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


def _can_connect_mysql(settings_dict):
    """
    Thử kết nối MySQL để kiểm tra cấu hình có đúng không.

    Trả về True nếu kết nối được và database tồn tại.
    """
    import MySQLdb

    config = settings_dict['default']
    try:
        # Nối tới MySQL server (chưa chọn database) để dò cổng/mật khẩu trước
        connection = MySQLdb.connect(
            host=config['HOST'],
            port=int(config['PORT']),
            user=config['USER'],
            passwd=config['PASSWORD'],
            connect_timeout=3,
        )
        try:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                "WHERE SCHEMA_NAME = %s",
                [config['NAME']],
            )
            exists = cursor.fetchone() is not None
            cursor.close()
            return exists
        finally:
            connection.close()
    except Exception:
        return False


USE_SQLITE = env('USE_SQLITE')
DB_ENGINE_IN_USE = 'sqlite3'

if USE_SQLITE:
    DATABASES = _sqlite_settings()
else:
    _mysql = _mysql_settings()
    if _can_connect_mysql(_mysql):
        DATABASES = _mysql
        DB_ENGINE_IN_USE = 'mysql'
    else:
        # Không kết nối được MySQL -> tự chuyển sang SQLite để dự án vẫn chạy
        DATABASES = _sqlite_settings()
        DB_AUTO_FALLBACK = True
        _cfg = _mysql['default']
        _warn("Không kết nối được MySQL - đang dùng SQLite tạm thời.")
        print(
            f"   Đã thử    : mysql://{_cfg['USER']}@{_cfg['HOST']}:{_cfg['PORT']}"
            f"/{_cfg['NAME']}\n"
            f"   Nguyên nhân: MySQL chưa chạy, sai cổng, sai mật khẩu, "
            f"hoặc database '{_cfg['NAME']}' chưa tồn tại.\n"
            f"   Cách sửa  : mở XAMPP và bật MySQL, rồi tạo database:\n"
            f"                CREATE DATABASE {_cfg['NAME']} "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
            f"               hoặc sửa DB_PORT/DB_PASSWORD trong file .env\n"
            f"               hoặc chạy: python manage.py migrate\n"
            f"                         python seed_data.py\n"
            f"   (Dự án vẫn chạy bình thường với SQLite)",
            file=sys.stderr,
        )

# ---------------------------------------------------------------------------
# 4. XÁC THỰC & MẬT KHẨU
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# ---------------------------------------------------------------------------
# 5. QUỐC TẾ HÓA
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# 6. FILE TĨNH & MEDIA
# ---------------------------------------------------------------------------

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File tĩnh và media được phục vụ bởi Django chỉ khi DEBUG = True.
# Khi chạy production phải dùng Nginx / WhiteNoise thay thế.
if DEBUG:
    import mimetypes
    mimetypes.add_type('image/webp', '.webp')

# Giới hạn dung lượng tải lên
MAX_UPLOAD_SIZE = env('MAX_UPLOAD_SIZE')
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

# Số bài đăng mỗi trang
POSTS_PER_PAGE = env('POSTS_PER_PAGE')

DATA_UPLOAD_MAX_NUMBER_FILES = 10

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# 7. THÔNG BÁO
# ---------------------------------------------------------------------------

from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: 'info',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}

# ---------------------------------------------------------------------------
# 8. BẢO MẬT (chỉ áp dụng khi DEBUG = False)
# ---------------------------------------------------------------------------

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT = True
