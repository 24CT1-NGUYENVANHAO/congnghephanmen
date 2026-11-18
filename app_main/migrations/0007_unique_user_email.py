"""Đảm bảo ``auth_user.email`` là duy nhất ở tầng cơ sở dữ liệu.

Trước đây chỉ form đăng ký chặn email trùng; dữ liệu tạo qua admin/shell vẫn
có thể trùng. Khi đó bước tra ``User.objects.filter(email__iexact=...).first()``
lúc đăng nhập sẽ chọn một tài khoản bất kỳ — rủi ro chiếm tài khoản.

MySQL/MariaDB không hỗ trợ index duy nhất trên biểu thức kèm điều kiện, nên
ta thêm một cột sinh ``email_unique`` = ``LOWER(email)`` (rỗng → NULL) rồi đặt
unique index trên cột đó. Nhiều bản ghi email rỗng vẫn hợp lệ vì MySQL cho
phép nhiều NULL trong unique index.

Dùng hai ``RunSQL`` riêng vì MariaDB không nhận nhiều câu lệnh DDL trong một
lần gọi; do đó migration phải ``atomic = False``.
"""

from django.db import migrations


ADD_COLUMN = """
ALTER TABLE auth_user
    ADD COLUMN email_unique VARCHAR(254)
    GENERATED ALWAYS AS (NULLIF(LOWER(email), '')) STORED
"""

ADD_INDEX = """
CREATE UNIQUE INDEX auth_user_email_unique ON auth_user (email_unique)
"""

DROP_INDEX = "DROP INDEX auth_user_email_unique ON auth_user"

DROP_COLUMN = "ALTER TABLE auth_user DROP COLUMN email_unique"


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('app_main', '0006_resync_post_is_sold'),
    ]

    operations = [
        migrations.RunSQL(ADD_COLUMN, reverse_sql=DROP_COLUMN),
        migrations.RunSQL(ADD_INDEX, reverse_sql=DROP_INDEX),
    ]
