# Thiết kế: Vai trò Kiểm duyệt viên (Moderator)

- Ngày: 2026-11-17
- Trạng thái: Chờ duyệt
- Liên quan: `app_main/models.py`, `views.py`, `urls.py`, `forms.py`, `admin.py`,
  `context_processors.py`, `templates/`, `seed_data.py`, `tests.py`,
  `README.md`, báo cáo `BaoCao_GiuaKy_CNPM_SachGocUni.docx`

---

## 1. Mục tiêu

Bổ sung vai trò **Kiểm duyệt viên (Moderator)** với 4 nhiệm vụ:

1. Duyệt bài đăng mới **trước khi** hiển thị lên sàn (kiểm tra ảnh, nội dung).
2. Xử lý báo cáo vi phạm: spam, tin giả, **hàng cấm**, ngôn từ không phù hợp.
3. Khoá / ẩn bài vi phạm quy định.
4. Hỗ trợ giải đáp thắc mắc và xử lý tranh chấp cơ bản giữa người mua – người bán.

Kết quả mong đợi: hệ thống có **3 vai trò** rõ ràng — Sinh viên, Kiểm duyệt viên,
Quản trị viên — và toàn bộ vòng đời bài đăng / đơn hàng đi qua được bàn kiểm duyệt.

## 2. Quyết định đã chốt với người dùng

| # | Quyết định |
|---|------------|
| D1 | Moderator là **tài khoản riêng, chỉ kiểm duyệt**: không đăng bài, không đặt mua, không bình luận/đánh giá/báo cáo/yêu thích. |
| D2 | **Admin (`is_staff`) cao hơn Moderator**: giữ toàn quyền cũ và làm được mọi việc Moderator làm. |
| D3 | **Mọi lần người bán sửa bài → bài về `PENDING`, duyệt lại.** (Trừ bài đã `SOLD`.) |
| D4 | **Phiên hỗ trợ chỉ gắn với một đơn hàng**, mở bởi người mua hoặc người bán của đơn đó. |
| D5 | Mức tranh chấp: **phiên hỗ trợ 2 chiều + Moderator được can thiệp trạng thái đơn** (huỷ đơn / xác nhận hoàn tất thay hai bên). |
| D6 | Cơ chế vai trò: **`Profile.role`** (`STUDENT` / `MODERATOR`); Admin vẫn xác định bằng `is_staff`. |

## 3. Mô hình dữ liệu

### 3.1 `Profile` — thêm trường `role`

```python
class Profile(models.Model):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Sinh viên'
        MODERATOR = 'MODERATOR', 'Kiểm duyệt viên'

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STUDENT,
        db_index=True, verbose_name="Vai trò",
    )

    @property
    def is_moderator(self):
        return self.role == self.Role.MODERATOR
```

- Quy ước: `is_staff` **luôn thắng**. Tài khoản admin có `role = STUDENT` vẫn là admin.
- Hàm dùng chung trong view:

```python
def _can_moderate(user):
    return (
        user.is_authenticated
        and (
            user.is_staff
            or (hasattr(user, 'profile') and user.profile.role == Profile.Role.MODERATOR)
        )
    )
```

### 3.2 `Report.Reason` — thêm "hàng cấm"

```python
PROHIBITED = 'PROHIBITED', 'Hàng cấm / vi phạm pháp luật'
```

Giữ nguyên 5 lý do cũ. `ReportForm` tự cập nhật vì dùng `Report.Reason.choices`.

### 3.3 `Order.Status` — thêm `DISPUTED`

```python
DISPUTED = 'DISPUTED', 'Đang tranh chấp'
```

- `is_open` = `PENDING | CONFIRMED | DISPUTED`.
- Khi mở phiên hỗ trợ loại **tranh chấp**: đơn chuyển `DISPUTED` (chỉ khi đơn đang
  `PENDING`/`CONFIRMED`).
- Trong lúc `DISPUTED`: chặn người bán `accept_order` / `reject_order` /
  `complete_order` và người mua `cancel_order`; chỉ Moderator/Admin quyết định.

### 3.4 Model mới `SupportTicket`

```python
class SupportTicket(models.Model):
    class Category(models.TextChoices):
        DISPUTE = 'DISPUTE', 'Tranh chấp đơn hàng'
        QUESTION = 'QUESTION', 'Cần giải đáp'
        OTHER = 'OTHER', 'Vấn đề khác'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Chờ tiếp nhận'
        IN_PROGRESS = 'IN_PROGRESS', 'Đang xử lý'
        RESOLVED = 'RESOLVED', 'Đã giải quyết'

    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                              related_name='support_tickets', verbose_name="Đơn hàng")
    opened_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                  related_name='support_tickets_opened',
                                  verbose_name="Người mở")
    category = models.CharField(max_length=20, choices=Category.choices,
                                default=Category.QUESTION, verbose_name="Loại yêu cầu")
    subject = models.CharField(max_length=200, verbose_name="Tiêu đề")
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.OPEN, db_index=True,
                              verbose_name="Trạng thái")
    handled_by = models.ForeignKey(User, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='support_tickets_handled',
                                   verbose_name="Người xử lý")
    resolution_note = models.TextField(max_length=1000, blank=True,
                                       verbose_name="Kết luận xử lý")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
```

Ràng buộc "mỗi đơn chỉ có 1 phiên chưa kết thúc" kiểm tra trong view (MySQL không
hỗ trợ partial unique index — cùng lý do đã ghi ở `Order`).

### 3.5 Model mới `SupportMessage`

```python
class SupportMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE,
                               related_name='messages', verbose_name="Phiên hỗ trợ")
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='support_messages', verbose_name="Người gửi")
    body = models.TextField(max_length=2000, verbose_name="Nội dung")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
```

Không có ghi chú nội bộ (internal note) — mọi tin nhắn đều công khai cho người mua,
người bán và người kiểm duyệt của phiên đó.

### 3.6 Migration

Một migration duy nhất `app_main/migrations/0005_moderator_support.py`, gồm:
thêm `Profile.role`, `Order.Status` (AlterField), `Report.Reason` (AlterField),
tạo `SupportTicket`, `SupportMessage`.

## 4. Phân quyền

| Hành động | Sinh viên | Moderator | Admin (`is_staff`) |
|---|---|---|---|
| Đăng bài / sửa bài của mình / đặt mua / bình luận / đánh giá / báo cáo / yêu thích | ✅ | ❌ | ✅ |
| Xem bài `PENDING`/`REJECTED`/`HIDDEN` | Chỉ bài của mình | ✅ | ✅ |
| Duyệt / từ chối bài | ❌ | ✅ | ✅ |
| Xử lý / bỏ qua báo cáo | ❌ | ✅ | ✅ |
| Mở phiên hỗ trợ cho đơn của mình | ✅ | ❌ (không có đơn) | ✅ |
| Trả lời phiên hỗ trợ của mình | ✅ | ❌ | ✅ |
| Trả lời / kết luận mọi phiên hỗ trợ | ❌ | ✅ | ✅ |
| Huỷ / hoàn tất đơn khi có tranh chấp | ❌ | ✅ | ✅ |
| Vào `/quan-tri/` | ❌ | ✅ | ✅ |
| Vào `/django-admin/`, xem doanh thu & tổng người dùng | ❌ | ❌ | ✅ |

Hai decorator:

```python
def moderator_required(view):   # is_staff OR role == MODERATOR
def student_required(view):     # chặn role == MODERATOR; is_staff vẫn được
```

`student_required` gắn vào: `create_post`, `edit_post`, `delete_post`,
`toggle_sold`, `upload_post_image`, `delete_post_image`, `buy_post`,
`report_post`, `toggle_favorite`, `add_comment`, `add_review`,
`open_support_ticket`, `support_ticket_reply`.

`staff_required` cũ: sau khi chuyển cả 5 view quản trị (`admin_dashboard`,
`admin_approve_post`, `admin_reject_post`, `admin_resolve_report`,
`admin_dismiss_report`) sang `moderator_required` thì không còn chỗ dùng —
xoá hẳn để tránh hai nguồn sự thật.

## 5. Luồng nghiệp vụ

### 5.1 Đăng bài & duyệt

1. Sinh viên gửi form → `Post.status = PENDING`, thông báo
   "Tin đã được gửi và đang chờ kiểm duyệt".
2. Chuyển tới trang chi tiết (chủ bài xem được bài `PENDING` của mình).
3. Bài `PENDING` **không** xuất hiện ở trang chủ, tìm kiếm, hồ sơ người bán.
4. Moderator mở `/quan-tri/` → xem ảnh, nội dung → **Duyệt** (`ACTIVE`) hoặc
   **Từ chối** (`REJECTED` + lý do, hiển thị cho người bán ở "Tin của tôi" và
   trang chi tiết).

### 5.2 Sửa bài

- Người bán sửa bài `ACTIVE` / `PENDING` / `REJECTED` / `HIDDEN` → về `PENDING`,
  xoá `rejection_reason` cũ.
- Bài `SOLD` sửa nội dung → giữ `SOLD` (không duyệt lại, không bán lại).
- Admin sửa bài → giữ nguyên trạng thái (không kích hoạt duyệt lại).

### 5.3 Xem bài theo trạng thái

- `ACTIVE`, `SOLD`: công khai.
- `PENDING`, `REJECTED`, `HIDDEN`: chỉ chủ bài hoặc người kiểm duyệt; người khác
  nhận 404.
- Trang chi tiết hiện banner trạng thái + lý do từ chối cho chủ bài.

### 5.4 Báo cáo vi phạm

- Giữ nguyên luồng gửi báo cáo; thêm lý do `PROHIBITED` (hàng cấm).
- Moderator xử lý: báo cáo → `RESOLVED`, bài `PENDING`/`ACTIVE` → `HIDDEN`
  (giữ nguyên nếu `SOLD`/`REJECTED`/`HIDDEN`).
- Bỏ qua: báo cáo → `DISMISSED`, bài không đổi.

### 5.5 Hỗ trợ & tranh chấp

1. Trong trang chi tiết đơn, người mua hoặc người bán bấm **"Cần hỗ trợ"**.
2. Form: loại yêu cầu (Tranh chấp / Cần giải đáp / Khác), tiêu đề, nội dung đầu.
3. Nếu là **Tranh chấp** và đơn đang `PENDING`/`CONFIRMED` → đơn chuyển `DISPUTED`.
4. Hai bên trao đổi trong phiên; mỗi tin nhắn lưu `SupportMessage`.
5. Moderator trả lời → phiên `IN_PROGRESS`.
6. Moderator kết luận (bắt buộc nhập kết luận):
   - **Huỷ đơn** → `Order.status = CANCELLED`.
   - **Xác nhận hoàn tất** → `Order.status = COMPLETED`, bài → `SOLD`,
     `is_sold = True`.
   - Phiên → `RESOLVED`, ghi `handled_by`, `resolved_at`, `resolution_note`.
7. Đơn đã ở trạng thái kết thúc (`COMPLETED`/`CANCELLED`/`REJECTED`) thì chỉ ghi
   kết luận, không đổi trạng thái đơn.

## 6. Routes

Thêm vào `app_main/urls.py`:

```python
# Hỗ trợ (người mua / người bán)
path('ho-tro/', views.my_tickets, name='my_tickets'),
path('ho-tro/<int:pk>/', views.support_ticket_detail, name='support_ticket_detail'),
path('don-hang/<int:pk>/ho-tro/', views.open_support_ticket, name='open_support_ticket'),
path('ho-tro/<int:pk>/tra-loi/', views.support_ticket_reply, name='support_ticket_reply'),

# Kiểm duyệt
path('quan-tri/ho-tro/', views.moderator_ticket_list, name='moderator_ticket_list'),
path('quan-tri/ho-tro/<int:pk>/', views.moderator_ticket_detail,
     name='moderator_ticket_detail'),
path('quan-tri/ho-tro/<int:pk>/tra-loi/', views.moderator_ticket_reply,
     name='moderator_ticket_reply'),
path('quan-tri/ho-tro/<int:pk>/ket-luan/', views.moderator_ticket_resolve,
     name='moderator_ticket_resolve'),
path('quan-tri/ho-tro/<int:pk>/quyet-dinh/', views.moderator_order_decision,
     name='moderator_order_decision'),
```

Tất cả endpoint thay đổi dữ liệu đều `@require_POST` + CSRF; endpoint kiểm duyệt
dùng `@moderator_required`.

## 7. Giao diện

### 7.1 `/quan-tri/` — 2 chế độ

- **Admin** (`is_staff`): giữ nguyên toàn bộ thẻ số liệu (gồm doanh thu, người
  dùng) + link Django admin.
- **Moderator**: ẩn thẻ doanh thu / tổng người dùng / mọi link `/django-admin/`
  và các nút "Xem tất cả →" trỏ sang Django admin. Vẫn thấy: bài chờ duyệt,
  báo cáo chờ, đơn chờ xác nhận, phiên hỗ trợ đang mở.

Thêm mục **"Hỗ trợ & tranh chấp"**: 10 phiên `OPEN`/`IN_PROGRESS` mới nhất, kèm
badge trạng thái đơn và nút vào xử lý.

### 7.2 Navbar

- Moderator: nút "🛡️ Kiểm duyệt" (badge tổng việc chờ), ẩn nút "Đăng tin",
  ẩn "Đơn hàng"/"Yêu thích"; giữ Hồ sơ / Đổi mật khẩu / Đăng xuất.
- Admin: giữ "🛡️ Trang quản trị" + Django admin như cũ.
- Sinh viên: thêm mục "🆘 Hỗ trợ" trong menu tài khoản (danh sách phiên của mình).

`context_processors.site_context` cấp thêm `pending_total` (int, tổng bài chờ +
báo cáo chờ + phiên đang mở) cho Admin/Moderator; `pending_reports` mở cho cả
Moderator (hiện chỉ `is_staff`). Không trả `pending_posts`/`open_tickets` ra
context để khỏi trùng tên với QuerySet mà `admin_dashboard` truyền.

### 7.3 Các trang mới

| Template | Nội dung |
|---|---|
| `my_tickets.html` | Danh sách phiên của người dùng, lọc theo trạng thái |
| `support_ticket_detail.html` | Tóm tắt đơn, luồng tin nhắn, form trả lời (ẩn khi `RESOLVED`) |
| `support_ticket_form.html` | Mở phiên mới cho một đơn |
| `moderator_ticket_list.html` | Danh sách phiên hỗ trợ cho kiểm duyệt viên, lọc theo trạng thái |
| `moderator_ticket_detail.html` | Luồng tin nhắn + form trả lời + form kết luận + nút quyết định đơn |

### 7.4 Sửa template hiện có

- `admin_dashboard.html`: ẩn/ hiện theo vai trò, thêm mục hỗ trợ.
- `my_posts.html`: thêm chip lọc **"Chờ duyệt"**, thống kê số bài chờ duyệt.
- `post_detail.html`: banner trạng thái cho chủ bài; ẩn nút mua/báo cáo khi bài
  không `ACTIVE`.
- `order_detail.html`, `my_orders.html`: badge `DISPUTED`, nút "Cần hỗ trợ",
  danh sách phiên của đơn.
- `navbar.html`: như 7.2.

## 8. Forms mới

- `SupportTicketForm` — `category`, `subject`, `body` (nội dung đầu tiên).
- `SupportReplyForm` — `body`.
- `TicketResolveForm` — `resolution_note`, `decision`
  (`cancel` / `complete` / `none`).

Tất cả dùng class CSS hiện có (`INPUT_CLASS`, `TEXTAREA_CLASS`).

## 9. Seed data

Thêm vào `seed_data.py`:

- Tài khoản `moderator` / mật khẩu `123456`, email
  `moderator@sachgocuni.edu.vn`, `Profile.role = MODERATOR` (idempotent).
- 2 bài `PENDING` mẫu để dashboard có việc.
- 1 phiên tranh chấp mẫu gắn với một đơn `CONFIRMED` sẵn có (nếu có), gồm 2 tin
  nhắn (người mua + người bán) và đơn chuyển `DISPUTED`.
- Cập nhật bảng tóm tắt tài khoản in ra cuối script.

## 10. Test

### 10.1 Test cũ phải sửa

| Test | Sửa |
|---|---|
| `UserJourneyTests.test_full_journey` | Sau khi đăng tin, duyệt bằng ORM (`status=ACTIVE`) trước bước tìm kiếm; hoặc duyệt qua view moderator. |
| `PostManagementTests.test_create_post` | Khẳng định bài mới có `status=PENDING` (thay vì ngầm hiểu `ACTIVE`). |
| `AdminDashboardTests.test_non_staff_redirected_home` | Vẫn đúng (sinh viên thường), giữ nguyên. |
| `AdminDashboardTests.test_staff_sees_stats` | Giữ nguyên; thêm `pending_tickets` vào stats nếu có. |

Các test dùng helper `create_post()` (tạo trực tiếp ORM, mặc định `ACTIVE`) **không**
bị ảnh hưởng.

### 10.2 Test mới (khoảng 40 test)

**`ModeratorRoleTests`**
- `Profile.role` mặc định `STUDENT`.
- Moderator vào `/quan-tri/` được; sinh viên bị đẩy về trang chủ.
- Moderator không tạo được bài / không đặt mua / không bình luận / không báo cáo.
- Moderator không thấy link `/django-admin/` và thẻ doanh thu.
- Navbar hiện "Kiểm duyệt" cho moderator, ẩn với sinh viên.
- Context processor trả đúng số việc chờ cho moderator.

**`PostApprovalTests`**
- Đăng bài → `PENDING`, không có trên trang chủ.
- Chủ bài xem được chi tiết; người khác nhận 404.
- Moderator duyệt → `ACTIVE`, xuất hiện trên trang chủ.
- Từ chối kèm lý do → `REJECTED`, chủ bài thấy lý do.
- Sửa bài `ACTIVE` → `PENDING` và xoá lý do từ chối cũ.
- Sửa bài `SOLD` → vẫn `SOLD`.
- Admin sửa bài → không đổi trạng thái.
- Xử lý báo cáo "hàng cấm" → bài `HIDDEN`.

**`SupportTicketTests`**
- Người mua mở phiên tranh chấp → đơn `DISPUTED`.
- Người bán mở phiên cần giải đáp → đơn không đổi.
- Người ngoài đơn không mở/xem được phiên (404/redirect).
- Mỗi đơn chỉ 1 phiên chưa kết thúc.
- Trả lời thêm `SupportMessage`; người ngoài không trả lời được.
- Moderator trả lời → `IN_PROGRESS`.
- Kết luận thiếu nội dung → lỗi, phiên không đổi.
- Kết luận huỷ đơn → `CANCELLED` + phiên `RESOLVED` + `handled_by`.
- Kết luận hoàn tất → `COMPLETED`, bài `SOLD`.
- Đơn `DISPUTED` chặn người bán xác nhận/từ chối/hoàn tất và người mua huỷ.
- Sinh viên không vào được trang xử lý của moderator.
- Endpoint POST từ chối GET (405).

Tổng test dự kiến: **142 → khoảng 182**. Đây là thay đổi có chủ đích; ràng buộc
"giữ đúng 142 test" chỉ áp dụng cho lần sửa luồng QR trước đó.

## 11. Ảnh hưởng tài liệu & báo cáo

- `README.md`: cập nhật số test, thêm mô tả vai trò Moderator và luồng duyệt bài.
- Báo cáo Word: thêm mục mô tả vai trò/phân quyền, luồng duyệt bài, báo cáo vi phạm
  (bổ sung "hàng cấm"), phiên hỗ trợ & tranh chấp; thêm hình chụp dashboard
  moderator + trang xử lý tranh chấp; cập nhật số test.
- Việc sửa báo cáo thực hiện **sau khi code + test xong**, theo đúng quy trình đã
  dùng cho lần sửa QR (backup trước, chỉ thay đúng đoạn).

## 12. Rủi ro & ngoài phạm vi

- **Đổi hành vi đăng bài** (trước đây hiện ngay) ảnh hưởng trải nghiệm và test cũ
  → xử lý bằng thông báo rõ ràng + cập nhật test như mục 10.1.
- **Hai nguồn sự thật** (`role` và `is_staff`) → quy ước `is_staff` thắng, ghi rõ
  trong docstring và báo cáo.
- **Không** làm trong phạm vi này: thông báo realtime, email, phân trang nâng cao
  cho danh sách kiểm duyệt, ghi chú nội bộ, lịch sử thay đổi trạng thái (audit log).
- Không đụng tới luồng QR thanh toán.

## 13. Thứ tự triển khai

1. Model + migration + admin registration.
2. Decorator, helper phân quyền, context processor.
3. Luồng duyệt bài (create/edit/detail/my_posts template).
4. Báo cáo vi phạm (reason mới, quyền moderator).
5. Hỗ trợ & tranh chấp (model đã có ở bước 1 → form, view, route, template).
6. Dashboard 2 chế độ + navbar.
7. Seed data.
8. Test mới + sửa test cũ, chạy toàn bộ.
9. README.
10. Báo cáo Word (bước riêng, xin duyệt trước khi sửa).

## 14. Tiêu chí nghiệm thu

- [ ] Sinh viên đăng bài → bài ở "Chờ duyệt", không lên trang chủ.
- [ ] Moderator duyệt/từ chối được, lý do từ chối hiển thị cho người bán.
- [ ] Sửa bài đã duyệt → quay lại chờ duyệt.
- [ ] Báo cáo "hàng cấm"/spam/tin giả xử lý được, bài bị ẩn.
- [ ] Người mua/bán mở phiên hỗ trợ cho đơn; hai bên trao đổi được.
- [ ] Moderator kết luận và huỷ/hoàn tất đơn tranh chấp được.
- [ ] Moderator không đăng bài, không đặt mua, không vào Django admin.
- [ ] Admin giữ nguyên toàn bộ chức năng cũ.
- [ ] Toàn bộ test pass; README và báo cáo khớp code.
