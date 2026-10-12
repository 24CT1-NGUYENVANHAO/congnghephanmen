"""
Bảng định tuyến URL của ứng dụng app_main.

Nhóm theo nhóm chức năng để dễ tra cứu:
  - Trang chủ & tìm kiếm
  - Xem & tương tác với bài đăng
  - Quản lý bài đăng của tôi
  - Hồ sơ người dùng
  - Xác thực
"""

from django.urls import path

from . import views

# Không đặt app_name để các template dùng tên URL đơn giản: {% url 'home' %}

urlpatterns = [
    # --- Trang chủ & tĩnh ---
    path('', views.home, name='home'),
    path('gioi-thieu/', views.about, name='about'),

    # --- Bài đăng: xem & tương tác ---
    path('san-pham/<int:pk>/', views.post_detail, name='post_detail'),
    path('san-pham/<int:pk>/yeu-thich/', views.toggle_favorite, name='toggle_favorite'),
    path('san-pham/<int:pk>/bao-cao/', views.report_post, name='report_post'),
    path('san-pham/<int:pk>/binh-luan/', views.add_comment, name='add_comment'),
    path('binh-luan/<int:pk>/xoa/', views.delete_comment, name='delete_comment'),

    # --- Quản lý bài đăng ---
    path('dang-tin/', views.create_post, name='create_post'),
    path('tin-cua-toi/', views.my_posts, name='my_posts'),
    path('tin-cua-toi/yeu-thich/', views.wishlist, name='wishlist'),
    path('san-pham/<int:pk>/sua/', views.edit_post, name='edit_post'),
    path('san-pham/<int:pk>/xoa/', views.delete_post, name='delete_post'),
    path('san-pham/<int:pk>/doi-trang-thai/', views.toggle_sold, name='toggle_sold'),
    path('san-pham/<int:pk>/them-anh/', views.upload_post_image, name='upload_post_image'),
    path('anh-san-pham/<int:pk>/xoa/', views.delete_post_image, name='delete_post_image'),

    # --- Hồ sơ người dùng ---
    path('nguoi-dung/<str:username>/', views.user_profile, name='user_profile'),
    path('nguoi-dung/<str:username>/danh-gia/', views.add_review, name='add_review'),
    path('tai-khoan/', views.edit_profile, name='edit_profile'),
    path('tai-khoan/doi-mat-khau/', views.change_password, name='change_password'),

    # --- Xác thực ---
    path('dang-ky/', views.register, name='register'),
    path('dang-nhap/', views.user_login, name='login'),
    path('dang-xuat/', views.logout_view, name='logout'),
]
