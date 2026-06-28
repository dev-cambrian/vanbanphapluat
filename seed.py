#!/usr/bin/env python3
"""
Script thêm dữ liệu mẫu cho ứng dụng Văn bản pháp luật Xây dựng

Cách dùng:
  source venv/bin/activate
  python seed.py
"""
import sys
import os
from pathlib import Path

# Đảm bảo chạy được từ thư mục bất kỳ
os.chdir(Path(__file__).resolve().parent)
sys.path.insert(0, ".")

from app import VanBan, SessionLocal, Base, engine

def seed():
    print("🔄 Đang tạo bảng...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Kiểm tra nếu đã có dữ liệu
    existing = db.query(VanBan).count()
    if existing > 0:
        print(f"⚠️  Đã có {existing} văn bản trong DB. Bỏ qua seed.")
        db.close()
        return

    samples = [
        VanBan(
            loai="Luật",
            so_hieu="55/2014/QH13",
            tieu_de="Luật Xây dựng 2014",
            nam=2014,
            co_quan="Quốc hội",
            ngay_ban_hanh="2014-06-18",
            ngay_hieu_luc="2015-01-01",
            trich_dan="Luật Xây dựng số 55/2014/QH13 ngày 18/06/2014 quy định về hoạt động xây dựng.",
            noi_dung="""# Luật Xây dựng 2014

## Chương I: NHỮNG QUY ĐỊNH CHUNG

### Điều 1. Phạm vi điều chỉnh

Luật này quy định về quyền và nghĩa vụ của tổ chức, cá nhân trong hoạt động xây dựng.

### Điều 2. Đối tượng áp dụng

1. Tổ chức, cá nhân trong nước và nước ngoài có hoạt động xây dựng trên lãnh thổ Việt Nam.
2. Cơ quan nhà nước có thẩm quyền trong hoạt động xây dựng.
""",
        ),
        VanBan(
            loai="Nghị định",
            so_hieu="15/2021/NĐ-CP",
            tieu_de="Nghị định về quản lý dự án đầu tư xây dựng",
            nam=2021,
            co_quan="Chính phủ",
            ngay_ban_hanh="2021-03-03",
            ngay_hieu_luc="2021-04-20",
            trich_dan="Quản lý dự án đầu tư xây dựng theo Nghị định 15/2021/NĐ-CP",
            noi_dung="""# Nghị định 15/2021/NĐ-CP

## Chương I: QUY ĐỊNH CHUNG

### Điều 1. Phạm vi điều chỉnh

Nghị định này quy định chi tiết một số nội dung về quản lý dự án đầu tư xây dựng.

### Điều 2. Đối tượng áp dụng

Các cơ quan, tổ chức, cá nhân có liên quan đến hoạt động đầu tư xây dựng.
""",
        ),
        VanBan(
            loai="Thông tư",
            so_hieu="10/2021/TT-BXD",
            tieu_de="Thông tư hướng dẫn về định mức xây dựng",
            nam=2021,
            co_quan="Bộ",
            ngay_ban_hanh="2021-06-15",
            ngay_hieu_luc="2021-08-01",
            trich_dan="Định mức xây dựng theo Thông tư 10/2021/TT-BXD",
            noi_dung="""# Thông tư 10/2021/TT-BXD

## Điều 1. Phạm vi điều chỉnh

Thông tư này hướng dẫn về định mức xây dựng, bao gồm định mức hao phí vật liệu, nhân công, máy thi công.
""",
        ),
        VanBan(
            loai="Quyết định",
            so_hieu="68/2023/QĐ-TTg",
            tieu_de="Quyết định phê duyệt Chiến lược phát triển nhà ở quốc gia",
            nam=2023,
            co_quan="Chính phủ",
            ngay_ban_hanh="2023-05-20",
            ngay_hieu_luc="2023-05-20",
            trich_dan="Phê duyệt Chiến lược phát triển nhà ở quốc gia đến năm 2030, tầm nhìn 2045",
            noi_dung="""# Quyết định 68/2023/QĐ-TTg

## Điều 1. Phê duyệt Chiến lược

Phê duyệt Chiến lược phát triển nhà ở quốc gia đến năm 2030, tầm nhìn đến năm 2045.
""",
        ),
        VanBan(
            loai="Tiêu chuẩn",
            so_hieu="TCVN 2737:2023",
            tieu_de="Tải trọng và tác động - Tiêu chuẩn thiết kế",
            nam=2023,
            co_quan="Bộ Khoa học và Công nghệ",
            ngay_ban_hanh="2023-12-15",
            ngay_hieu_luc="2024-07-01",
            trich_dan="Tiêu chuẩn tải trọng và tác động - TCVN 2737:2023",
            noi_dung="""# TCVN 2737:2023 - Tải trọng và tác động

## 1. Phạm vi áp dụng

Tiêu chuẩn này quy định tải trọng và tác động dùng trong thiết kế công trình xây dựng.
""",
        ),
    ]

    for vb in samples:
        db.add(vb)
    db.commit()
    db.close()
    print(f"✅ Đã thêm {len(samples)} văn bản mẫu thành công!")


if __name__ == "__main__":
    seed()
