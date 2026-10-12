"""
Nạp dữ liệu múi giờ (timezone) vào MySQL 8.

Vì sao cần?
------------
Khi USE_TZ = True và ModelAdmin dùng `date_hierarchy`, Django sinh truy vấn
dùng hàm TruncDate. MySQL cần các bảng:

    mysql.time_zone
    mysql.time_zone_name
    mysql.time_zone_transition_type
    mysql.time_zone_transition

...để chuyển đổi múi giờ. MySQL/XAMPP mới cài thường để trống các bảng này,
khiến trang quản trị báo lỗi:

    ValueError: Database returned an invalid datetime value.
    Are time zone definitions for your database installed?

Script này nạp dữ liệu từ thư viện chuẩn `zoneinfo` của Python, không cần
chạy `mysql_tzinfo_to_sql` (công cụ chỉ có trong bản phân phối MySQL Server).

Cách chạy:
    python load_tzinfo.py
"""

import os
import sys
from datetime import datetime, timezone as dt_timezone

import pymysql

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from zoneinfo import ZoneInfo, available_timezones
except ImportError:  # Python < 3.9
    from backports.zoneinfo import ZoneInfo, available_timezones  # type: ignore


START_YEAR = 1970
END_YEAR = 2037


def load_env():
    """Đọc thông tin kết nối MySQL từ file .env (nếu có)."""
    values = {
        'DB_HOST': '127.0.0.1',
        'DB_PORT': '3306',
        'DB_USER': 'root',
        'DB_PASSWORD': '',
    }
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        with open(env_file, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') or '=' not in line:
                    continue
                key, _, val = line.partition('=')
                if key.strip() in values:
                    values[key.strip()] = val.strip()
    return values


def offset_seconds(tz, year):
    """Chênh lệch UTC (giây) của múi giờ `tz` vào giữa năm `year`."""
    probe = datetime(year, 6, 15, 12, 0, tzinfo=dt_timezone.utc).astimezone(tz)
    return int(probe.utcoffset().total_seconds())


def year_start_utc_ts(year):
    """Mốc UTC (dạng timestamp) của 00:00 ngày 1/1 năm `year`."""
    return int(datetime(year, 1, 1, tzinfo=dt_timezone.utc).timestamp())


def run():
    cfg = load_env()

    print("=" * 62)
    print("  NẠP DỮ LIỆU MÚI GIỜ VÀO MYSQL")
    print("=" * 62)
    print(f"  Kết nối: {cfg['DB_USER']}@{cfg['DB_HOST']}:{cfg['DB_PORT']}\n")

    conn = pymysql.connect(
        host=cfg['DB_HOST'],
        port=int(cfg['DB_PORT']),
        user=cfg['DB_USER'],
        password=cfg['DB_PASSWORD'],
        charset='utf8mb4',
        autocommit=False,
    )
    cursor = conn.cursor()

    try:
        # --- Kiểm tra phiên bản & bảng cần dùng ---
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA='mysql' AND TABLE_NAME='time_zone_transition'
        """)
        columns = [r[0] for r in cursor.fetchall()]

        if 'Transition_type_id' in columns:
            layout = 'mysql8'
        elif 'offset' in columns:
            layout = 'legacy'
        else:
            layout = 'unknown'

        print(f"  Phiên bản MySQL : {version}")
        print(f"  Cấu trúc bảng   : {layout}")
        if layout == 'unknown':
            print("  ✗ Không nhận ra cấu trúc bảng timezone. Hãy kiểm tra thủ công.")
            conn.rollback()
            return

        cursor.execute("SELECT COUNT(*) FROM mysql.time_zone_name")
        before = cursor.fetchone()[0]
        if before > 0:
            print(f"\n⚠️  Database đang có {before} múi giờ.")
            answer = input("   Xoá và nạp lại? [y/N]: ").strip().lower()
            if answer != 'y':
                print("   Đã huỷ.\n")
                conn.rollback()
                return

        # --- Xoá dữ liệu cũ (đúng thứ tự khoá ngoại) ---
        print("\n🧹 Đang xoá dữ liệu múi giờ cũ...")
        if layout == 'mysql8':
            cursor.execute("DELETE FROM mysql.time_zone_transition")
            cursor.execute("DELETE FROM mysql.time_zone_transition_type")
        else:
            cursor.execute("DELETE FROM mysql.time_zone_transition")
        cursor.execute("DELETE FROM mysql.time_zone_name")
        cursor.execute("DELETE FROM mysql.time_zone")

        zones = sorted(available_timezones())
        print(f"   Đang nạp {len(zones)} múi giờ...")

        type_rows = []
        transition_rows = []

        for name in zones:
            try:
                tz = ZoneInfo(name)
            except Exception:
                continue

            # 1) Cấp id cho múi giờ
            cursor.execute("INSERT INTO mysql.time_zone () VALUES ()")
            tz_id = cursor.lastrowid

            # 2) Thu thập các độ lệch UTC khác nhau trong khoảng năm
            offsets = []
            for year in range(START_YEAR, END_YEAR + 1):
                try:
                    value = offset_seconds(tz, year)
                except Exception:
                    continue
                if not offsets or offsets[-1][1] != value:
                    offsets.append((year, value))

            if not offsets:
                continue

            # 3) Gán transition_type_id (bắt đầu từ 1) cho từng độ lệch
            offset_to_type = {}
            for type_id, (_, value) in enumerate(offsets, start=1):
                offset_to_type[value] = type_id
                if layout == 'mysql8':
                    type_rows.append((tz_id, type_id, value, 0, ''))
                else:
                    type_rows.append((tz_id, type_id))

            # 4) Ghi các mốc chuyển đổi
            for year, value in offsets:
                transition_rows.append(
                    (tz_id, year_start_utc_ts(year), offset_to_type[value])
                )

            # 5) Đăng ký tên
            cursor.execute(
                "INSERT INTO mysql.time_zone_name (Name, Time_zone_id) VALUES (%s, %s)",
                (name, tz_id)
            )

        print(f"   Đang ghi {len(type_rows)} transition type...")
        if type_rows:
            if layout == 'mysql8':
                cursor.executemany(
                    "INSERT INTO mysql.time_zone_transition_type "
                    "(Time_zone_id, Transition_type_id, Offset, Is_DST, Abbreviation) "
                    "VALUES (%s, %s, %s, %s, %s)", type_rows
                )
            else:
                cursor.executemany(
                    "INSERT INTO mysql.time_zone_transition_type "
                    "(Time_zone_id, Transition_type_id) VALUES (%s, %s)", type_rows
                )

        print(f"   Đang ghi {len(transition_rows)} mốc chuyển đổi...")
        if transition_rows:
            cursor.executemany(
                "INSERT INTO mysql.time_zone_transition "
                "(Time_zone_id, Transition_time, Transition_type_id) VALUES (%s, %s, %s)",
                transition_rows
            )

        cursor.execute("SET GLOBAL time_zone = 'SYSTEM'")
        conn.commit()

        # --- Kết quả ---
        counts = {}
        for table in ['time_zone_name', 'time_zone_transition', 'time_zone_transition_type']:
            cursor.execute(f"SELECT COUNT(*) FROM mysql.{table}")
            counts[table] = cursor.fetchone()[0]

        print("\n✅ Đã nạp thành công:")
        print(f"   Múi giờ             : {counts['time_zone_name']}")
        print(f"   Mốc chuyển đổi      : {counts['time_zone_transition']}")
        print(f"   Loại chuyển đổi      : {counts['time_zone_transition_type']}")

        print("\n🧪 Kiểm tra chuyển đổi múi giờ:")
        cursor.execute("SELECT @@global.time_zone")
        print(f"   time_zone toàn cục  : {cursor.fetchone()[0]}")
        for zone in ['UTC', 'Asia/Ho_Chi_Minh']:
            cursor.execute(
                "SELECT CONVERT_TZ('2026-07-17 12:00:00', 'UTC', %s)", (zone,)
            )
            print(f"   12:00 UTC -> {zone:<20}= {cursor.fetchone()[0]}")

        print("\n" + "=" * 62)
        print("  ✅ HOÀN TẤT! Trang quản trị sẽ không còn lỗi datetime.")
        print("=" * 62)

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    run()
