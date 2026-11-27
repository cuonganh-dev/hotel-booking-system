import json
import time
import redis
from flask import Flask, request, jsonify
from psycopg2 import errors
from db import get_db_connection

app = Flask(__name__)

# --- KẾT NỐI REDIS CACHE ---
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    print("✅ [REDIS] Kết nối Redis Cache thành công (localhost:6379)")
except Exception as e:
    redis_client = None
    print(f"⚠️ [REDIS] Không thể kết nối Redis, hệ thống sẽ chạy trực tiếp qua PostgreSQL: {e}")


def clear_rooms_cache():
    """Xóa toàn bộ cache danh sách phòng trống khi có thay đổi đặt/hủy phòng (Cache Invalidation)"""
    if not redis_client:
        return
    try:
        keys = redis_client.keys("available_rooms:*")
        if keys:
            redis_client.delete(*keys)
            print(f"🧹 [REDIS INVALIDATION] Đã xóa {len(keys)} key cache phòng trống do dữ liệu thay đổi.")
    except Exception as e:
        print(f"⚠️ [REDIS] Lỗi xóa cache: {e}")


# 1. API CORE: Đặt phòng (Tự tính tiền bằng SQL + Chống trùng bằng Exclusion Constraint)
@app.route('/api/bookings', methods=['POST'])
def create_booking():
    data = request.get_json()
    user_id = data.get('user_id')
    room_id = data.get('room_id')
    check_in = data.get('check_in')
    check_out = data.get('check_out')

    if not all([user_id, room_id, check_in, check_out]):
        return jsonify({"error": "Vui lòng nhập đủ user_id, room_id, check_in, check_out!"}), 400

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Lỗi kết nối Database"}), 500
            
        cur = conn.cursor()
        sql = """
            INSERT INTO bookings (user_id, room_id, stay_dates, total_price, status) 
            SELECT %s, r.id, daterange(%s, %s, '[)'), 
                   r.price_per_night * (%s::date - %s::date), 'pending'
            FROM rooms r
            WHERE r.id = %s
            RETURNING id, total_price;
        """
        cur.execute(sql, (user_id, check_in, check_out, check_out, check_in, room_id))
        result = cur.fetchone()

        if not result:
            conn.rollback()
            cur.close()
            return jsonify({"error": "Phòng không tồn tại!"}), 404

        new_id, calculated_price = result[0], float(result[1])
        conn.commit()
        cur.close()

        # Xóa cache phòng trống vì vừa có phòng được đặt
        clear_rooms_cache()
        
        return jsonify({
            "message": "Đặt phòng thành công!",
            "booking_id": new_id,
            "total_price": calculated_price
        }), 201

    except errors.ExclusionViolation:
        if conn:
            conn.rollback()
        return jsonify({
            "error": "Trùng lịch! Phòng này đã được đặt trong khoảng thời gian trên."
        }), 409

    except (errors.ForeignKeyViolation, errors.CheckViolation, errors.DataException):
        if conn:
            conn.rollback()
        return jsonify({
            "error": "Dữ liệu không hợp lệ (Kiểm tra lại user_id hoặc ngày check_in < check_out)."
        }), 400
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Lỗi hệ thống: {str(e)}"}), 500
        
    finally:
        if conn:
            conn.close()


# 2. API Tìm phòng trống theo ngày (Áp dụng Redis Cache-Aside + TTL 60s)
@app.route('/api/rooms/available', methods=['GET'])
def get_available_rooms():
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')

    if not check_in or not check_out:
        return jsonify({"error": "Thiếu tham số check_in hoặc check_out"}), 400

    start_time = time.perf_counter()
    cache_key = f"available_rooms:{check_in}:{check_out}"

    # BƯỚC 1: Kiểm tra trong Redis Cache trước (CACHE HIT)
    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                print(f"⚡ [CACHE HIT] Lấy từ Redis ({cache_key}) - Thời gian: {elapsed_ms} ms")
                return jsonify({
                    "source": "Redis Cache (CACHE HIT)",
                    "response_time_ms": elapsed_ms,
                    "data": json.loads(cached_data)
                }), 200
        except Exception as e:
            print(f"⚠️ [REDIS] Lỗi đọc cache: {e}")

    # BƯỚC 2: Không có trong Redis -> Truy vấn PostgreSQL (CACHE MISS)
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sql = """
            SELECT r.id, h.name, r.room_number, r.type, r.price_per_night
            FROM rooms r
            JOIN hotels h ON r.hotel_id = h.id
            WHERE r.id NOT IN (
                SELECT b.room_id FROM bookings b
                WHERE b.status <> 'cancelled'
                  AND b.stay_dates && daterange(%s, %s, '[)')
            )
            ORDER BY r.id;
        """
        cur.execute(sql, (check_in, check_out))
        rows = cur.fetchall()
        cur.close()

        rooms = [
            {
                "id": r[0],
                "hotel_name": r[1],
                "room_number": r[2],
                "type": r[3],
                "price_per_night": float(r[4])
            } for r in rows
        ]

        # BƯỚC 3: Lưu kết quả vào Redis với thời gian hết hạn TTL = 60 giây
        if redis_client:
            try:
                redis_client.setex(cache_key, 60, json.dumps(rooms))
            except Exception as e:
                print(f"⚠️ [REDIS] Lỗi ghi cache: {e}")

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        print(f"🐢 [CACHE MISS] Truy vấn PostgreSQL ({cache_key}) - Thời gian: {elapsed_ms} ms")

        return jsonify({
            "source": "PostgreSQL (CACHE MISS)",
            "response_time_ms": elapsed_ms,
            "data": rooms
        }), 200
    except Exception as e:
        return jsonify({"error": f"Lỗi hệ thống: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


# 3. API Cập nhật trạng thái đơn (Duyệt 'confirmed' hoặc Hủy 'cancelled' để nhả phòng)
@app.route('/api/bookings/<int:booking_id>/status', methods=['PATCH'])
def update_booking_status(booking_id):
    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ('confirmed', 'cancelled'):
        return jsonify({"error": "Trạng thái chỉ nhận 'confirmed' hoặc 'cancelled'"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE bookings SET status = %s WHERE id = %s RETURNING id;",
            (new_status, booking_id)
        )
        updated = cur.fetchone()
        if not updated:
            conn.rollback()
            cur.close()
            return jsonify({"error": "Không tìm thấy đơn đặt phòng!"}), 404

        conn.commit()
        cur.close()

        # Xóa cache phòng trống vì trạng thái đơn vừa thay đổi (đặc biệt khi hủy phòng để nhả lịch)
        clear_rooms_cache()

        return jsonify({"message": f"Đã cập nhật đơn #{booking_id} sang {new_status}"}), 200
    except errors.ExclusionViolation:
        if conn:
            conn.rollback()
        return jsonify({"error": "Không thể khôi phục đơn vì khoảng ngày này đã có người khác đặt!"}), 409
    finally:
        if conn:
            conn.close()


# 4. API Đăng nhập & Kiểm tra phân quyền (Role)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Vui lòng nhập đủ email và mật khẩu"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, full_name, role FROM users WHERE email = %s AND password_hash = %s;",
            (email, password)
        )
        user = cur.fetchone()
        cur.close()

        if not user:
            return jsonify({"error": "Sai email hoặc mật khẩu!"}), 401

        return jsonify({
            "message": "Đăng nhập thành công",
            "user": {
                "id": user[0],
                "email": user[1],
                "full_name": user[2],
                "role": user[3]
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Lỗi hệ thống: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)