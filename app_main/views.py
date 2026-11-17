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
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CommentForm, OrderDecisionForm, OrderForm, PostForm, PostImageForm,
    ProfileForm, RegisterForm, ReportForm, ReviewForm,
    SupportReplyForm, SupportTicketForm, TicketResolveForm,
)
from .models import (
    Category, Comment, Favorite, Order, Post, Report, Review,
    SupportMessage, SupportTicket,
)
from .permissions import can_moderate, moderator_required, student_required


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

    # Bài chưa duyệt / bị từ chối / bị ẩn chỉ chủ bài và người kiểm duyệt xem được
    if (
        post.status not in (Post.Status.ACTIVE, Post.Status.SOLD)
        and post.seller != request.user
        and not can_moderate(request.user)
    ):
        raise Http404("Bài đăng không tồn tại")

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
        'can_moderate': can_moderate(request.user),
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
@student_required
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

@student_required
def create_post(request):
    """Đăng tin bán hoặc tặng sản phẩm mới."""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.seller = request.user
            # Mới đăng tin vẫn chờ kiểm duyệt trước khi hiển thị trên sàn.
            post.status = Post.Status.PENDING
            post.save()
            messages.success(
                request,
                "📝 Tin đã được gửi và đang chờ kiểm duyệt. "
                "Tin sẽ hiển thị trên sàn sau khi được duyệt.",
            )
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


@student_required
def edit_post(request, pk):
    """Chỉnh sửa bài đăng — chỉ chủ bài đăng được phép."""
    post = get_object_or_404(Post, pk=pk)

    if post.seller != request.user and not request.user.is_staff:
        messages.error(request, "Bạn không có quyền sửa bài đăng của người khác.")
        return redirect(post.get_absolute_url())

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            # Admin sửa thì giữ nguyên trạng thái; người bán sửa thì duyệt lại.
            # Bài đã bán (SOLD) giữ nguyên trạng thái, không quay lại sàn.
            if not request.user.is_staff and post.status != Post.Status.SOLD:
                post.status = Post.Status.PENDING
                # Xoá lý do từ chối cũ khi bán lại / đăng lại tin.
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


@student_required
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
@student_required
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
@student_required
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
@student_required
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
@student_required
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

@student_required
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

    # Đã có đơn đang mở (bao gồm đơn đang tranh chấp) thì không tạo thêm,
    # chỉ hiện lại trạng thái đã gửi
    existing = Order.objects.filter(
        post=post, buyer=request.user,
        status__in=[Order.Status.PENDING, Order.Status.CONFIRMED,
                    Order.Status.DISPUTED]
    ).first()

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
            order.post = post
            order.buyer = request.user
            order.seller = post.seller
            # Chốt giá tại thời điểm đặt mua
            order.price_snapshot = post.price
            order.save()
            # Ở lại trang đặt mua để hiện mã QR thanh toán cho người mua
            return render(request, 'app_main/buy_post.html', {
                'post': post,
                'form': OrderForm(),
                'sent_order': order,
            })
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

    if order.status == Order.Status.DISPUTED:
        messages.error(
            request,
            "Đơn đang tranh chấp. Chỉ kiểm duyệt viên mới xử lý được.",
        )
        return redirect('order_detail', pk=order.pk)

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

    if order.status == Order.Status.DISPUTED:
        messages.error(
            request,
            "Đơn đang tranh chấp. Chỉ kiểm duyệt viên mới xử lý được.",
        )
        return redirect('order_detail', pk=order.pk)

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

    if order.status == Order.Status.DISPUTED:
        messages.error(
            request,
            "Đơn đang tranh chấp. Chỉ kiểm duyệt viên mới xử lý được.",
        )
        return redirect('order_detail', pk=order.pk)

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

    if order.status == Order.Status.DISPUTED:
        messages.error(
            request,
            "Đơn đang tranh chấp. Chỉ kiểm duyệt viên mới xử lý được.",
        )
        return redirect('order_detail', pk=order.pk)

    if order.status not in (Order.Status.PENDING, Order.Status.CONFIRMED):
        messages.error(request, "Đơn hàng này không thể huỷ.")
        return redirect('order_detail', pk=order.pk)

    order.status = Order.Status.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    messages.info(request, f"Đã huỷ đơn #{order.pk}.")
    return redirect('my_orders')


# ---------------------------------------------------------------------------
#  HỖ TRỢ / TRANH CHẤP (phiên hỗ trợ gắn với một đơn hàng)
# ---------------------------------------------------------------------------

def _is_order_party(user, order):
    """Người mua hoặc người bán của đơn."""
    return user in (order.buyer, order.seller)


def _can_view_ticket(user, ticket):
    """Người mở phiên, hai bên của đơn, hoặc người kiểm duyệt."""
    return can_moderate(user) or _is_order_party(user, ticket.order)


@login_required
def my_tickets(request):
    """Danh sách phiên hỗ trợ liên quan đến người dùng hiện tại.

    Lấy phiên mà người dùng là người mở, hoặc là người mua / người bán của
    đơn hàng gắn kèm. Hỗ trợ lọc ?status=open|resolved qua tham số GET.
    """
    tickets = (
        SupportTicket.objects.filter(
            Q(opened_by=request.user)
            | Q(order__buyer=request.user)
            | Q(order__seller=request.user)
        )
        .distinct()
        .select_related('order__post', 'order__buyer', 'order__seller')
        .order_by('-created_at')
    )

    status_filter = request.GET.get('status', '')
    if status_filter == 'open':
        tickets = tickets.exclude(status=SupportTicket.Status.RESOLVED)
    elif status_filter == 'resolved':
        tickets = tickets.filter(status=SupportTicket.Status.RESOLVED)

    return render(request, 'app_main/my_tickets.html', {
        'tickets': tickets,
        'status_filter': status_filter,
    })


@login_required
def support_ticket_detail(request, pk, reply_form=None):
    """Xem chi tiết một phiên hỗ trợ kèm luồng tin nhắn.

    Nếu caller truyền `reply_form` (bound form đã lỗi validation từ
    support_ticket_reply) thì dùng luôn form đó để hiển thị lỗi inline
    ngay bên cạnh ô nhập, thay vì thông báo chung qua messages.
    """
    ticket = get_object_or_404(
        SupportTicket.objects.select_related(
            'order__post', 'order__buyer', 'order__seller'
        ).prefetch_related('messages__author__profile'),
        pk=pk,
    )

    if not _can_view_ticket(request.user, ticket):
        raise Http404("Phiên hỗ trợ không tồn tại.")

    if reply_form is None:
        reply_form = (
            None
            if ticket.status == SupportTicket.Status.RESOLVED
            else SupportReplyForm()
        )

    return render(request, 'app_main/support_ticket_detail.html', {
        'ticket': ticket,
        'reply_form': reply_form,
    })


@student_required
def open_support_ticket(request, pk):
    """Mở phiên hỗ trợ cho một đơn hàng (GET hiện form, POST tạo phiên).

    Chỉ người mua hoặc người bán của đơn được mở. Mỗi đơn chỉ được có tối
    đa 1 phiên chưa kết thúc (OPEN / IN_PROGRESS) — kiểm tra trước cả GET
    và POST để luôn về phiên cũ nếu đã có.

    Lưu ý: view dùng `@student_required` mà KHÔNG kèm `@require_POST`
    vì spec Step 4 yêu cầu GET để hiện form mở phiên
    (support_ticket_form.html). Đây là thiết kế deliberate, không phải
    Regression.
    """
    order = get_object_or_404(Order.objects.select_related('post'), pk=pk)

    if not _is_order_party(request.user, order):
        raise Http404("Bạn không thuộc đơn hàng này.")

    existing = (
        SupportTicket.objects.filter(
            order=order,
            status__in=[SupportTicket.Status.OPEN,
                        SupportTicket.Status.IN_PROGRESS],
        )
        .first()
    )
    if existing:
        messages.warning(
            request,
            f"Đơn #{order.pk} đã có phiên hỗ trợ #{existing.pk} đang mở."
        )
        return redirect('support_ticket_detail', pk=existing.pk)

    if request.method == 'POST':
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.order = order
            ticket.opened_by = request.user
            ticket.save()

            # Tin nhắn đầu tiên là nội dung người dùng gửi khi mở phiên.
            SupportMessage.objects.create(
                ticket=ticket, author=request.user,
                body=form.cleaned_data['body'],
            )

            # Mở phiên loại tranh chấp thì chuyển đơn sang DISPUTED.
            if (
                ticket.category == SupportTicket.Category.DISPUTE
                and order.status in (Order.Status.PENDING, Order.Status.CONFIRMED)
            ):
                order.status = Order.Status.DISPUTED
                order.save(update_fields=['status', 'updated_at'])

            messages.success(
                request,
                f"🆘 Đã mở phiên hỗ trợ #{ticket.pk} cho đơn #{order.pk}."
            )
            return redirect('support_ticket_detail', pk=ticket.pk)
    else:
        form = SupportTicketForm()

    return render(request, 'app_main/support_ticket_form.html', {
        'order': order,
        'form': form,
    })


@require_POST
@student_required
def support_ticket_reply(request, pk):
    """Trả lời một phiên hỗ trợ (POST + CSRF). Chỉ người có quyền xem."""
    ticket = get_object_or_404(SupportTicket.objects.select_related('order'), pk=pk)

    if not _can_view_ticket(request.user, ticket):
        raise Http404("Phiên hỗ trợ không tồn tại.")

    if ticket.status == SupportTicket.Status.RESOLVED:
        messages.error(request, "Phiên hỗ trợ này đã kết thúc, không thể trả lời.")
        return redirect('support_ticket_detail', pk=ticket.pk)

    form = SupportReplyForm(request.POST)
    if form.is_valid():
        SupportMessage.objects.create(
            ticket=ticket, author=request.user,
            body=form.cleaned_data['body'],
        )
        # Cập nhật updated_at để phiên hiển thị đúng thứ tự hoạt động mới nhất.
        ticket.save(update_fields=['updated_at'])
        messages.success(request, "💬 Đã gửi tin nhắn.")
        return redirect('support_ticket_detail', pk=ticket.pk)

    # Form lỗi: render lại trang chi tiết kèm form ràng lỗi để người dùng
    # sửa lại nội dung thay vì bị mất input vừa nhập.
    return support_ticket_detail(request, pk, reply_form=form)


# ===========================================================================
#  ĐÁNH GIÁ & BÁO CÁO
# ===========================================================================

@require_POST
@student_required
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


@student_required
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
        'pending': Post.Status.PENDING,
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
        'pending': all_posts.filter(status=Post.Status.PENDING).count(),
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


#: Các đuôi email được phép dùng để đăng nhập.
#: Gmail cho sinh viên, .edu.vn cho tài khoản giảng viên / quản trị.
ALLOWED_EMAIL_DOMAINS = ('gmail.com',)


def _is_allowed_email(value):
    """Kiểm tra email có thuộc miền được phép đăng nhập không.

    Chấp nhận @gmail.com (sinh viên) và mọi đuối .edu.vn (email trường).
    Trả về False với email rỗng, thiếu '@', hoặc thuộc miền khác.
    """
    value = (value or '').strip().lower()
    if '@' not in value:
        return False
    domain = value.rsplit('@', 1)[1]
    if not domain:
        return False
    return domain in ALLOWED_EMAIL_DOMAINS or domain.endswith('.edu.vn')


def user_login(request):
    """Đăng nhập bằng email Gmail / email trường .edu.vn.

    Tên đăng nhập được sinh tự động từ email lúc đăng ký nên người dùng không
    phải nhớ: biểu mẫu chỉ nhận email, tra bản ghi ``User`` theo email rồi để
    ``AuthenticationForm`` kiểm tra mật khẩu như bình thường.
    """
    if request.user.is_authenticated:
        return redirect('home')

    error = ''
    email = ''
    form = AuthenticationForm()
    if request.method == 'POST':
        email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if '@' not in email:
            error = (
                'Vui lòng đăng nhập bằng địa chỉ email '
                '(@gmail.com hoặc email trường @edu.vn).'
            )
        elif not _is_allowed_email(email):
            error = (
                'Chỉ chấp nhận email @gmail.com hoặc email trường @edu.vn. '
                'Vui lòng nhập lại.'
            )
        else:
            from django.contrib.auth import get_user_model
            matched = get_user_model().objects.filter(email__iexact=email).first()
            if not matched:
                error = 'Không tìm thấy tài khoản nào dùng email này.'
            else:
                form = AuthenticationForm(
                    request,
                    data={'username': matched.username, 'password': password},
                )
                if form.is_valid():
                    login(request, form.get_user())
                    messages.success(request, f"Xin chào, {request.user.profile.display_name}!")
                    return redirect(request.GET.get('next') or request.POST.get('next') or 'home')
                error = 'Email hoặc mật khẩu không chính xác. Vui lòng thử lại.'

    return render(request, 'registration/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
        'login_error': error,
        'login_email': email,
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
#  QUẢN TRỊ (Admin và Kiểm duyệt viên)
# ===========================================================================


@moderator_required
def admin_dashboard(request):
    """
    Bảng điều khiển quản trị: số liệu tổng quan + kiểm duyệt nhanh.

    Mỗi bảng chỉ lấy 10 bản ghi mới nhất; muốn xem đầy đủ thì theo lối tắt
    sang Django admin (đã lọc sẵn theo trạng thái).
    """
    pending_posts = (
        Post.objects.filter(status=Post.Status.PENDING)
        .select_related('seller', 'category')
        .order_by('-created_at')[:10]
    )
    pending_reports = (
        Report.objects.filter(status=Report.Status.PENDING)
        .select_related('post', 'post__seller', 'reporter')
        .order_by('-created_at')[:10]
    )

    # Doanh thu = tổng giá chốt của các đơn đã hoàn tất
    revenue = (
        Order.objects.filter(status=Order.Status.COMPLETED)
        .aggregate(total=Sum('price_snapshot'))['total'] or 0
    )

    # Phiên hỗ trợ đang mở (chưa giải quyết)
    open_tickets_qs = (
        SupportTicket.objects.filter(
            status__in=[SupportTicket.Status.OPEN, SupportTicket.Status.IN_PROGRESS]
        )
        .select_related('order__post', 'opened_by')
    )

    stats = {
        'pending_posts': Post.objects.filter(status=Post.Status.PENDING).count(),
        'pending_reports': Report.objects.filter(status=Report.Status.PENDING).count(),
        'pending_orders': Order.objects.filter(status=Order.Status.PENDING).count(),
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'total_posts': Post.objects.count(),
        'completed_orders': Order.objects.filter(status=Order.Status.COMPLETED).count(),
        'revenue': revenue,
        'pending_tickets': open_tickets_qs.count(),
        'disputed_orders': Order.objects.filter(status=Order.Status.DISPUTED).count(),
    }

    return render(request, 'app_main/admin_dashboard.html', {
        'stats': stats,
        'pending_posts': pending_posts,
        'pending_reports': pending_reports,
        'open_tickets': open_tickets_qs.order_by('-updated_at')[:10],
        'is_moderator_only': can_moderate(request.user) and not request.user.is_staff,
    })


@require_POST
@moderator_required
def admin_approve_post(request, pk):
    """Duyệt một bài đang chờ: PENDING → ACTIVE."""
    post = get_object_or_404(Post, pk=pk)
    if post.status != Post.Status.PENDING:
        messages.warning(
            request,
            f"Bài “{post.title}” không còn ở trạng thái chờ duyệt."
        )
    else:
        post.status = Post.Status.ACTIVE
        post.rejection_reason = ''
        post.save(update_fields=['status', 'rejection_reason'])
        messages.success(request, f"✅ Đã duyệt bài “{post.title}”.")
    return redirect('admin_dashboard')


@require_POST
@moderator_required
def admin_reject_post(request, pk):
    """Từ chối một bài đang chờ: PENDING → REJECTED, kèm lý do."""
    post = get_object_or_404(Post, pk=pk)
    if post.status != Post.Status.PENDING:
        messages.warning(
            request,
            f"Bài “{post.title}” không còn ở trạng thái chờ duyệt."
        )
    else:
        reason = request.POST.get('reason', '').strip()
        post.status = Post.Status.REJECTED
        post.rejection_reason = (
            reason[:255] or "Không phù hợp với quy định đăng tin."
        )
        post.save(update_fields=['status', 'rejection_reason'])
        messages.success(request, f"🚫 Đã từ chối bài “{post.title}”.")
    return redirect('admin_dashboard')


@require_POST
@moderator_required
def admin_resolve_report(request, pk):
    """
    Xử lý báo cáo: report → RESOLVED và ẩn bài bị báo cáo.

    Chỉ ẩn khi bài còn đang chờ duyệt hoặc đang hiển thị; bài đã bán / đã bị
    từ chối / đã ẩn thì giữ nguyên trạng thái để không làm sai lịch sử.
    """
    report = get_object_or_404(Report.objects.select_related('post'), pk=pk)
    if report.status != Report.Status.PENDING:
        messages.warning(request, "Báo cáo này đã được xử lý trước đó.")
        return redirect('admin_dashboard')

    report.status = Report.Status.RESOLVED
    report.save(update_fields=['status'])

    post = report.post
    if post.status in (Post.Status.PENDING, Post.Status.ACTIVE):
        post.status = Post.Status.HIDDEN
        post.save(update_fields=['status'])

    messages.success(
        request,
        f"✅ Đã xử lý báo cáo và ẩn bài “{post.title}”."
    )
    return redirect('admin_dashboard')


@require_POST
@moderator_required
def admin_dismiss_report(request, pk):
    """Bỏ qua báo cáo: report → DISMISSED, không đổi bài đăng."""
    report = get_object_or_404(Report.objects.select_related('post'), pk=pk)
    if report.status != Report.Status.PENDING:
        messages.warning(request, "Báo cáo này đã được xử lý trước đó.")
    else:
        report.status = Report.Status.DISMISSED
        report.save(update_fields=['status'])
        messages.success(
            request,
            f"⚪ Đã bỏ qua báo cáo cho bài “{report.post.title}”."
        )
    return redirect('admin_dashboard')


# ===========================================================================
#  KIỂM DUYỊT VIÊN: HỖ TRỢ / TRANH CHẤP VÀ QUYẾT ĐỊNH ĐƠN HÀNG
# ===========================================================================

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


def _render_moderator_ticket_detail(request, ticket, reply_form=None, resolve_form=None):
    """Render chung trang chi tiết phiên hỗ trợ cho kiểm duyệt viên.

    Nạp ticket kèm đơn → sản phẩm, người mua / người bán, và luồng tin nhắn
    kèm hồ sơ tác giả. Mặc định trống form trả lời và form kết luận.
    """
    ticket = (
        SupportTicket.objects.select_related(
            'order__post', 'order__buyer', 'order__seller'
        )
        .prefetch_related('messages__author__profile')
        .get(pk=ticket.pk)
    )
    if reply_form is None:
        reply_form = SupportReplyForm()
    if resolve_form is None:
        resolve_form = TicketResolveForm()
    return render(request, 'app_main/moderator_ticket_detail.html', {
        'ticket': ticket,
        'reply_form': reply_form,
        'resolve_form': resolve_form,
    })


@moderator_required
def moderator_ticket_list(request):
    """Danh sách tất cả phiên hỗ trợ / tranh chấp (chỉ kiểm duyệt viên).

    Hỗ trợ lọc ?status=open|resolved|all (mặc định open = OPEN | IN_PROGRESS),
    sắp xếp theo cập nhật gần nhất.
    """
    tickets = (
        SupportTicket.objects.select_related(
            'order__post', 'opened_by', 'handled_by'
        )
        .order_by('-updated_at')
    )
    status_filter = request.GET.get('status', 'open')
    if status_filter == 'open':
        tickets = tickets.filter(
            status__in=[
                SupportTicket.Status.OPEN,
                SupportTicket.Status.IN_PROGRESS,
            ]
        )
    elif status_filter == 'resolved':
        tickets = tickets.filter(status=SupportTicket.Status.RESOLVED)
    # 'all' → không lọc, hiển thị tất cả phiên
    return render(request, 'app_main/moderator_ticket_list.html', {
        'tickets': tickets,
        'status_filter': status_filter,
    })


@moderator_required
def moderator_ticket_detail(request, pk):
    """Xem chi tiết một phiên hỗ trợ — kiểm duyệt viên xem được tất cả."""
    ticket = get_object_or_404(SupportTicket, pk=pk)
    return _render_moderator_ticket_detail(request, ticket)


@moderator_required
@require_POST
def moderator_ticket_reply(request, pk):
    """Trả lời một phiên hỗ trợ từ trang kiểm duyệt (POST + CSRF)."""
    ticket = get_object_or_404(SupportTicket.objects.select_related('order'), pk=pk)

    if ticket.status == SupportTicket.Status.RESOLVED:
        messages.error(request, "Phiên đã kết thúc.")
        return redirect('moderator_ticket_detail', pk=ticket.pk)

    form = SupportReplyForm(request.POST)
    if not form.is_valid():
        # Giữ lại input vừa nhập để hiển thị lỗi inline trên trang chi tiết
        return _render_moderator_ticket_detail(request, ticket, reply_form=form)

    if ticket.status == SupportTicket.Status.OPEN:
        ticket.status = SupportTicket.Status.IN_PROGRESS
    SupportMessage.objects.create(
        ticket=ticket, author=request.user,
        body=form.cleaned_data['body'],
    )
    ticket.save(update_fields=['status', 'updated_at'])
    messages.success(request, "💬 Đã gửi tin nhắn.")
    return redirect('moderator_ticket_detail', pk=ticket.pk)


@moderator_required
@require_POST
def moderator_ticket_resolve(request, pk):
    """Kết luận phiên + quyết định đơn hàng gắn kèm."""
    ticket = get_object_or_404(SupportTicket.objects.select_related('order'), pk=pk)
    form = TicketResolveForm(request.POST)
    if not form.is_valid():
        return _render_moderator_ticket_detail(request, ticket, resolve_form=form)

    _resolve_order_decision(ticket.order, form.cleaned_data['decision'])

    ticket.status = SupportTicket.Status.RESOLVED
    ticket.handled_by = request.user
    ticket.resolution_note = form.cleaned_data['resolution_note']
    ticket.resolved_at = timezone.now()
    ticket.save(
        update_fields=[
            'status', 'handled_by', 'resolution_note', 'resolved_at', 'updated_at',
        ]
    )
    messages.success(request, "✅ Đã kết luận phiên hỗ trợ.")
    return redirect('moderator_ticket_detail', pk=ticket.pk)


@moderator_required
@require_POST
def moderator_order_decision(request, pk):
    """Quyết định trạng thái đơn hàng từ trang chi tiết phiên (không đóng phiên).

    Nếu đơn đã kết thúc thì chỉ cảnh báo, không đổi trạng thái.
    """
    ticket = get_object_or_404(SupportTicket.objects.select_related('order'), pk=pk)
    form = TicketResolveForm(request.POST)
    if not form.is_valid():
        return _render_moderator_ticket_detail(request, ticket, resolve_form=form)

    order = ticket.order
    open_states = (Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.DISPUTED)
    if order.status in open_states:
        _resolve_order_decision(order, form.cleaned_data['decision'])
    else:
        messages.warning(
            request, "Đơn đã kết thúc, không đổi được trạng thái."
        )
    return redirect('moderator_ticket_detail', pk=ticket.pk)


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
