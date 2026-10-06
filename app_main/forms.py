from django import forms
from .models import Post, Comment, Category

class PostForm(forms.ModelForm):
    """Form tạo và cập nhật bài đăng bán hoặc tặng đồ dùng học tập."""
    # Lấy danh mục động từ CSDL thay vì chọn cứng
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="-- Chọn danh mục --",
        widget=forms.Select(attrs={'class': 'w-full p-2 border rounded-lg bg-white'})
    )

    class Meta:
        model = Post
        # Đã đổi 'image_url' thành 'image' để tải file lên
        fields = ['title', 'category', 'price', 'is_free', 'condition', 'image', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg', 'placeholder': 'Nhập tên sách/dụng cụ...'}),
            'price': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded-lg', 'value': 0}),
            # Django sẽ tự load Mới/Cũ từ CONDITION_CHOICES trong models.py
            'condition': forms.Select(attrs={'class': 'w-full p-2 border rounded-lg bg-white'}),
            # Dùng FileInput cho phép tải file ảnh từ máy tính
            'image': forms.FileInput(attrs={'class': 'w-full p-2 border rounded-lg bg-white', 'accept': 'image/*'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded-lg', 'rows': 4, 'placeholder': 'Mô tả chi tiết về sản phẩm...'}),
        }

class CommentForm(forms.ModelForm):
    """Form gửi bình luận và trao đổi trực tiếp dưới bài đăng."""
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-lg', 'placeholder': 'Hỏi người bán về sản phẩm này...'}),
        }