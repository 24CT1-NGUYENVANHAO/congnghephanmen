from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/buy/', views.buy_post, name='buy_post'), # Thêm dòng này
    path('post/create/', views.create_post, name='create_post'),
    path('my-posts/', views.my_posts, name='my_posts'),
    path('post/<int:pk>/toggle-sold/', views.toggle_sold, name='toggle_sold'),
    path('post/<int:pk>/wishlist/', views.toggle_wishlist, name='toggle_wishlist'),
    path('accounts/register/', views.register, name='register'),
]