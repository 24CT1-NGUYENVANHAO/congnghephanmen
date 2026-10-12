"""
Định tuyến URL cấp cao nhất cho dự án SáchGóc Uni.

Bao gồm: Django Admin, ứng dụng app_main, và phục vụ file media khi DEBUG.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "HỆ THỐNG QUẢN TRỊ SÁCHGÓC UNI"
admin.site.site_title = "Admin SáchGócUni"
admin.site.index_title = "Bảng điều khiển & Kiểm duyệt"

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('app_main.urls')),
]

# Media (ảnh người dùng tải lên) được Django phục vụ khi DEBUG = True.
# KHÔNG cần khai báo thủ công cho static files: django.contrib.staticfiles
# đã tự phục vụ từ STATICFILES_DIRS trong lúc chạy `manage.py runserver`.
# Khi chạy production phải dùng `collectstatic` + Nginx/WhiteNoise.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Xử lý trang lỗi tập trung
handler404 = 'app_main.views.handler_404'
handler500 = 'app_main.views.handler_500'
