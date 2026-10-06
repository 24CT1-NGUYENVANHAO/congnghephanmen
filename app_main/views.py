from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Post, Category, Comment
from .forms import PostForm, CommentForm

# 1. Trang chủ
def home(request):
    """Trang chủ hiển thị danh sách bài đăng, hỗ trợ tìm kiếm và lọc theo danh mục hoặc đồ tặng 0đ."""
    posts = Post.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    
    # Tìm kiếm theo từ khóa
    query = request.GET.get('q', '')
    if query:
        posts = posts.filter(title__icontains=query)
        
    # Lọc theo Danh mục
    cat_param = request.GET.get('cat') or request.GET.get('category')
    if cat_param and cat_param != 'all':
        if cat_param.isdigit():
            posts = posts.filter(category_id=int(cat_param))
        else:
            posts = posts.filter(category__name__icontains=cat_param)
        
    # Lọc hàng tặng 0đ
    is_free = request.GET.get('free')
    if is_free == '1':
        posts = posts.filter(is_free=True)

    context = {
        'posts': posts,
        'categories': categories,
        'query': query,
        'cat_id': cat_param,
        'selected_category': cat_param,
        'free_only': is_free == '1',
    }
    return render(request, 'app_main/home.html', context)


# 2. Chi tiết bài viết & Bình luận
def post_detail(request, pk):
    """Hiển thị chi tiết bài đăng sản phẩm và tiếp nhận bình luận trao đổi."""
    post = get_object_or_404(Post, pk=pk)
    comment_form = CommentForm()
    
    # Xử lý gửi bình luận bằng CommentForm
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect('post_detail', pk=pk)

    return render(request, 'app_main/detail.html', {
        'post': post,
        'comment_form': comment_form
    })


# 3. Đặt mua / Đăng ký nhận sản phẩm
@login_required
def buy_post(request, pk):
    """Xử lý yêu cầu mua sản phẩm hoặc nhận tặng đồ 0đ từ người dùng khác."""
    post = get_object_or_404(Post, pk=pk)
    
    # Không cho phép chủ tin tự mua bài của mình
    if post.seller == request.user:
        return redirect('post_detail', pk=pk)

    if request.method == 'POST':
        post.is_sold = True
        post.save()

    return redirect('post_detail', pk=pk)


# 4. Tạo bài viết / Đăng tin (Dùng PostForm chuẩn)
@login_required
def create_post(request):
    """Xử lý đăng bài bán sách, giáo trình hoặc tặng đồ miễn phí."""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.seller = request.user  # Gán người đăng tin
            
            # Tự động đánh dấu is_free nếu giá bán = 0
            if post.price == 0:
                post.is_free = True

            post.save()
            return redirect('home')
    else:
        form = PostForm()

    return render(request, 'app_main/create_post.html', {'form': form})


# 5. Danh sách tin đã đăng của người dùng
@login_required
def my_posts(request):
    """Hiển thị tất cả bài đăng cá nhân do người dùng hiện tại quản lý."""
    posts = Post.objects.filter(seller=request.user).order_by('-created_at')
    return render(request, 'app_main/my_posts.html', {'posts': posts})


# 6. Đánh dấu đã bán / chưa bán
@login_required
def toggle_sold(request, pk):
    """Chuyển đổi trạng thái Đã bán <-> Còn hàng cho bài đăng cá nhân."""
    post = get_object_or_404(Post, pk=pk, seller=request.user)
    if hasattr(post, 'is_sold'):
        post.is_sold = not post.is_sold
        post.save()
    return redirect('my_posts')


# 7. Thêm / Xóa khỏi danh sách yêu thích
@login_required
def toggle_wishlist(request, pk):
    """Thêm hoặc gỡ bỏ sản phẩm khỏi danh sách yêu thích cá nhân."""
    post = get_object_or_404(Post, pk=pk)
    if request.user in post.wishlist.all():
        post.wishlist.remove(request.user)
    else:
        post.wishlist.add(request.user)
    return redirect('post_detail', pk=pk)


# 8. Đăng ký tài khoản
def register(request):
    """Xử lý đăng ký tài khoản sinh viên mới với kiểm tra độ mạnh mật khẩu."""
    if request.user.is_authenticated:
        return redirect('home')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        pass1 = request.POST.get('password1')
        pass2 = request.POST.get('password2')

        if pass1 != pass2:
            error = "Mật khẩu xác nhận không khớp!"
        elif len(pass1) < 6 or not pass1[0].isupper():
            error = "Mật khẩu phải từ 6 ký tự trở lên và chữ cái đầu tiên phải viết HOA!"
        elif User.objects.filter(username=username).exists():
            error = "Tên đăng nhập này đã tồn tại!"
        else:
            user = User.objects.create_user(username=username, password=pass1)
            login(request, user)
            return redirect('home')

    return render(request, 'registration/register.html', {'error': error})