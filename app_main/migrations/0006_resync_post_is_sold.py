"""Đồng bộ lại cờ ``Post.is_sold`` theo ``Post.status``.

Trước đây hai cờ có thể lệch nhau (ví dụ bài HIDDEN nhưng is_sold=True do
đoạn mã cũ tự suy ra status từ is_sold). Từ nay ``status`` là nguồn sự thật
duy nhất, nên dữ liệu cũ cần được chuẩn hoá một lần.
"""

from django.db import migrations


def resync_is_sold(apps, schema_editor):
    Post = apps.get_model('app_main', 'Post')
    # Dùng chuỗi thay vì Post.Status vì model lịch sử không mang class Status.
    Post.objects.filter(status='SOLD').update(is_sold=True)
    Post.objects.exclude(status='SOLD').update(is_sold=False)


def noop(apps, schema_editor):
    """Không thể khôi phục giá trị sai cũ — để trống khi rollback."""


class Migration(migrations.Migration):

    dependencies = [
        ('app_main', '0005_moderator_support'),
    ]

    operations = [
        migrations.RunPython(resync_is_sold, noop),
    ]
