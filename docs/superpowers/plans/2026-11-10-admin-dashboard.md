# Dashboard quản trị trong app — Kế hoạch triển khai

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm trang `/quan-tri/` staff-only với 5 thẻ số liệu, bảng duyệt bài chờ, bảng xử lý báo cáo và lối tắt sang Django admin.

**Architecture:** 5 view hàm trong `app_main/views.py` (1 trang + 4 thao tác POST) dùng chung decorator `staff_required`; 1 template kế thừa `base.html`; URL đặt trong nhóm "Quản trị" của `app_main/urls.py`; không đụng `app_main/admin.py`.

**Tech Stack:** Django 5, Tailwind (CDN nội bộ + `static/css/main.css`), SQLite/MySQL, `django.contrib.humanize`.

**Spec:** `docs/superpowers/specs/2026-11-10-admin-dashboard-design.md`

## Global Constraints

- Chỉ `request.user.is_staff` được vào `/quan-tri/`; chưa đăng nhập → `reverse('login') + '?next=' + path`.
- Mọi thao tác thay đổi dữ liệu: `@require_POST` + `{% csrf_token %}`.
- Duyệt/từ chối chỉ áp dụng khi `Post.status == PENDING`; báo cáo chỉ khi `Report.status == PENDING`.
- "Xử lý báo cáo" = report → `RESOLVED` **và** post `PENDING/ACTIVE` → `HIDDEN`.
- Mỗi bảng tối đa 10 bản ghi mới nhất; không phân trang.
- Dùng lại class có sẵn: `.card`, `.btn`, `.btn-primary/.btn-outline/.btn-danger/.btn-sm`, `.badge-*`.
- Không sửa `app_main/admin.py`, không thêm dependency.

## Review Focus

- Hai admin bấm "Duyệt" cùng lúc trên một bài → lần thứ hai phải chỉ cảnh báo, không ghi đè trạng thái `SOLD`/`HIDDEN` (test ở Task 2).
- Report trỏ tới bài đã `SOLD` → xử lý báo cáo không được đổi bài sang `HIDDEN` (test ở Task 2).
- POST trực tiếp bằng GET (dán link) → phải 405, không đổi dữ liệu (test ở Task 2).
- `?next=` chứa query string (`/quan-tri/?x=1`) → vẫn quay lại đúng sau đăng nhập (test ở Task 1, dùng `request.get_full_path()`).
- Doanh thu khi chưa có đơn hoàn tất → hiển thị `0`, không lỗi `None` (test ở Task 1).

---

### Task 1: Decorator + trang dashboard (số liệu, khung rỗng)

**Files:**
- Modify: `app_main/views.py` (import `wraps`, `reverse`, `Sum`; thêm khối "QUẢN TRỊ" cuối file)
- Modify: `app_main/urls.py` (nhóm URL mới)
- Create: `templates/app_main/admin_dashboard.html` (tạm: tiêu đề + 5 con số thô)
- Test: `app_main/tests.py` (class `AdminDashboardTests`)

**Interfaces:**
- Produces: `staff_required(view)` decorator; `admin_dashboard(request)` render `app_main/admin_dashboard.html` với context `stats` (dict: `pending_posts`, `pending_reports`, `pending_orders`, `total_users`, `active_users`, `total_posts`, `completed_orders`, `revenue`), `pending_posts` (QuerySet ≤10), `pending_reports` (QuerySet ≤10).
- Produces: URL names `admin_dashboard`.

- [ ] **Step 1: Viết test cho quyền truy cập + số liệu**

```python
@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class AdminDashboardTests(TestCase):
    def setUp(self):
        self.staff = create_user('adminuser', is_staff=True)
        self.normal = create_user('sinhvien2')
        self.seller = create_user('nguoiban')
        create_post(self.seller, title='Bài chờ duyệt')
        self.post_active = create_post(
            self.seller, title='Bài đã duyệt', status=Post.Status.ACTIVE)
        self.report = Report.objects.create(
            post=self.post_active, reporter=self.normal,
            reason=Report.Reason.SPAM)

    def test_guest_redirected_to_login(self):
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('admin_dashboard')}",
            fetch_redirect_response=False)

    def test_non_staff_redirected_home(self):
        self.client.force_login(self.normal)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(response, reverse('home'))

    def test_staff_sees_stats(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['pending_posts'], 1)
        self.assertEqual(response.context['stats']['pending_reports'], 1)
        self.assertEqual(response.context['stats']['total_users'], 3)
        self.assertEqual(response.context['stats']['revenue'], 0)
        self.assertContains(response, 'Bài chờ duyệt')
```

- [ ] **Step 2: Chạy test để thấy fail**

Run: `python manage.py test app_main.tests.AdminDashboardTests -v 2`
Expected: FAIL — `NoReverseMatch: 'admin_dashboard'`

- [ ] **Step 3: Thêm decorator + view + URL + template tối thiểu**

`app_main/views.py`: thêm `from functools import wraps`, `from django.db.models import ..., Sum`, `from django.urls import reverse`; decorator `staff_required` theo spec mục 5, dùng `request.get_full_path()` cho `?next=`; `admin_dashboard` theo spec mục 3–5.

`app_main/urls.py`: `path('quan-tri/', views.admin_dashboard, name='admin_dashboard')`.

Template tối thiểu: `{% extends 'base.html' %}{% block content %}` in 5 con số + tiêu đề bài chờ.

- [ ] **Step 4: Chạy lại test**

Run: `python manage.py test app_main.tests.AdminDashboardTests -v 2`
Expected: 3 test OK

- [ ] **Step 5: Commit**

```bash
git add app_main/views.py app_main/urls.py templates/app_main/admin_dashboard.html app_main/tests.py
git commit -m "feat: them khung dashboard quan tri /quan-tri/"
```

---

### Task 2: 4 thao tác kiểm duyệt

**Files:**
- Modify: `app_main/views.py`
- Modify: `app_main/urls.py`
- Test: `app_main/tests.py` (thêm method vào `AdminDashboardTests`)

**Interfaces:**
- Consumes: `staff_required`, URL `admin_dashboard`.
- Produces: views `admin_approve_post(request, pk)`, `admin_reject_post(request, pk)`, `admin_resolve_report(request, pk)`, `admin_dismiss_report(request, pk)`; URL names `admin_approve_post`, `admin_reject_post`, `admin_resolve_report`, `admin_dismiss_report`.

- [ ] **Step 1: Viết test cho 4 thao tác + các case biên**

```python
    def test_approve_pending_post(self):
        self.client.force_login(self.staff)
        post = Post.objects.get(title='Bài chờ duyệt')
        self.client.post(reverse('admin_approve_post', args=[post.pk]))
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.ACTIVE)

    def test_reject_pending_post(self):
        self.client.force_login(self.staff)
        post = Post.objects.get(title='Bài chờ duyệt')
        self.client.post(reverse('admin_reject_post', args=[post.pk]))
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.REJECTED)
        self.assertTrue(post.rejection_reason)

    def test_approve_non_pending_post_is_noop(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('admin_approve_post', args=[self.post_active.pk]))
        self.post_active.refresh_from_db()
        self.assertEqual(self.post_active.status, Post.Status.ACTIVE)

    def test_resolve_report_hides_post(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('admin_resolve_report', args=[self.report.pk]))
        self.report.refresh_from_db()
        self.post_active.refresh_from_db()
        self.assertEqual(self.report.status, Report.Status.RESOLVED)
        self.assertEqual(self.post_active.status, Post.Status.HIDDEN)

    def test_resolve_report_keeps_sold_post(self):
        self.post_active.status = Post.Status.SOLD
        self.post_active.save(update_fields=['status'])
        self.client.force_login(self.staff)
        self.client.post(reverse('admin_resolve_report', args=[self.report.pk]))
        self.post_active.refresh_from_db()
        self.assertEqual(self.post_active.status, Post.Status.SOLD)

    def test_dismiss_report_keeps_post(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('admin_dismiss_report', args=[self.report.pk]))
        self.report.refresh_from_db()
        self.post_active.refresh_from_db()
        self.assertEqual(self.report.status, Report.Status.DISMISSED)
        self.assertEqual(self.post_active.status, Post.Status.ACTIVE)

    def test_action_rejects_get(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse('admin_approve_post', args=[self.report.post_id]))
        self.assertEqual(response.status_code, 405)

    def test_non_staff_cannot_act(self):
        self.client.force_login(self.normal)
        post = Post.objects.get(title='Bài chờ duyệt')
        response = self.client.post(reverse('admin_approve_post', args=[post.pk]))
        self.assertRedirects(response, reverse('home'))
        post.refresh_from_db()
        self.assertEqual(post.status, Post.Status.PENDING)
```

- [ ] **Step 2: Chạy test để thấy fail**

Run: `python manage.py test app_main.tests.AdminDashboardTests -v 2`
Expected: FAIL — `NoReverseMatch: 'admin_approve_post'`

- [ ] **Step 3: Cài 4 view + 4 URL**

Mỗi view: `@staff_required` + `@require_POST` + `get_object_or_404`, so sánh trạng thái trước khi ghi, `messages.success/warning`, `redirect('admin_dashboard')`. Lý do từ chối mặc định: `"Không phù hợp với quy định đăng tin."` (nếu `request.POST['reason']` rỗng).

- [ ] **Step 4: Chạy lại test**

Run: `python manage.py test app_main.tests.AdminDashboardTests -v 2`
Expected: 11 test OK

- [ ] **Step 5: Commit**

```bash
git add app_main/views.py app_main/urls.py app_main/tests.py
git commit -m "feat: them thao tac duyet bai va xu ly bao cao cho admin"
```

---

### Task 3: Giao diện dashboard + navbar

**Files:**
- Modify: `templates/app_main/admin_dashboard.html` (thay bản tối thiểu bằng bố cục spec mục 4)
- Modify: `templates/partials/navbar.html:85-91`
- Test: `app_main/tests.py` (1 test giao diện)

**Interfaces:**
- Consumes: context của `admin_dashboard`, URL names ở Task 2.

- [ ] **Step 1: Viết test giao diện**

```python
    def test_dashboard_shows_action_buttons(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertContains(response, reverse('admin_approve_post', args=[1]))
        self.assertContains(response, 'Duyệt')
        self.assertContains(response, 'Xử lý')
        self.assertContains(response, 'Không có gì cần xử lý')
```

(Ghi chú: `args=[1]` chỉ đúng khi bài chờ duyệt đầu tiên có pk=1 — dùng `Post.objects.get(title='Bài chờ duyệt').pk` thay vì số cứng.)

- [ ] **Step 2: Chạy test để thấy fail**

Expected: FAIL — thiếu chuỗi/nút

- [ ] **Step 3: Dựng template theo bố cục spec mục 4**

5 thẻ (lưới `sm:grid-cols-2 lg:grid-cols-5`), 2 bảng, khối rỗng "Không có gì cần xử lý 🎉", dải lối tắt 4 nút sang `/django-admin/` (`app_main_post_changelist`, `app_main_report_changelist`, `app_main_order_changelist`, `auth_user_changelist`). `{% load humanize %}`, `{{ stats.revenue|intcomma }}đ`, `{{ post.price_display }}`.

Navbar: link "🛡️ Trang quản trị" → `{% url 'admin_dashboard' %}`, thêm mục "⚙️ Django admin" → `/django-admin/`.

- [ ] **Step 4: Chạy test**

Run: `python manage.py test app_main.tests.AdminDashboardTests -v 2`
Expected: 12 test OK

- [ ] **Step 5: Kiểm tra tổng thể**

Run: `python manage.py check && python manage.py test -v 1`
Expected: `System check identified no issues`; toàn bộ test OK

- [ ] **Step 6: Commit**

```bash
git add templates/app_main/admin_dashboard.html templates/partials/navbar.html app_main/tests.py
git commit -m "feat: giao dien dashboard quan tri va loi tat tren navbar"
```
