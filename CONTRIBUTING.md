# Hướng dẫn Đóng góp & Làm việc nhóm (Contributing Guidelines)

Tài liệu quy định quy trình quản lý mã nguồn (Git Flow), quy ước commit và phối hợp làm việc nhóm cho đồ án **Hệ thống Quản lý Đặt phòng Khách sạn**.

## 1. Quy tắc phân nhánh (Branching Strategy)
- `main`: Nhánh chính chứa mã nguồn ổn định, đã kiểm thử, sẵn sàng để demo và nộp báo cáo. Không push trực tiếp code chưa kiểm tra lên nhánh này.
- `feature/<ten-tinh-nang>`: Tạo nhánh mới khi phát triển tính năng mới (Ví dụ: `feature/database-rbac`, `feature/streamlit-dashboard`).
- `fix/<ten-loi>`: Tạo nhánh mới khi sửa lỗi (Ví dụ: `fix/booking-overlap`, `fix/admin-permission`).
- `docs/<noi-dung>`: Tạo nhánh khi cập nhật tài liệu, báo cáo hoặc hướng dẫn (Ví dụ: `docs/update-readme`).

## 2. Quy ước viết Commit Message
Sử dụng tiền tố rõ ràng theo chuẩn Conventional Commits để dễ theo dõi lịch sử thay đổi:
- `feat:` Thêm tính năng mới (VD: `feat: add hotel_admin_role and RBAC grants`)
- `fix:` Sửa lỗi chương trình hoặc CSDL (VD: `fix: prevent admin from creating direct bookings`)
- `docs:` Cập nhật tài liệu, README, CONTRIBUTING (VD: `docs: add installation guide in README.md`)
- `test:` Thêm hoặc cập nhật kịch bản kiểm thử (VD: `test: add concurrency booking test script`)
- `chore:` Cập nhật cấu hình, thư viện, `.gitignore` (VD: `chore: add .gitignore to exclude venv`)

## 3. Quy trình đóng góp mã nguồn
1. Cập nhật phiên bản mới nhất từ nhánh `main`:
   ```bash
   git checkout main
   git pull origin main
   ```
2. Tạo nhánh làm việc mới cho nhiệm vụ được giao:
   ```bash
   git checkout -b feature/ten-tinh-nang
   ```
3. Thực hiện thay đổi, kiểm thử cục bộ và commit với thông điệp rõ ràng:
   ```bash
   git add .
   git commit -m "feat: mô tả ngắn gọn thay đổi"
   ```
4. Đẩy nhánh lên GitHub:
   ```bash
   git push origin feature/ten-tinh-nang
   ```
5. Tạo **Pull Request (PR)** vào nhánh `main` trên GitHub để kiểm duyệt trước khi gộp code (merge).

## 4. Checklist trước khi tạo Pull Request
- [ ] Mã nguồn chạy không phát sinh lỗi khi khởi động `app.py` và `dashboard.py`.
- [ ] Các thay đổi về cấu trúc CSDL đã được cập nhật đồng bộ vào file `database.sql`.
- [ ] Không đẩy các file rác hoặc môi trường ảo (`venv/`, `__pycache__/`) lên repository.
- [ ] Đã kiểm thử lại tính năng liên quan (đặt phòng, chống trùng lịch, phân quyền).