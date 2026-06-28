#!/usr/bin/env python3
"""
Scraper tự động lấy văn bản pháp luật từ nguồn Công báo Chính phủ.
Chạy 1 lần, lấy tất cả văn bản liên quan đến Xây dựng từ RSS.

Cách dùng:
  source venv/bin/activate
  python scrape_legal.py

Nguồn: https://congbao.chinhphu.vn/cac-van-ban-moi-ban-hanh.rss
"""
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

# ─── Cấu hình ─────────────────────────────────────────────
RSS_URL = "https://congbao.chinhphu.vn/cac-van-ban-moi-ban-hanh.rss"
# Delay giữa các requests (tránh bị chặn)
REQUEST_DELAY = 1.5  # giây

# Từ khoá lọc văn bản liên quan Xây dựng
KEYWORDS_BUILDING = [
    "xây dựng", "xay dung", "nhà ở", "nha o", "đô thị", "do thi",
    "công trình", "cong trinh", "kiến trúc", "kien truc",
    "hạ tầng", "ha tang", "vật liệu", "vat lieu",
    "đất đai", "dat dai", "quy hoạch", "quy hoach",
    "đầu tư xây dựng", "dau tu xay dung", "xây dựng công trình",
    "chất lượng công trình", "chat luong cong trinh",
    "giao thông", "gia thong", "cầu đường", "cau duong",
    "quy hoạch xây dựng", "phát triển nhà", "phat trien nha",
    "BXD", "Bộ Xây dựng", "Bo Xay dung",
]

# Map loại văn bản từ URL sang danh mục trong app
LOAI_MAP = {
    "nghi-dinh": "Nghị định",
    "nghi-quyet": "Nghị định",       # Nghị quyết → tạm xếp Nghị định
    "thong-tu": "Thông tư",
    "quyet-dinh": "Quyết định",
    "chi-thi": "Hướng dẫn",          # Chỉ thị → tạm xếp Hướng dẫn
    "van-ban-hop-nhat": "Hướng dẫn", # Văn bản hợp nhất → Hướng dẫn
}

CO_QUAN_MAP = {
    "Chính phủ": "Chính phủ",
    "Thủ tướng": "Chính phủ",
    "BXD": "Bộ",
    "Bộ Xây dựng": "Bộ",
    "BTC": "Bộ",
    "BCT": "Bộ",
    "BKHCN": "Bộ",
    "BGDDT": "Bộ",
    "BTTTT": "Bộ",
    "BNN": "Bộ",
    "BQP": "Bộ",
    "BCA": "Bộ",
    "BNV": "Bộ",
    "BTP": "Bộ",
}

# ─── Database ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "vanban.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class VanBan(Base):
    __tablename__ = "vanban"
    id = Column(Integer, primary_key=True, index=True)
    loai = Column(String(50), nullable=False, index=True)
    so_hieu = Column(String(200), default="")
    tieu_de = Column(String(500), nullable=False)
    nam = Column(Integer, index=True, default=datetime.now().year)
    co_quan = Column(String(200), default="")
    ngay_ban_hanh = Column(String(20), default="")
    ngay_hieu_luc = Column(String(20), default="")
    trich_dan = Column(Text, default="")
    noi_dung = Column(Text, default="")
    file_goc = Column(String(500), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ─── Helper ────────────────────────────────────────────────

def is_xaydung_related(text: str) -> bool:
    """Kiểm tra văn bản có liên quan Xây dựng không."""
    if not text:
        return False
    text_lower = text.lower()
    for kw in KEYWORDS_BUILDING:
        if kw.lower() in text_lower:
            return True
    return False


def extract_loai_sohieu(url: str) -> tuple:
    """Trích xuất loại văn bản + số hiệu từ URL.
    Ví dụ: /van-ban/nghi-dinh-so-209-2026-nd-cp-469771.htm
    → ('Nghị định', '209/2026/NĐ-CP')
    """
    # Lấy phần giữa domain và .htm
    match = re.search(r'/van-ban/([^/]+?)\.htm', url)
    if not match:
        return ("Văn bản", "")

    slug = match.group(1)

    # Xác định loại
    loai = "Văn bản"
    for key, val in LOAI_MAP.items():
        if slug.startswith(key):
            loai = val
            break

    # Trích số hiệu (chỉ lấy đến trước dấu - cuối cùng hoặc kết thúc)
    # Pattern: so-209-2026-nd-cp-469771 → 209/2026/NĐ-CP
    # Pattern: so-861-qd-bxd-469737 → 861/QĐ-BXD
    # Pattern: so-1062-qd-ttg-469763 → 1062/QĐ-TTg
    # Pattern: so-27-vbhn-bxd-469765 → 27/VBHN-BXD
    sohieu_match = re.search(r'so-(\d+)-(\d{4})([a-z-]+?)(?:-\d+)?$', slug)
    if sohieu_match:
        so = sohieu_match.group(1)
        nam = sohieu_match.group(2)
        suffix = sohieu_match.group(3).strip('-')

        # Chuẩn hoá ký hiệu
        suffix = suffix.upper()
        suffix = suffix.replace("ND-CP", "NĐ-CP")
        suffix = suffix.replace("CT-TTG", "CT-TTg")
        suffix = suffix.replace("QD-BXD", "QĐ-BXD")
        suffix = suffix.replace("QD-TTG", "QĐ-TTg")
        suffix = suffix.replace("QD-", "QĐ-")
        suffix = suffix.replace("TT-BXD", "TT-BXD")
        suffix = suffix.replace("TT-BKHCN", "TT-BKHCN")
        suffix = suffix.replace("TT-BCT", "TT-BCT")
        suffix = suffix.replace("TT-BGDDT", "TT-BGDĐT")
        suffix = suffix.replace("TT-BNN", "TT-BNN")
        suffix = suffix.replace("TT-NHNN", "TT-NHNN")
        suffix = suffix.replace("TT-BTTTT", "TT-BTTTT")
        suffix = suffix.replace("TT-BTC", "TT-BTC")
        suffix = suffix.replace("VBHN-", "VBHN-")
        suffix = suffix.replace("CT-TTG", "CT-TTg")

        so_hieu = f"{so}/{nam}/{suffix}"
        return (loai, so_hieu)

    # Pattern không có năm: so-26-ct-ttg-469761 → 26/CT-TTg
    # Pattern không có năm: so-27-vbhn-bxd-469765 → 27/VBHN-BXD
    sohieu_match2 = re.search(r'so-(\d+)-([a-z-]+?)(?:-\d+)?$', slug)
    if sohieu_match2:
        so = sohieu_match2.group(1)
        suffix = sohieu_match2.group(2).upper()
        # Chuẩn hoá
        suffix = suffix.replace("CT-TTG", "CT-TTg")
        suffix = suffix.replace("QD-BXD", "QĐ-BXD")
        suffix = suffix.replace("QD-TTG", "QĐ-TTg")
        suffix = suffix.replace("VBHN-BXD", "VBHN-BXD")
        so_hieu = f"{so}/{suffix}"
        return (loai, so_hieu)

    return (loai, "")


def extract_co_quan(so_hieu: str, title: str, description: str) -> str:
    """Xác định cơ quan ban hành từ số hiệu."""
    sogoc = so_hieu.upper()

    if "QH" in sogoc or "QUỐC HỘI" in sogoc:
        return "Quốc hội"
    if "ND-CP" in sogoc:
        return "Chính phủ"
    if "QD-TTg" in sogoc or "QD-TTG" in sogoc or "CT-TTg" in sogoc:
        return "Chính phủ"
    if "TT-BXD" in sogoc or "VBHN-BXD" in sogoc:
        return "Bộ"
    if "TT-BKHCN" in sogoc:
        return "Bộ"
    if "TT-BCT" in sogoc:
        return "Bộ"
    if "TT-BGDDT" in sogoc or "TT-BGDĐT" in sogoc:
        return "Bộ"
    if "TT-BNN" in sogoc:
        return "Bộ"
    if "TT-NHNN" in sogoc:
        return "Cơ quan khác"
    if "TT-BTTTT" in sogoc:
        return "Bộ"
    if "TT-BTC" in sogoc:
        return "Bộ"
    if "NQ-CP" in sogoc:
        return "Chính phủ"

    # Nếu không match, đoán từ nội dung
    title_lower = (title + " " + description).lower()
    for key, val in CO_QUAN_MAP.items():
        if key.lower() in title_lower:
            return val

    return "Cơ quan khác"


def extract_full_title(client: httpx.Client, url: str) -> str:
    """Vào trang chi tiết để lấy tên đầy đủ từ thẻ H1."""
    try:
        resp = client.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text(strip=True)
            if text:
                return text
    except Exception:
        pass
    return ""


def format_date(rss_date: str) -> str:
    """Chuyển RSS date sang YYYY-MM-DD."""
    try:
        # Parse: Tue, 16 Jun 2026 00:00:00 GMT
        dt = datetime.strptime(rss_date, "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


# ─── Main ──────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("SCRAPER VĂN BẢN PHÁP LUẬT XÂY DỰNG")
    print(f"Nguồn: {RSS_URL}")
    print("=" * 60)

    # Tạo DB nếu chưa có
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Fetch RSS
        print("\n[1] Đang lấy RSS feed...")
        rss_resp = httpx.get(RSS_URL, timeout=30)
        rss_resp.raise_for_status()

        root = ET.fromstring(rss_resp.content)
        items = root.findall(".//item")

        print(f"  → Tổng số văn bản trong RSS: {len(items)}")

        # Lọc văn bản liên quan Xây dựng
        candidates = []
        for item in items:
            title_text = item.findtext("title", "")
            desc_text = item.findtext("description", "")
            full_text = title_text + " " + desc_text

            if is_xaydung_related(full_text):
                pub_date = item.findtext("pubDate", "")
                link = item.findtext("link", "")
                candidates.append({
                    "desc": desc_text.strip() or title_text.strip(),
                    "date": pub_date,
                    "url": link,
                })

        print(f"  → Văn bản liên quan Xây dựng: {len(candidates)}")

        if not candidates:
            print("\n⚠️  Không tìm thấy văn bản Xây dựng nào trong RSS hiện tại.")
            print("   Thử mở rộng từ khoá hoặc chạy lại sau khi có RSS mới.")
            return

        # Kiểm tra trùng lặp với DB hiện tại
        existing_sohieus = set(
            r[0] for r in db.query(VanBan.so_hieu).filter(VanBan.so_hieu != "").all()
        )
        new_count = 0
        skip_count = 0
        error_count = 0

        print("\n[2] Đang xử lý từng văn bản...")
        client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
                "Accept": "text/html,application/xhtml+xml",
            },
            follow_redirects=True,
            timeout=20,
        )

        for i, cand in enumerate(candidates, 1):
            url = cand["url"]
            desc = cand["desc"]
            rss_date = cand["date"]

            # Trích xuất loại + số hiệu từ URL
            loai, so_hieu = extract_loai_sohieu(url)

            # Kiểm tra trùng
            if so_hieu and so_hieu in existing_sohieus:
                print(f"  [{i}/{len(candidates)}] ⏭️  {so_hieu} — đã có trong DB")
                skip_count += 1
                continue

            # Fetch chi tiết để lấy title đầy đủ
            print(f"  [{i}/{len(candidates)}] {url.split('/')[-1][:50]}...", end=" ", flush=True)
            full_title = extract_full_title(client, url)
            time.sleep(REQUEST_DELAY)

            if not full_title:
                # Fallback: dùng description từ RSS
                full_title = desc
                if not full_title:
                    print("⚠️  Bỏ qua (không có title)")
                    error_count += 1
                    continue

            # Xác định cơ quan ban hành
            co_quan = extract_co_quan(so_hieu, full_title, desc)

            # Xác định năm
            nam = datetime.now().year
            nam_match = re.search(r'/20(\d{2})', so_hieu)
            if nam_match:
                nam = 2000 + int(nam_match.group(1))

            # Format ngày ban hành
            ngay_bh = format_date(rss_date)

            # Tóm tắt: dùng description từ RSS
            trich_dan = desc

            # Tạo văn bản mới
            vanban = VanBan(
                loai=loai,
                so_hieu=so_hieu,
                tieu_de=full_title,
                nam=nam,
                co_quan=co_quan,
                ngay_ban_hanh=ngay_bh,
                trich_dan=trich_dan,
            )
            db.add(vanban)
            db.commit()

            existing_sohieus.add(so_hieu)
            new_count += 1
            print(f"✅ {so_hieu}")

        client.close()

        # Tổng kết
        print("\n" + "=" * 60)
        print(f"✅ HOÀN THÀNH!")
        print(f"   - Đã thêm mới: {new_count} văn bản")
        print(f"   - Bỏ qua (đã có): {skip_count}")
        print(f"   - Lỗi: {error_count}")

        # Hiển thị các văn bản mới
        if new_count > 0:
            print(f"\n📋 Danh sách văn bản mới:")
            new_vanbans = (
                db.query(VanBan)
                .order_by(VanBan.ngay_ban_hanh.desc())
                .limit(20)
                .all()
            )
            for vb in new_vanbans:
                print(f"   [{vb.loai}] {vb.so_hieu} — {vb.tieu_de[:80]}")

        # Thống kê
        total = db.query(VanBan).count()
        print(f"\n📊 Tổng số văn bản trong DB: {total}")

    except httpx.HTTPError as e:
        print(f"\n❌ Lỗi HTTP: {e}")
        if "403" in str(e):
            print("   ⚠️  Nguồn có thể đã chặn truy cập. Thử lại sau hoặc dùng VPN.")
        if "timeout" in str(e).lower():
            print("   ⚠️  Kết nối chậm. Thử tăng timeout hoặc chạy lại.")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    print("\n💡 Mẹo: Chạy lại script này sau để cập nhật văn bản mới.")
    print("   Văn bản đã có sẽ tự động bỏ qua (kiểm tra theo số hiệu).")


if __name__ == "__main__":
    main()
