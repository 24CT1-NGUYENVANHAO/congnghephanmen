"""Quy tắc miền email dùng chung cho đăng ký và đăng nhập.

Sinh viên tự đăng ký bằng Gmail; tài khoản giảng viên / kiểm duyệt viên do
quản trị viên tạo có thể dùng email trường ``*.edu.vn``. Hai danh sách miền
nằm ở đúng một chỗ để form đăng ký và view đăng nhập không bị lệch nhau.
"""

from django.core.exceptions import ValidationError

#: Miền email chính xác được chấp nhận (dùng cho cả đăng ký và đăng nhập).
ALLOWED_EMAIL_DOMAINS = ('gmail.com',)

#: Đuôi email trường được chấp nhận khi đăng nhập (tài khoản do quản trị cấp).
ALLOWED_LOGIN_EMAIL_SUFFIXES = ('.edu.vn',)


def _domain_of(value):
    """Trả về phần miền đã chuẩn hoá, hoặc chuỗi rỗng nếu email không hợp lệ."""
    value = (value or '').strip().lower()
    if '@' not in value:
        return ''
    return value.rsplit('@', 1)[1]


def is_allowed_login_email(value):
    """Email đăng nhập: Gmail hoặc email trường ``*.edu.vn``."""
    domain = _domain_of(value)
    if not domain:
        return False
    return (
        domain in ALLOWED_EMAIL_DOMAINS
        or domain.endswith(ALLOWED_LOGIN_EMAIL_SUFFIXES)
    )


def is_allowed_registration_email(value):
    """Email tự đăng ký: chỉ Gmail (email trường do quản trị viên cấp)."""
    return _domain_of(value) in ALLOWED_EMAIL_DOMAINS


def validate_registration_email(value):
    """Ném ValidationError nếu email không dùng được để tự đăng ký."""
    if not is_allowed_registration_email(value):
        raise ValidationError("Chỉ chấp nhận địa chỉ email @gmail.com.")
    return value
