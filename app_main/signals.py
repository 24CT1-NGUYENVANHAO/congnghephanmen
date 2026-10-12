"""
Tín hiệu (signals) của Django.

Tự động tạo Profile mỗi khi có tài khoản User mới, đảm bảo
`user.profile` luôn tồn tại và không bao giờ gây lỗi AttributeError.
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Tạo hồ sơ sinh viên ngay khi đăng ký tài khoản mới."""
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    """Đảm bảo hồ sơ tồn tại kể cả khi user được tạo qua admin/shell."""
    Profile.objects.get_or_create(user=instance)
