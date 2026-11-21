# Hệ Thống Quản Lý Đặt Phòng Khách Sạn (Hotel Booking Management System)

Đồ án môn học **Cơ sở dữ liệu** xây dựng hệ thống quản lý đặt phòng khách sạn hoàn chỉnh, ứng dụng các kỹ thuật quản trị CSDL nâng cao trên **PostgreSQL 19** kết hợp Backend **Flask** và giao diện **Streamlit**.

## 1. Công nghệ sử dụng
- **Cơ sở dữ liệu:** PostgreSQL 19 (`btree_gist`, `EXCLUSION CONSTRAINT`, View, Function, Trigger, Stored Procedure, B-Tree Index, RBAC).
- **Backend:** Python (Flask REST API, `psycopg2-binary`).
- **Frontend:** Streamlit (`dashboard.py`).

## 2. Cấu trúc thư mục
- `database.sql`: Script khởi tạo toàn bộ bảng, ràng buộc, View, Function, Trigger, Procedure, Index và phân quyền.
- `backup_hotel.backup`: File sao lưu cơ sở dữ liệu định dạng Custom (`pg_dump`).
- `db.py`: Module quản lý kết nối tới PostgreSQL.
- `app.py`: Backend Flask cung cấp các REST API nghiệp vụ.
- `dashboard.py`: Giao diện người dùng Streamlit phân tách theo 3 vai trò (`admin`, `staff`, `customer`).
- `concurrency_test.py`: Script kiểm thử đặt phòng đồng thời (chống trùng lịch).
- `test_api.py`: Script kiểm thử các endpoint API.
- `requirements.txt`: Danh sách các thư viện Python cần thiết.

## 3. Tính năng & Chuẩn đầu ra (CLO1 – CLO7)
- **Chống đặt trùng phòng (Concurrency Control):** Sử dụng `EXCLUSION CONSTRAINT` kết hợp `btree_gist` đảm bảo không xảy ra xung đột lịch đặt phòng ngay cả khi nhiều người dùng đặt đồng thời.
- **Thành phần CSDL nâng cao:**
  - View `v_hotel_revenue`: Tổng hợp báo cáo doanh thu theo khách sạn.
  - Function `fn_calculate_booking_price` & Trigger `before_booking_save`: Tự động tính tổng tiền đặt phòng.
  - Stored Procedure `sp_cancel_booking`: Xử lý hủy đơn đặt phòng an toàn.
  - B-Tree Index (`idx_bookings_user_status`, `idx_rooms_hotel_type`): Tối ưu hiệu năng truy vấn.
- **Phân quyền 3 cấp (RBAC):**
  - `hotel_admin_role`: Toàn quyền quản trị hệ thống và xem báo cáo.
  - `hotel_staff_role`: Xem danh sách, đặt phòng hộ khách và duyệt/hủy đơn.
  - `hotel_customer_role`: Xem phòng và tự tạo đơn đặt phòng.
- **Sao lưu & Phục hồi:** Hỗ trợ `pg_dump` và `pg_restore`.

## 4. Hướng dẫn cài đặt và chạy dự án

### Bước 1: Khởi tạo Cơ sở dữ liệu
Tạo database `hotel_demo` trong PostgreSQL, sau đó chạy file `database.sql` hoặc phục hồi trực tiếp từ file `backup_hotel.backup`:

```bash
pg_restore -U postgres -d hotel_demo --clean backup_hotel.backup
```

### Bước 2: Cài đặt thư viện Python
Tạo môi trường ảo (khuyên dùng) và cài đặt các gói phụ thuộc:

```bash
pip install -r requirements.txt
```

### Bước 3: Chạy ứng dụng
Mở 2 cửa sổ Terminal riêng biệt trong thư mục dự án:

```bash
# Terminal 1: Chạy Backend Flask
python app.py

# Terminal 2: Chạy Frontend Streamlit
streamlit run dashboard.py
```

### Bước 4: Kiểm thử hệ thống (Tùy chọn)
```bash
# Kiểm thử đặt phòng đồng thời
python concurrency_test.py

# Kiểm thử API
python test_api.py
```