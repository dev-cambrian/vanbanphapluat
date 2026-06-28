# Văn bản pháp luật Xây dựng

Web app tra cứu, quản lý văn bản pháp luật chuyên ngành Xây dựng. Giao diện dark theme, tìm kiếm full-text, lọc theo danh mục, xuất PDF.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.138+-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Tính năng

- **Tra cứu đa chiều** — tìm kiếm full-text, lọc theo loại văn bản (Luật, Nghị định, Thông tư, Quyết định, Hướng dẫn, Tiêu chuẩn), năm ban hành, cơ quan ban hành
- **Quản lý văn bản** — thêm, sửa, xoá văn bản pháp luật
- **Soạn thảo Markdown** — nhập nội dung bằng Markdown, hiển thị đẹp
- **Upload file gốc** — đính kèm file PDF/DOCX/TXT
- **Xuất PDF** — xuất văn bản ra file PDF (Unicode, font DejaVu)
- **Giao diện dark theme** — phong cách Hermes Agent, tối giản, chuyên nghiệp
- **Phân trang** — tự động cho danh sách dài
- **Thống kê** — hiển thị số lượng từng loại văn bản ở sidebar

## Danh mục văn bản hỗ trợ

| Loại | Mô tả |
|------|-------|
| Luật | Luật do Quốc hội ban hành |
| Nghị định | Nghị định của Chính phủ |
| Thông tư | Thông tư của Bộ, ngành |
| Quyết định | Quyết định của Thủ tướng, Bộ trưởng |
| Hướng dẫn | Văn bản hướng dẫn thi hành |
| Tiêu chuẩn | TCVN, TCXD, tiêu chuẩn ngành |

## Yêu cầu

- Python 3.11 trở lên
- pip (Python package manager)
- ~3.7 GB RAM (tối thiểu)
- Hệ điều hành: Linux, macOS, Windows

## Cài đặt nhanh

### 1. Clone hoặc tải project

```bash
git clone <url-của-repo> vanbanphapluat
cd vanbanphapluat
```

Hoặc nếu có sẵn thư mục project:

```bash
cd ~/Documents/dev-project/vanbanphapluat
```

### 2. Tạo môi trường ảo

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows
```

### 3. Cài dependencies

```bash
pip install --upgrade pip
pip install fastapi uvicorn[standard] jinja2 python-multipart aiosqlite sqlalchemy markdown fpdf2
```

### 4. Chạy ứng dụng

```bash
python app.py
```

Server sẽ chạy tại **http://localhost:8000**

Mở trình duyệt và vào địa chỉ đó để bắt đầu sử dụng.

## Cấu trúc thư mục

```
vanbanphapluat/
├── app.py                # Ứng dụng FastAPI chính
├── vanban.db             # Cơ sở dữ liệu SQLite (tự động tạo)
├── .gitignore
├── README.md
├── requirements.txt      # Danh sách dependencies (xem bên dưới)
├── uploads/              # File upload (PDF, DOCX, TXT)
├── static/               # File tĩnh (font DejaVu)
└── templates/            # Jinja2 HTML templates
    ├── base.html          # Layout chung (sidebar, topbar, dark theme)
    ├── index.html         # Trang chủ — danh sách + tìm kiếm + lọc
    ├── detail.html        # Chi tiết văn bản
    └── form.html          # Form thêm/sửa văn bản
```

## API endpoints

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/` | Trang chủ — danh sách + tìm kiếm + lọc |
| GET | `/vanban/{id}` | Chi tiết văn bản |
| GET | `/them` | Form thêm văn bản |
| POST | `/them` | Lưu văn bản mới |
| GET | `/sua/{id}` | Form sửa văn bản |
| POST | `/sua/{id}` | Lưu thay đổi văn bản |
| POST | `/xoa/{id}` | Xoá văn bản |
| GET | `/xuat-pdf/{id}` | Xuất PDF văn bản |
| GET | `/uploads/{filename}` | Tải file gốc |

## Ví dụ dữ liệu

Sau khi chạy ứng dụng, bạn có thể thêm văn bản qua giao diện hoặc dùng curl:

```bash
curl -X POST http://localhost:8000/them \
  -d "loai=Luật" \
  -d "so_hieu=55/2014/QH13" \
  -d "tieu_de=Luật Xây dựng 2014" \
  -d "nam=2014" \
  -d "co_quan=Quốc hội" \
  -d "noi_dung=# Chương I - Những quy định chung\n\nLuật này quy định về hoạt động xây dựng..."
```

## requirements.txt

Nếu muốn cài từ file `requirements.txt`, tạo file với nội dung:

```
fastapi>=0.138
uvicorn[standard]>=0.49
jinja2>=3.1
python-multipart>=0.0.32
aiosqlite>=0.22
sqlalchemy>=2.0
markdown>=3.10
fpdf2>=2.8
```

Rồi chạy:

```bash
pip install -r requirements.txt
```

## License

MIT License — được sử dụng tự do cho mục đích cá nhân và thương mại.

---

*Xây dựng bởi [dev-cambrian](https://github.com/dev-cambrian) với Hermes Agent*
