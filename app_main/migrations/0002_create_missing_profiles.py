"""
Tạo hồ sơ cho các tài khoản User đang tồn tại nhưng chưa có Profile.

Vì sao cần?
------------
Signal `post_save` chỉ tạo Profile cho tài khoản MỚI. Những tài khoản đã có
sẵn trong database (ví dụ khi nâng cấp từ phiên bản cũ, hoặc tạo bằng
`createsuperuser`) sẽ không có hồ sơ, dẫn đến lỗi:

    User has no profile.

Migration này bù lại phần thiếu cho mọi tài khoản hiện có.
"""

from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    """Tạo Profile cho mọi User chưa có."""
    User = apps.get_model('auth', 'User')
    Profile = apps.get_model('app_main', 'Profile')

    existing_ids = set(Profile.objects.values_list('user_id', flat=True))
    missing = [u.id for u in User.objects.all() if u.id not in existing_ids]

    if missing:
        Profile.objects.bulk_create(
            [Profile(user_id=user_id) for user_id in missing]
        )


def remove_orphans(apps, schema_editor):
    """Đảo ngược: xoá hồ sơ không gắn với tài khoản nào (nếu có)."""
    Profile = apps.get_model('app_main', 'Profile')
    Profile.objects.filter(user_id__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app_main', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_missing_profiles, remove_orphans),
    ]
