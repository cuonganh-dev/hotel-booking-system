import streamlit as st
import pandas as pd
import requests
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from db import get_db_connection

st.set_page_config(page_title="Grand Hotel Booking", page_icon="🏨", layout="wide")

# CSS tùy chỉnh nhẹ cho giao diện thẻ phòng đẹp hơn
st.markdown("""
<style>
    .room-card {
        background-color: #1e2129;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #313644;
        margin-bottom: 15px;
    }
    .price-tag {
        color: #ff4b4b;
        font-size: 20px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Ảnh minh họa theo loại phòng
ROOM_IMAGES = {
    "single": "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=500",
    "double": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500",
    "suite": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
}

if "user" not in st.session_state:
    st.session_state.user = None

# --- SIDEBAR: ĐĂNG NHẬP ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2933/2933939.png", width=70)
    st.title("Grand Hotel")
    if st.session_state.user is None:
        st.subheader("🔐 Đăng nhập hệ thống")
        email = st.text_input("Email", placeholder="Nhập email của bạn...")
        password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...")
        if st.button("Đăng nhập", type="primary", use_container_width=True):
            res = requests.post("http://127.0.0.1:5000/api/login", json={"email": email, "password": password})
            if res.status_code == 200:
                st.session_state.user = res.json()["user"]
                st.rerun()
            else:
                st.error(res.json().get("error", "Sai email hoặc mật khẩu!"))
    else:
        u = st.session_state.user
        st.success(f"👤 **{u['full_name']}**")
        st.caption(f"Email: {u['email']}")
        st.info(f"Quyền hạn: **{u['role'].upper()}**")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.user = None
            st.rerun()

# --- HEADER ---
st.title("🏨 Hệ thống Đặt phòng Khách sạn Trực tuyến")
st.caption("Đồ án Cơ sở dữ liệu — Xử lý tranh chấp đặt phòng bằng PostgreSQL Exclusion Constraint (GiST + DATERANGE)")

# --- KHUNG TÌM KIẾM PHÒNG TRỐNG (AI CŨNG XEM ĐƯỢC) ---
# --- KHUNG TÌM KIẾM PHÒNG TRỐNG ---
with st.container(border=True):
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1.8, 1.2])
    check_in = c1.date_input("📅 Ngày nhận phòng", value=date(2026, 11, 25))
    check_out = c2.date_input("📅 Ngày trả phòng", value=date(2026, 11, 28))
    hotel_filter = c3.selectbox("🏨 Chọn khách sạn", ["Tất cả", "Khách sạn Hoa Hồng", "Khách sạn Biển Xanh"])
    room_filter = c4.selectbox("🛏️ Hạng phòng", ["Tất cả", "single", "double", "suite"])
    nights = max((check_out - check_in).days, 0)
    c5.metric("Số đêm", f"{nights} đêm")

# Tạo Menu theo Role
role = st.session_state.user["role"] if st.session_state.user else "guest"
menu = ["🏨 Danh sách Phòng trống"]
if role == "customer":
    menu.append("🧾 Đơn đặt của tôi")
if role in ("staff", "admin"):
    menu.append("📋 Quản lý Đặt phòng")
if role == "admin":
    menu.extend(["📊 Dashboard Thống kê", "⚡ Test Tranh chấp (Concurrency)"])

tabs = st.tabs(menu)

# ==========================================
# TAB 1: DANH SÁCH PHÒNG DẠNG THẺ & ĐẶT NGAY
with tabs[0]:
    if check_in >= check_out:
        st.error("⚠️ Ngày trả phòng phải sau ngày nhận phòng ít nhất 1 ngày!")
    else:
        res = requests.get("http://127.0.0.1:5000/api/rooms/available", params={"check_in": str(check_in), "check_out": str(check_out)})
        if res.status_code == 200:
            rooms = res.json()["data"]
            if hotel_filter != "Tất cả":
                rooms = [r for r in rooms if r["hotel_name"] == hotel_filter]
            if room_filter != "Tất cả":
                rooms = [r for r in rooms if r["type"] == room_filter]

            st.subheader(f"Tìm thấy {len(rooms)} phòng trống từ {check_in} đến {check_out}")
            
            # 1. Chỉ hiện ô nhập ID đặt hộ khi vai trò là Lễ tân (staff)
            target_user_id = st.session_state.user["id"] if role == "customer" else None
            if role == "staff":
                target_user_id = st.number_input("🧑‍💼 Nhập ID Khách hàng để đặt phòng hộ:", min_value=1, value=2, step=1)

            cols = st.columns(3)
            for idx, room in enumerate(rooms):
                with cols[idx % 3]:
                    with st.container(border=True):
                        st.image(ROOM_IMAGES.get(room["type"], ROOM_IMAGES["single"]), use_container_width=True)
                        st.caption(f"📍 {room['hotel_name']} (ID Phòng: #{room['id']})")
                        st.markdown(f"### Phòng {room['room_number']} — {room['type'].upper()}")
                        total = room["price_per_night"] * nights
                        st.markdown(f"Giá: **{room['price_per_night']:,.0f} đ/đêm** | Tổng ({nights} đêm): <span class='price-tag'>{total:,.0f} đ</span>", unsafe_allow_html=True)
                        
                        # 2. Cụm nút bấm phân quyền: Guest & Admin bị khóa nút đặt
                        if role == "guest":
                            st.button("🔒 Đăng nhập để đặt", key=f"btn_{room['id']}", disabled=True, use_container_width=True)
                        elif role == "admin":
                            st.button("👁️ Chế độ xem (Admin)", key=f"btn_{room['id']}", disabled=True, use_container_width=True)
                        else:
                            if st.button("✅ Đặt phòng này ngay", key=f"btn_{room['id']}", type="primary", use_container_width=True):
                                book_res = requests.post("http://127.0.0.1:5000/api/bookings", json={
                                    "user_id": int(target_user_id),
                                    "room_id": int(room["id"]),
                                    "check_in": str(check_in),
                                    "check_out": str(check_out)
                                })
                                if book_res.status_code == 201:
                                    st.toast(f"Đặt thành công Phòng {room['room_number']}!", icon="🎉")
                                    st.success(f"Đã đặt Phòng {room['room_number']} (Mã đơn #{book_res.json()['booking_id']})")
                                    st.rerun()
                                else:
                                    st.error(book_res.json().get("error"))

# ==========================================
# TAB CỦA CUSTOMER: ĐƠN CỦA TÔI
# ==========================================
if role == "customer":
    with tabs[1]:
        st.subheader("🧾 Lịch sử đặt phòng của bạn")
        conn = get_db_connection()
        df_my = pd.read_sql("""
            SELECT b.id AS "Mã đơn", h.name AS "Khách sạn", r.room_number AS "Số phòng", 
                   r.type AS "Hạng phòng", b.stay_dates::text AS "Khoảng ngày", 
                   b.total_price AS "Tổng tiền (VNĐ)", b.status AS "Trạng thái"
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            JOIN hotels h ON r.hotel_id = h.id
            WHERE b.user_id = %s ORDER BY b.id DESC;
        """, conn, params=(st.session_state.user["id"],))
        conn.close()
        st.dataframe(df_my, use_container_width=True, hide_index=True)

        c1, c2 = st.columns([1, 3])
        cancel_id = c1.number_input("Mã đơn muốn hủy", min_value=1, value=1, step=1)
        if c2.button("❌ Hủy đơn đặt phòng"):
            res = requests.patch(f"http://127.0.0.1:5000/api/bookings/{int(cancel_id)}/status", json={"status": "cancelled"})
            if res.status_code == 200:
                st.success(res.json()["message"])
                st.rerun()
            else:
                st.error(res.json().get("error"))

# ==========================================
# TAB CỦA STAFF & ADMIN: QUẢN LÝ TẤT CẢ ĐƠN
# ==========================================
if role in ("staff", "admin"):
    with tabs[1]:
        st.subheader("📋 Danh sách toàn bộ đơn đặt phòng")
        conn = get_db_connection()
        df_all = pd.read_sql("""
            SELECT b.id AS "Mã đơn", u.full_name AS "Khách hàng", h.name AS "Khách sạn", 
                   r.room_number AS "Số phòng", b.stay_dates::text AS "Khoảng ngày", 
                   b.total_price AS "Tổng tiền", b.status AS "Trạng thái"
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN rooms r ON b.room_id = r.id
            JOIN hotels h ON r.hotel_id = h.id
            ORDER BY b.id DESC;
        """, conn)
        conn.close()
        st.dataframe(df_all, use_container_width=True, hide_index=True)

        with st.container(border=True):
            st.write("**Thao tác duyệt / hủy đơn (Tự động nhả phòng khi chuyển sang `cancelled`)**")
            c1, c2, c3 = st.columns([1, 2, 1])
            b_id = c1.number_input("Nhập Mã đơn", min_value=1, value=1, step=1)
            new_st = c2.selectbox("Trạng thái mới", ["confirmed", "cancelled"])
            if c3.button("Lưu trạng thái", type="primary", use_container_width=True):
                res = requests.patch(f"http://127.0.0.1:5000/api/bookings/{int(b_id)}/status", json={"status": new_st})
                if res.status_code == 200:
                    st.success(res.json()["message"])
                    st.rerun()
                else:
                    st.error(res.json().get("error"))

# ==========================================
# TAB CỦA ADMIN: DASHBOARD THỐNG KÊ
# ==========================================
if role == "admin":
    with tabs[2]:
        conn = get_db_connection()
        df_kpi = pd.read_sql("""
            SELECT 
                COALESCE(SUM(total_price) FILTER (WHERE status = 'confirmed'), 0) AS revenue,
                COUNT(*) FILTER (WHERE status = 'confirmed') AS confirmed_cnt,
                COUNT(*) FILTER (WHERE status = 'pending') AS pending_cnt,
                COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_cnt
            FROM bookings;
        """, conn)
        df_rev = pd.read_sql("""
            SELECT TO_CHAR(lower(stay_dates), 'YYYY-MM') AS thang, SUM(total_price) AS doanh_thu
            FROM bookings WHERE status = 'confirmed' GROUP BY thang ORDER BY thang;
        """, conn)
        df_type = pd.read_sql("""
            SELECT r.type AS loai_phong, SUM(b.total_price) AS doanh_thu
            FROM bookings b JOIN rooms r ON b.room_id = r.id
            WHERE b.status <> 'cancelled' GROUP BY r.type;
        """, conn)
        conn.close()

        # 4 Thẻ chỉ số KPI
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Doanh thu thực tế", f"{df_kpi['revenue'][0]:,.0f} đ")
        k2.metric("✅ Đơn đã xác nhận", f"{df_kpi['confirmed_cnt'][0]} đơn")
        k3.metric("⏳ Đơn chờ duyệt", f"{df_kpi['pending_cnt'][0]} đơn")
        k4.metric("❌ Đơn đã hủy", f"{df_kpi['cancelled_cnt'][0]} đơn")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📈 Biểu đồ Doanh thu theo tháng")
            if not df_rev.empty:
                st.bar_chart(df_rev.set_index("thang")["doanh_thu"])
        with c2:
            st.subheader("🏨 Doanh thu theo hạng phòng")
            if not df_type.empty:
                st.bar_chart(df_type.set_index("loai_phong")["doanh_thu"])

    # ==========================================
    # TAB TEST TRANH CHẤP TRỰC TIẾP TRÊN WEB
    # ==========================================
    with tabs[3]:
        st.subheader("⚡ Mô phỏng 10 khách hàng đặt trùng 1 phòng tại cùng một mili-giây")
        st.info("Chức năng này bắn đồng thời 10 luồng HTTP POST vào cùng một `room_id` và cùng khoảng ngày để kiểm chứng sức mạnh của `Exclusion Constraint` trong PostgreSQL.")
        
        col1, col2, col3 = st.columns(3)
        t_room = col1.number_input("ID Phòng đem ra test", min_value=1, value=3, step=1)
        t_in = col2.date_input("Ngày nhận test", value=date(2026, 12, 30))
        t_out = col3.date_input("Ngày trả test", value=date(2027, 1, 2))

        if st.button("🚀 Bắn 10 request đặt phòng cùng lúc", type="primary"):
            def race_book(i):
                r = requests.post("http://127.0.0.1:5000/api/bookings", json={
                    "user_id": 2, "room_id": int(t_room), "check_in": str(t_in), "check_out": str(t_out)
                })
                return {"Khách hàng": f"Khách #{i:02d}", "HTTP Code": r.status_code, "Kết quả từ PostgreSQL": r.json().get("message") or r.json().get("error")}

            with ThreadPoolExecutor(max_workers=10) as ex:
                results = list(ex.map(race_book, range(1, 11)))
            
            df_res = pd.DataFrame(results)
            win = len(df_res[df_res["HTTP Code"] == 201])
            lose = len(df_res[df_res["HTTP Code"] == 409])
            st.success(f"Kết quả kiểm thử: **{win} người đặt thành công (201)** — **{lose} người bị chặn trùng lịch (409)**")
            st.dataframe(df_res, use_container_width=True, hide_index=True)