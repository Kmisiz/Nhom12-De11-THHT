# Chủ đề 11: Chuẩn hóa và chuyển đổi thông điệp bằng Enterprise Integration Patterns

Hệ thống Integration Adapter đứng giữa các kênh đăng ký học phần (Portal, Mobile, Legacy) và dịch vụ Tài chính (Finance API), thực hiện chuẩn hóa dữ liệu về mô hình Canonical, kiểm tra hợp lệ, tra cứu đơn giá, lọc trường dữ liệu (whitelist) và chuyển tiếp khoản học phí sang Finance.

---

## 1. Yêu cầu cài đặt

* **Python:** Phiên bản `3.12` (không dùng bản 3.15 thử nghiệm).
* **Postman:** Bản **Postman Desktop** (bản web không gọi được `127.0.0.1`).
* **Git** và **VS Code** (khuyến nghị).

---

## 2. Cài đặt môi trường & Thư viện

Mở PowerShell tại thư mục gốc của dự án và chạy các lệnh sau:

```powershell
# Tạo môi trường ảo với Python 3.12
py -3.12 -m venv .venv

# Kích hoạt môi trường ảo (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt