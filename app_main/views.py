"""
Tầng điều khiển (Controller) của hệ thống SáchGóc Uni.

Nguyên tắc áp dụng:
  - Mọi thay đổi trạng thái (đánh dấu bán, yêu thích) dùng POST + @require_POST
    để chống CSRF, không dùng GET như bản cũ.
  - Mọi hành động ghi/xoá đều kiểm tra quyền sở hữu trước khi thực hiện.
  - Validation ủy quyền cho Form, view chỉ điều phối.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    CommentForm, OrderDecisionForm, OrderForm, PostForm, PostImageForm,
    ProfileForm, RegisterForm, ReportForm, ReviewForm,
)
from .models import Category, Comment, Favorite, Order, Post, Report, Review


# ===========================================================================
#  TRANG CHỦ & TÌM KIẾM
# ===========================================================================

def home(request):
    """
    Trang chủ: danh sách bài đăng kèm tìm kiếm, lọc nâng cao và phân trang.

    Hỗ trợ tham số GET:
      q        - từ khoá tìm kiếm (tiêu đề, mô tả, mã môn, khoa)
      cat      - id danh mục
      free     - 1 nếu chỉ lấy đồ tặng 0đ
      condition- Lọc theo tình trạng
      faculty  - Lọc theo khoa/ngành
      min/max  - Lọc theo khoảng giá
      sort     - newest | price_asc | price_desc | popular
    """
    queryset = Post.objects.with_related().active()

    # --- Tìm kiếm từ khoá ---
    query = request.GET.get('q', '').strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(course_code__icontains=query)
            | Q(faculty__icontains=query)
        )

    # --- Lọc theo danh mục ---
    selected_category = None
    cat_param = request.GET.get('cat')
    if cat_param and cat_param.isdigit():
        selected_category = Category.objects.filter(pk=int(cat_param)).first()
        if selected_category:
            queryset = queryset.filter(category=selected_category)

    # --- Lọc đồ tặng miễn phí ---
    free_only = request.GET.get('free') == '1'
    if free_only:
        queryset = queryset.free_items()

    # --- Lọc theo tình trạng ---
    condition = request.GET.get('condition', '')
    if condition in dict(Post.Condition.choices):
        queryset = queryset.filter(condition=condition)

    # --- Lọc theo khoa ---
    faculty = request.GET.get('faculty', '').strip()
    if faculty:
        queryset = queryset.filter(faculty__icontains=faculty)

    # --- Lọc theo khoảng giá ---
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    if min_price and min_price.isdigit():
        queryset = queryset.filter(price__gte=int(min_price))
    if max_price and max_price.isdigit():
        queryset = queryset.filter(price__lte=int(max_price))

    # --- Sắp xếp ---
    sort = request.GET.get('sort', 'newest')
    sort_options = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'popular': '-view_count',
    }
    queryset = queryset.order_by(sort_options.get(sort, '-created_at'))

    # --- Phân trang ---
    paginator = Paginator(queryset, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Danh sách khoa để điền vào ô lọc (lấy những khoa thực sự có bài đăng)
    faculties = (
        Post.objects.active()
        .exclude(faculty='')
        .values_list('faculty', flat=True)
        .distinct()
        .order_by('faculty')[:20]
    )

    context = {
        'page_obj': page_obj,
        'posts': page_obj.object_list,
        'categories': Category.objects.annotate(
            total=Count('posts', filter=Q(posts__status=Post.Status.ACTIVE))
        ),
        'query': query,
        'selected_category': selected_category,
        'free_only': free_only,
        'condition': condition,
        'condition_choices': Post.Condition.choices,
        'faculty': faculty,
        'faculties': faculties,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
        'sort_options': sort_options,
        'total_posts': paginator.count,
    }
    return render(request, 'app_main/home.html', context)


# ===========================================================================
#  CHI TIẾT SẢN PHẨM
# ===========================================================================

def post_detail(request, pk):
    """
    Trang chi tiết sản phẩm: thư viện ảnh, thông tin người bán,
    bình luận hỏi đáp và sản phẩm liên quan.
    """
    post = get_object_or_404(
        Post.objects.with_related().select_related('seller__profile'),
        pk=pk
    )

    # Chỉ tăng lượt xem khi người xem không phải chủ bài đăng
    if not (request.user.is_authenticated and request.user == post.seller):
        post.increment_view()
        post.refresh_from_db(fields=['view_count'])

    # Bình luận gốc kèm các trả lời lồng nhau
    comments = (
        Comment.objects.filter(post=post, parent__isnull=True)
        .select_related('author__profile')
        .prefetch_related('replies__author__profile')
    )

    # Sản phẩm liên quan: cùng danh mục, loại trừ bài hiện tại
    related_posts = (
        Post.objects.active()
        .filter(category=post.category)
        .exclude(pk=post.pk)
        .select_related('seller', 'category')[:4]
    )
    if not related_posts.exists() and post.category:
        related_posts = (
            Post.objects.active()
            .exclude(pk=post.pk)
            .select_related('seller', 'category')[:4]
        )

    is_favorited = (
        request.user.is_authenticated
        and Favorite.objects.filter(user=request.user, post=post).exists()
    )

    # Đơn hàng đang mở của người dùng hiện tại (để hiện nút "Đơn #...")
    my_order = None
    if request.user.is_authenticated and request.user != post.seller:
        my_order = (
            Order.objects.filter(
                post=post, buyer=request.user,
                status__in=[Order.Status.PENDING, Order.Status.CONFIRMED]
            ).first()
        )

    context = {
        'post': post,
        'comments': comments,
        'comment_form': CommentForm(),
        'reply_form': CommentForm(),
        'related_posts': related_posts,
        'is_favorited': is_favorited,
        'my_order': my_order,
        'can_report': (
            request.user.is_authenticated
            and request.user != post.seller
            and not Report.objects.filter(
                post=post, reporter=request.user,
                status=Report.Status.PENDING
            ).exists()
        ),
        'seller_avg': post.seller.reviews_received.aggregate(
            average=Avg('rating')
        )['average'],
        'seller_reviews_count': post.seller.reviews_received.count(),
    }
    return render(request, 'app_main/post_detail.html', context)


@require_POST
@login_required
def toggle_favorite(request, pk):
    """Yêu thích / bỏ yêu thích. POST + CSRF an toàn."""
    post = get_object_or_404(Post, pk=pk)
    favorite = Favorite.objects.filter(user=request.user, post=post).first()

    if favorite:
        favorite.delete()
        message, state = "Đã bỏ khỏi danh sách yêu thích.", 'info'
    else:
        Favorite.objects.create(user=request.user, post=post)
        message, state = "Đã thêm vào danh sách yêu thích ❤️", 'success'

    # Trả JSON nếu gọi bằng fetch (nút like không tải lại trang)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'favorited': not bool(favorite),
            'count': post.favorited_by.count(),
            'message': message,
        })

    messages.success(request, message)
    return redirect('post_detail', pk=pk)


# ===========================================================================
#  TẠO / SỬA / XOÁ BÀI ĐĂNG
# ===========================================================================

@login_required
def create_post(request):
    """Đăng tin bán hoặc tặng sản phẩm mới."""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.seller = request.user
            post.status = Post.Status.ACTIVE
            post.save()
            messages.success(request, "🎉 Đăng tin thành công! Sản phẩm đã hiển thị trên sàn.")
            return redirect(post.get_absolute_url())
    else:
        form = PostForm()

    return render(request, 'app_main/post_form.html', {
        'form': form,
        'post_image_form': PostImageForm(),
        'is_create': True,
        'title': "Đăng tin mới",
        'submit_text': "Đăng tin ngay",
    })


@login_required
def edit_post(request, pk):
    """Chỉnh sửa bài đăng — chỉ chủ bài đăng được phép."""
    post = get_object_or_404(Post, pk=pk)

    if post.seller != request.user and not request.user.is_staff:
        messages.error(request, "Bạn không có quyền sửa bài đăng của người khác.")
        return redirect(post.get_absolute_url())

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            # Nếu admin mở lại bài bị từ chối thì cho phép đăng lại
            if post.status == Post.Status.REJECTED:
                post.status = Post.Status.ACTIVE
                post.rejection_reason = ''
            form.save()
            messages.success(request, "✏️ Đã cập nhật bài đăng thành công!")
            return redirect(post.get_absolute_url())
    else:
        form = PostForm(instance=post)

    return render(request, 'app_main/post_form.html', {
        'form': form,
        'post_image_form': PostImageForm(),
        'post': post,
        'is_create': False,
        'title': "Chỉnh sửa bài đăng",
        'submit_text': "Lưu thay đổi",
    })


@login_required
def delete_post(request, pk):
    """Xoá bài đăng — chỉ chủ bài đăng hoặc Admin."""
    post = get_object_or_404(Post, pk=pk)

    if post.seller != request.user and not request.user.is_staff:
        messages.error(request, "Bạn không có quyền xoá bài đăng này.")
        return redirect(post.get_absolute_url())

    if post.seller == request.user:
        title = post.title
        post.delete()
        messages.success(request, f"🗑️ Đã xoá bài đăng \"{title[:40]}\".")
    else:
        post.status = Post.Status.HIDDEN
        post.save()
        messages.success(request, "🗑️ Admin đã ẩn bài đăng này.")

    return redirect('my_posts')


@require_POST
@login_required
def toggle_sold(request, pk):
    """Đánh dấu chưa bán / đã bán. POST + CSRF an toàn."""
    post = get_object_or_404(Post, pk=pk)

    if post.seller != request.user:
        messages.error(request, "Chỉ chủ bài đăng mới thay đổi được trạng thái.")
        return redirect(post.get_absolute_url())

    if post.is_sold:
        post.status = Post.Status.ACTIVE
        post.is_sold = False
        messages.info(request, "🔄 Đã mở lại bài đăng.")
    else:
        post.status = Post.Status.SOLD
        post.is_sold = True
        messages.success(request, "✅ Đã đánh dấu là đã bán / đã tặng.")
    post.save()

    return redirect(request.META.get('HTTP_REFERER', 'my_posts'))


@require_POST
@login_required
def upload_post_image(request, pk):
    """Thêm ảnh phụ cho bài đăng (tối đa 5 ảnh)."""
    post = get_object_or_404(Post, pk=pk)

    if post.seller != request.user:
        messages.error(request, "Bạn không có quyền thêm ảnh cho bài này.")
        return redirect(post.get_absolute_url())

    if post.images.count() >= 5:
        messages.warning(request, "Mỗi bài đăng chỉ được có tối đa 5 ảnh.")
        return redirect(post.get_absolute_url())

    form = PostImageForm(request.POST, request.FILES)
    if form.is_valid():
        post_image = form.save(commit=False)
        post_image.post = post
        post_image.order = post.images.count()
        post_image.save()
        messages.success(request, "📷 Đã thêm ảnh thành công.")
    else:
        for error in form.errors.values():
            messages.error(request, error[0])

    return redirect(post.get_absolute_url())


@require_POST
@login_required
def delete_post_image(request, pk):
    """Xoá một ảnh phụ của bài đăng."""
    post = get_object_or_404(Post, pk=pk)

    if post.seller != request.user:
        messages.error(request, "Bạn không có quyền xoá ảnh của bài này.")
        return redirect(post.get_absolute_url())

    image = get_object_or_404(post.images.all(), pk=pk)
    image.delete()
    messages.success(request, "🗑️ Đã xoá ảnh.")

    return redirect(post.get_absolute_url())


# ===========================================================================
#  BÌNH LUẬN & HỎI ĐÁP
# ===========================================================================

@require_POST
@login_required
def add_comment(request, pk):
    """Thêm bình luận mới hoặc trả lời bình luận có sẵn."""
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user

        # Nếu có parent_id thì đây là trả lời
        parent_id = request.POST.get('parent_id')
        if parent_id:
            parent = Comment.objects.filter(pk=parent_id, post=post).first()
            comment.parent = parent

        comment.save()
        messages.success(request, "💬 Đã gửi bình luận.")
    else:
        messages.error(request, "Bình luận không hợp lệ: " + str(form.errors['content'][0]))

    return redirect(post.get_absolute_url())


@require_POST
@login_required
def delete_comment(request, pk):
    """Xoá bình luận — tác giả, chủ bài đăng hoặc Admin."""
    comment = get_object_or_404(Comment.objects.select_related('post'), pk=pk)

    is_author = comment.author == request.user
    is_post_owner = comment.post.seller == request.user
    if not (is_author or is_post_owner or request.user.is_staff):
        messages.error(request, "Bạn không có quyền xoá bình luận này.")
        return redirect(comment.post.get_absolute_url())

    comment.delete()
    messages.success(request, "🗑️ Đã xoá bình luận.")
    return redirect(comment.post.get_absolute_url())


# ===========================================================================
#  ĐẶT MUA & QUẢN LÝ ĐƠN HÀNG
# ===========================================================================

@login_required
def buy_post(request, pk):
    """
    Gửi yêu cầu đặt mua sản phẩm.

    Chỉ hiển thị form khi người dùng duyệt web (GET). Khi gửi (POST) thì tạo
    đơn hàng với trạng thái PENDING và chờ người bán xác nhận.
    """
    post = get_object_or_404(Post, pk=pk)

    # Không cho mua bài của chính mình
    if post.seller == request.user:
        messages.error(request, "Bạn không thể đặt mua sản phẩm của chính mình.")
        return redirect(post.get_absolute_url())

    # Chỉ mua được sản phẩm còn hiển thị
    if not post.is_available:
        messages.error(request, "Sản phẩm này đã bán, không thể đặt mua.")
        return redirect(post.get_absolute_url())

    # Đã có đơn đang mở thì không tạo thêm
    existing = Order.objects.filter(
        post=post, buyer=request.user,
        status__in=[Order.Status.PENDING, Order.Status.CONFIRMED]
    ).first()

    if existing:
        messages.warning(
            request,
            f"Bạn đã gửi yêu cầu mua sản phẩm này (đơn #{existing.pk}). "
            f"Trạng thái: {existing.get_status_display()}."
        )
        return redirect('my_orders')

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.post = post
            order.buyer = request.user
            order.seller = post.seller
            # Chốt giá tại thời điểm đặt mua
            order.price_snapshot = post.price
            order.save()
            messages.success(
                request,
                f"🎉 Đã gửi yêu cầu mua! Đơn #{order.pk}. "
                f"Người bán '{post.seller.profile.display_name}' sẽ liên hệ lại."
            )
            return redirect('my_orders')
    else:
        form = OrderForm()

    return render(request, 'app_main/buy_post.html', {
        'post': post,
        'form': form,
    })


@login_required
def my_orders(request):
    """Danh sách đơn hàng người dùng đã đặt (mua) và đã nhận (bán)."""
    buying = (
        Order.objects.filter(buyer=request.user)
        .select_related('post', 'seller__profile')
    )
    selling = (
        Order.objects.filter(seller=request.user)
        .select_related('post', 'buyer__profile')
    )

    # Số đơn chờ xử lại mà người dùng đang là người bán
    pending_sell_count = selling.filter(status=Order.Status.PENDING).count()

    return render(request, 'app_main/my_orders.html', {
        'buying': buying,
        'selling': selling,
        'pending_sell_count': pending_sell_count,
        'status_choices': Order.Status.choices,
    })


@login_required
def order_detail(request, pk):
    """Chi tiết một đơn hàng — chỉ người mua và người bán được xem."""
    order = get_object_or_404(
        Order.objects.select_related('post', 'buyer__profile', 'seller__profile'),
        pk=pk
    )

    if request.user not in (order.buyer, order.seller):
        messages.error(request, "Bạn không có quyền xem đơn hàng này.")
        return redirect('my_orders')

    return render(request, 'app_main/order_detail.html', {'order': order})


@require_POST
@login_required
def accept_order(request, pk):
    """Người bán xác nhận đơn hàng."""
    order = get_object_or_404(Order, pk=pk)

    if order.seller != request.user:
        messages.error(request, "Chỉ người bán mới xác nhận được đơn hàng.")
        return redirect('my_orders')

    if order.status != Order.Status.PENDING:
        messages.error(request, "Đơn hàng này không còn ở trạng thái chờ xác nhận.")
        return redirect('order_detail', pk=order.pk)

    order.status = Order.Status.CONFIRMED
    order.save(update_fields=['status', 'updated_at'])
    messages.success(
        request,
        f"✅ Đã xác nhận đơn #{order.pk}. "
        f"Hãy liên hệ {order.buyer.profile.display_name} để hẹn gặp."
    )
    return redirect('order_detail', pk=order.pk)


@require_POST
@login_required
def reject_order(request, pk):
    """Người bán từ chối đơn hàng."""
    order = get_object_or_404(Order, pk=pk)

    if order.seller != request.user:
        messages.error(request, "Chỉ người bán mới từ chối được đơn hàng.")
        return redirect('my_orders')

    if order.status != Order.Status.PENDING:
        messages.error(request, "Đơn hàng này không còn ở trạng thái chờ xác nhận.")
        return redirect('order_detail', pk=order.pk)

    form = OrderDecisionForm(request.POST)
    order.status = Order.Status.REJECTED
    order.seller_note = form.data.get('seller_note', '').strip()[:300]
    order.save(update_fields=['status', 'seller_note', 'updated_at'])

    messages.info(
        request,
        f"🚫 Đã từ chối đơn #{order.pk}. Sản phẩm vẫn đang hiển thị trên sàn."
    )
    return redirect('order_detail', pk=order.pk)


@require_POST
@login_required
def complete_order(request, pk):
    """Đánh dấu giao dịch hoàn tất — tự động chuyển sản phẩm sang ĐÃ BÁN."""
    order = get_object_or_404(Order, pk=pk)

    if request.user not in (order.buyer, order.seller):
        messages.error(request, "Bạn không có quyền xử lý đơn hàng này.")
        return redirect('my_orders')

    if order.status not in (Order.Status.PENDING, Order.Status.CONFIRMED):
        messages.error(request, "Đơn hàng này không thể đánh dấu hoàn tất.")
        return redirect('order_detail', pk=order.pk)

    order.status = Order.Status.COMPLETED
    order.save(update_fields=['status', 'updated_at'])

    # Tự động chuyển sản phẩm sang trạng thái đã bán
    order.post.status = Post.Status.SOLD
    order.post.is_sold = True
    order.post.save(update_fields=['status', 'is_sold', 'updated_at'])

    messages.success(
        request,
        f"🎊 Giao dịch hoàn tất! Sản phẩm đã chuyển sang 'Đã bán'. "
        f"Hãy để lại đánh giá cho người bán."
    )
    return redirect('order_detail', pk=order.pk)


@require_POST
@login_required
def cancel_order(request, pk):
    """Người mua huỷ đơn hàng."""
    order = get_object_or_404(Order, pk=pk)

    if order.buyer != request.user:
        messages.error(request, "Chỉ người mua mới huỷ được đơn hàng.")
        return redirect('my_orders')

    if order.status not in (Order.Status.PENDING, Order.Status.CONFIRMED):
        messages.error(request, "Đơn hàng này không thể huỷ.")
        return redirect('order_detail', pk=order.pk)

    order.status = Order.Status.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    messages.info(request, f"Đã huỷ đơn #{order.pk}.")
    return redirect('my_orders')


# ===========================================================================
#  ĐÁNH GIÁ & BÁO CÁO
# ===========================================================================

@require_POST
@login_required
def add_review(request, username):
    """Đánh giá uy tín một người dùng khác."""
    seller = get_object_or_404(User, username=username)

    if seller == request.user:
        messages.error(request, "Bạn không thể tự đánh giá chính mình.")
        return redirect('user_profile', username=username)

    if Review.objects.filter(seller=seller, reviewer=request.user).exists():
        messages.warning(request, "Bạn đã đánh giá người dùng này rồi.")
        return redirect('user_profile', username=username)

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.seller = seller
        review.reviewer = request.user
        review.save()
        messages.success(request, "⭐ Cảm ơn bạn đã đánh giá uy tín!")
    else:
        messages.error(request, "Đánh giá không hợp lệ. Vui lòng thử lại.")

    return redirect('user_profile', username=username)


@login_required
def report_post(request, pk):
    """Gửi báo cáo vi phạm một bài đăng."""
    post = get_object_or_404(Post, pk=pk)

    if post.seller == request.user:
        messages.error(request, "Bạn không thể báo cáo bài đăng của chính mình.")
        return redirect(post.get_absolute_url())

    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.post = post
            report.reporter = request.user
            report.save()
            messages.success(
                request,
                "🚩 Cảm ơn bạn! Báo cáo đã được gửi tới ban quản trị."
            )
            return redirect(post.get_absolute_url())
    else:
        form = ReportForm()

    return render(request, 'app_main/report_post.html', {
        'post': post,
        'form': form,
    })


# ===========================================================================
#  TRANG CÁ NHÂN & DANH SÁCH
# ===========================================================================

def user_profile(request, username):
    """Trang hồ sơ công khai của một sinh viên."""
    profile_user = get_object_or_404(User, username=username)
    posts = (
        profile_user.posts.active()
        .with_related()
        .select_related('category')
    )
    reviews = (
        profile_user.reviews_received
        .select_related('reviewer__profile')
        .prefetch_related('post')[:10]
    )

    aggregate = profile_user.reviews_received.aggregate(average=Avg('rating'))

    # Nếu là hồ sơ của chính mình, cho phép mở form đánh giá
    review_form = None
    if (
        request.user.is_authenticated
        and request.user != profile_user
        and not Review.objects.filter(seller=profile_user, reviewer=request.user).exists()
    ):
        review_form = ReviewForm()

    context = {
        'profile_user': profile_user,
        'profile': profile_user.profile,
        'posts': posts,
        'reviews': reviews,
        'average_rating': aggregate['average'],
        'review_count': profile_user.reviews_received.count(),
        'total_sold': profile_user.profile.total_sold,
        'total_posts': profile_user.posts.count(),
        'review_form': review_form,
    }
    return render(request, 'app_main/user_profile.html', context)


@login_required
def my_posts(request):
    """Quản lý toàn bộ bài đăng của người dùng hiện tại."""
    posts = Post.objects.filter(seller=request.user).select_related('category')
    status_filter = request.GET.get('status', '')

    status_map = {
        'active': Post.Status.ACTIVE,
        'sold': Post.Status.SOLD,
        'hidden': Post.Status.HIDDEN,
        'rejected': Post.Status.REJECTED,
    }
    if status_filter in status_map:
        posts = posts.filter(status=status_map[status_filter])

    paginator = Paginator(posts.order_by('-created_at'), 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Thống kê nhỏ cho dashboard
    all_posts = Post.objects.filter(seller=request.user)
    stats = {
        'total': all_posts.count(),
        'active': all_posts.filter(status=Post.Status.ACTIVE).count(),
        'sold': all_posts.filter(status=Post.Status.SOLD).count(),
        'total_views': sum(p.view_count for p in all_posts),
    }

    context = {
        'page_obj': page_obj,
        'posts': page_obj.object_list,
        'status_filter': status_filter,
        'stats': stats,
        'status_choices': Post.Status.choices,
    }
    return render(request, 'app_main/my_posts.html', context)


@login_required
def wishlist(request):
    """Danh sách sản phẩm người dùng đã yêu thích."""
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related('post__seller', 'post__category')
        .order_by('-created_at')
    )
    paginator = Paginator(favorites, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'app_main/wishlist.html', {'page_obj': page_obj})


# ===========================================================================
#  XÁC THỰC
# ===========================================================================

def register(request):
    """Đăng ký tài khoản sinh viên mới."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"🎉 Chào mừng {user.profile.display_name} đến với SáchGóc Uni!"
            )
            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})


def user_login(request):
    """Đăng nhập bằng tên đăng nhập hoặc email."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        # Cho phép đăng nhập bằng email thay vì username
        username = request.POST.get('username', '').strip()
        if '@' in username:
            from django.contrib.auth import get_user_model
            matched = get_user_model().objects.filter(email__iexact=username).first()
            if matched:
                form = AuthenticationForm(
                    request,
                    data={
                        'username': matched.username,
                        'password': request.POST.get('password', ''),
                    }
                )

        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, f"Xin chào, {request.user.profile.display_name}!")
            return redirect(request.GET.get('next') or 'home')
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


@require_POST
@login_required
def logout_view(request):
    """Đăng xuất — chỉ chấp nhận POST + CSRF để tránh bị ép đăng xuất."""
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, "👋 Bạn đã đăng xuất. Hẹn gặp lại!")
    return redirect('home')


@login_required
def edit_profile(request):
    """Chỉnh sửa hồ sơ cá nhân."""
    profile, _ = request.user.profile.__class__.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = ProfileForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()

            # Lưu các trường mở rộng trong Profile
            profile.faculty = request.POST.get('faculty', '')
            profile.student_id = request.POST.get('student_id', '')
            profile.phone = request.POST.get('phone', '')
            profile.bio = request.POST.get('bio', '')
            if request.FILES.get('avatar'):
                profile.avatar = request.FILES['avatar']
            profile.save()

            messages.success(request, "✅ Hồ sơ đã được cập nhật.")
            return redirect('edit_profile')
    else:
        user_form = ProfileForm(instance=request.user)

    context = {
        'form': user_form,
        'profile': profile,
        'stats': {
            'total_posts': request.user.posts.count(),
            'total_sold': profile.total_sold,
            'average_rating': profile.average_rating,
            'total_reviews': profile.total_reviews,
        },
    }
    return render(request, 'app_main/edit_profile.html', context)


@login_required
def change_password(request):
    """Đổi mật khẩu tài khoản."""
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Giữ phiên đăng nhập sau khi đổi mật khẩu
            update_session_auth_hash(request, user)
            messages.success(request, "🔐 Đổi mật khẩu thành công!")
            return redirect('edit_profile')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'app_main/change_password.html', {'form': form})


# ===========================================================================
#  TRANG TĨNH / LỖI
# ===========================================================================

def about(request):
    """Trang giới thiệu về sàn giao dịch."""
    stats = {
        'total_posts': Post.objects.active().count(),
        'free_posts': Post.objects.active().free_items().count(),
        'total_users': User.objects.count(),
        'total_sold': Post.objects.filter(status=Post.Status.SOLD).count(),
    }
    return render(request, 'app_main/about.html', {'stats': stats})


def handler_404(request, exception):
    """Trang lỗi 404 với giao diện đồng nhất."""
    return render(request, '404.html', status=404)


def handler_500(request):
    """Trang lỗi 500 với giao diện đồng nhất."""
    return render(request, '500.html', status=500)
