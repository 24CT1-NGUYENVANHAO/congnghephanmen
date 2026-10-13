"""
Form xử lý dữ liệu đầu vào.

Mọi validation tập trung ở đây (thay vì trong view) để:
  - Tự sinh lỗi hiển thị đẹp trên template
  - Không bao giờ xảy ra lỗi IndexError như bản cũ
"""

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Category, Comment, Order, Post, PostImage, Report, Review


# Class CSS dùng chung cho ô nhập — giúp giao diện đồng nhất
INPUT_CLASS = (
    'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 '
    'text-sm shadow-sm transition placeholder:text-slate-400 '
    'focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 focus:outline-none'
)
SELECT_CLASS = f"{INPUT_CLASS} bg-white"
TEXTAREA_CLASS = f"{INPUT_CLASS} min-h-28 resize-y"
CHECKBOX_CLASS = (
    'w-5 h-5 rounded-md border-slate-300 text-indigo-600 '
    'focus:ring-indigo-500 cursor-pointer'
)


# ---------------------------------------------------------------------------
#  ĐĂNG KÝ / ĐĂNG NHẬP
# ---------------------------------------------------------------------------

class RegisterForm(forms.Form):
    """Đăng ký tài khoản sinh viên với kiểm tra mật khẩu mạnh và Gmail."""

    first_name = forms.CharField(
        label="Họ và tên", max_length=150,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS, 'placeholder': 'Nguyễn Văn Hào',
            'autocomplete': 'name',
        })
    )
    username = forms.CharField(
        label="Tên đăng nhập", max_length=150,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS, 'placeholder': 'hao.nguyen24',
            'autocomplete': 'username',
        })
    )
    email = forms.EmailField(
        label="Email sinh viên", max_length=254,
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASS, 'placeholder': 'hao123@gmail.com',
            'autocomplete': 'email',
        }),
        help_text="Bắt buộc dùng email @gmail.com để xác minh sinh viên.",
    )
    faculty = forms.CharField(
        label="Khoa / Ngành", max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS, 'placeholder': 'Khoa Kiến trúc',
        })
    )
    student_id = forms.CharField(
        label="Mã sinh viên", max_length=20, required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS, 'placeholder': '24CT100001',
        })
    )
    password1 = forms.CharField(
        label="Mật khẩu", min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS, 'placeholder': 'Tối thiểu 8 ký tự',
            'autocomplete': 'new-password', 'id': 'id_password1',
        })
    )
    password2 = forms.CharField(
        label="Xác nhận mật khẩu",
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CLASS, 'placeholder': "Nhập lại mật khẩu",
            'autocomplete': 'new-password', 'id': 'id_password2',
        })
    )
    agree = forms.BooleanField(
        label="Tôi đồng ý với điều khoản sử dụng",
        widget=forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS})
    )

    def clean_username(self):
        """Chuẩn hoá và kiểm tra trùng tên đăng nhập."""
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Tên đăng nhập này đã tồn tại. Vui lòng chọn tên khác.")
        return username

    def clean_email(self):
        """Chỉ chấp nhận Gmail và không trùng lặp."""
        email = self.cleaned_data['email'].strip().lower()
        if not email.endswith('@gmail.com'):
            raise ValidationError("Chỉ chấp nhận địa chỉ email @gmail.com.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email này đã được đăng ký. Hãy đăng nhập hoặc dùng email khác.")
        return email

    def clean_password2(self):
        """Đối chiếu hai ô mật khẩu có khớp không."""
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError("Hai mật khẩu không khớp. Vui lòng nhập lại.")
        return p2

    def clean(self):
        """Kiểm tra tổng hợp: mật khẩu mạnh + không trùng với tên/email."""
        cleaned = super().clean()
        p1 = cleaned.get('password1')

        if p1:
            username = cleaned.get('username', '')
            email = cleaned.get('email', '')
            full_name = cleaned.get('first_name', '')

            # Mật khẩu không được chứa thông tin cá nhân
            for value, label in ((username, 'tên đăng nhập'),
                                 (email.split('@')[0], 'email'),
                                 (full_name, 'họ tên')):
                if value and value.lower() in p1.lower():
                    self.add_error(
                        'password1',
                        f"Mật khẩu không được chứa {label} của bạn."
                    )
                    break

            if not any(c.isupper() for c in p1):
                self.add_error('password1', "Mật khẩu phải có ít nhất 1 chữ hoa (A-Z).")
            if not any(c.isdigit() for c in p1):
                self.add_error('password1', "Mật khẩu phải có ít nhất 1 chữ số (0-9).")

        return cleaned

    def save(self):
        """Tạo tài khoản mới và trả về User."""
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password1'],
            first_name=data['first_name'],
        )
        # Lưu thông tin sinh viên vào hồ sơ mở rộng
        user.profile.faculty = data.get('faculty', '')
        user.profile.student_id = data.get('student_id', '')
        user.profile.save()
        return user


# ---------------------------------------------------------------------------
#  HỒ SƠ
# ---------------------------------------------------------------------------

class ProfileForm(forms.ModelForm):
    """Chỉnh sửa hồ sơ cá nhân."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Văn Hào'}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nguyễn'}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS, 'placeholder': 'email@gmail.com'}),
        }
        labels = {'first_name': "Tên", 'last_name': "Họ", 'email': "Email"}

    def clean_email(self):
        """Email phải là Gmail và không trùng với tài khoản khác."""
        email = self.cleaned_data['email'].strip().lower()
        if not email.endswith('@gmail.com'):
            raise ValidationError("Chỉ chấp nhận địa chỉ email @gmail.com.")
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Email này đã được tài khoản khác sử dụng.")
        return email


# ---------------------------------------------------------------------------
#  BÀI ĐĂNG
# ---------------------------------------------------------------------------

class PostForm(forms.ModelForm):
    """Tạo và cập nhật bài đăng bán / tặng."""

    class Meta:
        model = Post
        fields = [
            'title', 'category', 'description',
            'price', 'is_free', 'condition', 'image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'VD: Giáo trình Lập trình Python cơ bản',
            }),
            'category': forms.Select(attrs={'class': SELECT_CLASS}),
            'description': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'placeholder': 'Mô tả chi tiết: tình trạng sách, có ghi chú/bài tập không, '
                               'lý do bán, cách giao dịch...',
                'rows': 6,
            }),
            'price': forms.NumberInput(attrs={
                'class': INPUT_CLASS, 'placeholder': '45000', 'min': 0, 'step': 1000,
            }),
            'is_free': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASS}),
            'condition': forms.Select(attrs={'class': SELECT_CLASS}),
            'image': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-slate-600 file:mr-4 file:rounded-xl '
                         'file:border-0 file:bg-indigo-50 file:px-5 file:py-3 '
                         'file:text-sm file:font-semibold file:text-indigo-700 '
                         'hover:file:bg-indigo-100 cursor-pointer',
                'accept': 'image/*',
            }),
        }

    def clean_image(self):
        """Kiểm tra kích thước và định dạng ảnh tải lên."""
        image = self.cleaned_data.get('image')
        if not image:
            return image

        from django.conf import settings
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024)

        if image.size > max_size:
            mb = max_size / (1024 * 1024)
            raise ValidationError(
                f"Ảnh vượt quá {mb:.0f}MB. Vui lòng chọn ảnh nhỏ hơn hoặc nén lại trước."
            )

        valid_extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif']
        extension = image.name.rsplit('.', 1)[-1].lower() if '.' in image.name else ''
        if extension not in valid_extensions:
            raise ValidationError(
                "Định dạng ảnh không hợp lệ. Chỉ chấp nhận: JPG, PNG, WEBP, GIF."
            )
        return image

    def clean(self):
        """Đồng bộ giá và cờ tặng miễn phí."""
        cleaned = super().clean()
        price = cleaned.get('price')
        is_free = cleaned.get('is_free')

        if is_free and price and price > 0:
            # Người dùng tick "tặng 0đ" nhưng vẫn nhập giá -> coi như bán
            cleaned['is_free'] = False
        elif (price == 0) and not is_free:
            cleaned['is_free'] = True
        return cleaned


class PostImageForm(forms.ModelForm):
    """Thêm ảnh phụ cho bài đăng."""

    class Meta:
        model = PostImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-slate-600 file:mr-4 file:rounded-xl '
                         'file:border-0 file:bg-indigo-50 file:px-5 file:py-3 '
                         'file:text-sm file:font-semibold file:text-indigo-700 '
                         'hover:file:bg-indigo-100 cursor-pointer',
                'accept': 'image/*',
            })
        }
        labels = {'image': "Chọn ảnh phụ"}

    def clean_image(self):
        """Kiểm tra ảnh phụ giống ảnh đại diện."""
        image = self.cleaned_data.get('image')
        if not image:
            return image

        from django.conf import settings
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024)
        if image.size > max_size:
            mb = max_size / (1024 * 1024)
            raise ValidationError(f"Ảnh vượt quá {mb:.0f}MB.")

        valid_extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif']
        extension = image.name.rsplit('.', 1)[-1].lower() if '.' in image.name else ''
        if extension not in valid_extensions:
            raise ValidationError("Định dạng ảnh không hợp lệ.")
        return image


# ---------------------------------------------------------------------------
#  TƯƠNG TÁC
# ---------------------------------------------------------------------------

class CommentForm(forms.ModelForm):
    """Gửi bình luận hoặc trả lời bình luận."""

    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'placeholder': 'Viết câu hỏi hoặc thông tin trao đổi với người bán...',
                'rows': 3,
                'maxlength': 1000,
            })
        }
        labels = {'content': "Nội dung"}

    def clean_content(self):
        """Loại bỏ khoảng trắng thừa và kiểm tra độ dài."""
        content = self.cleaned_data['content'].strip()
        if not content:
            raise ValidationError("Nội dung bình luận không được để trống.")
        if len(content) < 2:
            raise ValidationError("Bình luận quá ngắn.")
        return content


class ReviewForm(forms.ModelForm):
    """Đánh giá uy tín người bán."""

    RATING_CHOICES = [
        (5, '⭐⭐⭐⭐⭐ 5 sao - Rất hài lòng'),
        (4, '⭐⭐⭐⭐ 4 sao - Hài lòng'),
        (3, '⭐⭐⭐ 3 sao - Bình thường'),
        (2, '⭐⭐ 2 sao - Không hài lòng'),
        (1, '⭐ 1 sao - Rất không hài lòng'),
    ]

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES, coerce=int,
        widget=forms.RadioSelect(attrs={'class': 'mt-2 space-y-2'}),
        label="Chấm điểm"
    )

    class Meta:
        model = Review
        fields = ['rating', 'content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'placeholder': 'Chia sẻ trải nghiệm giao dịch của bạn với người bán...',
                'rows': 3, 'maxlength': 500,
            })
        }
        labels = {'content': "Nhận xét (không bắt buộc)"}

    def clean_content(self):
        """Nhận xét nếu có thì không được để trống hoàn toàn."""
        return (self.cleaned_data.get('content') or '').strip()


class ReportForm(forms.ModelForm):
    """Báo cáo bài đăng vi phạm."""

    class Meta:
        model = Report
        fields = ['reason', 'detail']
        widgets = {
            'reason': forms.RadioSelect(
                choices=Report.Reason.choices,
                attrs={'class': 'mt-2 space-y-2'}
            ),
            'detail': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'placeholder': 'Mô tả cụ thể vấn đề bạn gặp phải...',
                'rows': 3, 'maxlength': 500,
            }),
        }
        labels = {'reason': "Lý do báo cáo", 'detail': "Chi tiết (không bắt buộc)"}


# ---------------------------------------------------------------------------
#  ĐẶT MUA
# ---------------------------------------------------------------------------

class OrderForm(forms.ModelForm):
    """Gửi yêu cầu đặt mua sản phẩm."""

    class Meta:
        model = Order
        fields = ['message', 'contact']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': TEXTAREA_CLASS,
                'placeholder': 'Xin chào, tôi muốn mua sản phẩm này. '
                               'Có thể giao dịch vào thời gian nào ạ?',
                'rows': 4, 'maxlength': 500,
            }),
            'contact': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Số điện thoại hoặc email để người bán liên hệ',
                'maxlength': 120,
            }),
        }
        labels = {
            'message': "Lời nhắn cho người bán",
            'contact': "Thông tin liên hệ",
        }
        help_texts = {
            'message': "Không bắt buộc. Nên nói rõ thời gian và địa điểm giao dịch.",
            'contact': "Người bán sẽ dùng thông tin này để liên hệ với bạn.",
        }

    def clean_contact(self):
        """Kiểm tra thông tin liên hệ có chứa email hoặc số điện thoại."""
        contact = self.cleaned_data.get('contact', '').strip()
        if not contact:
            return contact
        has_email = '@' in contact
        has_phone = any(char.isdigit() for char in contact)
        if not (has_email or has_phone):
            raise ValidationError(
                "Thông tin liên hệ phải chứa email hoặc số điện thoại."
            )
        return contact


class OrderDecisionForm(forms.Form):
    """Ghi chú của người bán khi xác nhận / từ chối đơn hàng."""

    seller_note = forms.CharField(
        required=False, max_length=300,
        widget=forms.Textarea(attrs={
            'class': TEXTAREA_CLASS,
            'placeholder': 'Ghi chú thêm cho người mua (không bắt buộc)...',
            'rows': 3, 'maxlength': 300,
        }),
        label="Ghi chú"
    )
