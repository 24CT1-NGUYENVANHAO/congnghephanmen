"""Quy tắc phân quyền dùng chung cho view và context processor.

Quy ước: is_staff luôn thắng role. Moderator là tài khoản riêng, chỉ kiểm duyệt.
"""

from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .models import Profile


def is_moderator(user):
    """Đúng khi hồ sơ có role MODERATOR (không xét is_staff)."""
    return (
        user.is_authenticated
        and getattr(getattr(user, 'profile', None), 'role', None)
        == Profile.Role.MODERATOR
    )


def can_moderate(user):
    """Admin hoặc Moderator — người được vào khu kiểm duyệt."""
    return user.is_authenticated and (user.is_staff or is_moderator(user))


def _login_redirect(request):
    return redirect(
        f"{reverse(settings.LOGIN_URL)}?next={quote(request.get_full_path())}"
    )


def moderator_required(view):
    """Chặn người không phải Admin/Moderator khỏi khu kiểm duyệt."""
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _login_redirect(request)
        if not can_moderate(request.user):
            messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
            return redirect('home')
        return view(request, *args, **kwargs)
    return _wrapped


def student_required(view):
    """Chặn Moderator khỏi chức năng của sinh viên; Admin vẫn được."""
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _login_redirect(request)
        if is_moderator(request.user) and not request.user.is_staff:
            messages.error(
                request,
                "Tài khoản kiểm duyệt viên không thực hiện được chức năng này.",
            )
            return redirect('home')
        return view(request, *args, **kwargs)
    return _wrapped
