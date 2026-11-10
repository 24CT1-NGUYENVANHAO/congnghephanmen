# Thiết kế: Dashboard quản trị trong app (`/quan-tri/`)

Ngày: 2026-11-10
Trạng thái: chờ duyệt

## 1. Mục tiêu

Thêm một trang quản trị **nằm trong chính website** (không phải Django admin), dùng
giao diện Tailwind sẵn có, để admin/staff:

- Nhìn được tình hình hệ thống trong một màn hình (thẻ số liệu).
- Duyệt / từ chối bài đăng đang chờ ngay tại chỗ.
- Xử lý / bỏ qua báo cáo vi phạm ngay tại chỗ.
- Có lối tắt sang `/django-admin/` cho các thao tác sâu (sửa chi tiết, phân quyền…).

Không thay thế Django admin — hai thứ song song, bổ trợ nhau.

## 2. Phạm vi

### Làm

| Hạng mục | Chi tiết |
|---|---|
| Trang `/quan-tri/` | 5 thẻ số liệu + 2 bảng kiểm duyệt + dải lối tắt |
| Duyệt bài | `PENDING → ACTIVE` |
| Từ chối bài | `PENDING → REJECTED` |
| Xử lý báo cáo | `Report → RESOLVED` **và** ẩn bài bị báo cáo (`Post → HIDDEN`) |
| Bỏ qua báo cáo | `Report → DISMISSED` (không đổi bài đăng) |
| Phân quyền | Chỉ `is_staff`; người thường bị chặn |
| Cập nhật navbar | Link "🛡️ Trang quản trị" trỏ về `/quan-tri/` thay vì `/django-admin/`, vẫn giữ badge số báo cáo chờ |
| Test | Thêm `AdminDashboardTests` vào `app_main/tests.py` |

### Không làm (cố ý)

- Không quản lý đơn hàng / khoá tài khoản trong dashboard → dùng Django admin.
- Không CRUD danh mục, không sửa nội dung bài đăng.
- Không phân trang / lọc nâng cao: mỗi bảng lấy 10 bản ghi mới nhất, kèm link
  "Xem tất cả" sang Django admin (đã lọc sẵn theo trạng thái).
- Không viết CSS mới đáng kể: dùng `.card`, `.btn`, `.badge-*` trong `static/css/main.css`.

## 3. Thẻ số liệu (5 thẻ)

| Thẻ | Nguồn | Ghi chú |
|---|---|---|
| Bài chờ duyệt | `Post.objects.filter(status=PENDING).count()` | nhấn → cuộn xuống bảng bên dưới |
| Báo cáo chờ xử lý | `Report.objects.filter(status=PENDING).count()` | |
| Đơn chờ xác nhận | `Order.objects.filter(status=PENDING).count()` | chỉ để xem |
| Người dùng | `User.objects.count()` | kèm số đang hoạt động nếu tiện |
| Doanh thu | `Order.objects.filter(status=COMPLETED).aggregate(Sum('price_snapshot'))` | đơn vị VNĐ, dùng `floatformat:"0"` + `intcomma` |

Số liệu gộp trong **một** `aggregate`/`count` cho mỗi model, không N+1.

## 4. Bố cục

```
┌ trang /quan-tri/ ────────────────────────────────────────────┐
│ Tiêu đề: Bảng điều khiển quản trị                            │
│ Phụ đề: Xin chào <tên> · <thời gian cập nhật>                │
│                                                              │
│ [Bài chờ duyệt] [Báo cáo chờ] [Đơn chờ] [Người dùng] [Doanh thu] │
│                                                              │
│ ── Bài đăng chờ duyệt ────────────── Xem tất cả →            │
│ Ảnh | Tiêu đề (+ người đăng, danh mục, giá) | Ngày | Thao tác │
│                    [✅ Duyệt] [🚫 Từ chối]                    │
│                                                              │
│ ── Báo cáo vi phạm ────────────────── Xem tất cả →            │
│ Bài bị báo cáo | Lý do | Người báo cáo | Ngày | Thao tác      │
│              [✅ Xử lý & ẩn bài] [⚪ Bỏ qua]                  │
│                                                              │
│ ── Lối tắt ────────────────────────────────────────────────  │
│ [Quản lý bài đăng] [Báo cáo] [Đơn hàng] [Người dùng]          │
└──────────────────────────────────────────────────────────────┘
```

- Bảng rỗng → hiện khối "Không có gì cần xử lý 🎉".
- Thao tác là `<form method="post">` + `{% csrf_token %}` + `onsubmit="return confirm(...)"`.
- Sau mỗi thao tác: `messages.success(...)` rồi `redirect('admin_dashboard')`.

## 5. URL & view

Thêm vào `app_main/urls.py` (đặt cuối, nhóm riêng "Quản trị"):

```python
path('quan-tri/', views.admin_dashboard, name='admin_dashboard'),
path('quan-tri/bai-dang/<int:pk>/duyet/', views.admin_approve_post, name='admin_approve_post'),
path('quan-tri/bai-dang/<int:pk>/tu-choi/', views.admin_reject_post, name='admin_reject_post'),
path('quan-tri/bao-cao/<int:pk>/xu-ly/', views.admin_resolve_report, name='admin_resolve_report'),
path('quan-tri/bao-cao/<int:pk>/bo-qua/', views.admin_dismiss_report, name='admin_dismiss_report'),
```

Decorator dùng chung, đặt trong `app_main/views.py` cạnh các view khác:

```python
def staff_required(view):
    """Chỉ cho phép is_staff; người thường bị đẩy về trang chủ kèm thông báo."""
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        if not request.user.is_staff:
            messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
            return redirect('home')
        return view(request, *args, **kwargs)
    return _wrapped
```

- 4 view thao tác: `@staff_required` + `@require_POST`.
- Duyệt/từ chối chỉ áp dụng cho bài đang `PENDING`; nếu không đúng trạng thái →
  `messages.warning` và không đổi gì (tránh ghi đè trạng thái SOLD).
- Xử lý báo cáo: chỉ áp dụng khi report đang `PENDING`.

## 6. Template

`templates/app_main/admin_dashboard.html`, `{% extends 'base.html' %}`.
Dùng `{% block content %}`. Không cần `{% block scripts %}` (không có JS riêng
ngoài `confirm()` inline).

Badge trạng thái dùng lại `.badge .badge-warning/.badge-success/.badge-danger/.badge-slate`.

## 7. Navbar

`templates/partials/navbar.html`: đổi `{% url 'admin_dashboard' %}` cho mục
"🛡️ Trang quản trị", giữ nguyên badge `pending_reports`.
Thêm 1 mục nhỏ "⚙️ Django admin" trỏ `/django-admin/` ngay dưới, để không mất lối vào cũ.

## 8. Test (`AdminDashboardTests`)

1. Khách chưa đăng nhập → redirect `/dang-nhap/?next=/quan-tri/`.
2. User thường đã đăng nhập → 302 về `home`, không thấy dữ liệu.
3. Staff → 200, có số liệu đúng (1 bài chờ duyệt, 1 báo cáo chờ, …).
4. Duyệt bài: `PENDING → ACTIVE`.
5. Từ chối bài: `PENDING → REJECTED`.
6. Duyệt bài đã `SOLD` → không đổi trạng thái.
7. Xử lý báo cáo: report `RESOLVED` + post `HIDDEN`.
8. Bỏ qua báo cáo: report `DISMISSED`, post giữ nguyên.
9. Gọi GET vào endpoint thao tác → 405.
10. User thường POST vào endpoint thao tác → 302, dữ liệu không đổi.

## 9. Rủi ro / lưu ý

- `LOGIN_URL = 'login'` (đã xác nhận trong `core/settings.py`), nên dùng
  `reverse(settings.LOGIN_URL)` + `?next=...` thay vì nối chuỗi thủ công.
- Doanh thu dùng `Sum` trên `DecimalField`; nếu chưa có đơn hoàn tất thì trả `0`.
- Dashboard chỉ đọc + 4 thao tác nhỏ nên không ảnh hưởng luồng nghiệp vụ hiện có.
- Không đụng vào `app_main/admin.py`.
