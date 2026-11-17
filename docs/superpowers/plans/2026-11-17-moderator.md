# Vai trò Kiểm duyệt viên (Moderator) — Kế hoạch thực thi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bổ sung vai trò Kiểm duyệt viên (Moderator) duyệt bài trước khi hiển thị, xử lý báo cáo vi phạm, khoá/ẩn bài và hỗ trợ — xử lý tranh chấp đơn hàng, trong khi Admin giữ nguyên toàn bộ quyền cũ.

**Architecture:** Thêm `Profile.role` (`STUDENT` / `MODERATOR`) với quy ước `is_staff` luôn thắng; gom logic phân quyền vào module mới `app_main/permissions.py`. Bài đăng mới và mọi lần người bán sửa bài đều về `PENDING`; Moderator duyệt qua `/quan-tri/` hiện có. Tranh chấp dùng hai model mới `SupportTicket` / `SupportMessage` gắn với `Order`, thêm `Order.Status.DISPUTED`.

**Tech Stack:** Django 5, MariaDB/MySQL (XAMPP cổng 3307), Django template + Tailwind class có sẵn, `manage.py test`.

**Spec:** `docs/superpowers/specs/2026-11-17-moderator-design.md`

## Global Constraints

- Chỉ MySQL (XAMPP cổng 3307); không SQLite, không thêm `USE_SQLITE`, không tạo `db.sqlite3`.
- Chỉ **một** migration mới: `app_main/migrations/0005_moderator_support.py`.
- `is_staff` **luôn thắng**: admin có `role = STUDENT` vẫn làm được mọi việc của Moderator, và vẫn vào `/django-admin/`.
- Moderator **không** đăng bài, sửa/xoá bài, đặt mua, bình luận, đánh giá, báo cáo, yêu thích, mở/trả lời phiên hỗ trợ với tư cách sinh viên.
- `Post.status` giữ `default=ACTIVE`; **chỉ** view `create_post` đặt `PENDING` để helper test tạo trực tiếp ORM không bị ảnh hưởng.
- Người bán sửa bài → `PENDING` (trừ bài `SOLD` giữ `SOLD`), xoá `rejection_reason` cũ; Admin sửa bài → giữ nguyên trạng thái.
- Phiên hỗ trợ chỉ gắn với một đơn; mỗi đơn tối đa **một** phiên chưa kết thúc (kiểm tra trong view, không dùng partial unique index vì MySQL không hỗ trợ).
- Mọi endpoint thay đổi dữ liệu: `@require_POST` + CSRF; gọi bằng GET trả 405.
- Không làm: thông báo realtime, email, ghi chú nội bộ, audit log trạng thái, phân trang nâng cao cho danh sách kiểm duyệt.
- Không đụng luồng QR thanh toán (`buy_post` chỉ được sửa bộ lọc đơn đang mở, không đổi cách hiện QR).
- Copy tiếng Việt, comment tiếng Việt, dùng lại `INPUT_CLASS` / `SELECT_CLASS` / `TEXTAREA_CLASS` và các class `card`, `btn`, `badge` sẵn có.
- **Không commit/push cho tới khi người dùng xác nhận** — mọi bước Commit đều dừng chờ xác nhận.
- 142 test cũ phải pass sau khi sửa đúng 2 test ở mục 10.1 của spec; test mới **40** (Model 5, Role 6, Report 4, PostApproval 8, SupportTicket 16, AdminDashboard 1), tổng **182** (README ghi số thực tế `manage.py test` in ra).
- Việc sửa báo cáo Word là **task riêng, phải xin duyệt trước khi sửa**.

## Review Focus

- Moderator gọi thẳng URL/POST của sinh viên (`/dang-tin/`, `/dat-mua/`, `/binh-luan/`, `/bao-cao/`, `/yeu-thich/`): phải bị chặn, không tạo bản ghi nào, không 500.
- Chủ bài mở bài `PENDING`/`REJECTED`/`HIDDEN` của mình: 200 kèm banner + lý do; sinh viên khác mở cùng URL: 404.
- Người bán sửa bài `SOLD`: vẫn `SOLD`, không quay lại sàn; sửa bài `REJECTED`: về `PENDING` và lý do cũ bị xoá.
- Người ngoài đơn (không phải người mua, người bán, người kiểm duyệt) mở/xem/trả lời phiên hỗ trợ: 404; mở phiên thứ hai khi đơn đã có phiên chưa kết thúc: không tạo thêm.
- Đơn `DISPUTED`: người bán không xác nhận/từ chối/hoàn tất được, người mua không huỷ được; Moderator kết luận với nội dung rỗng: form báo lỗi, trạng thái đơn và phiên không đổi.

## Cấu trúc tệp

| Tệp | Việc |
|---|---|
| `app_main/models.py` | `Profile.role`, `Report.Reason.PROHIBITED`, `Order.Status.DISPUTED`, `SupportTicket`, `SupportMessage` |
| `app_main/migrations/0005_moderator_support.py` | Migration duy nhất |
| `app_main/permissions.py` | **Mới** — `is_moderator`, `can_moderate`, `moderator_required`, `student_required` |
| `app_main/forms.py` | `SupportTicketForm`, `SupportReplyForm`, `TicketResolveForm` |
| `app_main/views.py` | Gắn decorator, sửa luồng duyệt bài, 9 view hỗ trợ/kiểm duyệt, chặn thao tác trên đơn `DISPUTED` |
| `app_main/urls.py` | 9 route `ho-tro/` + `quan-tri/ho-tro/` |
| `app_main/admin.py` | Đăng ký 2 model mới, thêm `role` vào `ProfileAdmin` / `ProfileInline` |
| `app_main/context_processors.py` | `pending_reports` cho Moderator, thêm `pending_total` (tổng việc chờ) |
| `templates/` | Sửa `admin_dashboard`, `my_posts`, `post_detail`, `order_detail`, `my_orders`, `home`; `partials/navbar`, `partials/footer`; thêm 5 template hỗ trợ |
| `seed_data.py` | Tài khoản `moderator`, 2 bài `PENDING`, 1 phiên tranh chấp mẫu |
| `app_main/tests.py` | Helper `create_moderator`, 4 class test mới, sửa 2 test cũ |
| `README.md` | Vai trò Moderator, luồng duyệt bài, số test thực tế |

---

### Task 1: Model, migration và admin

**Files:**
- Modify: `app_main/models.py` (`Profile` ~L64, `Report.Reason` ~L475, `Order.Status` ~L530 + `is_open` ~L585, thêm 2 model sau `Order`)
- Create: `app_main/migrations/0005_moderator_support.py` (do `makemigrations` sinh ra)
- Modify: `app_main/admin.py` (`ProfileAdmin` ~L158, `ProfileInline` ~L259, cuối tệp)
- Test: `app_main/tests.py` (thêm `ModeratorModelTests`)

**Interfaces:**
- Consumes: `User`, `Order` sẵn có.
- Produces:
  - `Profile.Role.STUDENT` / `Profile.Role.MODERATOR`, `Profile.role`, `Profile.is_moderator`
  - `Report.Reason.PROHIBITED`
  - `Order.Status.DISPUTED`; `Order.is_open` gồm `PENDING | CONFIRMED | DISPUTED`
  - `SupportTicket` (fields đúng spec §3.4), `SupportMessage` (spec §3.5)
  - `SupportTicket.__str__` → `"#<pk> <loại> — <subject[:40]>"`; `SupportMessage.__str__` → `"<username>: <body[:30]>"`

- [ ] **Step 1: Viết test thất bại**

Thêm vào `app_main/tests.py` (import thêm `SupportMessage`, `SupportTicket`; import `from django.contrib import admin`):

```python
@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class ModeratorModelTests(TestCase):
    """Trường vai trò, lý do báo cáo mới, trạng thái tranh chấp và model hỗ trợ."""

    def test_profile_role_defaults_to_student(self):
        user = create_user('sv1')
        self.assertEqual(user.profile.role, Profile.Role.STUDENT)
        self.assertFalse(user.profile.is_moderator)

    def test_report_has_prohibited_reason(self):
        self.assertEqual(
            Report.Reason.PROHIBITED.label, 'Hàng cấm / vi phạm pháp luật'
        )

    def test_disputed_order_is_open(self):
        self.assertTrue(Order(status=Order.Status.DISPUTED).is_open)

    def test_support_ticket_and_messages(self):
        buyer = create_user('buyer1')
        seller = create_user('seller1')
        post = create_post(seller)
        order = Order.objects.create(
            post=post, buyer=buyer, seller=seller,
            price_snapshot=50000, status=Order.Status.CONFIRMED,
        )
        ticket = SupportTicket.objects.create(
            order=order, opened_by=buyer,
            category=SupportTicket.Category.DISPUTE,
            subject='Sách không đúng mô tả',
        )
        self.assertEqual(ticket.status, SupportTicket.Status.OPEN)
        self.assertIn('#{}'.format(ticket.pk), str(ticket))
        SupportMessage.objects.create(ticket=ticket, author=buyer, body='Tin 1')
        SupportMessage.objects.create(ticket=ticket, author=seller, body='Tin 2')
        self.assertEqual(
            [m.body for m in ticket.messages.all()], ['Tin 1', 'Tin 2']
        )

    def test_support_models_registered_in_admin(self):
        self.assertTrue(admin.site.is_registered(SupportTicket))
        self.assertTrue(admin.site.is_registered(SupportMessage))
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `python manage.py test app_main.tests.ModeratorModelTests -v 2`
Expected: FAIL/ERROR vì chưa có `SupportTicket`, `SupportMessage`, `Profile.Role`, `Report.Reason.PROHIBITED`, `Order.Status.DISPUTED`.

- [ ] **Step 3: Sửa `app_main/models.py`**

Thêm vào `Profile` (ngay trên `created_at`):

```python
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Sinh viên'
        MODERATOR = 'MODERATOR', 'Kiểm duyệt viên'

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STUDENT,
        db_index=True, verbose_name="Vai trò",
    )
```

và property dưới `__str__` của `Profile`:

```python
    @property
    def is_moderator(self):
        """Chỉ đúng khi role là MODERATOR; quyền admin xét riêng bằng is_staff."""
        return self.role == self.Role.MODERATOR
```

Thêm vào `Report.Reason` (giữa `DUPLICATE` và `OTHER`):

```python
        PROHIBITED = 'PROHIBITED', 'Hàng cấm / vi phạm pháp luật'
```

Thêm vào `Order.Status` (sau `CANCELLED`) và sửa `is_open`:

```python
        DISPUTED = 'DISPUTED', 'Đang tranh chấp'
```

```python
    @property
    def is_open(self):
        """Đơn còn chờ xử lý (chưa bị từ chối/huỷ/hoàn tất)."""
        return self.status in (
            self.Status.PENDING, self.Status.CONFIRMED, self.Status.DISPUTED
        )
```

Thêm hai model mới ngay sau `Order`:

```python
class SupportTicket(models.Model):
    """Phiên hỗ trợ / tranh chấp gắn với một đơn hàng."""

    class Category(models.TextChoices):
        DISPUTE = 'DISPUTE', 'Tranh chấp đơn hàng'
        QUESTION = 'QUESTION', 'Cần giải đáp'
        OTHER = 'OTHER', 'Vấn đề khác'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Chờ tiếp nhận'
        IN_PROGRESS = 'IN_PROGRESS', 'Đang xử lý'
        RESOLVED = 'RESOLVED', 'Đã giải quyết'

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name='support_tickets', verbose_name="Đơn hàng",
    )
    opened_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='support_tickets_opened', verbose_name="Người mở",
    )
    category = models.CharField(
        max_length=20, choices=Category.choices,
        default=Category.QUESTION, verbose_name="Loại yêu cầu",
    )
    subject = models.CharField(max_length=200, verbose_name="Tiêu đề")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN,
        db_index=True, verbose_name="Trạng thái",
    )
    handled_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='support_tickets_handled', verbose_name="Người xử lý",
    )
    resolution_note = models.TextField(
        max_length=1000, blank=True, verbose_name="Kết luận xử lý",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Phiên hỗ trợ"
        verbose_name_plural = "Phiên hỗ trợ"

    def __str__(self):
        return f"#{self.pk} {self.get_category_display()} — {self.subject[:40]}"


class SupportMessage(models.Model):
    """Một tin nhắn trong phiên hỗ trợ."""

    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.CASCADE,
        related_name='messages', verbose_name="Phiên hỗ trợ",
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='support_messages', verbose_name="Người gửi",
    )
    body = models.TextField(max_length=2000, verbose_name="Nội dung")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Tin nhắn hỗ trợ"
        verbose_name_plural = "Tin nhắn hỗ trợ"

    def __str__(self):
        return f"{self.author.username}: {self.body[:30]}"
```

- [ ] **Step 4: Sinh migration và migrate**

Run: `python manage.py makemigrations app_main --name moderator_support`
Expected: tạo `app_main/migrations/0005_moderator_support.py` với `AddField` (role), 2 `AlterField` (order.status, report.reason) và 2 `CreateModel`.

Run: `python manage.py migrate`
Expected: `Applying app_main.0005_moderator_support... OK`.

- [ ] **Step 5: Chạy lại test model**

Run: `python manage.py test app_main.tests.ModeratorModelTests -v 2`
Expected: PASS (5 test).

- [ ] **Step 6: Đăng ký admin**

Trong `app_main/admin.py`:
- `ProfileInline.fields`: thêm `'role'`.
- `ProfileAdmin.list_display`: thêm `'role'`; `list_filter`: thêm `'role'`.
- Cuối tệp, thêm `SupportTicketAdmin` (`list_display = ('subject', 'order', 'opened_by', 'category', 'status', 'handled_by', 'created_at')`, `list_filter = ('category', 'status')`, `search_fields = ('subject', 'order__post__title')`, `autocomplete_fields` không dùng) và `SupportMessageAdmin` (`list_display = ('ticket', 'author', 'created_at')`, `search_fields = ('body',)`), đăng ký bằng `@admin.register`.

- [ ] **Step 7: Chạy lại test và commit**

Run: `python manage.py test app_main.tests.ModeratorModelTests -v 2`
Expected: PASS.

```bash
git add app_main/models.py app_main/admin.py app_main/migrations/0005_moderator_support.py app_main/tests.py
git commit -m "feat: them vai tro moderator, tranh chap don hang va ly do hang cam"
```

---

### Task 2: Phân quyền dùng chung, context processor và kiểm duyệt báo cáo

**Files:**
- Create: `app_main/permissions.py`
- Modify: `app_main/views.py` (import, thay decorator ở 11 view sinh viên — 2 view hỗ trợ thêm ở Task 4 — và 5 view quản trị)
- Modify: `app_main/context_processors.py`
- Test: `app_main/tests.py` (helper `create_moderator`, thêm `ModeratorRoleTests`, `ReportModerationTests`)

**Interfaces:**
- Consumes: `Profile.Role`, `can_moderate` (Task 1).
- Produces:
  - `is_moderator(user) -> bool` — chỉ đúng khi `profile.role == MODERATOR`
  - `can_moderate(user) -> bool` — `is_authenticated and (is_staff or is_moderator(user))`
  - `@moderator_required`, `@student_required`
  - context keys: `pending_reports` (Moderator/Admin), `pending_total` (tổng bài + báo cáo + phiên đang chờ)

- [ ] **Step 1: Viết test thất bại**

Thêm helper dưới `create_user`:

```python
def create_moderator(username='moderator', password='MatKhau123', **kwargs):
    """Tạo tài khoản kiểm duyệt viên."""
    user = create_user(username, password, **kwargs)
    user.profile.role = Profile.Role.MODERATOR
    user.profile.save()
    return user
```

Thêm 2 class:

```python
@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class ModeratorRoleTests(TestCase):
    """Moderator vào được khu kiểm duyệt nhưng không dùng được chức năng sinh viên."""

    def setUp(self):
        self.mod = create_moderator('moder')
        self.student = create_user('sv')
        self.seller = create_user('seller')
        self.post = create_post(self.seller)

    def test_moderator_can_open_dashboard(self):
        self.client.force_login(self.mod)
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 200)

    def test_student_redirected_from_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(response, reverse('home'))

    def test_moderator_blocked_from_student_actions(self):
        self.client.force_login(self.mod)
        requests = [
            ('create_post', {}, {'title': 'x', 'description': 'x', 'price': '1',
                                 'condition': Post.Condition.GOOD, 'category': ''}),
            ('buy_post', {'pk': self.post.pk}, {'contact': '0901'}),
            ('add_comment', {'pk': self.post.pk}, {'content': 'x'}),
            ('report_post', {'pk': self.post.pk}, {'reason': Report.Reason.SPAM}),
            ('toggle_favorite', {'pk': self.post.pk}, {}),
        ]
        for name, kwargs, data in requests:
            response = self.client.post(reverse(name, kwargs=kwargs), data)
            self.assertRedirects(response, reverse('home'))
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(Report.objects.count(), 0)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_context_processor_counts_for_moderator(self):
        create_post(self.seller, title='Cho duyet', status=Post.Status.PENDING)
        Report.objects.create(
            post=self.post, reporter=self.student, reason=Report.Reason.SPAM
        )
        self.client.force_login(self.mod)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['pending_reports'], 1)
        self.assertEqual(response.context['pending_total'], 2)
```

```python
@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class ReportModerationTests(TestCase):
    """Xử lý báo cáo vi phạm, gồm lý do hàng cấm."""

    def setUp(self):
        self.mod = create_moderator('moder')
        self.reporter = create_user('reporter')
        self.seller = create_user('seller')
        self.post = create_post(self.seller, status=Post.Status.ACTIVE)

    def test_report_form_lists_prohibited_reason(self):
        self.client.force_login(self.reporter)
        response = self.client.get(reverse('report_post', args=[self.post.pk]))
        self.assertContains(response, 'Hàng cấm')

    def test_resolve_prohibited_report_hides_post(self):
        report = Report.objects.create(
            post=self.post, reporter=self.reporter,
            reason=Report.Reason.PROHIBITED,
        )
        self.client.force_login(self.mod)
        self.client.post(reverse('admin_resolve_report', args=[report.pk]))
        report.refresh_from_db(); self.post.refresh_from_db()
        self.assertEqual(report.status, Report.Status.RESOLVED)
        self.assertEqual(self.post.status, Post.Status.HIDDEN)

    def test_resolve_sold_post_keeps_sold(self):
        self.post.status = Post.Status.SOLD; self.post.save()
        report = Report.objects.create(
            post=self.post, reporter=self.reporter, reason=Report.Reason.FAKE
        )
        self.client.force_login(self.mod)
        self.client.post(reverse('admin_resolve_report', args=[report.pk]))
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, Post.Status.SOLD)

    def test_dismiss_report_keeps_post(self):
        report = Report.objects.create(
            post=self.post, reporter=self.reporter, reason=Report.Reason.OTHER
        )
        self.client.force_login(self.mod)
        self.client.post(reverse('admin_dismiss_report', args=[report.pk]))
        report.refresh_from_db(); self.post.refresh_from_db()
        self.assertEqual(report.status, Report.Status.DISMISSED)
        self.assertEqual(self.post.status, Post.Status.ACTIVE)
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `python manage.py test app_main.tests.ModeratorRoleTests app_main.tests.ReportModerationTests -v 2`
Expected: FAIL — chưa có `create_moderator`, moderator bị `staff_required` đẩy về trang chủ, `report_post` vẫn cho moderator gửi.

- [ ] **Step 3: Tạo `app_main/permissions.py`**

```python
"""Quy tắc phân quyền dùng chung cho view và context processor.

Quy ước: is_staff luôn thắng role. Moderator là tài khoản riêng, chỉ kiểm duyệt.
"""

from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .models import Profile


def is_moderator(user):
    """Đúng khi hồ sơ có role MODERATOR (không xét is_staff)."""
    return (
        user.is_authenticated
        and getattr(getattr(user, 'profile', None), 'role', None)
        == Profile.Role.MODERATOR
    )


def can_moderate(user):
    """Admin hoặc Moderator — người được vào khu kiểm duyệt."""
    return user.is_authenticated and (user.is_staff or is_moderator(user))


def _login_redirect(request):
    return redirect(
        f"{reverse(settings.LOGIN_URL)}?next={quote(request.get_full_path())}"
    )


def moderator_required(view):
    """Chặn người không phải Admin/Moderator khỏi khu kiểm duyệt."""
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _login_redirect(request)
        if not can_moderate(request.user):
            messages.error(request, "Bạn không có quyền truy cập trang quản trị.")
            return redirect('home')
        return view(request, *args, **kwargs)
    return _wrapped


def student_required(view):
    """Chặn Moderator khỏi chức năng của sinh viên; Admin vẫn được."""
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _login_redirect(request)
        if is_moderator(request.user) and not request.user.is_staff:
            messages.error(
                request,
                "Tài khoản kiểm duyệt viên không thực hiện được chức năng này.",
            )
            return redirect('home')
        return view(request, *args, **kwargs)
    return _wrapped
```

- [ ] **Step 4: Gắn decorator trong `app_main/views.py`**

- Import `from .permissions import can_moderate, moderator_required, student_required`.
- Thay `@login_required` bằng `@student_required` ở: `create_post`, `edit_post`, `delete_post`, `toggle_sold`, `upload_post_image`, `delete_post_image`, `buy_post`, `report_post`, `toggle_favorite`, `add_comment`, `add_review`. Giữ nguyên thứ tự: `@require_POST` ở trên, `@student_required` ở dưới.
- Thay `@staff_required` bằng `@moderator_required` ở: `admin_dashboard`, `admin_approve_post`, `admin_reject_post`, `admin_resolve_report`, `admin_dismiss_report`. Sau khi `grep -rn "staff_required" app_main` xác nhận không còn tham chiếu, **xoá** hàm `staff_required` để tránh hai nguồn sự thật, xoá `from functools import wraps` và `from urllib.parse import quote`; **giữ** `from django.conf import settings` vì view `home` còn dùng `settings.POSTS_PER_PAGE`.
- Thêm `from .models import Profile` và `SupportTicket` khi cần ở các task sau.

- [ ] **Step 5: Sửa `app_main/context_processors.py`**

```python
from .models import Category, Post, Report, SupportTicket
from .permissions import can_moderate
```

Trong `site_context`, thay khối `pending_reports` bằng:

```python
    is_mod = can_moderate(request.user)
    open_ticket_states = (
        SupportTicket.Status.OPEN, SupportTicket.Status.IN_PROGRESS
    )
    if is_mod:
        pending_posts = Post.objects.filter(status=Post.Status.PENDING).count()
        pending_reports = Report.objects.filter(status=Report.Status.PENDING).count()
        open_tickets = SupportTicket.objects.filter(
            status__in=open_ticket_states
        ).count()
    else:
        pending_posts = pending_reports = open_tickets = 0
    return {
        'nav_categories': Category.objects.all()[:8],
        'pending_reports': pending_reports,
        'pending_total': pending_posts + pending_reports + open_tickets,
    }
```

Ghi chú: chỉ trả `pending_reports` và `pending_total` ra context, không trả
`pending_posts`/`open_tickets` để tránh trùng tên với QuerySet cùng tên mà
`admin_dashboard` truyền. `pending_total` luôn là số nguyên nên navbar so sánh
an toàn ở mọi trang.

- [ ] **Step 6: Chạy lại test**

Run: `python manage.py test app_main.tests.ModeratorRoleTests app_main.tests.ReportModerationTests -v 2`
Expected: PASS (8 test).

- [ ] **Step 7: Chạy các class cũ bị ảnh hưởng**

Run: `python manage.py test app_main.tests.AdminDashboardTests app_main.tests.OrderFlowTests app_main.tests.AuthViewTests -v 2`
Expected: PASS — admin vẫn vào `/quan-tri/`, sinh viên vẫn dùng được chức năng cũ.

- [ ] **Step 8: Commit**

```bash
git add app_main/permissions.py app_main/views.py app_main/context_processors.py app_main/tests.py
git commit -m "feat: phan quyen moderator va xu ly bao cao vi pham"
```

---

### Task 3: Luồng duyệt bài đăng

**Files:**
- Modify: `app_main/views.py` (`create_post` ~L251, `edit_post` ~L275, `post_detail` ~L146, `my_posts` ~L747)
- Modify: `templates/app_main/post_detail.html` (khối tiêu đề ~L20–80, khối nút mua/báo cáo ~L180–250)
- Modify: `templates/app_main/my_posts.html` (thống kê ~L19–36, bộ lọc ~L38–52)
- Test: `app_main/tests.py` (sửa `PostManagementTests.test_create_post` ~L535, `UserJourneyTests.test_full_journey` ~L841; thêm `PostApprovalTests`)

**Interfaces:**
- Consumes: `can_moderate`, `student_required`, `@moderator_required` (Task 2).
- Produces: `post_detail` trả 404 cho người không có quyền xem bài không `ACTIVE`/`SOLD`; `my_posts` nhận `?status=pending`; context `stats.pending`.

- [ ] **Step 1: Viết test thất bại**

Thêm `PostApprovalTests`:

```python
@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class PostApprovalTests(TestCase):
    """Duyệt bài trước khi hiển thị, duyệt lại khi sửa, chặn xem bài ẩn."""

    def setUp(self):
        self.mod = create_moderator('moder')
        self.seller = create_user('seller')
        self.other = create_user('other')

    def _create(self, title='Bài mới'):
        return self.client.post(reverse('create_post'), {
            'title': title, 'description': 'Mô tả đủ dài.',
            'price': '30000', 'condition': Post.Condition.GOOD, 'category': '',
        })

    def test_new_post_is_pending_and_hidden_from_home(self):
        self.client.force_login(self.seller)
        self._create('Giáo trình chờ duyệt')
        post = Post.objects.get(title='Giáo trình chờ duyệt')
        self.assertEqual(post.status, Post.Status.PENDING)
        self.assertNotContains(self.client.get(reverse('home')), 'Giáo trình chờ duyệt')

    def test_owner_sees_pending_post_but_other_gets_404(self):
        post = create_post(self.seller, status=Post.Status.PENDING)
        self.client.force_login(self.seller)
        self.assertEqual(
            self.client.get(reverse('post_detail', args=[post.pk])).status_code, 200
        )
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse('post_detail', args=[post.pk])).status_code, 404
        )

    def test_moderator_approves_post(self):
        post = create_post(self.seller, status=Post.Status.PENDING, title='Chờ duyệt')
        self.client.force_login(self.mod)
        self.client.post(reverse('admin_approve_post', args=[post.pk]))
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.ACTIVE)
        self.assertContains(self.client.get(reverse('home')), 'Chờ duyệt')

    def test_reject_shows_reason_to_owner(self):
        post = create_post(self.seller, status=Post.Status.PENDING)
        self.client.force_login(self.mod)
        self.client.post(reverse('admin_reject_post', args=[post.pk]), {
            'reason': 'Ảnh mờ, không rõ sản phẩm.'
        })
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.REJECTED)
        self.client.force_login(self.seller)
        response = self.client.get(reverse('post_detail', args=[post.pk]))
        self.assertContains(response, 'Ảnh mờ, không rõ sản phẩm.')

    def test_seller_edit_active_post_returns_to_pending(self):
        post = create_post(self.seller, status=Post.Status.ACTIVE,
                           rejection_reason='Lý do cũ')
        self.client.force_login(self.seller)
        self.client.post(reverse('edit_post', args=[post.pk]), {
            'title': 'Đã sửa', 'description': 'Mô tả mới.',
            'price': '30000', 'condition': Post.Condition.GOOD, 'category': '',
        })
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.PENDING)
        self.assertEqual(post.rejection_reason, '')

    def test_seller_edit_sold_post_keeps_sold(self):
        post = create_post(self.seller, status=Post.Status.SOLD)
        post.is_sold = True; post.save()
        self.client.force_login(self.seller)
        self.client.post(reverse('edit_post', args=[post.pk]), {
            'title': 'Đã sửa', 'description': 'Mô tả mới.',
            'price': '30000', 'condition': Post.Condition.GOOD, 'category': '',
        })
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.SOLD)

    def test_admin_edit_keeps_status(self):
        post = create_post(self.seller, status=Post.Status.REJECTED)
        self.client.force_login(create_user('admin2', is_staff=True))
        self.client.post(reverse('edit_post', args=[post.pk]), {
            'title': 'Admin sửa', 'description': 'Mô tả mới.',
            'price': '30000', 'condition': Post.Condition.GOOD, 'category': '',
        })
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.REJECTED)

    def test_my_posts_counts_pending(self):
        create_post(self.seller, status=Post.Status.PENDING)
        create_post(self.seller, status=Post.Status.ACTIVE)
        self.client.force_login(self.seller)
        response = self.client.get(reverse('my_posts'), {'status': 'pending'})
        self.assertEqual(response.context['stats']['pending'], 1)
        self.assertEqual(len(response.context['posts']), 1)
```

Sửa `test_create_post`: thêm `self.assertEqual(post.status, Post.Status.PENDING)` sau dòng `self.assertEqual(post.seller, self.user)`.

Sửa `test_full_journey`: ngay sau `self.assertEqual(post.seller.username, 'hao')`, thêm comment và 2 dòng giả lập duyệt:

```python
        # Kiểm duyệt viên duyệt bài trước khi lên sàn
        post.status = Post.Status.ACTIVE
        post.save(update_fields=['status'])
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `python manage.py test app_main.tests.PostApprovalTests -v 2`
Expected: FAIL — bài mới vẫn `ACTIVE`, người khác vẫn xem được bài `PENDING`, sửa bài `ACTIVE` vẫn giữ `ACTIVE`.

- [ ] **Step 3: Sửa `create_post`**

```python
            post.status = Post.Status.PENDING
            post.save()
            messages.success(
                request,
                "📝 Tin đã được gửi và đang chờ kiểm duyệt. "
                "Tin sẽ hiển thị trên sàn sau khi được duyệt.",
            )
```

- [ ] **Step 4: Sửa `edit_post`**

Thay khối `if form.is_valid():` bằng:

```python
        if form.is_valid():
            post = form.save(commit=False)
            # Admin sửa thì giữ nguyên trạng thái; người bán sửa thì duyệt lại.
            if not request.user.is_staff and post.status != Post.Status.SOLD:
                post.status = Post.Status.PENDING
                post.rejection_reason = ''
            post.save()
            if request.user.is_staff:
                messages.success(request, "✏️ Đã cập nhật bài đăng thành công!")
            else:
                messages.success(
                    request,
                    "📝 Đã lưu thay đổi. Tin quay lại trạng thái chờ kiểm duyệt.",
                )
            return redirect(post.get_absolute_url())
```

- [ ] **Step 5: Thêm guard vào `post_detail`**

Import `Http404` từ `django.http`. Ngay sau khi lấy `post`, **trước** khối tăng lượt xem:

```python
    # Bài chưa duyệt / bị từ chối / bị ẩn chỉ chủ bài và người kiểm duyệt xem được
    if (
        post.status not in (Post.Status.ACTIVE, Post.Status.SOLD)
        and post.seller != request.user
        and not can_moderate(request.user)
    ):
        raise Http404("Bài đăng không tồn tại")
```

Truyền thêm `'can_moderate': can_moderate(request.user)` vào context của `post_detail` để template ẩn nút mua/báo cáo.

- [ ] **Step 6: Sửa `my_posts`**

- `status_map` thêm `'pending': Post.Status.PENDING`.
- `stats` thêm `'pending': all_posts.filter(status=Post.Status.PENDING).count()`.

- [ ] **Step 7: Sửa template**

- `my_posts.html`: đổi grid thống kê thành `grid-cols-2 lg:grid-cols-5`, thêm thẻ "Chờ duyệt" dùng `stats.pending` (màu `text-amber-600`); thêm chip lọc `<a href="?status=pending">Chờ duyệt ({{ stats.pending }})</a>` cùng style `btn btn-sm` với các chip hiện có.
- `post_detail.html`:
  - Ngay dưới tiêu đề sản phẩm, thêm banner khi `post.status != 'ACTIVE' and post.status != 'SOLD'`: bài `PENDING` → "⏳ Tin đang chờ kiểm duyệt"; `REJECTED` → "🚫 Tin bị từ chối" + `{{ post.rejection_reason }}`; `HIDDEN` → "🙈 Tin đã bị ẩn".
  - Bao khối nút "Đặt mua" và nút "Báo cáo" trong `{% if post.status == 'ACTIVE' %}`; nhánh else chỉ giữ nút "Yêu thích" cho người dùng thường.
  - Chỉ hiện nút "Báo cáo" khi `not can_moderate`.

- [ ] **Step 8: Chạy test**

Run: `python manage.py test app_main.tests.PostApprovalTests app_main.tests.PostManagementTests app_main.tests.UserJourneyTests app_main.tests.HomeViewTests -v 2`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add app_main/views.py templates/app_main/post_detail.html templates/app_main/my_posts.html app_main/tests.py
git commit -m "feat: duyet bai dang truoc khi hien thi va duyet lai khi sua"
```

---

### Task 4: Hỗ trợ — mở phiên và trao đổi hai chiều

**Files:**
- Modify: `app_main/forms.py` (thêm 3 form sau `OrderForm` ~L393)
- Modify: `app_main/views.py` (thêm `_is_order_party`, `_can_view_ticket`, 4 view; sửa `buy_post` bộ lọc đơn đang mở)
- Modify: `app_main/urls.py` (4 route hỗ trợ)
- Create: `templates/app_main/my_tickets.html`, `support_ticket_form.html`, `support_ticket_detail.html`
- Modify: `templates/app_main/order_detail.html`, `my_orders.html`
- Test: `app_main/tests.py` (thêm `SupportTicketTests` phần mở phiên/trả lời)

**Interfaces:**
- Consumes: `SupportTicket`, `SupportMessage`, `Order.Status.DISPUTED`.
- Produces:
  - `SupportTicketForm` (`category`, `subject`, `body`; `field_order = ['category', 'subject', 'body']`)
  - `SupportReplyForm` (`body`)
  - `TicketResolveForm` (`resolution_note`, `decision` ∈ `none|cancel|complete`) — Task 5 dùng
  - `my_tickets`, `support_ticket_detail`, `open_support_ticket`, `support_ticket_reply`
  - `_is_order_party(user, order)`, `_can_view_ticket(user, ticket)`

- [ ] **Step 1: Viết test thất bại**

```python
@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class SupportTicketTests(TestCase):
    """Phiên hỗ trợ gắn với đơn hàng và tranh chấp."""

    def setUp(self):
        self.buyer = create_user('buyer')
        self.seller = create_user('seller')
        self.outsider = create_user('outsider')
        self.mod = create_moderator('moder')
        self.post = create_post(self.seller)
        self.order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            price_snapshot=50000, status=Order.Status.CONFIRMED,
        )

    def _open(self, user, category=SupportTicket.Category.DISPUTE, subject='Sai mô tả'):
        self.client.force_login(user)
        return self.client.post(
            reverse('open_support_ticket', args=[self.order.pk]),
            {'category': category, 'subject': subject, 'body': 'Nội dung đầu tiên'},
        )

    def _ticket(self):
        return SupportTicket.objects.get(order=self.order)

    def test_buyer_opens_dispute(self):
        self._open(self.buyer)
        self.order.refresh_from_db()
        ticket = self._ticket()
        self.assertEqual(ticket.status, SupportTicket.Status.OPEN)
        self.assertEqual(ticket.opened_by, self.buyer)
        self.assertEqual(ticket.messages.count(), 1)
        self.assertEqual(self.order.status, Order.Status.DISPUTED)

    def test_seller_opens_question_keeps_order(self):
        self._open(self.seller, SupportTicket.Category.QUESTION, 'Hỏi về đơn')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)
        self.assertEqual(self._ticket().category, SupportTicket.Category.QUESTION)

    def test_outsider_cannot_open_or_view(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(reverse('open_support_ticket', args=[self.order.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse('support_ticket_detail', args=[ticket.pk])).status_code,
            404,
        )

    def test_only_one_active_ticket_per_order(self):
        self._open(self.buyer)
        response = self._open(self.buyer, subject='Mở lần hai')
        self.assertEqual(SupportTicket.objects.filter(order=self.order).count(), 1)
        self.assertRedirects(
            response,
            reverse('support_ticket_detail', args=[self._ticket().pk]),
        )

    def test_participant_reply_adds_message(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.seller)
        self.client.post(reverse('support_ticket_reply', args=[ticket.pk]),
                         {'body': 'Người bán trả lời'})
        self.assertEqual(ticket.messages.count(), 2)

    def test_outsider_cannot_reply(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.outsider)
        response = self.client.post(reverse('support_ticket_reply', args=[ticket.pk]),
                                    {'body': 'Chen ngang'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ticket.messages.count(), 1)

    def test_cannot_reply_to_resolved_ticket(self):
        self._open(self.buyer)
        ticket = self._ticket()
        ticket.status = SupportTicket.Status.RESOLVED
        ticket.save(update_fields=['status'])
        self.client.force_login(self.buyer)
        self.client.post(reverse('support_ticket_reply', args=[ticket.pk]),
                         {'body': 'Tin sau khi đóng'})
        self.assertEqual(ticket.messages.count(), 1)
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `python manage.py test app_main.tests.SupportTicketTests -v 2`
Expected: FAIL/ERROR vì chưa có route và view hỗ trợ.

- [ ] **Step 3: Thêm form trong `app_main/forms.py`**

Thêm `SupportTicket` vào import model. Viết 3 class:

```python
class SupportTicketForm(forms.ModelForm):
    """Mở phiên hỗ trợ cho một đơn hàng."""

    body = forms.CharField(
        label="Nội dung",
        widget=forms.Textarea(attrs={
            'class': TEXTAREA_CLASS, 'rows': 4, 'maxlength': 2000,
            'placeholder': 'Mô tả vấn đề bạn đang gặp...',
        }),
    )

    class Meta:
        model = SupportTicket
        fields = ['category', 'subject']
        field_order = ['category', 'subject', 'body']
        widgets = {
            'category': forms.Select(attrs={'class': SELECT_CLASS}),
            'subject': forms.TextInput(attrs={'class': INPUT_CLASS}),
        }
        labels = {'category': "Loại yêu cầu", 'subject': "Tiêu đề"}


class SupportReplyForm(forms.Form):
    """Một tin nhắn trong phiên hỗ trợ."""

    body = forms.CharField(
        label="Nội dung",
        max_length=2000,
        widget=forms.Textarea(attrs={
            'class': TEXTAREA_CLASS, 'rows': 3, 'maxlength': 2000,
            'placeholder': 'Nhập nội dung trao đổi...',
        }),
    )


class TicketResolveForm(forms.Form):
    """Kết luận của kiểm duyệt viên."""

    resolution_note = forms.CharField(
        label="Kết luận xử lý",
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': TEXTAREA_CLASS, 'rows': 3, 'maxlength': 1000,
        }),
    )
    decision = forms.ChoiceField(
        label="Quyết định cho đơn hàng",
        choices=[
            ('none', 'Chỉ kết luận phiên, không đổi đơn'),
            ('cancel', 'Huỷ đơn hàng'),
            ('complete', 'Xác nhận hoàn tất đơn hàng'),
        ],
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )
```

- [ ] **Step 4: Thêm helper + view trong `app_main/views.py`**

Import `timezone`, `Http404`, `SupportTicketForm`/`SupportReplyForm`/`TicketResolveForm`, `SupportMessage`/`SupportTicket`.

```python
def _is_order_party(user, order):
    """Người mua hoặc người bán của đơn."""
    return user in (order.buyer, order.seller)


def _can_view_ticket(user, ticket):
    """Người mở phiên, hai bên của đơn, hoặc người kiểm duyệt."""
    return can_moderate(user) or _is_order_party(user, ticket.order)
```

`my_tickets` (`@login_required`): lấy phiên mà người dùng là `opened_by` **hoặc** `order__buyer` **hoặc** `order__seller`, `.distinct()`, `select_related('order__post', 'order__buyer', 'order__seller')`; lọc `?status=open|resolved`; render `my_tickets.html` với `tickets`, `status_filter`.

`support_ticket_detail` (`@login_required`): lấy ticket kèm `order__post`, `order__buyer`, `order__seller`, prefetch `messages__author__profile`; nếu `not _can_view_ticket(...)` → `raise Http404`; context thêm `reply_form` (`None` khi `RESOLVED`).

`open_support_ticket` (`@require_POST` / `@student_required` cho POST, nhưng cần GET để hiện form → dùng `@student_required` không kèm `require_POST`):
- `order = get_object_or_404(Order.objects.select_related('post'), pk=pk)`; nếu `not _is_order_party` → `raise Http404`.
- `existing = SupportTicket.objects.filter(order=order, status__in=[SupportTicket.Status.OPEN, SupportTicket.Status.IN_PROGRESS]).first()`; nếu có → `messages.warning` và `redirect('support_ticket_detail', pk=existing.pk)`.
- POST hợp lệ → tạo ticket (`opened_by=request.user`), tạo `SupportMessage(author=request.user, body=form.cleaned_data['body'])`; nếu `category == DISPUTE` và `order.status in (PENDING, CONFIRMED)` → `order.status = DISPUTED; order.save(update_fields=['status', 'updated_at'])`; `redirect` tới chi tiết phiên.
- GET → render `support_ticket_form.html` với `order`, `form`.
- Lưu ý: khi `existing` tồn tại, chặn **trước** khi kiểm tra GET/POST để cả hai phương thức đều về phiên cũ.

`support_ticket_reply` (`@require_POST` + `@student_required`):
- Lấy ticket; `not _can_view_ticket` → `raise Http404`.
- `ticket.status == RESOLVED` → `messages.error` + redirect chi tiết.
- Form hợp lệ → tạo `SupportMessage`; cập nhật `ticket.updated_at` bằng `ticket.save(update_fields=['updated_at'])` để danh sách phiên sắp đúng thứ tự hoạt động; `messages.success`; redirect chi tiết.

- [ ] **Step 5: Sửa `buy_post` coi `DISPUTED` là đơn đang mở**

Đổi `status__in=[Order.Status.PENDING, Order.Status.CONFIRMED]` thành thêm `Order.Status.DISPUTED` — người mua không tạo đơn mới khi đơn cũ đang tranh chấp.

- [ ] **Step 6: Thêm route vào `app_main/urls.py`**

Đặt sau nhóm "Đặt mua & đơn hàng":

```python
    # --- Hỗ trợ (người mua / người bán) ---
    path('ho-tro/', views.my_tickets, name='my_tickets'),
    path('ho-tro/<int:pk>/', views.support_ticket_detail, name='support_ticket_detail'),
    path('don-hang/<int:pk>/ho-tro/', views.open_support_ticket, name='open_support_ticket'),
    path('ho-tro/<int:pk>/tra-loi/', views.support_ticket_reply, name='support_ticket_reply'),
```

- [ ] **Step 7: Tạo 3 template**

Dùng `{% extends 'base.html' %}`, class `card`/`btn`/`badge` sẵn có:
- `my_tickets.html`: tiêu đề "🆘 Hỗ trợ của tôi"; chip lọc Tất cả / Đang mở / Đã giải quyết; mỗi phiên là một card: `#{{ ticket.pk }} · {{ ticket.get_category_display }}`, tiêu đề, đơn `#{{ ticket.order.pk }}` + tên sản phẩm, badge trạng thái (`OPEN` → cảnh báo, `IN_PROGRESS` → info, `RESOLVED` → success), link tới `support_ticket_detail`.
- `support_ticket_form.html`: tóm tắt đơn (sản phẩm, người mua, người bán, trạng thái) + form (`{{ form.as_p }}` hoặc render từng field như các form hiện có) + nút "Gửi yêu cầu".
- `support_ticket_detail.html`: tóm tắt đơn + badge trạng thái đơn/phiên; luồng tin nhắn (`{% for m in ticket.messages.all %}` — tên người gửi, thời gian, `{{ m.body|linebreaks }}`); nếu `reply_form` thì form trả lời, ngược lại thông báo "Phiên đã kết thúc" + `ticket.resolution_note`.

- [ ] **Step 8: Sửa `order_detail.html` và `my_orders.html`**

- `order_detail.html`: thêm nhánh `{% elif order.status == 'DISPUTED' %}` hiển thị badge cảnh báo "Đang tranh chấp"; khối nút dưới cùng thêm link "🆘 Cần hỗ trợ" → `{% url 'open_support_ticket' order.pk %}` cho cả người mua và người bán; nếu đơn đã có phiên thì link tới phiên gần nhất (`order.support_tickets.first`).
- `my_orders.html`: thêm nhánh badge `DISPUTED` trong cả hai vòng lặp; thêm link "🆘 Hỗ trợ" cạnh link xem chi tiết.

- [ ] **Step 9: Chạy test**

Run: `python manage.py test app_main.tests.SupportTicketTests -v 2`
Expected: 7 test PASS.

- [ ] **Step 10: Commit**

```bash
git add app_main/forms.py app_main/views.py app_main/urls.py app_main/tests.py templates/app_main/my_tickets.html templates/app_main/support_ticket_form.html templates/app_main/support_ticket_detail.html templates/app_main/order_detail.html templates/app_main/my_orders.html
git commit -m "feat: phien ho tro va trao doi giua nguoi mua nguoi ban"
```

---

### Task 5: Kiểm duyệt viên xử lý phiên và quyết định đơn tranh chấp

**Files:**
- Modify: `app_main/views.py` (thêm 5 view; chặn 4 view đơn hàng khi `DISPUTED`)
- Modify: `app_main/urls.py` (5 route `quan-tri/ho-tro/`)
- Create: `templates/app_main/moderator_ticket_list.html`, `moderator_ticket_detail.html`
- Test: `app_main/tests.py` (thêm test vào `SupportTicketTests`)

**Interfaces:**
- Consumes: `moderator_required`, `TicketResolveForm`, `_can_view_ticket`, `SupportTicket` (Task 4).
- Produces:
  - `moderator_ticket_list`, `moderator_ticket_detail`, `moderator_ticket_reply`, `moderator_ticket_resolve`, `moderator_order_decision`
  - Chặn `accept_order` / `reject_order` / `complete_order` / `cancel_order` khi đơn `DISPUTED`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `SupportTicketTests`:

```python
    def test_moderator_reply_sets_in_progress(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.mod)
        self.client.post(reverse('moderator_ticket_reply', args=[ticket.pk]),
                         {'body': 'Kiểm duyệt viên đã tiếp nhận'})
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, SupportTicket.Status.IN_PROGRESS)
        self.assertEqual(ticket.messages.count(), 2)

    def test_resolve_requires_note(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.mod)
        response = self.client.post(reverse('moderator_ticket_resolve', args=[ticket.pk]),
                                    {'resolution_note': '', 'decision': 'cancel'})
        ticket.refresh_from_db(); self.order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ticket.status, SupportTicket.Status.OPEN)
        self.assertEqual(self.order.status, Order.Status.DISPUTED)

    def test_resolve_cancel_order(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.mod)
        self.client.post(reverse('moderator_ticket_resolve', args=[ticket.pk]), {
            'resolution_note': 'Hai bên xác nhận huỷ.', 'decision': 'cancel',
        })
        ticket.refresh_from_db(); self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(ticket.status, SupportTicket.Status.RESOLVED)
        self.assertEqual(ticket.handled_by, self.mod)
        self.assertEqual(ticket.resolution_note, 'Hai bên xác nhận huỷ.')

    def test_resolve_complete_marks_post_sold(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.mod)
        self.client.post(reverse('moderator_ticket_resolve', args=[ticket.pk]), {
            'resolution_note': 'Đã giao dịch xong.', 'decision': 'complete',
        })
        self.order.refresh_from_db(); self.post.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.COMPLETED)
        self.assertEqual(self.post.status, Post.Status.SOLD)
        self.assertTrue(self.post.is_sold)

    def test_resolve_finished_order_only_closes_ticket(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.order.status = Order.Status.COMPLETED
        self.order.save(update_fields=['status'])
        self.client.force_login(self.mod)
        self.client.post(reverse('moderator_ticket_resolve', args=[ticket.pk]), {
            'resolution_note': 'Đơn đã hoàn tất trước đó.', 'decision': 'cancel',
        })
        self.order.refresh_from_db(); ticket.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.COMPLETED)
        self.assertEqual(ticket.status, SupportTicket.Status.RESOLVED)

    def test_disputed_order_blocks_buyer_and_seller_actions(self):
        self._open(self.buyer)
        for name in ('accept_order', 'reject_order', 'complete_order'):
            self.client.force_login(self.seller)
            self.client.post(reverse(name, args=[self.order.pk]))
        self.client.force_login(self.buyer)
        self.client.post(reverse('cancel_order', args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DISPUTED)

    def test_student_cannot_use_moderator_ticket_pages(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.buyer)
        for name in ('moderator_ticket_list', 'moderator_ticket_detail'):
            kwargs = {'pk': ticket.pk} if name.endswith('detail') else {}
            response = self.client.get(reverse(name, kwargs=kwargs))
            self.assertRedirects(response, reverse('home'))

    def test_moderator_ticket_endpoints_reject_get(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.mod)
        for name in ('moderator_ticket_reply', 'moderator_ticket_resolve',
                     'moderator_order_decision'):
            self.assertEqual(
                self.client.get(reverse(name, args=[ticket.pk])).status_code, 405
            )

    def test_order_decision_cancels_without_closing_ticket(self):
        self._open(self.buyer)
        ticket = self._ticket()
        self.client.force_login(self.mod)
        self.client.post(reverse('moderator_order_decision', args=[ticket.pk]), {
            'resolution_note': 'Huỷ vì hàng không giao.', 'decision': 'cancel',
        })
        self.order.refresh_from_db(); ticket.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(ticket.status, SupportTicket.Status.OPEN)
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `python manage.py test app_main.tests.SupportTicketTests -v 2`
Expected: FAIL/ERROR vì thiếu route/view moderator và đơn `DISPUTED` vẫn cho người bán xác nhận.

- [ ] **Step 3: Thêm 5 view kiểm duyệt**

Tất cả dùng `@moderator_required`; các view thay đổi dữ liệu thêm `@require_POST` ngay dưới `@moderator_required` (giữ đúng thứ tự đang dùng cho `@staff_required` + `@require_POST`).

```python
def _resolve_order_decision(order, decision):
    """Áp dụng quyết định của moderator; chỉ đổi khi đơn còn mở."""
    open_states = (Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.DISPUTED)
    if decision == 'cancel' and order.status in open_states:
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
    elif decision == 'complete' and order.status in open_states:
        order.status = Order.Status.COMPLETED
        order.save(update_fields=['status', 'updated_at'])
        post = order.post
        post.status = Post.Status.SOLD
        post.is_sold = True
        post.save(update_fields=['status', 'is_sold', 'updated_at'])
```

- `moderator_ticket_list`: lấy tất cả phiên, `select_related('order__post', 'opened_by', 'handled_by')`, lọc `?status=open|resolved|all` (mặc định `open` = `OPEN|IN_PROGRESS`), sắp `-updated_at`; render `moderator_ticket_list.html`.
- `_render_moderator_ticket_detail(request, ticket, reply_form=None, resolve_form=None)`: helper render chung, nạp `ticket` kèm `order__post`, `order__buyer`, `order__seller`, prefetch `messages__author__profile`; mặc định `reply_form = SupportReplyForm()`, `resolve_form = TicketResolveForm()`; trả về `render(request, 'app_main/moderator_ticket_detail.html', {...})`.
- `moderator_ticket_detail`: lấy ticket (404 nếu không có) rồi gọi helper.
- `moderator_ticket_reply`: lấy ticket; nếu `RESOLVED` → `messages.error` "Phiên đã kết thúc." + redirect chi tiết; `form = SupportReplyForm(request.POST)`; nếu invalid → `_render_moderator_ticket_detail(request, ticket, reply_form=form)`; nếu hợp lệ → nếu `OPEN` thì chuyển `IN_PROGRESS`, tạo `SupportMessage(author=request.user)`, `ticket.save(update_fields=['status', 'updated_at'])`, redirect chi tiết.
- `moderator_ticket_resolve`: `form = TicketResolveForm(request.POST)`; nếu invalid → `_render_moderator_ticket_detail(request, ticket, resolve_form=form)` (status 200) kèm lỗi; nếu hợp lệ → `_resolve_order_decision(...)` rồi đặt `ticket.status = RESOLVED`, `handled_by`, `resolution_note`, `resolved_at=timezone.now()`, `save(...)`; redirect chi tiết.
- `moderator_order_decision`: dùng `TicketResolveForm`; nếu invalid → `_render_moderator_ticket_detail(request, ticket, resolve_form=form)`; nếu hợp lệ → `_resolve_order_decision(...)` **không** đổi trạng thái phiên; redirect chi tiết. Nếu đơn đã kết thúc → `messages.warning` "Đơn đã kết thúc, không đổi được trạng thái."

- [ ] **Step 4: Chặn thao tác trên đơn `DISPUTED`**

Trong `accept_order`, `reject_order`, `complete_order`, `cancel_order`: sau bước kiểm tra quyền của người dùng và **trước** kiểm tra trạng thái hiện có, thêm:

```python
    if order.status == Order.Status.DISPUTED:
        messages.error(
            request,
            "Đơn đang tranh chấp. Chỉ kiểm duyệt viên mới xử lý được.",
        )
        return redirect('order_detail', pk=order.pk)
```

- [ ] **Step 5: Thêm 5 route kiểm duyệt**

Sau nhóm `/quan-tri/` hiện có:

```python
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

- [ ] **Step 6: Tạo 2 template kiểm duyệt**

- `moderator_ticket_list.html`: tiêu đề "🛡️ Hỗ trợ & tranh chấp"; chip lọc Đang mở / Đã giải quyết / Tất cả; bảng gồm phiên, đơn + sản phẩm, người mở, loại, badge trạng thái phiên + trạng thái đơn, người xử lý, link vào chi tiết.
- `moderator_ticket_detail.html`:
  - Tóm tắt đơn: `#{{ ticket.order.pk }}`, sản phẩm, người mua, người bán, giá chốt, badge trạng thái đơn (gồm `DISPUTED` màu cảnh báo). **Không** đặt link `order_detail`: view `order_detail` chỉ cho người mua/người bán (kể cả staff cũng bị chuyển hướng), mà moderator không phải một bên của đơn.
  - Luồng tin nhắn như `support_ticket_detail.html`.
  - Form trả lời (POST `moderator_ticket_reply`).
  - Form kết luận (POST `moderator_ticket_resolve`, render `resolve_form`, nút "Kết luận & đóng phiên").
  - Khi đơn còn mở: thêm 2 form nhỏ POST `moderator_order_decision` với `decision=cancel` / `decision=complete` và một ô `resolution_note` dùng chung (hoặc hiển thị cả form quyết định, nút tương ứng).
  - Khi phiên `RESOLVED`: hiện `resolution_note`, người xử lý, thời điểm; ẩn form trả lời/kết luận; vẫn cho phép quyết định đơn nếu đơn còn mở.

- [ ] **Step 7: Chạy test**

Run: `python manage.py test app_main.tests.SupportTicketTests -v 2`
Expected: 16 test PASS.

- [ ] **Step 8: Commit**

```bash
git add app_main/views.py app_main/urls.py app_main/tests.py templates/app_main/moderator_ticket_list.html templates/app_main/moderator_ticket_detail.html
git commit -m "feat: moderator xu ly tranh chap va quyet dinh don hang"
```

---

### Task 6: Dashboard 2 chế độ và navbar theo vai trò

**Files:**
- Modify: `app_main/views.py` (`admin_dashboard` ~L980)
- Modify: `templates/app_main/admin_dashboard.html`
- Modify: `templates/partials/navbar.html` (~L44–135)
- Modify: `templates/partials/footer.html` (~L31)
- Modify: `templates/app_main/home.html` (~L234)
- Test: `app_main/tests.py` (thêm vào `ModeratorRoleTests`, `AdminDashboardTests`)

**Interfaces:**
- Consumes: `can_moderate`, `pending_total` (Task 2), `SupportTicket` (Task 1); `pending_posts`/`pending_reports`/`open_tickets` là QuerySet do chính view `admin_dashboard` truyền.
- Produces: context `is_moderator_only` (`can_moderate and not is_staff`) cho template; `stats.pending_tickets`, `stats.disputed_orders`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào `ModeratorRoleTests`:

```python
    def test_moderator_dashboard_hides_admin_only_blocks(self):
        self.client.force_login(self.mod)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertNotContains(response, 'Doanh thu')
        self.assertNotContains(response, '/django-admin/')
        self.assertContains(response, 'Hỗ trợ')

    def test_moderator_navbar_swaps_create_button(self):
        self.client.force_login(self.mod)
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Kiểm duyệt')
        self.assertNotContains(response, reverse('create_post'))
```

Thêm vào `AdminDashboardTests`:

```python
    def test_staff_still_sees_revenue_and_django_admin(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertContains(response, 'Doanh thu')
        self.assertContains(response, '/django-admin/')
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

Run: `python manage.py test app_main.tests.ModeratorRoleTests.test_moderator_dashboard_hides_admin_only_blocks app_main.tests.ModeratorRoleTests.test_moderator_navbar_swaps_create_button -v 2`
Expected: FAIL — dashboard và navbar vẫn hiện toàn bộ cho mọi người.

- [ ] **Step 3: Sửa `admin_dashboard`**

- Thêm `open_tickets_qs = SupportTicket.objects.filter(status__in=[SupportTicket.Status.OPEN, SupportTicket.Status.IN_PROGRESS]).select_related('order__post', 'opened_by')`.
- `stats` thêm `'pending_tickets': open_tickets_qs.count()` và `'disputed_orders': Order.objects.filter(status=Order.Status.DISPUTED).count()`.
- Context thêm `'open_tickets': open_tickets_qs.order_by('-updated_at')[:10]` và `'is_moderator_only': can_moderate(request.user) and not request.user.is_staff`.
- Giữ nguyên tên `pending_posts`/`pending_reports` cho QuerySet: context của view được push **sau** context processor nên thắng khi trùng tên, template dashboard vẫn nhận QuerySet (đã có `AdminDashboardTests` cũ bảo vệ). Navbar chỉ dùng `pending_total`.

- [ ] **Step 4: Sửa `admin_dashboard.html`**

Template hiện có **7 link `/django-admin/`**: L25 (nút "⚙️ Django admin" ở header), L107 và L204 (hai link "Xem tất cả →"), L291, L296, L301, L306 (4 thẻ trong section "Lối tắt quản lý"). Ngoài ra L71–82 là thẻ "Người dùng" và L84–97 là thẻ "Doanh thu" trong grid 5 thẻ ở L30.

- Nhãn nhỏ L12–14: `{% if is_moderator_only %}Khu vực kiểm duyệt{% else %}Khu vực quản trị{% endif %}`.
- L25: bọc nút "⚙️ Django admin" trong `{% if not is_moderator_only %}`.
- Grid L30: đổi class thành `grid grid-cols-2 {% if is_moderator_only %}lg:grid-cols-4{% else %}lg:grid-cols-3 xl:grid-cols-6{% endif %} gap-4 mb-8`, và thêm thẻ thứ 6 "Phiên hỗ trợ" (trỏ `#ho-tro`, dùng `stats.pending_tickets`) cho cả hai chế độ — admin 6 thẻ, moderator còn 4 thẻ (Bài chờ duyệt, Báo cáo chờ, Đơn chờ xác nhận, Phiên hỗ trợ).
- Bọc thẻ "Người dùng" (L71–82) và thẻ "Doanh thu" (L84–97) trong `{% if not is_moderator_only %}`.
- Bọc link "Xem tất cả →" ở L107 và L204 trong `{% if not is_moderator_only %}` — chỉ ẩn link, giữ tiêu đề + dòng đếm của hai section.
- Bọc **toàn bộ** section "Lối tắt quản lý" (L287–312, cả thẻ `<section>` mở và đóng) trong `{% if not is_moderator_only %}` vì cả 4 thẻ đều trỏ `/django-admin/`.
- Thêm section `id="ho-tro"` **trước** section "Lối tắt quản lý": tiêu đề "Phiên hỗ trợ đang mở" kèm dòng phụ "🔺 {{ stats.disputed_orders }} đơn đang tranh chấp" (chỉ in khi `stats.disputed_orders > 0`), bảng 10 phiên mới nhất (`open_tickets`) với cột phiên (subject + `get_category_display`), đơn (link `order.post`), người mở, trạng thái, link "Xử lý" → `moderator_ticket_detail`; nếu rỗng hiện "Không có phiên nào đang mở.".

- [ ] **Step 5: Sửa `navbar.html`**

- Điều kiện dùng lại ở mọi chỗ: `{% if not user.profile.is_moderator or user.is_staff %}`. Người chưa đăng nhập vẫn thoả (template trả chuỗi rỗng cho `is_moderator`); admin có `role = MODERATOR` vẫn thoả vì `is_staff` thắng.
- `navbar.html`: bọc nút "Đăng tin" bản desktop (khối `<a>` L47–53) và bản mobile (L129) bằng điều kiện trên. Trong thanh điều hướng desktop, thêm một lớp `{% if not user.profile.is_moderator or user.is_staff %}` **lồng bên trong** khối `{% if user.is_authenticated %}` sẵn có (L28–38) để ẩn "Tin của tôi", "📋 Đơn hàng", "♡ Yêu thích" với moderator. Trong menu mobile, bọc tương tự "📦 Tin của tôi", "📋 Đơn hàng của tôi", "♡ Danh sách yêu thích" (L130–132). Lý do: moderator không đăng bài, không đặt mua, không dùng danh sách yêu thích.
- Dropdown tài khoản: nhánh `{% if user.is_staff %}` giữ "🛡️ Trang quản trị" + link `/django-admin/`, nhưng đổi badge từ `pending_reports` sang `pending_total` khi `> 0`. Lý do: trên `/quan-tri/`, view truyền `pending_reports` là QuerySet đã cắt 10 phần tử nên `{% if pending_reports > 0 %}` luôn sai (Django nuốt `TypeError` và trả `False`) → badge biến mất; `pending_total` luôn là int từ context processor. Thêm `{% elif user.profile.is_moderator %}` với mục "🛡️ Kiểm duyệt" trỏ `admin_dashboard`, kèm badge `pending_total` khi `> 0`.
- Thêm mục "🆘 Hỗ trợ" trỏ `my_tickets` cho sinh viên ở **hai chỗ**: trong dropdown tài khoản (chèn sau "🔐 Đổi mật khẩu", trước khối `{% if user.is_staff %}`) và trong menu mobile (sau "♡ Danh sách yêu thích"); cả hai bọc bằng điều kiện trên.
- `footer.html`: bọc link "Đăng tin bán" (L31) bằng điều kiện trên.
- `home.html`: bọc link "➕ Đăng tin ngay" trong khối trạng thái rỗng (L234) bằng điều kiện trên.

- [ ] **Step 6: Chạy test**

Run: `python manage.py test app_main.tests.ModeratorRoleTests app_main.tests.AdminDashboardTests -v 2`
Expected: PASS (6 + 21 test).

- [ ] **Step 7: Commit**

```bash
git add app_main/views.py templates/app_main/admin_dashboard.html templates/partials/navbar.html templates/partials/footer.html templates/app_main/home.html app_main/tests.py
git commit -m "feat: dashboard hai che do va navbar theo vai tro"
```

---

### Task 7: Seed data

**Files:**
- Modify: `seed_data.py` (sau khối tạo người dùng ~L280, sau khối tạo bài ~L307, cuối script ~L400)
- Test: chạy script hai lần trên DB demo + kiểm tra bằng shell

**Interfaces:**
- Consumes: `Profile.Role.MODERATOR`, `SupportTicket`, `SupportMessage`, `Order.Status.DISPUTED`.
- Produces: tài khoản `moderator` / `123456`; 2 bài `PENDING`; 1 phiên tranh chấp mẫu.

- [ ] **Step 1: Thêm tài khoản moderator**

Sau khối tạo người dùng sinh viên, thêm (idempotent):

```python
    # --- 4b. Tài khoản kiểm duyệt viên ---
    moderator, created = User.objects.get_or_create(
        username='moderator',
        defaults={
            'email': 'moderator@sachgocuni.edu.vn',
            'first_name': 'Kiểm duyệt viên',
        },
    )
    if created:
        moderator.set_password('123456')
        moderator.save()
    moderator.profile.role = Profile.Role.MODERATOR
    moderator.profile.faculty = 'Ban quản trị sàn'
    moderator.profile.save()
    print("   ✅ Tài khoản kiểm duyệt viên: moderator / 123456")
```

- [ ] **Step 2: Thêm 2 bài chờ duyệt**

Sau vòng tạo bài đăng, thêm 2 bài `get_or_create` theo tiêu đề, `seller` là một sinh viên có sẵn trong `users`, `status=Post.Status.PENDING`, có `category` từ `cat_map`, giá > 0:

```python
    for title, cat_name in (
        ('Giáo trình Xác suất thống kê (bản mới)', 'Giáo trình'),
        ('Bộ đề thi TOEIC có đáp án', 'Giáo trình'),
    ):
        Post.objects.get_or_create(
            title=title,
            defaults={
                'seller': users[0],
                'category': cat_map.get(cat_name),
                'description': 'Bài mẫu đang chờ kiểm duyệt viên xử lý.',
                'price': 45000,
                'condition': 'GOOD',
                'status': Post.Status.PENDING,
                'location': 'KTX A',
            },
        )
```

- [ ] **Step 3: Thêm phiên tranh chấp mẫu**

Cuối script, trước khi in bảng tóm tắt:

```python
    # --- Phiên tranh chấp mẫu trên một đơn đã xác nhận ---
    sample_order = Order.objects.filter(status=Order.Status.CONFIRMED).first()
    if sample_order and not SupportTicket.objects.filter(order=sample_order).exists():
        ticket = SupportTicket.objects.create(
            order=sample_order,
            opened_by=sample_order.buyer,
            category=SupportTicket.Category.DISPUTE,
            subject='Sản phẩm không đúng mô tả',
        )
        SupportMessage.objects.create(
            ticket=ticket, author=sample_order.buyer,
            body='Sách nhận được bị rách bìa và thiếu phụ lục.',
        )
        SupportMessage.objects.create(
            ticket=ticket, author=sample_order.seller,
            body='Mình đã gửi ảnh trước khi giao, nhờ kiểm duyệt viên xem giúp.',
        )
        sample_order.status = Order.Status.DISPUTED
        sample_order.save(update_fields=['status', 'updated_at'])
        print(f"   ✅ Phiên tranh chấp mẫu cho đơn #{sample_order.pk}.")
```

- [ ] **Step 4: Cập nhật bảng tóm tắt tài khoản**

Thêm dòng in tài khoản moderator và ghi chú "Duyệt bài / xử lý báo cáo / tranh chấp" vào bảng cuối script.

- [ ] **Step 5: Chạy seed hai lần và kiểm tra**

Run: `python seed_data.py`
Expected: không lỗi; in tài khoản moderator; tạo 2 bài chờ duyệt + 1 phiên tranh chấp (nếu có đơn `CONFIRMED`).

Run lại: `python seed_data.py`
Expected: không nhân đôi dữ liệu (số bài `PENDING` mẫu vẫn 2; phiên vẫn 1).

Run kiểm tra:

```bash
PYTHONIOENCODING=utf-8 python manage.py shell -c "from app_main.models import Post,SupportTicket; from django.contrib.auth.models import User; print(User.objects.get(username='moderator').profile.role, Post.objects.filter(status='PENDING').count(), SupportTicket.objects.count())"
```

Expected: `MODERATOR 2 1` (hoặc số phiên hiện có, không tăng sau lần chạy thứ hai).

- [ ] **Step 6: Commit**

```bash
git add seed_data.py
git commit -m "chore: seed tai khoan moderator va tranh chap mau"
```

---

### Task 8: Chạy toàn bộ test, sửa sót và cập nhật README

**Files:**
- Modify: `app_main/tests.py` (chỉ khi còn test cũ đỏ)
- Modify: `README.md` (mô tả vai trò, luồng duyệt bài, số test)
- Test: toàn bộ

**Interfaces:**
- Consumes: mọi thay đổi Task 1–7.
- Produces: bộ test xanh, README khớp code.

- [ ] **Step 1: Chạy toàn bộ test**

Run: `python manage.py test -v 2`
Expected: `Ran <N> tests ... OK`, với N khoảng 182 (142 cũ + 40 mới). Ghi lại N thực tế.

- [ ] **Step 2: Sửa các test cũ còn đỏ**

Chỉ sửa nguyên nhân do thay đổi có chủ đích (bài mới `PENDING`, chặn xem bài ẩn, moderator bị chặn). Không nới lỏng assertion của test mới. Với test cũ tạo bài qua `create_post` view rồi mong bài lên trang chủ: thêm bước duyệt ORM như `test_full_journey`.

- [ ] **Step 3: Chạy lại đến khi xanh**

Run: `python manage.py test`
Expected: `OK`.

- [ ] **Step 4: Cập nhật README**

- Thêm mục "Vai trò & phân quyền": Sinh viên / Kiểm duyệt viên / Quản trị viên, quy ước `is_staff` thắng.
- Thêm mục "Luồng kiểm duyệt": đăng bài → `PENDING` → duyệt/từ chối; sửa bài → duyệt lại (trừ `SOLD`); báo cáo vi phạm gồm "hàng cấm"; phiên hỗ trợ & tranh chấp.
- Thêm tài khoản demo `moderator / 123456`.
- Đổi số test "142" thành N thực tế (chỉ sửa đúng con số, không đổi cấu trúc mục).

- [ ] **Step 5: Kiểm tra không còn tham chiếu cũ**

Run: `grep -rn "142 test\|142/142\|USE_SQLITE\|db.sqlite3" README.md app_main core`
Expected: không còn kết quả (trừ lịch sử trong `docs/superpowers/plans/`).

- [ ] **Step 6: Commit**

```bash
git add README.md app_main/tests.py
git commit -m "docs: cap nhat README cho vai tro moderator va so test moi"
```

---

### Task 9: Báo cáo Word (xin duyệt trước khi sửa)

**Files:**
- `C:\Users\ACER\OneDrive\Desktop\BaoCao_GiuaKy_CNPM_SachGocUni.docx`

- [ ] **Step 0: Xin phép người dùng** trước khi mở/sửa báo cáo; xác nhận báo cáo không đang mở trong Word.
- [ ] Backup báo cáo vào `C:\Users\ACER\AppData\Local\Temp\opencode\docx-backup\` với tên `BaoCao_truoc_Moderator.docx`.
- [ ] Bổ sung mục mô tả 3 vai trò + bảng phân quyền (theo spec §4), luồng duyệt bài (spec §5.1–5.3), báo cáo vi phạm có "hàng cấm" (spec §5.4), phiên hỗ trợ & tranh chấp (spec §5.5).
- [ ] Chụp ảnh: dashboard Moderator, trang `/quan-tri/ho-tro/<pk>/` đang xử lý tranh chấp, màn hình "Tin của tôi" có chip "Chờ duyệt"; chèn đúng vị trí, giữ khổ ảnh như các hình hiện có.
- [ ] Cập nhật số test và bảng chức năng/demo account.
- [ ] Xuất PDF, kiểm tra phân trang và xem bằng mắt các trang đã sửa; báo lại số trang.
- [ ] Không commit gì vào repo cho task này (báo cáo nằm ngoài repo).

---

## Ghi chú thực thi

- Thứ tự bắt buộc: Task 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8; Task 9 chỉ sau khi Task 8 xanh và có xác nhận của người dùng.
- Sau mỗi task, chạy đúng lệnh test ghi trong task; không chạy cả bộ mỗi bước để tránh chậm (~50 s/lần).
- Khi gặp test cũ đỏ ngoài dự kiến, dừng và báo người dùng thay vì nới assertion.
- Không tự ý thêm tính năng ngoài spec (email, realtime, audit log, ghi chú nội bộ).
