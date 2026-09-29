from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Category, Post, Comment, Review

# Tùy chỉnh tiêu đề hiển thị trên trang Admin
admin.site.site_header = "HỆ THỐNG QUẢN TRỊ SÁCHGÓC UNI"
admin.site.site_title = "Admin SáchGócUni"
admin.site.index_title = "Bảng điều khiển & Quản trị hệ thống"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'category', 'price', 'is_free', 'is_sold', 'created_at')
    list_filter = ('category', 'is_sold', 'is_free', 'condition', 'created_at')
    search_fields = ('title', 'course_code', 'faculty', 'seller__username')
    list_editable = ('is_sold', 'is_free')
    date_hierarchy = 'created_at'

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post', 'created_at')
    search_fields = ('author__username', 'content', 'post__title')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'seller', 'reviewer', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('seller__username', 'reviewer__username', 'comment')

# Tùy chỉnh Quản lý Người dùng (Khóa / Mở khóa tài khoản)
admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    actions = ['deactivate_users', 'activate_users']

    @admin.action(description='🔒 Khóa tài khoản đã chọn')
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description='🔓 Mở khóa tài khoản đã chọn')
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)