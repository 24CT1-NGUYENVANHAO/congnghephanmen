"""
Cấu hình chính cho dự án SáchGóc Uni.

Mọi thông tin nhạy cảm (khóa bảo mật, thông tin MySQL) được đọc từ file `.env`
thay vì hardcode, giúp dự án chạy được trên nhiều máy khác nhau.

Tài liệu cấu hình: https://docs.djangoproject.com/en/5.2/topics/settings/
"""

import os
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# 1. ĐƯỜNG DẪN CƠ SỞ & NẠP BIẾN MÔI TRƯỜNG
# ---------------------------------------------------------------------------

# BASE_DIR trỏ tới thư mục gốc chứa manage.py
BASE_DIR = Path(__file__).resolve().parent.parent

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
# Mặc định dùng MySQL (đúng với kiến trúc dự án). Nếu không bật XAMPP,
# đặt USE_SQLITE=True trong .env để chuyển sang SQLite.
# ---------------------------------------------------------------------------

if env('USE_SQLITE'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
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

# Cho phép dùng PyMySQL (driver thuần Python) thay cho mysqlclient
# nếu máy chưa cài thư viện C cho mysqlclient.
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:  # pragma: no cover
    pass

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

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
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
