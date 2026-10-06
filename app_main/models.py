from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    """Mô hình danh mục phân loại đồ dùng, sách giáo trình."""
    name = models.CharField(max_length=100, verbose_name="Tên danh mục")
    slug = models.SlugField(unique=True, verbose_name="Đường dẫn (Slug)")

    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "1. Danh mục sản phẩm"

    def __str__(self):
        return self.name

class Post(models.Model):
    """Mô hình bài đăng trao đổi, mua bán hoặc tặng 0đ sách và đồ dùng học tập."""
    CONDITION_CHOICES = [
        ('NEW', 'Mới (100%)'),
        ('LIKE_NEW', 'Như mới (90-99%)'),
        ('GOOD', 'Tốt (70-89%)'),
        ('USED', 'Cũ (Dưới 70%)'),
    ]

    title = models.CharField(max_length=200, verbose_name="Tiêu đề")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name="Người đăng")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name="Danh mục")
    course_code = models.CharField(max_length=50, blank=True, verbose_name="Mã học phần / Tên môn")
    faculty = models.CharField(max_length=100, blank=True, verbose_name="Khoa / Ngành")
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Giá bán (VNĐ)")
    is_free = models.BooleanField(default=False, verbose_name="Tặng miễn phí (0đ)")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='GOOD', verbose_name="Tình trạng")
    description = models.TextField(verbose_name="Mô tả chi tiết")
    
    # Đã thay đổi từ URLField sang ImageField
    image = models.ImageField(upload_to='posts/', blank=True, null=True, verbose_name="Ảnh sản phẩm")
    
    is_sold = models.BooleanField(default=False, verbose_name="Đã bán")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đăng")
    wishlist = models.ManyToManyField(User, related_name='favorite_posts', blank=True, verbose_name="Lượt yêu thích")

    class Meta:
        verbose_name = "Bài đăng"
        verbose_name_plural = "2. Quản lý bài đăng"

    def __str__(self):
        return self.title

class Comment(models.Model):
    """Mô hình lưu trữ bình luận, trao đổi giữa sinh viên trên từng bài đăng."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="Bài đăng")
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Người bình luận")
    content = models.TextField(verbose_name="Nội dung")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        verbose_name = "Bình luận"
        verbose_name_plural = "3. Quản lý bình luận"

    def __str__(self):
        return f"{self.author.username} - {self.post.title[:20]}"

class Review(models.Model):
    """Mô hình đánh giá uy tín người bán (1-5 sao) sau khi hoàn tất giao dịch."""
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received', verbose_name="Người bán")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given', verbose_name="Người đánh giá")
    rating = models.IntegerField(default=5, verbose_name="Số sao")
    comment = models.TextField(verbose_name="Nội dung đánh giá")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        verbose_name = "Đánh giá"
        verbose_name_plural = "4. Đánh giá uy tín"

    def __str__(self):
        return f"{self.reviewer.username} -> {self.seller.username} ({self.rating} sao)"