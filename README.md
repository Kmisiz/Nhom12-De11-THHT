# Chủ đề 11: Chuẩn hóa và chuyển đổi thông điệp bằng Enterprise Integration Patterns

Hệ thống Integration Adapter đứng giữa các kênh đăng ký học phần (Portal, Mobile, Legacy) và dịch vụ Tài chính (Finance API), thực hiện chuẩn hóa dữ liệu về mô hình Canonical, kiểm tra hợp lệ, tra cứu đơn giá, lọc trường dữ liệu (whitelist) và chuyển tiếp khoản học phí sang Finance.

Pattern áp dụng: Normalizer (Content-Based Router + 3 Message Translator), Canonical Data Model, Content Enricher, Content Filter, Invalid Message Channel, Idempotent Receiver, Message Store.

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
```

Nếu PowerShell báo không cho chạy script khi kích hoạt `.venv`, chạy một lần: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

---

## 3. Chạy kiểm thử tự động

```powershell
pytest -v
```

Kết quả đúng: **69 passed**. Kiểm thử dùng Flask test client, không cần bật dịch vụ.

---

## 4. Chạy hệ thống

Mỗi dịch vụ chạy trong **một cửa sổ PowerShell riêng**, cả hai đứng ở thư mục gốc dự án và đã kích hoạt `.venv`.

**Bước 1. Bắt đầu từ dữ liệu sạch** (bắt buộc trước mỗi lần chạy Postman):

```powershell
Remove-Item -Recurse -Force runtime -ErrorAction SilentlyContinue
```

**Bước 2. Cửa sổ 1: bật Finance** (cổng 5001):

```powershell
python -m finance.app
```

**Bước 3. Cửa sổ 2: bật Adapter** (cổng 5000):

```powershell
python -m adapter.app
```

Kiểm tra nhanh: mở `http://127.0.0.1:5000/health` và `http://127.0.0.1:5001/health`, cả hai trả `{"status": "ok"}`.

Biến môi trường (không bắt buộc, đã có giá trị mặc định):

| Biến | Dịch vụ | Mặc định |
|---|---|---|
| `FINANCE_URL` | Adapter | `http://127.0.0.1:5001` |
| `PRICE_FILE` | Adapter | `data/course_prices.csv` |
| `RUNTIME_DIR` | Adapter | `runtime` |
| `FINANCE_DB` | Finance | `runtime/finance.db` |

---

## 5. Chạy kiểm thử tích hợp bằng Postman

1. Mở Postman Desktop, chọn **Import**, chọn file `postman/Chu_de_11_EIP.postman_collection.json`.
2. Bấm vào collection, chọn **Run**. Chỉ tích các thư mục **0 đến 5**, bỏ thư mục 6, rồi bấm **Run**.
3. Kết quả đúng: **25 request, 60 kiểm tra, 0 failed**. Finance có 10 khoản học phí, tổng 15.200.000 VND.

> Chạy Postman lần hai mà không xóa `runtime/` thì phiếu SV001 đầu tiên trả 200 `DUPLICATE_IGNORED` thay vì 201 và kiểm tra báo đỏ. Đây là hành vi đúng của cơ chế chống trùng. Tắt Finance, làm lại từ Bước 1 của mục 4.

### Thư mục 6: kịch bản sự cố (chạy tay, đúng thứ tự)

| Request | Trước khi gửi | Kết quả đúng |
|---|---|---|
| S2 - Bảng giá không đọc được | Đổi tên `data/course_prices.csv` thành `course_prices.csv.bak`. Gửi xong thì đổi tên lại như cũ | 503 `LOOKUP_UNAVAILABLE` |
| S1a - Finance đang tắt | Nhấn `Ctrl+C` ở cửa sổ đang chạy Finance | 503 `FINANCE_UNAVAILABLE` |
| S1b - Gửi lại sau khi bật Finance | Chạy lại `python -m finance.app` ở cửa sổ 1 | 201 `FORWARDED` |
| Finance có 11 khoản | | 11 khoản học phí |

---

## 6. Xem dữ liệu qua từng bước

Adapter ghi ra thư mục `runtime/`:

| Vị trí | Nội dung |
|---|---|
| `runtime/traces/` | Mỗi thông điệp một file: dữ liệu sau từng bước `input`, `normalized`, `enriched`, `filtered` |
| `runtime/logs/adapter.jsonl` | Mỗi thông điệp một dòng log |
| `runtime/invalid/` | Invalid Message Channel: chỉ thông điệp lỗi do dữ liệu (400, 422), kèm `error_code` và `stage`. Sau thư mục 4 có đúng 5 file X1–X5 |
| `runtime/finance.db` | Cơ sở dữ liệu SQLite của Finance |

Ba file trace SV001 (`*_PORTAL-P-1001.json`, `*_MOBILE-M-2001.json`, `*_LEGACY-L-3001.json`) có khối `filtered` giống nhau, chỉ khác `message_id`: ba định dạng đầu vào cho ra cùng một kết quả.

---

## 7. Cấu trúc thư mục

```
adapter/
  normalizer.py       Normalizer: Content-Based Router + 3 Message Translator
  validator.py        Kiểm tra dữ liệu bắt buộc
  enricher.py         Content Enricher: tra đơn giá, tính thành tiền
  content_filter.py   Content Filter: chỉ giữ 9 trường cho Finance
  pipeline.py         Pipes and Filters: gọi 4 bước theo thứ tự
  finance_client.py   Gửi HTTP sang Finance
  app.py              POST /api/registrations, ghi trace, log, invalid
  errors.py           AdapterError dùng chung
finance/
  db.py               SQLite, ràng buộc UNIQUE chống thu tiền hai lần
  app.py              POST/GET /api/tuition-charges
data/                 Bảng đơn giá và 18 file dữ liệu mẫu (giả lập)
postman/              Postman collection (29 request)
tests/                Kiểm thử tự động (pytest)
evidence/             Bằng chứng kiểm thử
```

---

## 8. Bằng chứng kiểm thử (`evidence/`)

| File | Nội dung |
|---|---|
| `pytest.txt` | Kết quả `pytest -v`: 69 passed |
| `postman_run.json`, `01_postman_runner_0_5.png` | Postman Runner thư mục 0–5: 60 kiểm tra, 0 failed |
| `02_su_co_S2_bang_gia.png` … `05_su_co_finance_11_khoan.png` | Kịch bản sự cố S2, S1a, S1b |
| `*_PORTAL-P-1001.json`, `*_MOBILE-M-2001.json`, `*_LEGACY-L-3001.json` | Trace SV001 qua 3 kênh |
| `*_PORTAL-P-9001.json`, `*_LEGACY-L-9003.json` | Trace phiếu lỗi X1 (thiếu trường), X3 (tra cứu thất bại) |
| `invalid/` | 5 file Invalid Message Channel của X1–X5 |

Toàn bộ dữ liệu trong `data/` là dữ liệu giả lập, không chứa thông tin cá nhân thật.

---

## 9. Công cụ AI đã sử dụng

Nhóm dùng trợ lý AI Claude (Anthropic) để tra cứu lý thuyết EIP, rà soát thiết kế, hỗ trợ viết tài liệu và rà soát mã nguồn. Mọi kết quả được nhóm tự kiểm chứng bằng bộ kiểm thử tự động (pytest) và Postman collection.
