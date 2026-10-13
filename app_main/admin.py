"""
Trang quản trị Django cho SáchGóc Uni.

Cung cấp chức năng kiểm duyệt bài đăng, duyệt báo cáo vi phạm,
xem thống kê và khóa/mở khóa tài khoản sinh viên.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from django.utils.html import format_html

from .models import (
    Category, Comment, Favorite, Order, Post, PostImage, Profile, Report, Review,
)


# ---------------------------------------------------------------------------
#  INLINE
# ---------------------------------------------------------------------------

class PostImageInline(admin.TabularInline):
    """Cho phép thêm/xoá nhiều ảnh phụ ngay trong trang sửa bài đăng."""
    model = PostImage
    extra = 1
    fields = ['image', 'order']


class CommentInline(admin.TabularInline):
    """Xem bình luận ngay trong trang bài đăng."""
    model = Comment
    extra = 0
    fields = ['author', 'content', 'created_at']
    readonly_fields = ['author', 'created_at']
    max_num = 20


# ---------------------------------------------------------------------------
#  CATEGORY
# ---------------------------------------------------------------------------

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'icon', 'name', 'slug', 'total_posts', 'created_display')
    list_editable = ('icon',)
    list_display_links = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    ordering = ('order', 'name')

    @admin.display(description="Số bài đăng")
    def total_posts(self, obj):
        return obj.posts.count()

    @admin.display(description="Biểu tượng")
    def created_display(self, obj):
        return obj.icon


# ---------------------------------------------------------------------------
#  POST
# ---------------------------------------------------------------------------

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title_display', 'seller', 'category', 'price_display',
        'condition', 'status', 'view_count', 'created_at'
    )
    list_filter = ('status', 'is_free', 'condition', 'category', 'created_at')
    search_fields = ('title', 'description', 'course_code', 'faculty', 'seller__username')
    readonly_fields = ('view_count', 'created_at', 'updated_at', 'slug')
    list_display_links = ('title_display',)
    date_hierarchy = 'created_at'
    inlines = [PostImageInline, CommentInline]
    actions = ['approve_posts', 'hide_posts', 'mark_sold', 'feature_posts']
    list_per_page = 25

    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('title', 'description', 'category', 'seller')
        }),
        ('Giá & Tình trạng', {
            'fields': ('price', 'is_free', 'condition', 'status', 'rejection_reason')
        }),
        ('Thông tin học thuật', {
            'classes': ('collapse',),
            'fields': ('course_code', 'faculty', 'location')
        }),
        ('Ảnh & Thống kê', {
            'classes': ('collapse',),
            'fields': ('image', 'view_count', 'slug', 'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('seller', 'category')

    @admin.display(description="Tiêu đề", ordering='title')
    def title_display(self, obj):
        thumb = format_html(
            '<img src="{}" style="width:40px;height:40px;object-fit:cover;'
            'border-radius:6px;margin-right:8px;" />',
            obj.get_absolute_image_url() or ''
        )
        return format_html('{}{}', thumb, obj.title[:60])

    @admin.display(description="Giá", ordering='price')
    def price_display(self, obj):
        return "Miễn phí" if obj.is_free or obj.price == 0 else f"{int(obj.price):,}đ"

    @admin.display(description="Trạng thái", ordering='status')
    def status_badge(self, obj):
        colors = {
            'ACTIVE': ('#10b981', 'Đang hiển thị'),
            'PENDING': ('#f59e0b', 'Chờ duyệt'),
            'SOLD': ('#6b7280', 'Đã bán'),
            'REJECTED': ('#ef4444', 'Từ chối'),
            'HIDDEN': ('#64748b', 'Đã ẩn'),
        }
        color, label = colors.get(obj.status, ('#6b7280', obj.status))
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:bold;">{}</span>',
            color, label
        )

    # --- Hành động kiểm duyệt hàng loạt ---
    @admin.action(description="✅ Duyệt hiển thị")
    def approve_posts(self, request, queryset):
        updated = queryset.update(status=Post.Status.ACTIVE, rejection_reason='')
        self.message_user(request, f"Đã duyệt {updated} bài đăng.")

    @admin.action(description="🚫 Ẩn bài đăng")
    def hide_posts(self, request, queryset):
        updated = queryset.update(status=Post.Status.HIDDEN)
        self.message_user(request, f"Đã ẩn {updated} bài đăng.")

    @admin.action(description="💰 Đánh dấu đã bán")
    def mark_sold(self, request, queryset):
        updated = queryset.update(status=Post.Status.SOLD, is_sold=True)
        self.message_user(request, f"Đã đánh dấu {updated} bài đăng là đã bán.")

    @admin.action(description="⭐ Đánh dấu nổi bật (đưa lên đầu)")
    def feature_posts(self, request, queryset):
        # Bài ACTIVE được đưa lên đầu bằng cách cập nhật updated_at
        from django.utils import timezone
        updated = queryset.update(created_at=timezone.now())
        self.message_user(request, f"Đã làm nổi bật {updated} bài đăng.")


# ---------------------------------------------------------------------------
#  PROFILE
# ---------------------------------------------------------------------------

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'faculty', 'phone', 'rating_display')
    search_fields = ('user__username', 'student_id', 'faculty')
    list_filter = ('faculty',)

    @admin.display(description="Điểm uy tín")
    def rating_display(self, obj):
        average = obj.average_rating
        return f"⭐ {average:.1f}/5 ({obj.total_reviews})" if average else "Chưa có đánh giá"


# ---------------------------------------------------------------------------
#  TƯƠNG TÁC
# ---------------------------------------------------------------------------

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post_title', 'content_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__username', 'post__title')
    readonly_fields = ('post', 'author', 'content', 'created_at')
    date_hierarchy = 'created_at'

    @admin.display(description="Bài đăng")
    def post_title(self, obj):
        return obj.post.title[:50]

    @admin.display(description="Nội dung")
    def content_preview(self, obj):
        return obj.content[:80] + ("..." if len(obj.content) > 80 else "")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('seller', 'reviewer', 'stars_display', 'content_preview', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('seller__username', 'reviewer__username', 'content')
    date_hierarchy = 'created_at'

    @admin.display(description="Sao")
    def stars_display(self, obj):
        return "★" * obj.rating + "☆" * (5 - obj.rating)

    @admin.display(description="Nhận xét")
    def content_preview(self, obj):
        return obj.content[:60] if obj.content else "(không có nhận xét)"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'post_title', 'created_at')
    search_fields = ('user__username', 'post__title')
    list_filter = ('created_at',)

    @admin.display(description="Bài đăng")
    def post_title(self, obj):
        return obj.post.title[:50]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Bảng điều khiển xử lý báo cáo vi phạm."""

    list_display = ('id', 'post_title', 'reporter', 'reason', 'status_badge', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('post__title', 'reporter__username', 'detail')
    readonly_fields = ('post', 'reporter', 'reason', 'detail', 'created_at')
    actions = ['resolve_reports', 'dismiss_reports']
    date_hierarchy = 'created_at'

    @admin.display(description="Bài đăng bị báo cáo")
    def post_title(self, obj):
        return obj.post.title[:50]

    @admin.display(description="Trạng thái")
    def status_badge(self, obj):
        colors = {'PENDING': '#f59e0b', 'RESOLVED': '#10b981', 'DISMISSED': '#6b7280'}
        labels = {'PENDING': 'Chờ xử lý', 'RESOLVED': 'Đã xử lý', 'DISMISSED': 'Bỏ qua'}
        color = colors.get(obj.status, '#6b7280')
        label = labels.get(obj.status, obj.status)
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:bold;">{}</span>',
            color, label
        )

    @admin.action(description="✅ Đánh dấu đã xử lý")
    def resolve_reports(self, request, queryset):
        updated = queryset.update(status=Report.Status.RESOLVED)
        self.message_user(request, f"Đã xử lý {updated} báo cáo.")

    @admin.action(description="⚪ Bỏ qua báo cáo")
    def dismiss_reports(self, request, queryset):
        updated = queryset.update(status=Report.Status.DISMISSED)
        self.message_user(request, f"Đã bỏ qua {updated} báo cáo.")


# ---------------------------------------------------------------------------
#  QUẢN LÝ TÀI KHOẢN
# ---------------------------------------------------------------------------

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    fields = ('student_id', 'faculty', 'phone', 'bio', 'avatar')


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Mở rộng trang quản lý người dùng của Django."""

    list_display = (
        'username', 'email', 'full_name', 'faculty',
        'rating_display', 'post_count', 'is_staff', 'is_active', 'date_joined'
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    actions = ['deactivate_users', 'activate_users']
    inlines = [ProfileInline]

    @admin.display(description="Họ tên", ordering='first_name')
    def full_name(self, obj):
        return obj.get_full_name() or "—"

    @admin.display(description="Khoa")
    def faculty(self, obj):
        return obj.profile.faculty or "—"

    @admin.display(description="Uy tín")
    def rating_display(self, obj):
        stats = obj.reviews_received.aggregate(avg=Avg('rating'), count=Count('id'))
        if stats['count']:
            return f"⭐ {stats['avg']:.1f} ({stats['count']})"
        return "—"

    @admin.display(description="Số tin")
    def post_count(self, obj):
        return obj.posts.count()

    @admin.action(description="🔒 Khoá tài khoản đã chọn")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Đã khoá {updated} tài khoản.")

    @admin.action(description="🔓 Mở khoá tài khoản đã chọn")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Đã mở khoá {updated} tài khoản.")


# ===========================================================================
#  ĐẶT MUA - ĐƠN HÀNG
# ===========================================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Theo dõi đơn hàng giữa người mua và người bán."""

    list_display = [
        'id_short', 'post_title', 'buyer_name', 'seller_name',
        'price_display_short', 'status_badge', 'created_at',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['post__title', 'buyer__username', 'seller__username']
    autocomplete_fields = ['post', 'buyer', 'seller']
    readonly_fields = ['price_snapshot', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    list_per_page = 25
    ordering = ['-created_at']

    fieldsets = (
        ('Giao dịch', {
            'fields': ('post', 'buyer', 'seller', 'price_snapshot', 'status')
        }),
        ('Nội dung liên hệ', {
            'fields': ('message', 'contact', 'seller_note')
        }),
        ('Thông tin hệ thống', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description="Mã", ordering='id')
    def id_short(self, obj):
        return f"#{obj.pk}"

    @admin.display(description="Sản phẩm", ordering='post__title')
    def post_title(self, obj):
        return format_html('<strong>{}</strong>', obj.post.title[:60])

    @admin.display(description="Người mua", ordering='buyer__username')
    def buyer_name(self, obj):
        return obj.buyer.profile.display_name

    @admin.display(description="Người bán", ordering='seller__username')
    def seller_name(self, obj):
        return obj.seller.profile.display_name

    @admin.display(description="Giá chốt", ordering='price_snapshot')
    def price_display_short(self, obj):
        if obj.price_snapshot == 0:
            return "Miễn phí"
        return f"{int(obj.price_snapshot):,}đ".replace(",", ".")

    @admin.display(description="Trạng thái", ordering='status')
    def status_badge(self, obj):
        colors = {
            Order.Status.PENDING:   ('#92400e', '#fef3c7'),
            Order.Status.CONFIRMED: ('#1e40af', '#dbeafe'),
            Order.Status.COMPLETED: ('#14532d', '#dcfce7'),
            Order.Status.REJECTED:  ('#7f1d1d', '#fee2e2'),
            Order.Status.CANCELLED: ('#334155', '#e2e8f0'),
        }
        fg, bg = colors.get(obj.status, ('#334155', '#e2e8f0'))
        return format_html(
            '<span style="padding:3px 10px;border-radius:9999px;'
            'background:{};color:{};font-weight:600;font-size:11px;white-space:nowrap;">{}</span>',
            bg, fg, obj.get_status_display(),
        )

    @admin.action(description="✅ Đánh dấu hoàn tất + chuyển sản phẩm sang Đã bán")
    def mark_completed(self, request, queryset):
        count = 0
        for order in queryset.filter(
            status__in=[Order.Status.PENDING, Order.Status.CONFIRMED]
        ):
            order.status = Order.Status.COMPLETED
            order.save(update_fields=['status', 'updated_at'])
            order.post.status = Post.Status.SOLD
            order.post.is_sold = True
            order.post.save(update_fields=['status', 'is_sold', 'updated_at'])
            count += 1
        self.message_user(request, f"Đã hoàn tất {count} đơn hàng.")

    actions = [mark_completed]
