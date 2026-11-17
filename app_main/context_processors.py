"""
Context processor dùng chung cho mọi template.

Cung cấp biến: danh mục (điều hướng), số báo cáo chờ xử lý (cho Admin/
Kiểm duyệt viên) và tổng số việc đang chờ (bài đăng + báo cáo + phiên
hỗ trợ) — giúp template không phải query lặp lại ở mỗi trang.
"""

from .models import Category, Post, Report, SupportTicket
from .permissions import can_moderate


def site_context(request):
    """Biến dùng chung có sẵn trong mọi template."""
    is_mod = can_moderate(request.user)
    open_ticket_states = (
        SupportTicket.Status.OPEN,
        SupportTicket.Status.IN_PROGRESS,
    )
    if is_mod:
        pending_posts = Post.objects.filter(status=Post.Status.PENDING).count()
        pending_reports = Report.objects.filter(status=Report.Status.PENDING).count()
        open_tickets = SupportTicket.objects.filter(
            status__in=open_ticket_states
        ).count()
    else:
        pending_posts = pending_reports = open_tickets = 0
    return {
        # Danh mục cho thanh điều hướng (chỉ lấy danh mục có bài đăng)
        'nav_categories': Category.objects.all()[:8],
        # Số báo cáo chờ xử lý (dành cho Moderator/Admin)
        'pending_reports': pending_reports,
        # Tổng số việc chờ xử lý (bài đăng + báo cáo + phiên hỗ trợ)
        'pending_total': pending_posts + pending_reports + open_tickets,
    }
