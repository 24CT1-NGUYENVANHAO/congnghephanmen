"""
Kiểm tra nhanh: ứng dụng đang nối vào CSDL nào.

Cách chạy:  python check_db.py

Rất hữu ích khi bạn không chắc dữ liệu trên web có nằm trong MySQL hay không.
Máy có thể đang chạy CẢ HAI MySQL server (ví dụ MySQL cài riêng ở 3306 và
XAMPP ở 3307), mỗi server lại có một database cùng tên -> rất dễ nhầm.
"""

import os
import sys

# Windows mặc định cp1252, ép UTF-8 để in được tiếng Việt
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection  # noqa: E402


def _line(char='─', width=62):
    return char * width


def main():
    db = settings.DATABASES['default']

    print()
    print(_line('═'))
    print('  CẤU HÌNH CƠ SỞ DỮ LIỆU ĐANG DÙNG')
    print(_line('═'))

    # --- 1. Engine nào ---
    engine = db['ENGINE']
    print(f'\n  Engine      : {engine}')

    if 'sqlite' in engine:
        print('  ⚠️  ĐANG DÙNG SQLITE, KHÔNG PHẢI MYSQL!')
        print('      Dữ liệu bạn thấy trên web KHÔNG nằm trong MySQL.')
        print('      Sửa DB_PORT / DB_PASSWORD trong .env rồi chạy lại:')
        print('          python manage.py migrate')
        print('          python seed_data.py')
        print(f'\n  File SQLite : {db["NAME"]}')

    else:
        print(f'  Host        : {db["HOST"]}')
        print(f'  Port        : {db["PORT"]}')
        print(f'  Database    : {db["NAME"]}')
        print(f'  User        : {db["USER"]}')
        print(f'  Password    : {"(rỗng)" if not db["PASSWORD"] else "***"}')

    # --- 2. Kết nối thật được không ---
    print(f'\n{_line()}')
    print('  KIỂM TRA KẾT NỐI THẬT')
    print(_line())

    try:
        connection.ensure_connection()
    except Exception as exc:
        print(f'\n  ❌ KHÔNG kết nối được: {exc}')
        return

    with connection.cursor() as cur:
        cur.execute('SELECT VERSION()')
        version = cur.fetchone()[0]
    print(f'\n  ✅ Kết nối thành công!')
    print(f'  Phiên bản   : {version}')

    # --- 3. Bảng trong database ---
    with connection.cursor() as cur:
        if 'sqlite' in engine:
            cur.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        else:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s",
                [db['NAME']],
            )
        table_count = cur.fetchone()[0]
    print(f'  Số bảng     : {table_count}')

    if table_count == 0:
        print('\n  ⚠️  Database rỗng — chạy migrate + seed_data.py để nạp dữ liệu:')
        print('          python manage.py migrate')
        print('          python seed_data.py')

    # --- 4. Đếm dữ liệu chính ---
    print(f'\n{_line()}')
    print('  DỮ LIỆU TRONG DATABASE NÀY')
    print(_line())

    for table, label in [
        ('auth_user', 'Tài khoản'),
        ('app_main_post', 'Sản phẩm'),
        ('app_main_category', 'Danh mục'),
        ('app_main_comment', 'Bình luận'),
        ('app_main_order', 'Đơn hàng'),
    ]:
        try:
            with connection.cursor() as cur:
                cur.execute(f'SELECT COUNT(*) FROM {table}')
                print(f'  {label:<12}: {cur.fetchone()[0]}')
        except Exception:
            print(f'  {label:<12}: (chưa có bảng)')

    # --- 5. Liệt kê MySQL server nào đang chạy ---
    if 'sqlite' not in engine:
        print(f'\n{_line()}')
        print('  CÁC MYSQL SERVER ĐANG CHẠY TRÊN MÁY NÀY')
        print(_line())
        print('\n  (Mỗi server có thể có một database cùng tên)')
        print('\n  Nếu bạn thấy nhiều dòng, hãy chắc chắn app nối đúng dòng:')

        try:
            import pymysql

            host = db['HOST']
            user = db['USER']
            password = db['PASSWORD']

            for port in (3306, 3307, 3308):
                try:
                    conn = pymysql.connect(
                        host=host, port=port, user=user,
                        password=password, connect_timeout=2,
                    )
                except Exception:
                    continue

                with conn.cursor() as cur:
                    cur.execute('SELECT VERSION()')
                    ver = cur.fetchone()[0]
                    cur.execute(
                        "SELECT COUNT(*) FROM information_schema.schemata "
                        "WHERE schema_name = %s",
                        [db['NAME']],
                    )
                    has_db = cur.fetchone()[0]
                    count = None
                    if has_db:
                        try:
                            cur.execute(
                                f"SELECT COUNT(*) FROM `{db['NAME']}`.auth_user"
                            )
                            count = cur.fetchone()[0]
                        except Exception:
                            count = '?'
                conn.close()

                mark = ' ◄── APP ĐANG DÙNG' if str(port) == str(db['PORT']) else ''
                info = f'{count} user' if count is not None else 'không có DB này'
                print(f'\n  Port {port}: {ver}')
                print(f'    có "{db["NAME"]}": '
                      f'{"có" if has_db else "không"} ({info}){mark}')
        except ImportError:
            pass

    print()


if __name__ == '__main__':
    main()