import requests
from concurrent.futures import ThreadPoolExecutor

URL = "http://127.0.0.1:5000/api/bookings"

def book_room(person_id):
    payload = {
        "user_id": 2,
        "room_id": 2,  # Cùng tranh nhau phòng 102 (id=2)
        "check_in": "2026-12-24",
        "check_out": "2026-12-27"
    }
    res = requests.post(URL, json=payload)
    return f"Khách #{person_id:02d} -> HTTP {res.status_code}: {res.json()}"

if __name__ == "__main__":
    print("=== TEST 10 NGƯỜI ĐẶT TRÙNG 1 PHÒNG CÙNG 1 THỜI ĐIỂM ===")
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(book_room, range(1, 11)))
    for r in results:
        print(r)