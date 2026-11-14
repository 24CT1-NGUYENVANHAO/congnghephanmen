# Báo cáo giữa kỳ SáchGóc Uni — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sinh file `docs/BaoCao_GiuaKy_CNPM_SachGocUni.docx` đúng khung 2 chương của giảng viên, đúng định dạng file mẫu, dùng dữ liệu thật của dự án.

**Architecture:** Hai script Python ở root: `make_report_assets.py` sinh toàn bộ hình (SVG tự vẽ → PNG qua Chrome headless, chụp HTML Figma, chụp app đang chạy), `make_report.py` dựng .docx bằng python-docx. Kiểm chứng bằng Word COM → PDF → PNG từng trang (PyMuPDF).

**Tech Stack:** Python 3.11, python-docx 1.2, matplotlib 3.11, Pillow 12, pywin32, PyMuPDF 1.28, Chrome headless, Django 4.2/5.2.

**Spec:** `docs/superpowers/specs/2026-11-15-bao-cao-giua-ky-design.md`

## Global Constraints

- Khổ A4; lề trái 3.5 cm, phải 2.5 cm, trên 2.5 cm, dưới 2.5 cm.
- Font Times New Roman 14 pt; giãn dòng 1.15; space_after 6 pt.
- Chú thích hình: `Hình N. …` in nghiêng, canh giữa, ngay dưới hình. Chú thích bảng: `Bảng N. …` in nghiêng, canh giữa, ngay trên bảng.
- Mỗi chương bắt đầu trang mới: `CHƯƠNG N: …` in đậm, canh giữa.
- Ảnh rộng tối đa 15.5 cm, canh giữa.
- Nội dung tiếng Việt có dấu; xưng "em", không xưng "nhóm" (báo cáo cá nhân).
- Không commit/push khi chưa có xác nhận.

## Review Focus

- Số hiệu hình/bảng phải liên tục và khớp với câu "Hình N" trong thân bài.
- Mục lục phải khớp số trang thật sau khi cập nhật field; nếu Word không cập nhật được thì ghi rõ trong báo cáo bàn giao.
- Ảnh chụp app không được lộ dữ liệu rác/mật khẩu; dùng dữ liệu seed.
- Bảng dài không được tràn lề phải; cột phải co giãn trong 15.5 cm.
- Chữ tiếng Việt không bị fallback font khi mở trên máy khác.

---

### Task 1: Khung sinh ảnh + helper SVG→PNG

**Files:**
- Create: `make_report_assets.py`
- Create: `docs/report/assets/` (thư mục)

**Interfaces:**
- Produces: `render_svg(svg: str, out_png: Path, width: int = 1600) -> Path`, `render_html(url_or_path: str, out_png: Path, width: int = 1440, height: int = 900, full_page: bool = False) -> Path`, hằng số `ASSETS = Path("docs/report/assets")`.

- [ ] **Step 1:** Viết helper dùng `subprocess` gọi `chrome --headless=new --disable-gpu --hide-scrollbars --screenshot=... --window-size=W,H file:///...`; SVG ghi tạm ra `.html` bọc `<img>` hoặc nhúng trực tiếp.
- [ ] **Step 2:** Kiểm tra: sinh 1 PNG thử 400×200 có nền trắng, mở bằng Pillow đọc `size` → `(400, 200)`.
- [ ] **Step 3:** Xoá PNG thử.

### Task 2: Bốn sơ đồ tuần tự

**Files:** Modify `make_report_assets.py`

**Interfaces:**
- Produces: `seq_dang_ky()`, `seq_dang_nhap()`, `seq_dang_tin()`, `seq_dat_mua()` → `docs/report/assets/seq-dang-ky.png` … `seq-dat-mua.png`.

- [ ] **Step 1:** Hàm `build_sequence(actors: list[str], messages: list[tuple[str,str,str]], fragments: list[dict], title: str, out: Path)` vẽ SVG thuần: hộp actor, lifeline nét đứt, mũi tên đặc (request) / mũi tên hở nét đứt (response), nhãn trên cung, khung `alt/opt` chữ nhật có tab.
- [ ] **Step 2:** Nội dung 4 sơ đồ bám đúng view:
  - Đăng ký: Người dùng → Trang đăng ký → `RegisterForm` → `User.objects.create_user` → signal `post_save` tạo `Profile` → `login()` → redirect `home`.
  - Đăng nhập: Người dùng → `user_login` → kiểm tra `@` + `_is_allowed_email` → `AuthenticationForm` → `authenticate()` → `login()` → session → redirect `next|home`.
  - Đăng tin: Người dùng → `create_post` → `PostForm` + `PostImageForm` → `Post.save()` (sinh slug, `is_free` nếu giá 0) → `PostImage` → redirect `post_detail`.
  - Đặt mua: Người mua → `buy_post` → kiểm tra `post.seller != user`, `is_available`, đơn mở tồn tại → `OrderForm` → `Order.save()` (`PENDING`, `price_snapshot`) → Người bán `accept_order` → `CONFIRMED`.
- [ ] **Step 3:** Sinh 4 PNG, kiểm tra bằng mắt qua `read` ảnh; sửa chồng chữ nếu có.

### Task 3: Sơ đồ PERT + bảng tính

**Files:** Modify `make_report_assets.py`

**Interfaces:**
- Produces: `PERT_EDGES: list[tuple[str,str,int]]`, `pert_times() -> dict` (ES/EF/LS/LF/slack mỗi đỉnh), `render_pert() -> Path` = `docs/report/assets/pert.png`.

- [ ] **Step 1:** Khai báo `PERT_EDGES` đúng file bài nhận thức 3: `A 0→1:9, B 0→2:8, C 0→3:6, D 1→4:5, B' 2→4:0, E 2→5:4, C' 3→5:0, F 3→6:3, E' 5→6:0, H 4→7:9, I 5→7:4, G 7→8:12, J 6→8:10`.
- [ ] **Step 2:** Tính ES/LS bằng hai lượt duyệt; assert `ES == [0,9,8,6,14,12,12,23,35]`, `LS == [0,9,14,19,14,19,25,23,35]`, `critical == [0,1,4,7,8]`, `T = 35`.
- [ ] **Step 3:** Vẽ SVG: đỉnh tròn ghi `ES/LS` phía trên, số đỉnh ở giữa, cung có nhãn `Tên(thời lượng)`, cung giả nét đứt, cung găng tô đỏ. Xuất PNG.

### Task 4: Ảnh 4 board Figma

**Files:** Modify `make_report_assets.py`

- [ ] **Step 1:** Chụp full-page `docs/figma-board-dang-ky.html`, `-dang-nhap`, `-dang-tin`, `-dat-mua` ở width 1440 → `docs/report/assets/figma-*.png`.
- [ ] **Step 2:** Kiểm tra chiều cao > 900 và ảnh không trắng trơn (Pillow `getextrema`).

### Task 5: Ảnh giao diện thật của app

**Files:** Create `docs/report/seed_demo.py` (management-style script chạy bằng `python manage.py shell <`), Modify `make_report_assets.py`

- [ ] **Step 1:** Script seed: tạo 1 staff `admin@sachgocuni.edu.vn`, 3 user sinh viên, 6 bài đăng (2 miễn phí, 4 có giá) thuộc 3 danh mục, 1 đơn `PENDING`, 1 đơn `COMPLETED`, 1 báo cáo `PENDING`. Dùng `get_or_create` để chạy lại không lỗi.
- [ ] **Step 2:** Chạy server nền `python manage.py runserver 8011 --noreload` với `USE_SQLITE=True`.
- [ ] **Step 3:** Chụp: `/` (trang chủ), `/dang-ky/`, `/dang-nhap/`, `/dang-tin/`, `/san-pham/<pk>/` , `/san-pham/<pk>/dat-mua/`, `/don-hang/`, `/quan-tri/`, `/django-admin/`.
- [ ] **Step 4:** Kiểm tra từng ảnh có nội dung (không phải trang lỗi) bằng cách grep HTML trước khi chụp (`curl` kiểm tra HTTP 200).

### Task 6: Sơ đồ ERD

**Files:** Modify `make_report_assets.py`

- [ ] **Step 1:** Vẽ SVG 10 hộp bảng (`auth_user`, `Category`, `Profile`, `Post`, `PostImage`, `Favorite`, `Comment`, `Review`, `Report`, `Order`) với 3–6 trường chính, nối quan hệ 1-n có nhãn `1`/`n`, bố trí 3 tầng.
- [ ] **Step 2:** Xuất `docs/report/assets/erd.png`, kiểm tra không chồng chéo.

### Task 7: Bộ dựng docx — trang, style, phần đầu

**Files:** Create `make_report.py`

**Interfaces:**
- Produces: `Doc` class với `h1(text)`, `h2(text)`, `h3(text)`, `p(text, bold=False, italic=False)`, `bullets(items)`, `figure(path, caption, width_cm=15.5)`, `table(headers, rows, caption)`, `code(text)`, `page_break()`, `save(path)`.

- [ ] **Step 1:** `setup_page()`: A4, lề theo constraint, style `Normal` Times New Roman 14, line 1.15, space_after 6.
- [ ] **Step 2:** Style `Heading1/2/3` đè lại: Times New Roman, đen, đậm, cỡ 14, canh giữa cho Heading1 (chương).
- [ ] **Step 3:** Bìa: 2 dòng trường/khoa, logo `docs/logo-dau.png` rộng 3.5 cm, `BÁO CÁO GIỮA KÌ`, `HỌC PHẦN CÔNG NGHỆ PHẦN MỀM`, `ĐỀ TÀI:`, tên đề tài, khối GVHD/SV/MSSV/Lớp, dòng ngày tháng.
- [ ] **Step 4:** Trang nhận xét (tiêu đề + 12 dòng chấm + khung "Điểm: …"), Tóm tắt, Lời mở đầu, Lời cảm ơn (mỗi phần trang riêng).
- [ ] **Step 5:** Mục lục bằng field `TOC \o "1-3" \h \z \u` + đoạn nhắc "Nhấn F9 để cập nhật".
- [ ] **Step 6:** Chạy `python make_report.py --only front` sinh file tạm, mở bằng Word COM xuất PDF, đếm số trang = 6–7, xem ảnh trang bìa.

### Task 8: Chương 1

- [ ] **Step 1:** Viết 1.1 → 1.5 theo spec, mỗi mục 2–4 đoạn văn xuôi tiếng Việt, không bullet rỗng.
- [ ] **Step 2:** Bảng 1.1 công cụ (6 dòng), Bảng 1.2 thư viện (7 dòng); Hình 1.1 kiến trúc MTV, Hình 1.2 cấu trúc thư mục.
- [ ] **Step 3:** Kiểm tra: `python make_report.py --only ch1` → PDF → trang Ch.1 không tràn, bảng không vỡ.

### Task 9: Chương 2 — 2.1 sequence + 2.2 PERT

- [ ] **Step 1:** 2.1.1–2.1.4: mỗi mục 1 đoạn dẫn + Hình + Bảng thông điệp (4 cột: STT, Nguồn → Đích, Thông điệp, Loại).
- [ ] **Step 2:** 2.2.1 bảng công việc 10 dòng (Mã, Công việc dự án, Trước, Thời lượng) + ghi chú giữ nguyên bài nhận thức 3.
- [ ] **Step 3:** 2.2.2 Hình PERT; 2.2.3 bảng 9 dòng ES/LS/dự trữ; 2.2.4 kết luận đường găng + công thức ngắn.

### Task 10: Chương 2 — 2.3 demo

- [ ] **Step 1:** Mỗi chức năng: (1) Luồng người dùng — 5 bước đánh số; (2) Bố cục phác thảo — ảnh board Figma crop phần wireframe; (3) Giao diện hoàn thiện — ảnh board phần UI + mô tả; (4) Kết quả thực hiện — ảnh app thật + đoạn mã nguồn chính (10–20 dòng).
- [ ] **Step 2:** Kiểm tra: 4 mục × ~2.5 trang, tổng 10–12 trang.

### Task 11: Chương 2 — 2.4 CSDL

- [ ] **Step 1:** 2.4.1 ERD + mô tả 10 bảng.
- [ ] **Step 2:** 2.4.2 ba bảng chi tiết trường (`Post`, `Order`, `Report`).
- [ ] **Step 3:** 2.4.3 bảng thống kê dữ liệu thật (đếm bằng ORM, ghi số thực tế) + ảnh dữ liệu mẫu.

### Task 12: Kết luận + tài liệu tham khảo

- [ ] **Step 1:** `KẾT LUẬN` 3 mục: đánh giá & phân tích, hướng phát triển (6 gạch đầu dòng), kết luận chung.
- [ ] **Step 2:** `TÀI LIỆU THAM KHẢO`: tài liệu Django chính thức, Python docs, Tailwind, MySQL, Figma, Draw.io.

### Task 13: Xuất bản + QA

- [ ] **Step 1:** `python make_report.py` sinh `docs/BaoCao_GiuaKy_CNPM_SachGocUni.docx`.
- [ ] **Step 2:** Word COM: mở, `Fields.Update()`, lưu, `ExportAsFixedFormat` → `docs/report/verify/report.pdf`.
- [ ] **Step 3:** PyMuPDF render từng trang → `docs/report/verify/page-NN.png`; đọc ảnh các trang then chốt (bìa, mục lục, mỗi chương, trang bảng).
- [ ] **Step 4:** Sửa lỗi bố cục, lặp Step 1–3 đến khi sạch.
- [ ] **Step 5:** `git status` — chỉ báo file mới, không commit.

## Self-Review

- Spec §4 (mục lục nội dung) → Task 7–12 phủ đủ.
- Spec §6 (20 hình) → Task 1–6 sinh đủ, Task 8–11 chèn.
- Spec §7 (kiểm chứng) → Task 13.
- Số liệu PERT/đường găng khớp file gốc; số liệu CSDL lấy trực tiếp từ ORM nên không lệch.
