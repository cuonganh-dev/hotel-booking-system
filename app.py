from flask import Flask, request, jsonify
from psycopg2 import errors
from db import get_db_connection

app = Flask(__name__)

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
        # Tự động tính tổng tiền = số đêm * giá phòng trong DB
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


# 2. API Tìm phòng trống theo ngày (Để Hiền lắp vào giao diện tìm phòng trên Streamlit)
@app.route('/api/rooms/available', methods=['GET'])
def get_available_rooms():
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')

    if not check_in or not check_out:
        return jsonify({"error": "Thiếu tham số check_in hoặc check_out"}), 400

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
        return jsonify({"data": rooms}), 200
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