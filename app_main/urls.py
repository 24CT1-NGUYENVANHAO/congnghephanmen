"""
Cấu hình định tuyến URL cho ứng dụng app_main (SáchGóc Uni).
Bao gồm các endpoint: Trang chủ, Chi tiết bài viết, Mua/nhận đồ, Đăng bài, Quản lý bài đăng cá nhân, Yêu thích và Đăng ký.
"""

from django.urls import path
from . import views

urlpatterns = [
    # 1. Trang chủ & Tìm kiếm
    path('', views.home, name='home'),
    
    # 2. Chi tiết sản phẩm, Mua hàng & Tương tác
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/buy/', views.buy_post, name='buy_post'),
    path('post/<int:pk>/wishlist/', views.toggle_wishlist, name='toggle_wishlist'),
    
    # 3. Quản lý bài đăng
    path('post/create/', views.create_post, name='create_post'),
    path('my-posts/', views.my_posts, name='my_posts'),
    path('post/<int:pk>/toggle-sold/', views.toggle_sold, name='toggle_sold'),
    
    # 4. Tài khoản người dùng
    path('accounts/register/', views.register, name='register'),
]