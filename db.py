import psycopg2

# CẤU HÌNH KẾT NỐI DATABASE
DB_CONFIG = {
    "host": "localhost",
    "database": "hotel_demo",       # <-- SỬA LẠI: Tên Database bạn đã tạo trên pgAdmin4 (VD: hotel_db)
    "user": "postgres",           # <-- Thường mặc định là postgres
    "password": "123456" # <-- SỬA LẠI: Mật khẩu Postgres bạn đã cài đặt lúc đầu
}

def get_db_connection():
    """
    Hàm tạo kết nối đến PostgreSQL.
    Trả về đối tượng connection nếu thành công, ngược lại trả về None.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Lỗi kết nối CSDL: {e}")
        return None
    