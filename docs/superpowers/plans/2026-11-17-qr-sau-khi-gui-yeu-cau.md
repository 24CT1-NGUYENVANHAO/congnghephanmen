# QR thanh toán chỉ hiện sau khi gửi yêu cầu — Kế hoạch thực thi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Chỉ hiển thị mã VietQR trên trang đặt mua khi người dùng đã gửi yêu cầu đặt mua cho sản phẩm đó.

**Architecture:** `views.buy_post` gom về một trạng thái "đã gửi" (`sent_order`): đơn vừa tạo khi POST thành công, hoặc đơn đang mở có sẵn khi GET. Template `buy_post.html` tách hai nhánh: chưa gửi (form, không QR) và đã gửi (xác nhận + QR nếu đơn có giá).

**Tech Stack:** Django 5, template engine Django, Tailwind (class có sẵn trong dự án), `manage.py test`.

**Spec:** Thiết kế đã được người dùng duyệt trong phiên làm việc ngày 2026-11-17 (mục "Thiết kế: QR chỉ hiện sau khi đã gửi yêu cầu").

## Global Constraints

- Chỉ MySQL (XAMPP cổng 3307), không SQLite.
- Giữ tổng số test = 142 (sửa test cũ, không thêm test mới).
- QR chỉ dành cho sản phẩm có giá: điều kiện `sent_order.price_snapshot > 0`.
- Không đổi tên URL nào; `don-hang/` và `don-hang/<pk>/` giữ nguyên.
- Văn phong tiếng Việt, comment code tiếng Việt như phần còn lại của repo.

## Review Focus

- Người dùng F5 ngay sau khi gửi: phải không tạo đơn trùng (nhánh `existing` chặn).
- Sản phẩm miễn phí sau khi gửi: không được lộ QR.
- Người bán mở trang đặt mua của chính mình: vẫn bị chặn như cũ.
- Sản phẩm đã bán: vẫn bị chặn như cũ.
- Đơn đã gửi trước đó (PENDING/CONFIRMED) rồi mở lại trang đặt mua: thấy trạng thái đã gửi + QR, không thấy form.

---

### Task 1: Trạng thái "đã gửi" trong `buy_post` + template

**Files:**
- Modify: `app_main/views.py` (`buy_post`)
- Modify: `templates/app_main/buy_post.html`
- Test: `app_main/tests.py` (`OrderFlowTests`)

**Interfaces:**
- Consumes: `Order.Status.PENDING`, `Order.price_snapshot`, `Order.price_display`, `order_detail` URL.
- Produces: context key `sent_order` (một `Order` hoặc `None`) cho `buy_post.html`.

- [x] **Step 1: Viết test thất bại**

Sửa trong `OrderFlowTests`:

```python
def test_buy_page_hides_qr_before_sending_request(self):
    response = self.client_buyer.get(reverse('buy_post', args=[self.post.pk]))
    self.assertNotContains(response, 'static/img/qr.jpg')

def test_buy_page_shows_qr_after_sending_request(self):
    response = self.client_buyer.post(reverse('buy_post', args=[self.post.pk]), {
        'contact': '0901234567',
    })
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, 'Đã gửi yêu cầu')
    self.assertContains(response, 'static/img/qr.jpg')
    self.assertContains(response, '8822172044')

def test_buy_page_hides_qr_for_free_post_after_sending(self):
    self.post.is_free = True
    self.post.price = 0
    self.post.save()
    response = self.client_buyer.post(reverse('buy_post', args=[self.post.pk]), {
        'contact': '0901234567',
    })
    self.assertEqual(response.status_code, 200)
    self.assertNotContains(response, 'static/img/qr.jpg')
```

Sửa `test_create_order_success` bỏ `assertRedirects(response, reverse('my_orders'))`, thay bằng `self.assertEqual(response.status_code, 200)`; sửa `test_duplicate_order_redirects_to_list` thành đơn vẫn 1 và trang trả 200.

- [x] **Step 2: Chạy test, xác nhận đỏ**

Run: `python manage.py test app_main.tests.OrderFlowTests -v 2`
Expected: FAIL ở các test QR/redirect vì trang đặt mua đang hiện QR ngay trên form và redirect `my_orders`.

- [x] **Step 3: Sửa `views.buy_post`**

Thay nhánh `existing` (bỏ `messages.warning` + redirect) và nhánh POST thành công (bỏ `messages.success` + redirect) bằng việc render cùng template với `sent_order`:

```python
    if existing:
        return render(request, 'app_main/buy_post.html', {
            'post': post,
            'form': OrderForm(),
            'sent_order': existing,
        })

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            ...
            order.save()
            return render(request, 'app_main/buy_post.html', {
                'post': post,
                'form': OrderForm(),
                'sent_order': order,
            })
```

- [x] **Step 4: Sửa `templates/app_main/buy_post.html`**

Bọc khối form trong `{% if not sent_order %}...{% else %}`; nhánh `else` hiện thẻ xác nhận (mã đơn, trạng thái, lời nhắn, liên hệ, nút "Xem chi tiết đơn" + "Về trang sản phẩm"); bên dưới chỉ render khối QR khi `sent_order.price_snapshot > 0`. Xoá khối QR cuối form cũ.

- [x] **Step 5: Chạy lại test**

Run: `python manage.py test`
Expected: `Ran 142 tests ... OK`.

- [x] **Step 6: Commit** (chờ người dùng xác nhận trước khi commit)

---

### Task 2: README

**Files:** Modify: `README.md:37`

- [x] Đổi mô tả: "Sau khi gửi yêu cầu, trang đặt mua hiển thị mã VietQR để chuyển khoản (chỉ với sản phẩm có giá)".

---

### Task 3: Báo cáo Word

**Files:** `C:\Users\ACER\OneDrive\Desktop\BaoCao_GiuaKy_CNPM_SachGocUni.docx`

- [x] Sửa đoạn mô tả thẻ VietQR (P370) theo luồng mới.
- [x] Chụp lại Hình 2.13 (trạng thái đã gửi + QR), thay `word/media/image16.png`, giữ `cx=5400000`, cập nhật `cy` theo tỉ lệ ảnh mới.
- [x] Xuất PDF kiểm tra phân trang không đổi.
