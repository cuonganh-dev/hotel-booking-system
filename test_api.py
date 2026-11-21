import requests

url = "http://127.0.0.1:5000/api/bookings"

# Case 1: Đặt phòng hợp lệ (Server tự tính tiền: 4 đêm * 500k = 2.000.000)
data_valid = {
    "user_id": 2,
    "room_id": 1,
    "check_in": "2026-10-01",
    "check_out": "2026-10-05"
}

# Case 2: Đặt trùng ngày (03/10 - 07/10 đè lên 01/10 - 05/10) -> Phải báo lỗi 409
data_overlap = {
    "user_id": 2,
    "room_id": 1,
    "check_in": "2026-10-03",
    "check_out": "2026-10-07"
}

# Case 3: Đặt nối tiếp ngày check-out (05/10 - 08/10) -> Phải thành công 201 nhờ khoảng nửa mở [)
data_adjacent = {
    "user_id": 2,
    "room_id": 1,
    "check_in": "2026-10-05",
    "check_out": "2026-10-08"
}

for name, payload in [("1. Đặt hợp lệ", data_valid), ("2. Đặt trùng ngày", data_overlap), ("3. Đặt nối ngày trả", data_adjacent)]:
    res = requests.post(url, json=payload)
    print(f"--- {name} ---")
    print(f"Mã trạng thái: {res.status_code}")
    print(f"Phản hồi từ Server: {res.json()}\n")