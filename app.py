#!/usr/bin/env python3
"""
Ứng dụng tra cứu văn bản pháp luật chuyên ngành Xây dựng
FastAPI + SQLite + Dark theme (Hermes-style)
"""

import os
import shutil
import re
from datetime import datetime
from pathlib import Path

import markdown
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

# --- PDF
from fpdf import FPDF

# --- Config
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "vanban.db"

# --- Database setup
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
    loai = Column(String(50), nullable=False, index=True)        # Luật, NĐ, TT, QĐ, Hướng dẫn, Tiêu chuẩn
    so_hieu = Column(String(200), default="")                    # Số hiệu
    tieu_de = Column(String(500), nullable=False)                # Tiêu đề
    nam = Column(Integer, index=True, default=datetime.now().year)
    co_quan = Column(String(200), default="")                    # Cơ quan ban hành
    ngay_ban_hanh = Column(String(20), default="")               # YYYY-MM-DD
    ngay_hieu_luc = Column(String(20), default="")
    trich_dan = Column(Text, default="")                         # Tóm tắt / trích dẫn
    noi_dung = Column(Text, default="")                          # Nội dung markdown
    file_goc = Column(String(500), default="")                   # File upload gốc
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


Base.metadata.create_all(bind=engine)


# --- FastAPI app
app = FastAPI(title="Văn bản pháp luật Xây dựng")

# --- Context processor (thêm biến chung cho mọi template)
def common_context(request: Request):
    db = SessionLocal()
    try:
        stats = {}
        for l in LOAI_VANBAN:
            cnt = db.query(VanBan).filter(VanBan.loai == l).count()
            if cnt > 0:
                stats[l] = cnt
        total = db.query(VanBan).count()
        years = sorted(
            r[0]
            for r in db.query(VanBan.nam).distinct().filter(VanBan.nam.isnot(None)).all()
            if r[0]
        )
    finally:
        db.close()
    return {
        "stats": stats,
        "total": total,
        "years": years,
        "loai_list": LOAI_VANBAN,
        "co_quan_list": CO_QUAN_LIST,
    }


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates"),
    context_processors=[common_context],
)
templates.env.globals["now"] = datetime.now


# --- Dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Danh mục loại văn bản
LOAI_VANBAN = ["Luật", "Nghị định", "Thông tư", "Quyết định", "Hướng dẫn", "Tiêu chuẩn"]

CO_QUAN_LIST = [
    "Quốc hội",
    "Chính phủ",
    "Thủ tướng Chính phủ",
    "Bộ Xây dựng",
    "Bộ Tài nguyên và Môi trường",
    "Bộ Kế hoạch và Đầu tư",
    "Bộ Tài chính",
    "Bộ Công Thương",
    "Bộ Giao thông Vận tải",
    "Bộ Nông nghiệp và Phát triển nông thôn",
    "Bộ Khoa học và Công nghệ",
    "Bộ Công an",
    "Bộ Quốc phòng",
    "Bộ Nội vụ",
    "Bộ Tư pháp",
    "Bộ Lao động - Thương binh và Xã hội",
    "Bộ Văn hóa, Thể thao và Du lịch",
    "Bộ Thông tin và Truyền thông",
    "Bộ Y tế",
    "Bộ Giáo dục và Đào tạo",
    "Ủy ban nhân dân cấp tỉnh",
    "Hội đồng nhân dân",
    "Liên bộ",
    "Khác",
]


# --- Helpers
def extract_text_from_file(filepath: str) -> str:
    """Trích xuất text từ file upload."""
    ext = Path(filepath).suffix.lower()
    try:
        if ext == ".txt":
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".md":
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        elif ext in (".pdf", ".docx"):
            # Trả về thông báo, user sẽ xem file gốc
            return f"*[Nội dung trong file: {Path(filepath).name} — hãy tải file gốc để xem]*"
        else:
            return ""
    except Exception:
        return ""


def md_to_html(text: str) -> str:
    """Chuyển markdown -> HTML."""
    if not text:
        return ""
    return markdown.markdown(text, extensions=["extra", "codehilite"])


def generate_pdf(vanban: VanBan) -> bytes:
    """Tạo PDF từ văn bản."""
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", str(BASE_DIR / "static" / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(BASE_DIR / "static" / "DejaVuSans-Bold.ttf"))

    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, vanban.tieu_de, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    pdf.set_font("DejaVu", "", 10)
    meta = f"Loại: {vanban.loai}  |  Số hiệu: {vanban.so_hieu or '—'}"
    pdf.cell(0, 8, meta, new_x="LMARGIN", new_y="NEXT")
    meta2 = f"Cơ quan: {vanban.co_quan or '—'}  |  Năm: {vanban.nam}"
    pdf.cell(0, 8, meta2, new_x="LMARGIN", new_y="NEXT")
    if vanban.ngay_ban_hanh:
        pdf.cell(0, 8, f"Ngày ban hành: {vanban.ngay_ban_hanh}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Trích dẫn
    if vanban.trich_dan:
        pdf.set_font("DejaVu", "B", 11)
        pdf.cell(0, 10, "Trích dẫn:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", "", 10)
        pdf.multi_cell(0, 6, vanban.trich_dan)
        pdf.ln(5)

    # Nội dung
    if vanban.noi_dung:
        pdf.set_font("DejaVu", "B", 11)
        pdf.cell(0, 10, "Nội dung:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", "", 10)
        text = vanban.noi_dung
        text = re.sub(r"#{1,6}\s*", "", text)
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"\*(.*?)\*", r"\1", text)
        text = re.sub(r"`(.*?)`", r"\1", text)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
        text = re.sub(r"[-*]\s", "• ", text)
        # Clean invalid chars
        text = text.encode("utf-8", errors="replace").decode("utf-8")
        pdf.multi_cell(0, 6, text)

    return bytes(pdf.output())


# =========== ROUTES ===========

@app.get("/", response_class=HTMLResponse)
async def trang_chu(
    request: Request,
    search: str = "",
    loai: str = "",
    nam: str = "",
    co_quan: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):
    per_page = 20
    query = db.query(VanBan)

    if search:
        like = f"%{search}%"
        query = query.filter(
            (VanBan.tieu_de.ilike(like))
            | (VanBan.so_hieu.ilike(like))
            | (VanBan.trich_dan.ilike(like))
            | (VanBan.noi_dung.ilike(like))
            | (VanBan.co_quan.ilike(like))
        )
    if loai:
        query = query.filter(VanBan.loai == loai)
    if nam:
        query = query.filter(VanBan.nam == int(nam))
    if co_quan:
        query = query.filter(VanBan.co_quan == co_quan)

    total = query.count()
    query = query.order_by(VanBan.updated_at.desc())
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse(request, "index.html", {
        "items": items,
        "search": search,
        "loai_filter": loai,
        "nam_filter": nam,
        "co_quan_filter": co_quan,
        "page": page,
        "total_pages": total_pages,
        "filtered_total": total,
    })


@app.get("/vanban/{vanban_id}", response_class=HTMLResponse)
async def chi_tiet(vanban_id: int, request: Request, db: Session = Depends(get_db)):
    vb = db.query(VanBan).filter(VanBan.id == vanban_id).first()
    if not vb:
        raise HTTPException(404, "Không tìm thấy văn bản")
    content_html = md_to_html(vb.noi_dung)
    return templates.TemplateResponse(request, "detail.html", {
        "vb": vb,
        "content_html": content_html,
    })


@app.get("/them", response_class=HTMLResponse)
async def them_form(request: Request):
    return templates.TemplateResponse(request, "form.html", {
        "vb": None,
    })


@app.post("/them")
async def them_submit(
    request: Request,
    loai: str = Form(...),
    so_hieu: str = Form(""),
    tieu_de: str = Form(...),
    nam: int = Form(datetime.now().year),
    co_quan: str = Form(""),
    ngay_ban_hanh: str = Form(""),
    ngay_hieu_luc: str = Form(""),
    trich_dan: str = Form(""),
    noi_dung: str = Form(""),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    file_goc = ""
    if file and file.filename:
        safe_name = f"{int(datetime.now().timestamp())}_{file.filename}"
        filepath = UPLOAD_DIR / safe_name
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        file_goc = safe_name

        # Nếu không có nội dung text, thử trích xuất từ file
        if not noi_dung:
            noi_dung = extract_text_from_file(str(filepath))

    vb = VanBan(
        loai=loai,
        so_hieu=so_hieu,
        tieu_de=tieu_de,
        nam=nam,
        co_quan=co_quan,
        ngay_ban_hanh=ngay_ban_hanh or None,
        ngay_hieu_luc=ngay_hieu_luc or None,
        trich_dan=trich_dan,
        noi_dung=noi_dung,
        file_goc=file_goc,
    )
    db.add(vb)
    db.commit()

    return RedirectResponse(url=f"/vanban/{vb.id}", status_code=303)


@app.get("/sua/{vanban_id}", response_class=HTMLResponse)
async def sua_form(vanban_id: int, request: Request, db: Session = Depends(get_db)):
    vb = db.query(VanBan).filter(VanBan.id == vanban_id).first()
    if not vb:
        raise HTTPException(404, "Không tìm thấy văn bản")
    return templates.TemplateResponse(request, "form.html", {
        "vb": vb,
    })


@app.post("/sua/{vanban_id}")
async def sua_submit(
    vanban_id: int,
    loai: str = Form(...),
    so_hieu: str = Form(""),
    tieu_de: str = Form(...),
    nam: int = Form(datetime.now().year),
    co_quan: str = Form(""),
    ngay_ban_hanh: str = Form(""),
    ngay_hieu_luc: str = Form(""),
    trich_dan: str = Form(""),
    noi_dung: str = Form(""),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    vb = db.query(VanBan).filter(VanBan.id == vanban_id).first()
    if not vb:
        raise HTTPException(404, "Không tìm thấy văn bản")

    if file and file.filename:
        safe_name = f"{int(datetime.now().timestamp())}_{file.filename}"
        filepath = UPLOAD_DIR / safe_name
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        # Xoá file cũ nếu có
        if vb.file_goc:
            old_path = UPLOAD_DIR / vb.file_goc
            if old_path.exists():
                old_path.unlink()
        vb.file_goc = safe_name

        if not noi_dung:
            noi_dung = extract_text_from_file(str(filepath))

    vb.loai = loai
    vb.so_hieu = so_hieu
    vb.tieu_de = tieu_de
    vb.nam = nam
    vb.co_quan = co_quan
    vb.ngay_ban_hanh = ngay_ban_hanh or None
    vb.ngay_hieu_luc = ngay_hieu_luc or None
    vb.trich_dan = trich_dan
    vb.noi_dung = noi_dung
    db.commit()

    return RedirectResponse(url=f"/vanban/{vanban_id}", status_code=303)


@app.post("/xoa/{vanban_id}")
async def xoa(vanban_id: int, db: Session = Depends(get_db)):
    vb = db.query(VanBan).filter(VanBan.id == vanban_id).first()
    if not vb:
        raise HTTPException(404, "Không tìm thấy văn bản")
    if vb.file_goc:
        fp = UPLOAD_DIR / vb.file_goc
        if fp.exists():
            fp.unlink()
    db.delete(vb)
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/xuat-pdf/{vanban_id}")
async def xuat_pdf(vanban_id: int, db: Session = Depends(get_db)):
    vb = db.query(VanBan).filter(VanBan.id == vanban_id).first()
    if not vb:
        raise HTTPException(404, "Không tìm thấy văn bản")
    pdf_bytes = generate_pdf(vb)
    filename = f"{vb.so_hieu or vb.tieu_de}.pdf".replace("/", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/uploads/{filename}")
async def tai_file(filename: str):
    fp = UPLOAD_DIR / filename
    if not fp.exists():
        raise HTTPException(404)
    return Response(
        content=fp.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
