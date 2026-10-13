"""
Sinh file docs/sequence-diagrams.md chứa 4 biểu đồ tuần tự Mermaid.

Cách dùng:
    python make_sequence_diagrams.py

Sau đó mở file docs/sequence-diagrams.md, chép từng khối ```mermaid
dán vào app.diagrams.net (Insert > Advanced > Mermaid) để xuất ảnh PNG.

Nội dung sơ đồ được viết theo đúng code nguồn hiện có:
  app_main/views.py    : user_login, register, create_post, buy_post
  app_main/forms.py    : RegisterForm, PostForm, OrderForm
  app_main/models.py   : Post.save() sinh slug, Order
  app_main/signals.py  : post_save tự tạo Profile
  app_main/urls.py     : các route tương ứng
"""

import io
import os

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUTPUT_FILE = os.path.join(DOCS_DIR, "sequence-diagrams.md")


HEADER = """# Biểu đồ tuần tự (Sequence Diagram) — SáchGóc Uni

Bốn chức năng chính của đề tài, vẽ theo **đúng mã nguồn đang chạy**:

| # | Chức năng | View xử lý | Route |
|---|---|---|---|
| 1 | Đăng nhập | `app_main.views.user_login` | `POST /dang-nhap/` |
| 2 | Đăng ký | `app_main.views.register` | `POST /dang-ky/` |
| 3 | Đăng tin sản phẩm | `app_main.views.create_post` | `POST /dang-tin/` |
| 4 | Đặt mua | `app_main.views.buy_post` | `POST /san-pham/<pk>/dat-mua/` |

## Cách tạo ảnh từ sơ đồ

1. Mở [app.diagrams.net](https://app.diagrams.net)
2. Chọn **Arrange > Insert > Advanced > Mermaid…**
3. Dán nội dung khối *mermaid* của sơ đồ cần vẽ
4. Nhấn **OK**, sau đó **File > Export as > PNG** để tải ảnh về

> Hoặc dùng <https://mermaid.live> — dán code, chọn Actions > PNG.

---

## 1. Đăng nhập

*Cho phép đăng nhập bằng **tên đăng nhập** hoặc **email**.*

```mermaid
sequenceDiagram
    autonumber
    actor SV as 👤 Sinh viên
    participant TB as 🌐 Trình duyệt
    participant MW as 🛡️ Middleware
    participant VW as 🎯 user_login
    participant FM as 📝 AuthenticationForm
    participant ORM as 🗃️ ORM
    participant DB as 🄽 MySQL

    SV->>TB: Nhập tên đăng nhập / email + mật khẩu
    TB->>TB: Gắn CSRF token vào form
    SV->>TB: Bấm "Đăng nhập" (POST /dang-nhap/)
    TB->>MW: Gửi request kèm cookie + CSRF token

    MW->>MW: Kiểm tra CSRF token
    alt CSRF token sai
        MW-->>TB: 403 Forbidden
        TB-->>SV: Báo lỗi "CSRF token không hợp lệ"
    end

    MW->>VW: Chuyển vào user_login(request)

    alt Đã đăng nhập rồi
        VW-->>TB: 302 → trang chủ
        TB-->>SV: Redirect /
    else Chưa đăng nhập
        VW->>FM: Khởi tạo form với dữ liệu POST
        FM->>VW: form

        VW->>VW: Đọc trường "username" từ POST

        alt Chuỗi nhập chứa "@" (đăng nhập bằng email)
            VW->>ORM: User.objects.filter(email__iexact=username)
            ORM->>DB: SELECT ... WHERE email = ?
            DB-->>ORM: Kết quả (0 hoặc 1 dòng)
            ORM-->>VW: matched hoặc None

            alt Tìm thấy tài khoản
                VW->>FM: Dựng lại form với username thật + mật khẩu
            else Không tìm thấy
                VW->>FM: Giữ nguyên form, báo lỗi ở lượt validate
            end
        else Nhập tên đăng nhập
            VW->>FM: Dùng luôn username đã nhập
        end

        VW->>FM: form.is_valid()
        FM->>ORM: authenticate(username, password)
        ORM->>DB: SELECT bảng auth_user
        DB-->>ORM: Bản ghi người dùng
        ORM->>ORM: So sánh mật khẩu bằng hash
        ORM-->>FM: User hoặc None

        alt Sai tên đăng nhập / mật khẩu
            FM-->>VW: is_valid() = False
            VW-->>TB: Render lại form + thông báo lỗi
            TB-->>SV: "Tên đăng nhập hoặc mật khẩu không đúng."
        else Đúng thông tin
            FM-->>VW: is_valid() = True, form.get_user()
            VW->>VW: login(request, user)
            Note over VW: Django tạo Session,<br/>lưu user_id vào DB và<br/>ghi sessionid cookie vào trình duyệt
            VW->>VW: messages.success("Xin chào, {tên}!")
            VW-->>TB: 302 → next hoặc trang chủ
            TB-->>SV: Hiển thị trang chủ + thanh thông báo
        end
    end
```

**Điểm bảo mật trong luồng này**

- `@csrf_protect` mặc định của Django chặn giả mạo request từ site khác
- Mật khẩu lưu dạng hash (`PBKDF2`), không bao giờ lưu dạng thường
- Khi đăng nhập bằng email, hệ thống tra cứu `email__iexact` — không phân biệt hoa/thường

---

## 2. Đăng ký tài khoản

*Kiểm tra mật khẩu mạnh, email phải là Gmail, tên đăng nhập không trùng.*

```mermaid
sequenceDiagram
    autonumber
    actor SV as 👤 Sinh viên mới
    participant TB as 🌐 Trình duyệt
    participant MW as 🛡️ Middleware
    participant VW as 🎯 register
    participant FM as 📝 RegisterForm
    participant SG as ⚡ signals.post_save
    participant US as 🗃️ User (ORM)
    participant PF as 🗃️ Profile (ORM)
    participant DB as 🄽 MySQL

    SV->>TB: Điền họ tên, tên đăng nhập,<br/>Gmail, khoa, MSSV, mật khẩu ×2
    SV->>TB: Bấm "Đăng ký" (POST /dang-ky/)
    TB->>MW: Gửi request kèm CSRF token

    MW->>MW: Kiểm tra CSRF token
    MW->>VW: Chuyển vào register(request)

    alt Đã đăng nhập rồi
        VW-->>TB: 302 → trang chủ
    else Chưa đăng nhập
        VW->>FM: RegisterForm(dữ liệu POST)
        FM->>FM: Kiểm tra độ dài các trường

        FM->>US: username đã tồn tại?
        US->>DB: SELECT ... WHERE username LIKE ?
        DB-->>US: Có / Không

        FM->>US: email đã tồn tại?
        US->>DB: SELECT ... WHERE email LIKE ?
        DB-->>US: Có / Không

        FM->>FM: password1 có khớp password2?<br/>mật khẩu có chứa tên/email/họ tên?<br/>mật khẩu đủ mạnh?
        FM->>FM: email có đuôi @gmail.com?

        alt Có lỗi
            FM-->>VW: is_valid() = False + danh sách lỗi
            VW-->>TB: Render lại form, tô đỏ ô sai
            TB-->>SV: "Tên đăng nhập này đã tồn tại" /<br/>"Hai mật khẩu không khớp" …
        else Hợp lệ
            FM-->>VW: is_valid() = True

            VW->>FM: form.save()
            FM->>US: create_user(username, email, password1, first_name)
            US->>DB: INSERT INTO auth_user<br/>(mật khẩu đã hash)
            DB-->>US: user_id

            US-->>SG: post_save tín hiệu phát ra
            SG->>PF: Profile.objects.get_or_create(user=user)
            PF->>DB: INSERT INTO app_main_profile
            DB-->>PF: Tạo hồ sơ rỗng
            PF-->>SG: xong

            FM->>PF: Gán faculty + student_id vào hồ sơ
            PF->>DB: UPDATE app_main_profile

            FM-->>VW: Trả về đối tượng User
            VW->>VW: login(request, user) — đăng nhập luôn
            VW->>VW: messages.success("Chào mừng bạn!")
            VW-->>TB: 302 → trang chủ
            TB-->>SV: Vào thẳng hệ thống, không cần đăng nhập lại
        end
    end
```

**Điểm bảo mật trong luồng này**

- `user.profile` luôn tồn tại nhờ signal `post_save` → không bao giờ lỗi `AttributeError`
- Ràng buộc email `@gmail.com` chống đăng ký bằng email rác/thư rác
- Mật khẩu không chứa thông tin cá nhân của chính người dùng (chống đoán dễ)

---

## 3. Đăng tin sản phẩm

*Đăng bán hoặc tặng sản phẩm cũ.*

```mermaid
sequenceDiagram
    autonumber
    actor SV as 👤 Sinh viên
    participant TB as 🌐 Trình duyệt
    participant MW as 🛡️ Middleware
    participant VW as 🎯 create_post
    participant FM as 📝 PostForm
    participant MD as 🗃️ Post model
    participant FS as 📁 Media storage
    participant DB as 🄽 MySQL

    SV->>TB: Bấm "Đăng tin mới"
    TB->>MW: GET /dang-tin/
    MW->>MW: Kiểm tra @login_required

    alt Chưa đăng nhập
        MW-->>TB: 302 → /dang-nhap/
        TB-->>SV: Bảo đăng nhập trước
    else Đã đăng nhập
        MW->>VW: Chuyển vào create_post(request)
        VW->>FM: PostForm() rỗng
        VW-->>TB: Render form nhập liệu
        TB-->>SV: Hiển thị form + danh mục + điều kiện
    end

    SV->>TB: Chọn ảnh + điền tiêu đề, danh mục,<br/>mô tả, giá, tình trạng
    SV->>TB: Bấm "Đăng tin ngay" (POST /dang-tin/)

    TB->>MW: multipart/form-data + CSRF token
    MW->>MW: Kiểm tra CSRF token
    MW->>VW: create_post(request)

    VW->>FM: PostForm(request.POST, request.FILES)
    FM->>FM: Kiểm tra title ≥ 5 ký tự,<br/>description ≥ 20 ký tự, giá ≥ 0,<br/>danh mục hợp lệ

    FM->>FM: clean_image():<br/>dung lượng ≤ 5MB,<br/>đuôi jpg/png/webp/gif

    alt Ảnh sai định dạng / quá lớn
        FM-->>VW: Lỗi "Ảnh vượt quá 5MB"
        VW-->>TB: Render lại form kèm lỗi
        TB-->>SV: Tô đỏ ô ảnh
    else Dữ liệu hợp lệ
        FM-->>VW: is_valid() = True

        VW->>VW: form.save(commit=False)
        VW->>VW: post.seller = request.user
        VW->>VW: post.status = ACTIVE

        VW->>MD: post.save()
        Note over MD: Post.save() tự sinh slug từ tiêu đề,<br/>nếu trùng thì thêm -2, -3…<br/>và đồng bộ cờ is_sold
        MD->>FS: Lưu ảnh vào media/posts/<slug>/
        FS-->>MD: Đường dẫn ảnh
        MD->>DB: INSERT INTO app_main_post<br/>(title, price, seller_id, image, slug…)
        DB-->>MD: post_id

        MD-->>VW: Đối tượng Post đã lưu
        VW->>VW: messages.success("Đăng tin thành công!")
        VW-->>TB: 302 → /san-pham/<slug>/
        TB-->>SV: Xem trang chi tiết sản phẩm vừa đăng
    end
```

**Điểm bảo mật trong luồng này**

- `@login_required` chặn người chưa đăng nhập ngay từ đầu
- Ảnh kiểm tra cả dung lượng lẫn đuôi file → không tải được file thực thi
- `seller` lấy từ `request.user` (phiên đăng nhập), **không lấy từ POST** → không thể giả mạo người bán

---

## 4. Đặt mua sản phẩm

*Tạo đơn hàng, người bán xác nhận, hoàn tất thì sản phẩm chuyển sang "Đã bán".*

### 4a. Người mua gửi yêu cầu

```mermaid
sequenceDiagram
    autonumber
    actor NM as 👤 Người mua
    participant TB as 🌐 Trình duyệt
    participant MW as 🛡️ Middleware
    participant VW as 🎯 buy_post
    participant FM as 📝 OrderForm
    participant OD as 🗃️ Order model
    participant PS as 🗃️ Post model
    participant DB as 🄽 MySQL

    NM->>TB: Mở trang sản phẩm
    TB->>MW: GET /san-pham/<pk>/
    MW->>VW: post_detail(request, pk)
    VW->>PS: Lấy Post + my_order (đơn đang mở của tôi)
    PS->>DB: SELECT post, order
    DB-->>VW: Dữ liệu
    VW-->>TB: Render trang chi tiết
    Note over TB: Nếu chưa có đơn → hiện nút<br/>🛒 "Đặt mua ngay";<br/>nếu đã có đơn → hiện nút "Đơn #…"

    NM->>TB: Bấm "Đặt mua ngay"
    TB->>MW: GET /san-pham/<pk>/dat-mua/
    MW->>MW: Kiểm tra @login_required

    alt Chưa đăng nhập
        MW-->>TB: 302 → /dang-nhap/?next=…
    else Đã đăng nhập
        MW->>VW: buy_post(request, pk)

        VW->>PS: post = get_object_or_404(Post, pk)
        PS->>DB: SELECT * FROM app_main_post WHERE id = ?
        DB-->>VW: post

        alt post.seller == request.user
            VW->>VW: messages.error("Không thể mua sản phẩm của chính mình")
            VW-->>TB: 302 → trang sản phẩm
        else post.is_available == False
            VW->>VW: messages.error("Sản phẩm này đã bán")
            VW-->>TB: 302 → trang sản phẩm
        else Hợp lệ
            VW->>OD: Tìm đơn đang mở của người mua cho post này
            OD->>DB: SELECT * FROM app_main_order<br/>WHERE post_id=? AND buyer_id=?<br/>AND status IN (PENDING, CONFIRMED)
            DB-->>OD: existing hoặc None

            alt Đã có đơn đang mở
                VW->>VW: messages.warning("Bạn đã gửi yêu cầu mua (đơn #…)")
                VW-->>TB: 302 → /don-hang/
            else Chưa có đơn
                VW->>FM: OrderForm() rỗng
                VW-->>TB: Render form đặt mua
                TB-->>NM: Ô "Lời nhắn" + "Thông tin liên hệ"
            end
        end
    end

    NM->>TB: Điền lời nhắn + SĐT/email rồi gửi
    TB->>MW: POST /san-pham/<pk>/dat-mua/
    MW->>MW: Kiểm tra CSRF token
    MW->>VW: buy_post(request, pk)

    VW->>VW: Kiểm tra lại 3 điều kiện<br/>(không phải chủ, còn hàng, chưa có đơn)
    VW->>FM: OrderForm(request.POST)
    FM->>FM: clean_contact():<br/>phải chứa email hoặc số điện thoại

    alt Thông tin liên hệ không hợp lệ
        FM-->>VW: Lỗi "Phải chứa email hoặc số điện thoại"
        VW-->>TB: Render lại form kèm lỗi
    else Hợp lệ
        FM-->>VW: is_valid() = True
        VW->>VW: form.save(commit=False)
        VW->>VW: order.post / buyer / seller gán từ server
        VW->>VW: order.price_snapshot = post.price<br/>(chốt giá tại thời điểm đặt mua)
        VW->>VW: order.status = PENDING
        VW->>OD: order.save()
        OD->>DB: INSERT INTO app_main_order<br/>(post_id, buyer_id, seller_id,<br/>price_snapshot, contact, message, status)
        DB-->>OD: order_id
        OD-->>VW: Đơn hàng
        VW->>VW: messages.success("Đã gửi yêu cầu mua! Đơn #…")
        VW-->>TB: 302 → /don-hang/
        TB-->>NM: Danh sách đơn hàng, đơn mới ở trạng thái "Chờ xác nhận"
    end
```

### 4b. Người bán xác nhận và hoàn tất

```mermaid
sequenceDiagram
    autonumber
    actor NB as 👤 Người bán
    participant TB as 🌐 Trình duyệt
    participant MW as 🛡️ Middleware
    participant VW as 🎯 accept / reject / complete
    participant OD as 🗃️ Order model
    participant PS as 🗃️ Post model
    participant DB as 🄽 MySQL

    NB->>TB: Vào /don-hang/ — thấy mục<br/>"Đơn người khác mua sản phẩm của tôi"
    TB->>MW: GET /don-hang/
    MW->>VW: my_orders(request)
    VW->>OD: SELECT đơn tôi mua + đơn tôi bán
    OD->>DB: SELECT ... WHERE buyer_id=? / seller_id=?
    DB-->>VW: Danh sách đơn
    VW-->>TB: Render + cảnh báo "Bạn có N yêu cầu chờ xác nhận"

    NB->>TB: Bấm "Xử lý" một đơn
    TB->>MW: GET /don-hang/<pk>/
    MW->>VW: order_detail(request, pk)
    VW->>OD: Lấy đơn + post + buyer + seller
    OD->>DB: SELECT ...
    DB-->>VW: order
    VW->>VW: Kiểm tra request.user ∈ {buyer, seller}
    alt Không phải hai bên
        VW-->>TB: 302 → /don-hang/
    else Hợp lệ
        VW-->>TB: Render chi tiết đơn + nút hành động
    end

    alt Người bán bấm "✅ Xác nhận đơn hàng"
        NB->>TB: POST /don-hang/<pk>/xac-nhan/
        TB->>MW: request + CSRF token
        MW->>MW: @require_POST + @login_required
        MW->>VW: accept_order(request, pk)
        VW->>OD: Kiểm tra order.seller == request.user<br/>và status == PENDING
        alt Sai người hoặc sai trạng thái
            VW->>VW: messages.error(...)
            VW-->>TB: 302 → /don-hang/
        else Hợp lệ
            VW->>OD: status = CONFIRMED; save()
            OD->>DB: UPDATE app_main_order SET status='CONFIRMED'
            VW-->>TB: 302 → chi tiết đơn
            TB-->>NB: "Đã xác nhận đơn #…"
        end
    else Người bán bấm "🚫 Từ chối"
        NB->>TB: POST /don-hang/<pk>/tu-choi/ + ghi chú
        TB->>MW: request + CSRF token
        MW->>VW: reject_order(request, pk)
        VW->>VW: Kiểm tra seller + status PENDING
        VW->>OD: status = REJECTED, seller_note = ghi chú
        OD->>DB: UPDATE app_main_order
        Note over PS: Sản phẩm vẫn ACTIVE,<br/>người mua được gửi yêu cầu lại
        VW-->>TB: 302 → chi tiết đơn
        TB-->>NB: "Đã từ chối đơn #…"
    else Hai bên bấm "🎊 Giao dịch đã hoàn tất"
        NB->>TB: POST /don-hang/<pk>/hoan-tat/
        TB->>MW: request + CSRF token
        MW->>VW: complete_order(request, pk)
        VW->>VW: Kiểm tra user ∈ {buyer, seller}<br/>và status ∈ {PENDING, CONFIRMED}

        VW->>OD: order.status = COMPLETED; save()
        OD->>DB: UPDATE app_main_order SET status='COMPLETED'

        VW->>PS: post.status = SOLD; post.is_sold = True; save()
        PS->>PS: save() đồng bộ lại is_sold
        PS->>DB: UPDATE app_main_post SET status='SOLD', is_sold=1

        VW-->>TB: 302 → chi tiết đơn
        TB-->>NB: "Giao dịch hoàn tất! Sản phẩm đã chuyển sang Đã bán"
        Note over TB: Trang chủ không còn hiển thị sản phẩm này,<br/>người mua được mời đánh giá người bán
    end

    opt Người mua đổi ý
        NM->>TB: POST /don-hang/<pk>/huy/
        TB->>MW: request + CSRF token
        MW->>VW: cancel_order(request, pk)
        VW->>VW: Kiểm tra order.buyer == request.user
        VW->>OD: status = CANCELLED
        OD->>DB: UPDATE app_main_order SET status='CANCELLED'
        VW-->>TB: 302 → /don-hang/
    end
```

**Điểm bảo mật trong luồng này**

| Rủi ro | Cách chặn trong code |
|---|---|
| Mua nhầm sản phẩm của chính mình | `if post.seller == request.user` → từ chối |
| Mua sản phẩm đã bán | `if not post.is_available` → từ chối |
| Tạo 100 đơn cho 1 sản phẩm | Kiểm tra đơn đang mở trước khi tạo |
| Người lạ xem đơn của người khác | `request.user not in (buyer, seller)` → 302 |
| Người mua tự xác nhận đơn | `order.seller != request.user` → từ chối |
| Giả mạo thao tác bằng link (GET) | `@require_POST` → GET trả về 405 |
| Giả mạo request từ site khác | CSRF token bắt buộc mọi POST |
| Đổi giá sau khi đặt mua | `price_snapshot` chốt giá lúc đặt |

---

## Sơ đồ trạng thái đơn hàng

```mermaid
stateDiagram-v2
    [*] --> PENDING: Người mua gửi yêu cầu

    PENDING --> CONFIRMED: Người bán xác nhận
    PENDING --> REJECTED: Người bán từ chối
    PENDING --> CANCELLED: Người mua huỷ

    CONFIRMED --> COMPLETED: Hai bên xác nhận xong
    CONFIRMED --> CANCELLED: Người mua huỷ

    COMPLETED --> [*]: Sản phẩm chuyển sang "Đã bán"
    REJECTED --> [*]
    CANCELLED --> [*]
```

> Sau khi đơn ở trạng thái `REJECTED` hoặc `CANCELLED`, người mua có thể gửi yêu cầu mới cho cùng sản phẩm đó.

---

## Biểu đồ phân lớp (Class Diagram) rút gọn cho phần đặt mua

```mermaid
classDiagram
    class User {
        +int id
        +str username
        +str email
        +create_user()
    }

    class Profile {
        +str display_name
        +str faculty
        +str student_id
    }

    class Post {
        +str title
        +int price
        +bool is_free
        +str slug
        +Status status
        +save()
        +is_available
    }

    class Order {
        +int id
        +Decimal price_snapshot
        +str message
        +str contact
        +Status status
        +is_open
        +price_display
    }

    User "1" --> "1" Profile : có
    User "1" --> "n" Post : đăng tin
    User "1" --> "n" Order : đặt mua (buyer)
    User "1" --> "n" Order : nhận đơn (seller)
    Post "1" --> "n" Order : có đơn

    class Status {
        <<enumeration>>
        ACTIVE
        SOLD
        PENDING
        CONFIRMED
        COMPLETED
        REJECTED
        CANCELLED
    }
```
"""

FOOTER = """
---

## Tóm tắt luồng đặt mua

```
Người mua                    Hệ thống                     Người bán
    │                           │                            │
    │ ① Bấm "Đặt mua ngay"    │                            │
    ├──────────────────────────►│                            │
    │                           │ ② Kiểm tra: không phải chủ,│
    │                           │    còn hàng, chưa có đơn    │
    │                           │                            │
    │ ③ Điền form + gửi POST    │                            │
    ├──────────────────────────►│ ④ INSERT app_main_order   │
    │                           │    status = PENDING        │
    │ ⑤ "Đơn #12 chờ xác nhận"│                            │
    │◄──────────────────────────┤                            │
    │                           │ ⑥ Thấy yêu cầu mới        │
    │                           │◄───────────────────────────┤
    │                           │ ⑦ Bấm "Xác nhận"          │
    │                           │    status = CONFIRMED      │
    │                           │───────────────────────────►│
    │ ⑧ "Đã xác nhận, hẹn gặp"│                            │
    │◄──────────────────────────┤                            │
    │                           │                            │
    │ ⑨ Hai bên giao xong       │                            │
    ├──────────────────────────►│ ⑩ status = COMPLETED      │
    │                           │    post.status = SOLD      │
    │ ⑪ "Giao dịch hoàn tất!"  │                            │
    │◄──────────────────────────┤───────────────────────────►│
    │                           │ ⑫ Sản phẩm biến mất khỏi sàn
```

---

*Nội dung sơ đồ được sinh tự động bởi `make_sequence_diagrams.py`.*
*Sửa mã nguồn `make_sequence_diagrams.py` rồi chạy lại để cập nhật.*
"""


def build():
    """Ghép nội dung và ghi ra docs/sequence-diagrams.md."""
    os.makedirs(DOCS_DIR, exist_ok=True)
    content = HEADER + FOOTER

    # Kiểm tra sơ bộ: số hàng rào ``` phải chẵn và có ít nhất 1 sơ đồ
    total_fences = content.count('```')
    diagrams = content.count('```mermaid')
    assert diagrams > 0, "Không có khối mermaid nào"
    assert total_fences % 2 == 0, (
        f"Không cân bằng hàng rào ```: {total_fences} (phải là số chẵn)"
    )

    with io.open(OUTPUT_FILE, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)

    print(f"Đã tạo {OUTPUT_FILE}")
    print(f"  Số biểu đồ mermaid : {diagrams}")
    print(f"  Dung lượng         : {len(content):,} ký tự")
    print()
    print("Cách tạo ảnh:")
    print("  1. Mở https://app.diagrams.net")
    print("  2. Arrange > Insert > Advanced > Mermaid")
    print("  3. Dán code trong khối ```mermaid của file vừa sinh")
    print("  4. OK > File > Export as > PNG")


if __name__ == '__main__':
    build()