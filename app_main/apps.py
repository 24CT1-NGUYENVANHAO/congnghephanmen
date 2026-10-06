from django.apps import AppConfig


class AppMainConfig(AppConfig):
    """Cấu hình ứng dụng app_main cho hệ thống SáchGóc Uni."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_main'
    verbose_name = 'SáchGóc Uni - Sàn Giao Dịch Sinh Viên'

