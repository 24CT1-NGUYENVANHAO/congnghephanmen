"""
Khởi tạo cấu hình cho dự án core (SáchGóc Uni).
Đảm bảo kết nối Cơ sở dữ liệu MySQL thông qua driver PyMySQL / mysqlclient.
"""

import pymysql

# Cấu hình PyMySQL hoạt động như MySQLdb chuẩn cho Django
pymysql.install_as_MySQLdb()
