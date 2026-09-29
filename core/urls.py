from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_main.urls')),
    path('accounts/', include('django.contrib.auth.urls')), # Hỗ trợ Đăng nhập/Đăng xuất
]

# Cấu hình đường dẫn hiển thị file media (ảnh upload)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)