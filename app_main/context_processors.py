"""
Context processor dùng chung cho mọi template.

Cung cấp biến: danh mục (điều hướng), số thông báo chưa đọc, số bài đang bán...
giúp template không phải query lặp lại ở mỗi trang.
"""

from .models import Category, Report


def site_context(request):
    """Biến dùng chung có sẵn trong mọi template."""
    return {
        # Danh mục cho thanh điều hướng (chỉ lấy danh mục có bài đăng)
        'nav_categories': Category.objects.all()[:8],
        # Số báo cáo chờ xử lý (dành cho Admin)
        'pending_reports': (
            Report.objects.filter(status=Report.Status.PENDING).count()
            if request.user.is_authenticated and request.user.is_staff else 0
        ),
    }
