"""
Tín hiệu (signals) của Django.

Tự động tạo Profile mỗi khi có tài khoản User, đảm bảo `user.profile`
luôn tồn tại và không bao giờ gây lỗi AttributeError.
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """
    Đảm bảo mỗi tài khoản đều có hồ sơ.

    Dùng get_or_create thay vì chỉ xử lý created=True, vì tài khoản tạo từ
    trước (nâng cấp database, createsuperuser) cũng cần được bù hồ sơ.
    """
    Profile.objects.get_or_create(user=instance)
