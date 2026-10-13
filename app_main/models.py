"""
Mô hình dữ liệu (Django ORM) cho hệ thống SáchGóc Uni.

Thiết kế mô hình:
  - Category  : danh mục sản phẩm (giao trình, dụng cụ, thiết bị...)
  - Post      : bài đăng bán / tặng, thuộc 1 Category, do 1 User đăng
  - PostImage : nhiều ảnh cho 1 Post (quan hệ 1-n)
  - Comment   : bình luận hỏi đáp dưới Post, hỗ trợ trả lời lồng nhau
  - Review    : đánh giá uy tín người bán (1-5 sao) sau khi giao dịch
  - Favorite  : quan hệ yêu thích (Wishlist) giữa User và Post
  - Report    : báo cáo vi phạm bài đăng để Admin kiểm duyệt

Toàn bộ dữ liệu được lưu trữ qua ORM vào MySQL hoặc SQLite tuỳ cấu hình .env
"""

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


# ---------------------------------------------------------------------------
#  DANH MỤC
# ---------------------------------------------------------------------------

class Category(models.Model):
    """Danh mục phân loại sản phẩm, ví dụ: Giáo trình, Dụng cụ học tập..."""

    name = models.CharField(max_length=100, verbose_name="Tên danh mục")
    slug = models.SlugField(unique=True, verbose_name="Đường dẫn")
    icon = models.CharField(
        max_length=10, blank=True, default="📦",
        verbose_name="Biểu tượng",
        help_text="Emoji đại diện, ví dụ 📚 🔧 💻"
    )
    description = models.TextField(blank=True, verbose_name="Mô tả ngắn")
    order = models.PositiveIntegerField(
        default=0, verbose_name="Thứ tự hiển thị",
        help_text="Số nhỏ sẽ hiển thị trước"
    )

    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f"{reverse('home')}?cat={self.pk}"

    @property
    def active_post_count(self):
        """Số bài đăng còn hiện trong danh mục này."""
        return self.posts.filter(status=Post.Status.ACTIVE).count()


# ---------------------------------------------------------------------------
#  HỒ SƠ SINH VIÊN (mở rộng cho User)
# ---------------------------------------------------------------------------

class Profile(models.Model):
    """
    Hồ sơ mở rộng cho tài khoản User.

    Giữ thông tin riêng tư và sinh viên tách khỏi bảng auth_user chuẩn,
    đồng thời tính sẵn điểm uy tín & số tin đang bán cho giao diện.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile', verbose_name="Tài khoản"
    )
    student_id = models.CharField(
        max_length=20, blank=True, verbose_name="Mã sinh viên"
    )
    faculty = models.CharField(
        max_length=100, blank=True, verbose_name="Khoa / Ngành"
    )
    phone = models.CharField(
        max_length=15, blank=True, verbose_name="Số điện thoại"
    )
    bio = models.TextField(
        max_length=500, blank=True, verbose_name="Giới thiệu bản thân"
    )
    avatar = models.ImageField(
        upload_to='avatars/', blank=True, null=True, verbose_name="Ảnh đại diện"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        verbose_name = "Hồ sơ sinh viên"
        verbose_name_plural = "Hồ sơ sinh viên"

    def __str__(self):
        return f"Hồ sơ {self.user.username}"

    @property
    def display_name(self):
        """Tên hiển thị: ưu tiên họ tên đầy đủ, fallback về username."""
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.username

    @property
    def average_rating(self):
        """Điểm đánh giá trung bình nhận được (None nếu chưa có đánh giá)."""
        return self.user.reviews_received.aggregate(
            average=models.Avg('rating')
        )['average']

    @property
    def total_reviews(self):
        """Tổng số lượt đánh giá nhận được."""
        return self.user.reviews_received.count()

    @property
    def total_sold(self):
        """Số sản phẩm đã bán / đã tặng thành công."""
        return self.user.posts.filter(status=Post.Status.SOLD).count()

    @property
    def total_active_posts(self):
        """Số sản phẩm đang hiển thị trên sàn."""
        return self.user.posts.filter(status=Post.Status.ACTIVE).count()


# ---------------------------------------------------------------------------
#  BÀI ĐĂNG
# ---------------------------------------------------------------------------

def post_image_path(instance, filename):
    """
    Đường dẫn lưu ảnh: posts/<user_id>/<timestamp>_<tên file gốc>.

    Gom theo user giúp dễ quản lý, thêm timestamp để tránh trùng tên file.
    """
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    return f"posts/user_{instance.post.seller_id}/{timezone.now():%Y%m%d_%H%M%S}.{extension}"


class PostQuerySet(models.QuerySet):
    """QuerySet tùy chỉnh để tái sử dụng điều kiện lọc bài đăng."""

    def active(self):
        """Chỉ lấy bài đăng đang hoạt động và đã được duyệt."""
        return self.filter(status=Post.Status.ACTIVE)

    def with_related(self):
        """Tối ưu truy vấn: lấy kèm seller, category, ảnh đầu, số bình luận."""
        return self.select_related('seller', 'category').prefetch_related(
            'images', 'comments'
        )

    def free_items(self):
        """Bài đăng tặng miễn phí 0đ."""
        return self.filter(is_free=True)


class Post(models.Model):
    """Bài đăng trao đổi: bán giáo trình, dụng cụ hoặc tặng miễn phí 0đ."""

    class Condition(models.TextChoices):
        NEW = 'NEW', 'Mới 100%'
        LIKE_NEW = 'LIKE_NEW', 'Như mới 90-99%'
        GOOD = 'GOOD', 'Tốt 70-89%'
        USED = 'USED', 'Cũ dưới 70%'

    class Status(models.TextChoices):
        """Vòng đời của một bài đăng."""
        PENDING = 'PENDING', 'Chờ duyệt'
        ACTIVE = 'ACTIVE', 'Đang hiển thị'
        SOLD = 'SOLD', 'Đã bán / Đã tặng'
        REJECTED = 'REJECTED', 'Bị từ chối'
        HIDDEN = 'HIDDEN', 'Người đăng ẩn'

    # --- Thông tin cơ bản ---
    title = models.CharField(max_length=200, verbose_name="Tiêu đề")
    slug = models.SlugField(max_length=220, unique=True, blank=True, verbose_name="Đường dẫn")
    description = models.TextField(verbose_name="Mô tả chi tiết")

    # --- Liên kết ---
    seller = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='posts',
        verbose_name="Người đăng"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='posts', verbose_name="Danh mục"
    )

    # --- Chi tiết học thuật (tùy chọn) ---
    course_code = models.CharField(
        max_length=50, blank=True, verbose_name="Mã học phần",
        help_text="Ví dụ: IT001, ARCH203"
    )
    faculty = models.CharField(
        max_length=100, blank=True, verbose_name="Khoa / Ngành",
        help_text="Ví dụ: Khoa Kiến trúc, Khoa CNTT"
    )

    # --- Giá & tình trạng ---
    price = models.DecimalField(
        max_digits=10, decimal_places=0, default=0, verbose_name="Giá bán (VNĐ)"
    )
    is_free = models.BooleanField(default=False, verbose_name="Tặng miễn phí (0đ)")
    condition = models.CharField(
        max_length=20, choices=Condition.choices,
        default=Condition.GOOD, verbose_name="Tình trạng"
    )

    # --- Địa điểm giao dịch ---
    location = models.CharField(
        max_length=120, blank=True,
        verbose_name="Khu vực giao dịch",
        help_text="Ví dụ: KTX A, Căn cứ Mỹ Đức, Khu 3"
    )

    # --- Ảnh ---
    image = models.ImageField(
        upload_to='posts/', blank=True, null=True,
        verbose_name="Ảnh đại diện"
    )

    # --- Trạng thái & kiểm duyệt ---
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE,
        db_index=True, verbose_name="Trạng thái"
    )
    is_sold = models.BooleanField(
        default=False, verbose_name="Đã bán",
        help_text="Cờ nhanh, đồng bộ với trạng thái SOLD"
    )
    rejection_reason = models.CharField(
        max_length=255, blank=True, verbose_name="Lý do từ chối"
    )

    # --- Tương tác ---
    wishlist = models.ManyToManyField(
        User, through='Favorite', related_name='favorite_posts', blank=True,
        verbose_name="Lượt yêu thích"
    )
    view_count = models.PositiveIntegerField(default=0, verbose_name="Lượt xem")

    # --- Thời gian ---
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Ngày đăng")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    objects = PostQuerySet.as_manager()

    class Meta:
        verbose_name = "Bài đăng"
        verbose_name_plural = "Bài đăng"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('post_detail', args=[self.pk])

    def save(self, *args, **kwargs):
        """Tự sinh slug và đồng bộ cờ is_sold với status."""
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.title)[:200] or 'bai-dang'
            slug, index = base, 2
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{index}"
                index += 1
            self.slug = slug

        # Giá bằng 0 thì coi như tặng miễn phí
        if self.price == 0:
            self.is_free = True

        # Đồng bộ hai cờ trạng thái
        if self.status == self.Status.SOLD:
            self.is_sold = True
        elif self.is_sold:
            self.status = self.Status.SOLD

        super().save(*args, **kwargs)

    # --- Thuộc tính hiển thị ---

    @property
    def price_display(self):
        """Giá hiển thị: 'Miễn phí' nếu tặng, ngược lại định dạng có dấu phân cách."""
        if self.is_free or self.price == 0:
            return "Miễn phí"
        return f"{int(self.price):,}đ".replace(",", ".")

    @property
    def is_available(self):
        """Bài còn giao dịch được không."""
        return self.status == self.Status.ACTIVE and not self.is_sold

    @property
    def main_image(self):
        """Ảnh đại diện: ưu tiên ảnh chính, lấy ảnh đầu tiên, cuối cùng là None."""
        if self.image:
            return self.image
        first = self.images.first()
        return first.image if first else None

    @property
    def gallery(self):
        """Danh sách ảnh hiển thị ở trang chi tiết."""
        photos = [self.image] if self.image else []
        photos += [img.image for img in self.images.all()]
        return photos

    def get_absolute_image_url(self):
        """URL ảnh, hoặc None nếu bài đăng chưa có ảnh nào."""
        image = self.main_image
        return image.url if image else None

    def increment_view(self):
        """Tăng lượt xem mà không tốn 1 lần UPDATE nặng."""
        Post.objects.filter(pk=self.pk).update(view_count=models.F('view_count') + 1)

    def seller_rating(self):
        """Điểm đánh giá trung bình của người bán (None nếu chưa có đánh giá)."""
        aggregate = self.seller.reviews_received.aggregate(
            average=models.Avg('rating')
        )
        return aggregate['average']

    def seller_review_count(self):
        """Tổng số đánh giá của người bán."""
        return self.seller.reviews_received.count()


class PostImage(models.Model):
    """Ảnh phụ của bài đăng (mỗi bài tối đa 5 ảnh)."""

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='images', verbose_name="Bài đăng"
    )
    image = models.ImageField(upload_to=post_image_path, verbose_name="Ảnh")
    order = models.PositiveIntegerField(default=0, verbose_name="Thứ tự")

    class Meta:
        verbose_name = "Ảnh sản phẩm"
        verbose_name_plural = "Ảnh sản phẩm"
        ordering = ['order', 'id']

    def __str__(self):
        return f"Ảnh {self.order + 1} - {self.post.title[:30]}"


# ---------------------------------------------------------------------------
#  TƯƠNG TÁC: YÊU THÍCH & BÌNH LUẬN
# ---------------------------------------------------------------------------

class Favorite(models.Model):
    """
    Bảng nối lưu sản phẩm yêu thích.

    Dùng bảng nối thay vì ManyToManyField trực tiếp để có thêm
    thời điểm yêu thích (created_at) cho mục "Yêu thích gần đây".
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites', verbose_name="Người dùng"
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='favorited_by', verbose_name="Bài đăng"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời điểm")

    class Meta:
        verbose_name = "Yêu thích"
        verbose_name_plural = "Yêu thích"
        ordering = ['-created_at']
        # Một người chỉ yêu thích một bài đăng duy nhất
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'post'], name='unique_favorite_per_user'
            )
        ]

    def __str__(self):
        return f"{self.user.username} ♥ {self.post.title[:30]}"


class Comment(models.Model):
    """Bình luận hỏi đáp dưới bài đăng, hỗ trợ trả lời lồng nhau 1 cấp."""

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='comments', verbose_name="Bài đăng"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='comments', verbose_name="Người viết"
    )
    content = models.TextField(max_length=1000, verbose_name="Nội dung")
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='replies', verbose_name="Trả lời"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        verbose_name = "Bình luận"
        verbose_name_plural = "Bình luận"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username}: {self.content[:40]}"

    @property
    def is_reply(self):
        return self.parent_id is not None


# ---------------------------------------------------------------------------
#  ĐÁNH GIÁ UY TÍN
# ---------------------------------------------------------------------------

class Review(models.Model):
    """Đánh giá uy tín người bán (1-5 sao) sau khi hoàn tất giao dịch."""

    seller = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviews_received',
        verbose_name="Người được đánh giá"
    )
    reviewer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviews_given',
        verbose_name="Người đánh giá"
    )
    post = models.ForeignKey(
        Post, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviews', verbose_name="Sản phẩm liên quan"
    )
    rating = models.PositiveSmallIntegerField(
        default=5, verbose_name="Số sao",
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    content = models.TextField(max_length=500, blank=True, verbose_name="Nhận xét")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        verbose_name = "Đánh giá"
        verbose_name_plural = "Đánh giá"
        ordering = ['-created_at']
        constraints = [
            # Mỗi người chỉ đánh giá 1 người bán 1 lần
            models.UniqueConstraint(
                fields=['seller', 'reviewer'], name='unique_review_per_seller'
            )
        ]

    def __str__(self):
        return f"{self.reviewer.username} → {self.seller.username} ({self.rating}★)"

    @property
    def stars(self):
        """Danh sách 5 sao để vẽ giao diện: 5 = đủ, 3 = 3 sao vàng + 2 xám."""
        return [1] * self.rating + [0] * (5 - self.rating)


# ---------------------------------------------------------------------------
#  BÁO CÁO VI PHẠM
# ---------------------------------------------------------------------------

class Report(models.Model):
    """Báo cáo bài đăng vi phạm để Admin kiểm duyệt."""

    class Reason(models.TextChoices):
        SPAM = 'SPAM', 'Quảng cáo / spam'
        FAKE = 'FAKE', 'Thông tin sai lệch / lừa đảo'
        INAPPROPRIATE = 'INAPPROPRIATE', 'Nội dung không phù hợp'
        DUPLICATE = 'DUPLICATE', 'Đăng trùng lặp'
        OTHER = 'OTHER', 'Vấn đề khác'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ xử lý'
        RESOLVED = 'RESOLVED', 'Đã xử lý'
        DISMISSED = 'DISMISSED', 'Bỏ qua'

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='reports', verbose_name="Bài đăng"
    )
    reporter = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reports_made',
        verbose_name="Người báo cáo"
    )
    reason = models.CharField(
        max_length=20, choices=Reason.choices, default=Reason.OTHER, verbose_name="Lý do"
    )
    detail = models.TextField(max_length=500, blank=True, verbose_name="Chi tiết")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
        db_index=True, verbose_name="Trạng thái"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        verbose_name = "Báo cáo vi phạm"
        verbose_name_plural = "Báo cáo vi phạm"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reporter.username} báo cáo: {self.post.title[:30]}"


# ---------------------------------------------------------------------------
#  ĐẶT MUA — ĐƠN HÀNG
# ---------------------------------------------------------------------------

class Order(models.Model):
    """
    Đơn đặt mua sản phẩm.

    Luồng xử lý: người mua gửi yêu cầu → người bán xác nhận hoặc từ chối →
    giao dịch hoàn tất. Mỗi người mua chỉ được gửi 1 yêu cầu còn mở cho
    mỗi sản phẩm.

    Ràng buộc "1 đơn mở / 1 sản phẩm / 1 người mua" được kiểm tra trong
    view buy_post chứ không dùng UniqueConstraint có điều kiện, vì MySQL
    không hỗ trợ partial index (chỉ SQLite/PostgreSQL mới có).
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ xác nhận'
        CONFIRMED = 'CONFIRMED', 'Đã xác nhận'
        COMPLETED = 'COMPLETED', 'Hoàn tất'
        REJECTED = 'REJECTED', 'Từ chối'
        CANCELLED = 'CANCELLED', 'Đã huỷ'

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='orders',
        verbose_name="Sản phẩm"
    )
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders_made',
        verbose_name="Người mua"
    )
    seller = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='orders_received',
        verbose_name="Người bán"
    )

    # Giá chốt tại thời điểm đặt mua, tránh giá thay đổi sau đó
    price_snapshot = models.DecimalField(
        max_digits=10, decimal_places=0, default=0, verbose_name="Giá chốt (VNĐ)"
    )

    message = models.TextField(
        max_length=500, blank=True, verbose_name="Lời nhắn cho người bán"
    )
    contact = models.CharField(
        max_length=120, blank=True, verbose_name="Thông tin liên hệ"
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
        db_index=True, verbose_name="Trạng thái"
    )
    seller_note = models.CharField(
        max_length=300, blank=True, verbose_name="Ghi chú của người bán"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian đặt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật")

    class Meta:
        verbose_name = "Đơn đặt mua"
        verbose_name_plural = "Đơn đặt mua"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', 'status'], name='idx_order_buyer_status'),
            models.Index(fields=['seller', 'status'], name='idx_order_seller_status'),
        ]

    def __str__(self):
        return f"#{self.pk} {self.buyer.username} → {self.post.title[:25]}"

    @property
    def is_open(self):
        """Đơn còn chờ xử lý (chưa bị từ chối/huỷ/hoàn tất)."""
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)

    @property
    def price_display(self):
        if self.price_snapshot == 0:
            return "Miễn phí"
        return f"{int(self.price_snapshot):,}đ".replace(",", ".")
