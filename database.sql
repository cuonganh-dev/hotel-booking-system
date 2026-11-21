-- ==========================================================
-- ĐỒ ÁN CƠ SỞ DỮ LIỆU: HỆ THỐNG QUẢN LÝ ĐẶT PHÒNG KHÁCH SẠN
-- Hệ quản trị: PostgreSQL (Sử dụng btree_gist & Exclusion Constraint)
-- ==========================================================

-- 1. Xóa các bảng cũ nếu tồn tại (giúp chạy lại script sạch từ đầu)
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS hotels CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 2. Kích hoạt Extension hỗ trợ chỉ mục GiST cho kiểu dữ liệu vô hướng (int) kết hợp daterange
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- 3. Tạo bảng Người dùng (Phân quyền 3 vai trò: customer, staff, admin)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'staff', 'admin')),
    password_hash VARCHAR(255) NOT NULL
);

-- 4. Tạo bảng Khách sạn
CREATE TABLE hotels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL
);

-- 5. Tạo bảng Phòng (Ràng buộc mỗi khách sạn không được trùng số phòng)
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    hotel_id INT NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    room_number VARCHAR(50) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('single', 'double', 'suite')),
    price_per_night DECIMAL(10, 2) NOT NULL CHECK (price_per_night > 0),
    CONSTRAINT unique_room_per_hotel UNIQUE (hotel_id, room_number)
);

-- 6. Tạo bảng Đặt phòng (Trọng tâm chống trùng lịch bằng Exclusion Constraint)
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    room_id INT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    stay_dates DATERANGE NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL CHECK (total_price >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ràng buộc kiểm tra khoảng ngày hợp lệ (không rỗng và ngày trả > ngày nhận)
    CONSTRAINT valid_stay_dates CHECK (NOT isempty(stay_dates) AND lower(stay_dates) < upper(stay_dates)),

    -- RÀNG BUỘC LOẠI TRỪ: Chặn tuyệt đối việc đặt trùng khoảng ngày trên cùng 1 phòng
    -- (Chỉ áp dụng với các đơn chưa bị hủy: status <> 'cancelled')
    CONSTRAINT no_overlapping_bookings EXCLUDE USING gist (
        room_id WITH =,
        stay_dates WITH &&
    ) WHERE (status <> 'cancelled')
);

-- ==========================================================
-- 7. DỮ LIỆU MẪU (SEED DATA)
-- ==========================================================

-- Tài khoản test cho 3 Actor (Mật khẩu chung: 123)
INSERT INTO users (email, full_name, role, password_hash) VALUES
('admin@hotel.com', 'Quản trị viên Hệ thống', 'admin', '123'),
('khach@gmail.com', 'Nguyễn Văn A', 'customer', '123'),
('staff@hotel.com', 'Lễ tân Trần Văn B', 'staff', '123');

-- Danh sách Khách sạn
INSERT INTO hotels (name, address) VALUES
('Khách sạn Hoa Hồng', '123 Phố Huế, Hai Bà Trưng, Hà Nội'),
('Khách sạn Biển Xanh', '45 Trần Phú, Nha Trang');

-- Danh sách Phòng
INSERT INTO rooms (hotel_id, room_number, type, price_per_night) VALUES
(1, '101', 'single', 500000),
(1, '102', 'double', 800000),
(1, '201', 'suite', 1500000),
(1, '202', 'double', 800000),
(2, '101', 'single', 600000),
(2, '102', 'suite', 1800000);

-- Dữ liệu đặt phòng mẫu phục vụ biểu đồ thống kê doanh thu
INSERT INTO bookings (user_id, room_id, stay_dates, total_price, status, created_at) VALUES
(2, 1, '[2026-01-10, 2026-01-13)', 1500000, 'confirmed', '2026-01-05 10:00:00'),
(2, 2, '[2026-02-14, 2026-02-17)', 2400000, 'confirmed', '2026-02-10 14:30:00'),
(2, 3, '[2026-03-08, 2026-03-10)', 3000000, 'confirmed', '2026-03-01 09:15:00'),
(2, 4, '[2026-04-30, 2026-05-03)', 2400000, 'confirmed', '2026-04-20 16:00:00'),
(2, 5, '[2026-06-15, 2026-06-20)', 3000000, 'confirmed', '2026-06-01 11:20:00'),
(2, 6, '[2026-08-10, 2026-08-14)', 7200000, 'confirmed', '2026-08-02 08:45:00'),
(2, 2, '[2026-09-02, 2026-09-05)', 2400000, 'cancelled', '2026-08-25 19:00:00');

-- ==========================================================
-- BỔ SUNG CLO3: VIEW, FUNCTION, STORED PROCEDURE & TRIGGER
-- ==========================================================

-- 1. VIEW: Thống kê doanh thu tổng hợp theo từng khách sạn (giúp truy vấn báo cáo ngắn gọn)
CREATE OR REPLACE VIEW v_hotel_revenue AS
SELECT 
    h.id AS hotel_id,
    h.name AS hotel_name,
    COUNT(b.id) FILTER (WHERE b.status = 'confirmed') AS confirmed_bookings,
    COUNT(b.id) FILTER (WHERE b.status = 'cancelled') AS cancelled_bookings,
    COALESCE(SUM(b.total_price) FILTER (WHERE b.status = 'confirmed'), 0) AS total_revenue
FROM hotels h
LEFT JOIN rooms r ON h.id = r.hotel_id
LEFT JOIN bookings b ON r.id = b.room_id
GROUP BY h.id, h.name;

-- 2. FUNCTION: Tính tổng tiền đặt phòng tự động dựa vào room_id và khoảng ngày
CREATE OR REPLACE FUNCTION fn_calculate_booking_price(p_room_id INT, p_dates DATERANGE)
RETURNS DECIMAL(10, 2) AS $$
DECLARE
    v_price DECIMAL(10, 2);
    v_nights INT;
BEGIN
    SELECT price_per_night INTO v_price FROM rooms WHERE id = p_room_id;
    v_nights := upper(p_dates) - lower(p_dates);
    RETURN v_price * v_nights;
END;
$$ LANGUAGE plpgsql;

-- 3. TRIGGER: Tự động tính lại total_price ở tầng CSDL mỗi khi INSERT hoặc UPDATE đơn đặt phòng
-- (Đảm bảo dù ai chèn trực tiếp vào DB không qua Python thì tiền vẫn luôn đúng)
CREATE OR REPLACE FUNCTION trg_auto_calculate_price()
RETURNS TRIGGER AS $$
BEGIN
    NEW.total_price := fn_calculate_booking_price(NEW.room_id, NEW.stay_dates);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS before_booking_save ON bookings;
CREATE TRIGGER before_booking_save
BEFORE INSERT OR UPDATE OF room_id, stay_dates ON bookings
FOR EACH ROW
EXECUTE FUNCTION trg_auto_calculate_price();

-- 4. STORED PROCEDURE: Hủy đơn đặt phòng an toàn (kiểm tra tồn tại trước khi hủy)
CREATE OR REPLACE PROCEDURE sp_cancel_booking(p_booking_id INT)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE bookings SET status = 'cancelled' WHERE id = p_booking_id AND status <> 'cancelled';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Đơn đặt phòng #% không tồn tại hoặc đã bị hủy trước đó!', p_booking_id;
    END IF;
END;
$$;

-- ==========================================================
-- BỔ SUNG CLO4: CHỈ MỤC (INDEX) TỐI ƯU HIỆU NĂNG
-- ==========================================================

-- Chỉ mục B-Tree tối ưu truy vấn lịch sử đặt phòng theo user_id và lọc trạng thái
CREATE INDEX IF NOT EXISTS idx_bookings_user_status ON bookings (user_id, status);
CREATE INDEX IF NOT EXISTS idx_rooms_hotel_type ON rooms (hotel_id, type);

-- ==========================================================
-- BỔ SUNG CLO5: PHÂN QUYỀN TẦNG CSDL (ROLE & GRANT)
-- ==========================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hotel_staff_role') THEN
        CREATE ROLE hotel_staff_role;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hotel_customer_role') THEN
        CREATE ROLE hotel_customer_role;
    END IF;
END $$;

-- Khách hàng chỉ được xem phòng/khách sạn và thêm/xem đơn đặt phòng
GRANT SELECT ON hotels, rooms TO hotel_customer_role;
GRANT SELECT, INSERT ON bookings TO hotel_customer_role;

-- Lễ tân được toàn quyền thao tác trên đơn đặt phòng và xem báo cáo View
GRANT SELECT, INSERT, UPDATE ON bookings TO hotel_staff_role;
GRANT SELECT ON hotels, rooms, users, v_hotel_revenue TO hotel_staff_role;
-- 1. Tạo role Admin và cấp toàn quyền trên tất cả bảng và View
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hotel_admin_role') THEN
        CREATE ROLE hotel_admin_role;
    END IF;
END $$;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hotel_admin_role;

--Kiểm tra danh sách phân quyền
SELECT 
    grantee AS vai_tro, 
    table_name AS ten_bang, 
    STRING_AGG(privilege_type, ', ') AS danh_sach_quyen
FROM information_schema.role_table_grants
WHERE grantee IN ('hotel_admin_role', 'hotel_staff_role', 'hotel_customer_role')
GROUP BY grantee, table_name
ORDER BY grantee, table_name;