"""
Bộ kiểm thử tự động cho ứng dụng SáchGóc Uni.

Chạy:  python manage.py test

Bao phủ: Model, Form, View, phân quyền, CSRF và luồng người dùng chính.
"""

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .forms import RegisterForm
from .models import (
    Category, Comment, Favorite, Order, Post, Profile, Report, Review,
)

# Hash mật khẩu nhanh để test chạy nhanh hơn (chỉ dùng trong test)
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']


def create_user(username='sinhvien', password='MatKhau123', **kwargs):
    """Tạo tài khoản kiểm thử."""
    return User.objects.create_user(
        username=username, password=password, **kwargs
    )


def create_post(seller, title='Giáo trình Python', price=50000, **kwargs):
    """Tạo bài đăng kiểm thử."""
    defaults = {
        'description': 'Sách tình trạng tốt, có ghi chú bài tập.',
        'price': price,
        'condition': Post.Condition.LIKE_NEW,
    }
    defaults.update(kwargs)
    return Post.objects.create(seller=seller, title=title, **defaults)


# ===========================================================================
#  MODEL
# ===========================================================================

@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class ProfileModelTests(TestCase):
    """Hồ sơ sinh viên tự động được tạo cùng tài khoản."""

    def test_profile_created_automatically(self):
        user = create_user('havo')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_display_name_falls_back_to_username(self):
        user = create_user('minh')
        self.assertEqual(user.profile.display_name, 'minh')

        user.first_name = 'Văn Minh'
        user.save()
        self.assertEqual(user.profile.display_name, 'Văn Minh')


@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class PostModelTests(TestCase):
    """Kiểm tra logic của mô hình Post."""

    def setUp(self):
        self.user = create_user('seller')
        self.category = Category.objects.create(name='Giáo trình', slug='giao-trinh', icon='📚')

    def test_slug_generated_automatically(self):
        post = create_post(self.user, title='Giáo trình Kiến Trúc Căn Bản')
        self.assertEqual(post.slug, 'giao-trinh-kien-truc-can-ban')

    def test_duplicate_titles_get_unique_slug(self):
        create_post(self.user, title='Sách Lập Trình')
        second = create_post(self.user, title='Sách Lập Trình')
        self.assertNotEqual(second.slug, 'sach-lap-trinh')
        self.assertEqual(second.slug, 'sach-lap-trinh-2')

    def test_zero_price_marks_as_free(self):
        post = create_post(self.user, price=0)
        self.assertTrue(post.is_free)

    def test_status_sold_syncs_is_sold_flag(self):
        post = create_post(self.user)
        post.status = Post.Status.SOLD
        post.save()
        self.assertTrue(post.is_sold)

    def test_price_display_format(self):
        self.assertEqual(create_post(self.user, price=45000).price_display, '45.000đ')
        self.assertEqual(create_post(self.user, price=0).price_display, 'Miễn phí')

    def test_is_available(self):
        post = create_post(self.user)
        self.assertTrue(post.is_available)

        post.status = Post.Status.SOLD
        post.save()
        self.assertFalse(post.is_available)

    def test_increment_view(self):
        post = create_post(self.user)
        post.increment_view()
        post.refresh_from_db()
        self.assertEqual(post.view_count, 1)

    def test_active_queryset_excludes_sold(self):
        active = create_post(self.user, title='Đang bán')
        sold = create_post(self.user, title='Đã bán')
        sold.status = Post.Status.SOLD
        sold.save()

        active_titles = set(Post.objects.active().values_list('title', flat=True))
        self.assertIn('Đang bán', active_titles)
        self.assertNotIn('Đã bán', active_titles)

    def test_free_items_queryset(self):
        free = create_post(self.user, title='Tặng', price=0)
        paid = create_post(self.user, title='Bán', price=50000)

        free_titles = set(Post.objects.free_items().values_list('title', flat=True))
        self.assertIn(free.title, free_titles)
        self.assertNotIn(paid.title, free_titles)


@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class FavoriteModelTests(TestCase):
    """Kiểm tra bảng nối yêu thích."""

    def setUp(self):
        self.user = create_user('user1')
        self.other = create_user('user2')
        self.post = create_post(self.user)

    def test_cannot_favorite_same_post_twice(self):
        """Ràng buộc unique(user, post) chặn yêu thích trùng."""
        Favorite.objects.create(user=self.user, post=self.post)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Favorite.objects.create(user=self.user, post=self.post)

    def test_get_or_create_is_idempotent(self):
        """Cách dùng đúng: get_or_create không tạo bản ghi trùng."""
        Favorite.objects.get_or_create(user=self.user, post=self.post)
        Favorite.objects.get_or_create(user=self.user, post=self.post)
        self.assertEqual(Favorite.objects.filter(user=self.user).count(), 1)

    def test_different_users_can_favorite(self):
        Favorite.objects.create(user=self.user, post=self.post)
        Favorite.objects.create(user=self.other, post=self.post)
        self.assertEqual(self.post.favorited_by.count(), 2)


@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class ReviewModelTests(TestCase):
    """Kiểm tra ràng buộc đánh giá."""

    def setUp(self):
        self.seller = create_user('seller')
        self.reviewer = create_user('reviewer')
        self.post = create_post(self.seller)

    def test_one_review_per_reviewer(self):
        Review.objects.create(seller=self.seller, reviewer=self.reviewer, rating=5)
        # Tạo lần 2 sẽ vi phạm unique constraint
        with self.assertRaises(Exception):
            Review.objects.create(seller=self.seller, reviewer=self.reviewer, rating=3)

    def test_stars_property(self):
        review = Review.objects.create(seller=self.seller, reviewer=self.reviewer, rating=4)
        self.assertEqual(review.stars, [1, 1, 1, 1, 0])


# ===========================================================================
#  FORM
# ===========================================================================

@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class RegisterFormTests(TestCase):
    """Kiểm tra validation của form đăng ký."""

    def valid_data(self, **overrides):
        data = {
            'first_name': 'Nguyễn Văn Hào',
            'username': 'hao.nguyen',
            'email': 'hao@gmail.com',
            'faculty': 'Khoa Kiến trúc',
            'student_id': '24CT100001',
            'password1': 'MatKhau123',
            'password2': 'MatKhau123',
            'agree': True,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = RegisterForm(data=self.valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_passwords_must_match(self):
        form = RegisterForm(data=self.valid_data(password2='KhacMatKhau'))
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_password_requires_uppercase(self):
        form = RegisterForm(data=self.valid_data(password1='matkhau123', password2='matkhau123'))
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_password_requires_digit(self):
        form = RegisterForm(data=self.valid_data(password1='MatKhauABC', password2='MatKhauABC'))
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_password_minimum_length(self):
        form = RegisterForm(data=self.valid_data(password1='Ab1', password2='Ab1'))
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_password_cannot_contain_username(self):
        form = RegisterForm(data=self.valid_data(
            username='hao.nguyen',
            password1='Hao.nguyen123',
            password2='Hao.nguyen123'
        ))
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)

    def test_must_use_gmail(self):
        form = RegisterForm(data=self.valid_data(email='hao@yahoo.com'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_duplicate_email_rejected(self):
        create_user('existing', email='hao@gmail.com')
        form = RegisterForm(data=self.valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_duplicate_username_rejected(self):
        create_user('hao.nguyen')
        form = RegisterForm(data=self.valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_agree_is_required(self):
        form = RegisterForm(data=self.valid_data(agree=False))
        self.assertFalse(form.is_valid())
        self.assertIn('agree', form.errors)

    def test_save_creates_user_and_profile(self):
        form = RegisterForm(data=self.valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertTrue(User.objects.filter(username='hao.nguyen').exists())
        self.assertEqual(user.profile.faculty, 'Khoa Kiến trúc')
        self.assertEqual(user.profile.student_id, '24CT100001')
        self.assertTrue(user.check_password('MatKhau123'))


# ===========================================================================
#  VIEW - TRANG CÔNG KHAI
# ===========================================================================

@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class PublicViewTests(TestCase):
    """Các trang không yêu cầu đăng nhập."""

    def setUp(self):
        self.client = Client()
        self.user = create_user('seller')
        self.category = Category.objects.create(name='Giáo trình', slug='giao-trinh', icon='📚')
        self.post = create_post(self.user, category=self.category, title='Giáo trình Python')

    def test_home_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Giáo trình Python')

    def test_post_detail_page(self):
        response = self.client.get(reverse('post_detail', args=[self.post.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Giáo trình Python')

    def test_post_detail_increments_view(self):
        self.client.get(reverse('post_detail', args=[self.post.pk]))
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 1)

    def test_owner_view_does_not_increment(self):
        self.client.force_login(self.user)
        self.client.get(reverse('post_detail', args=[self.post.pk]))
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 0)

    def test_search_filters_posts(self):
        create_post(self.user, title='Sách Kiến Trúc', category=self.category)
        response = self.client.get(reverse('home'), {'q': 'Kiến Trúc'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sách Kiến Trúc')
        self.assertNotContains(response, 'Giáo trình Python')

    def test_filter_by_category(self):
        other = Category.objects.create(name='Điện tử', slug='dien-tu')
        create_post(self.user, title='Chuột không dây', category=other)
        response = self.client.get(reverse('home'), {'cat': other.pk})
        self.assertContains(response, 'Chuột không dây')
        self.assertNotContains(response, 'Giáo trình Python')

    def test_filter_free_only(self):
        create_post(self.user, title='Sách tặng miễn phí', price=0)
        response = self.client.get(reverse('home'), {'free': '1'})
        self.assertContains(response, 'Sách tặng miễn phí')
        self.assertNotContains(response, 'Giáo trình Python')

    def test_sort_by_price(self):
        create_post(self.user, title='Rẻ nhất', price=10000)
        create_post(self.user, title='Đắt nhất', price=900000)
        response = self.client.get(reverse('home'), {'sort': 'price_asc'})
        posts = list(response.context['posts'])
        self.assertEqual(posts[0].title, 'Rẻ nhất')

    def test_price_range_filter(self):
        create_post(self.user, title='Trong khoảng', price=50000)
        create_post(self.user, title='Ngoài khoảng', price=900000)
        response = self.client.get(reverse('home'), {'min_price': '10000', 'max_price': '100000'})
        self.assertContains(response, 'Trong khoảng')
        self.assertNotContains(response, 'Ngoài khoảng')

    def test_sold_posts_hidden_from_home(self):
        post = create_post(self.user, title='Đã bán rồi')
        post.status = Post.Status.SOLD
        post.save()
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, 'Đã bán rồi')

    def test_user_profile_page(self):
        response = self.client.get(reverse('user_profile', args=['seller']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'seller')

    def test_about_page(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)

    def test_404_page(self):
        response = self.client.get(reverse('post_detail', args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_register_page(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)


# ===========================================================================
#  VIEW - XÁC THỰC
# ===========================================================================

@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class AuthViewTests(TestCase):
    """Đăng ký, đăng nhập và đăng xuất."""

    def setUp(self):
        self.client = Client()

    def test_register_creates_account(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Nguyễn Văn Hào',
            'username': 'hao.nguyen',
            'email': 'hao@gmail.com',
            'faculty': '',
            'student_id': '',
            'password1': 'MatKhau123',
            'password2': 'MatKhau123',
            'agree': True,
        })
        # Đăng ký thành công sẽ tự đăng nhập và chuyển trang
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(User.objects.filter(username='hao.nguyen').exists())

    def test_register_rejects_weak_password(self):
        response = self.client.post(reverse('register'), {
            'first_name': 'Test',
            'username': 'testuser',
            'email': 'test@gmail.com',
            'faculty': '',
            'student_id': '',
            'password1': 'abc',
            'password2': 'abc',
            'agree': True,
        })
        self.assertEqual(response.status_code, 200)  # hiển thị lại form
        self.assertFalse(User.objects.filter(username='testuser').exists())

    def test_register_empty_password_does_not_crash(self):
        """Bản cũ gây IndexError khi mật khẩu rỗng."""
        response = self.client.post(reverse('register'), {
            'first_name': 'Test',
            'username': 'testuser',
            'email': 'test@gmail.com',
            'faculty': '',
            'student_id': '',
            'password1': '',
            'password2': '',
            'agree': True,
        })
        self.assertEqual(response.status_code, 200)

    def test_login_with_username(self):
        create_user('sinhvien', 'MatKhau123')
        response = self.client.post(reverse('login'), {
            'username': 'sinhvien',
            'password': 'MatKhau123',
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_with_email(self):
        user = create_user('sinhvien', 'MatKhau123')
        user.email = 'sv@gmail.com'
        user.save()

        response = self.client.post(reverse('login'), {
            'username': 'sv@gmail.com',
            'password': 'MatKhau123',
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_wrong_password(self):
        create_user('sinhvien', 'MatKhau123')
        response = self.client.post(reverse('login'), {
            'username': 'sinhvien',
            'password': 'SaiMatKhau',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_requires_post(self):
        user = create_user('sinhvien')
        self.client.force_login(user)
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)

    def test_logout_via_post(self):
        user = create_user('sinhvien')
        self.client.force_login(user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)


# ===========================================================================
#  VIEW - PHẢI ĐĂNG NHẬP
# ===========================================================================

@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class LoginRequiredTests(TestCase):
    """Các trang cần đăng nhập phải chuyển hướng đúng."""

    def setUp(self):
        self.client = Client()

    def test_create_post_requires_login(self):
        response = self.client.get(reverse('create_post'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_my_posts_requires_login(self):
        self.assertEqual(self.client.get(reverse('my_posts')).status_code, 302)

    def test_wishlist_requires_login(self):
        self.assertEqual(self.client.get(reverse('wishlist')).status_code, 302)

    def test_edit_profile_requires_login(self):
        self.assertEqual(self.client.get(reverse('edit_profile')).status_code, 302)


# ===========================================================================
#  VIEW - QUẢN LÝ BÀI ĐĂNG
# ===========================================================================

@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class PostManagementTests(TestCase):
    """Tạo, sửa, xoá bài đăng và đánh dấu bán."""

    def setUp(self):
        self.client = Client()
        self.user = create_user('owner', 'MatKhau123')
        self.other = create_user('other', 'MatKhau123')
        self.client.force_login(self.user)

    def test_create_post(self):
        response = self.client.post(reverse('create_post'), {
            'title': 'Giáo trình Tin học văn phòng',
            'description': 'Sách mới, còn nguyên bìa.',
            'price': '40000',
            'condition': Post.Condition.NEW,
            'course_code': 'IT001',
            'faculty': 'Khoa CNTT',
            'location': 'Khu 3',
            'category': '',
        })
        # Sau khi đăng tin thành công, chuyển tới trang chi tiết sản phẩm vừa tạo
        post = Post.objects.get(title='Giáo trình Tin học văn phòng')
        self.assertRedirects(response, post.get_absolute_url())
        self.assertEqual(post.seller, self.user)

    def test_create_post_free_sets_flag(self):
        self.client.post(reverse('create_post'), {
            'title': 'Sách tặng miễn phí',
            'description': 'Tặng cho đàn em.',
            'price': '0',
            'condition': Post.Condition.GOOD,
            'category': '',
        })
        post = Post.objects.get(title='Sách tặng miễn phí')
        self.assertTrue(post.is_free)

    def test_create_post_sets_owner(self):
        self.client.post(reverse('create_post'), {
            'title': 'Bài của tôi',
            'description': 'Mô tả',
            'price': '10000',
            'condition': Post.Condition.GOOD,
            'category': '',
        })
        self.assertEqual(Post.objects.get(title='Bài của tôi').seller, self.user)

    def test_edit_own_post(self):
        post = create_post(self.user, title='Tiêu đề cũ')
        self.client.post(reverse('edit_post', args=[post.pk]), {
            'title': 'Tiêu đề mới',
            'description': 'Mô tả mới',
            'price': '70000',
            'condition': Post.Condition.GOOD,
            'category': '',
        })
        post.refresh_from_db()
        self.assertEqual(post.title, 'Tiêu đề mới')

    def test_cannot_edit_others_post(self):
        post = create_post(self.other, title='Bài của người khác')
        response = self.client.get(reverse('edit_post', args=[post.pk]))
        self.assertEqual(response.status_code, 302)

    def test_delete_own_post(self):
        post = create_post(self.user, title='Bài cần xoá')
        self.client.post(reverse('delete_post', args=[post.pk]))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_cannot_delete_others_post(self):
        post = create_post(self.other, title='Bài của người khác')
        self.client.post(reverse('delete_post', args=[post.pk]))
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_toggle_sold_via_post(self):
        post = create_post(self.user)
        self.client.post(reverse('toggle_sold', args=[post.pk]))
        post.refresh_from_db()
        self.assertTrue(post.is_sold)

        self.client.post(reverse('toggle_sold', args=[post.pk]))
        post.refresh_from_db()
        self.assertFalse(post.is_sold)

    def test_toggle_sold_rejects_get(self):
        """Trạng thái không được đổi bằng GET (chống CSRF)."""
        post = create_post(self.user)
        response = self.client.get(reverse('toggle_sold', args=[post.pk]))
        self.assertEqual(response.status_code, 405)
        post.refresh_from_db()
        self.assertFalse(post.is_sold)

    def test_cannot_toggle_others_post(self):
        post = create_post(self.other)
        self.client.post(reverse('toggle_sold', args=[post.pk]))
        post.refresh_from_db()
        self.assertFalse(post.is_sold)

    def test_my_posts_list(self):
        create_post(self.user, title='Bài của tôi')
        response = self.client.get(reverse('my_posts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bài của tôi')

    def test_my_posts_excludes_others(self):
        create_post(self.other, title='Bài của người khác')
        response = self.client.get(reverse('my_posts'))
        self.assertNotContains(response, 'Bài của người khác')


# ===========================================================================
#  VIEW - TƯƠNG TÁC
# ===========================================================================

@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class InteractionTests(TestCase):
    """Yêu thích, bình luận, đánh giá và báo cáo."""

    def setUp(self):
        self.client = Client()
        self.seller = create_user('seller', 'MatKhau123')
        self.buyer = create_user('buyer', 'MatKhau123')
        self.post = create_post(self.seller, title='Sách hay')

    def test_toggle_favorite_via_post(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse('toggle_favorite', args=[self.post.pk]))
        self.assertTrue(Favorite.objects.filter(user=self.buyer, post=self.post).exists())

        self.client.post(reverse('toggle_favorite', args=[self.post.pk]))
        self.assertFalse(Favorite.objects.filter(user=self.buyer, post=self.post).exists())

    def test_toggle_favorite_rejects_get(self):
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('toggle_favorite', args=[self.post.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertFalse(Favorite.objects.filter(user=self.buyer, post=self.post).exists())

    def test_toggle_favorite_ajax_returns_json(self):
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse('toggle_favorite', args=[self.post.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['favorited'])
        self.assertEqual(response.json()['count'], 1)

    def test_wishlist_page(self):
        Favorite.objects.create(user=self.buyer, post=self.post)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sách hay')

    def test_add_comment(self):
        self.client.force_login(self.buyer)
        self.client.post(
            reverse('add_comment', args=[self.post.pk]),
            {'content': 'Sách này còn không bạn?'}
        )
        self.assertTrue(
            Comment.objects.filter(post=self.post, author=self.buyer).exists()
        )

    def test_add_comment_requires_login(self):
        self.client.post(
            reverse('add_comment', args=[self.post.pk]),
            {'content': 'Không đăng nhập'}
        )
        self.assertEqual(Comment.objects.count(), 0)

    def test_add_empty_comment_rejected(self):
        self.client.force_login(self.buyer)
        self.client.post(
            reverse('add_comment', args=[self.post.pk]),
            {'content': '   '}
        )
        self.assertEqual(Comment.objects.count(), 0)

    def test_reply_to_comment(self):
        parent = Comment.objects.create(
            post=self.post, author=self.buyer, content='Còn hàng không?'
        )
        self.client.force_login(self.seller)
        self.client.post(
            reverse('add_comment', args=[self.post.pk]),
            {'content': 'Dạ còn nhé!', 'parent_id': parent.pk}
        )
        self.assertTrue(parent.replies.exists())

    def test_delete_own_comment(self):
        comment = Comment.objects.create(
            post=self.post, author=self.buyer, content='Xoá tôi'
        )
        self.client.force_login(self.buyer)
        self.client.post(reverse('delete_comment', args=[comment.pk]))
        self.assertEqual(Comment.objects.count(), 0)

    def test_seller_can_delete_comment_on_their_post(self):
        comment = Comment.objects.create(
            post=self.post, author=self.buyer, content='Spam'
        )
        self.client.force_login(self.seller)
        self.client.post(reverse('delete_comment', args=[comment.pk]))
        self.assertEqual(Comment.objects.count(), 0)

    def test_cannot_delete_others_comment(self):
        third = create_user('third')
        comment = Comment.objects.create(
            post=self.post, author=third, content='Không được xoá'
        )
        self.client.force_login(self.buyer)
        self.client.post(reverse('delete_comment', args=[comment.pk]))
        self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())

    def test_add_review(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse('add_review', args=['seller']), {
            'rating': 5,
            'content': 'Giao dịch tuyệt vời!',
        })
        review = Review.objects.filter(seller=self.seller, reviewer=self.buyer).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.rating, 5)

    def test_cannot_review_self(self):
        self.client.force_login(self.seller)
        self.client.post(reverse('add_review', args=['seller']), {
            'rating': 5, 'content': 'Tự đánh giá',
        })
        self.assertEqual(Review.objects.filter(seller=self.seller).count(), 0)

    def test_cannot_review_twice(self):
        Review.objects.create(seller=self.seller, reviewer=self.buyer, rating=4)
        self.client.force_login(self.buyer)
        self.client.post(reverse('add_review', args=['seller']), {
            'rating': 5, 'content': 'Lần hai',
        })
        self.assertEqual(
            Review.objects.filter(seller=self.seller, reviewer=self.buyer).count(), 1
        )

    def test_report_post(self):
        self.client.force_login(self.buyer)
        response = self.client.post(reverse('report_post', args=[self.post.pk]), {
            'reason': Report.Reason.SPAM,
            'detail': 'Quảng cáo lặp lại',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Report.objects.filter(post=self.post, reporter=self.buyer).exists())

    def test_cannot_report_own_post(self):
        self.client.force_login(self.seller)
        self.client.post(reverse('report_post', args=[self.post.pk]), {
            'reason': Report.Reason.SPAM, 'detail': '',
        })
        self.assertEqual(Report.objects.count(), 0)


# ===========================================================================
#  VIEW - HỒ SƠ & MẬT KHẨU
# ===========================================================================

@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class ProfileTests(TestCase):
    """Chỉnh sửa hồ sơ và đổi mật khẩu."""

    def setUp(self):
        self.client = Client()
        self.user = create_user('sinhvien', 'MatKhau123')

    def test_edit_profile(self):
        self.client.force_login(self.user)
        self.client.post(reverse('edit_profile'), {
            'first_name': 'Văn Hào',
            'last_name': 'Nguyễn',
            'email': 'hao@gmail.com',
            'student_id': '24CT100001',
            'faculty': 'Khoa Kiến trúc',
            'phone': '0901234567',
            'bio': 'Sinh viên Kiến trúc',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Văn Hào')
        self.assertEqual(self.user.profile.faculty, 'Khoa Kiến trúc')

    def test_change_password(self):
        self.client.force_login(self.user)
        self.client.post(reverse('change_password'), {
            'old_password': 'MatKhau123',
            'new_password1': 'MatKhauMoi456',
            'new_password2': 'MatKhauMoi456',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('MatKhauMoi456'))

    def test_change_password_wrong_old(self):
        self.client.force_login(self.user)
        self.client.post(reverse('change_password'), {
            'old_password': 'SaiMatKhau',
            'new_password1': 'MatKhauMoi456',
            'new_password2': 'MatKhauMoi456',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('MatKhau123'))


# ===========================================================================
#  LUỒNG NGƯỜI DÙNG THỰC TẾ
# ===========================================================================

@override_settings(PASSWORD_HASHERS=PASSWORD_HASHERS)
class UserJourneyTests(TestCase):
    """Mô phỏng hành trình thực tế của người dùng."""

    def test_full_journey(self):
        """Đăng ký → đăng tin → tìm kiếm → yêu thích → bình luận."""
        client = Client()

        # 1. Đăng ký
        client.post(reverse('register'), {
            'first_name': 'Nguyễn Văn Hào',
            'username': 'hao.nguyen',
            'email': 'hao@gmail.com',
            'faculty': 'Khoa Kiến trúc',
            'student_id': '24CT100001',
            'password1': 'MatKhau123',
            'password2': 'MatKhau123',
            'agree': True,
        })
        self.assertIn('_auth_user_id', client.session)

        # 2. Đăng tin
        client.post(reverse('create_post'), {
            'title': 'Giáo trình Đồ hoạ kỹ thuật',
            'description': 'Sách mới 95%, có đầy đủ slide.',
            'price': '75000',
            'condition': Post.Condition.LIKE_NEW,
            'course_code': 'GRAPH101',
            'faculty': 'Khoa Kiến trúc',
            'location': 'Khu 3',
            'category': '',
        })
        post = Post.objects.get(title='Giáo trình Đồ hoạ kỹ thuật')
        self.assertEqual(post.seller.username, 'hao.nguyen')

        # 3. Tìm kiếm
        response = client.get(reverse('home'), {'q': 'Đồ hoạ'})
        self.assertContains(response, 'Giáo trình Đồ hoạ kỹ thuật')

        # 4. Xem chi tiết
        response = client.get(reverse('post_detail', args=[post.pk]))
        self.assertEqual(response.status_code, 200)

        # 5. Đăng xuất rồi đăng nhập lại bằng email
        client.post(reverse('logout'))
        client.post(reverse('login'), {
            'username': 'hao@gmail.com',
            'password': 'MatKhau123',
        })
        self.assertIn('_auth_user_id', client.session)

        # 6. Người khác yêu thích và bình luận
        other = create_user('nguoidung2', 'MatKhau123')
        client.force_login(other)
        client.post(reverse('toggle_favorite', args=[post.pk]))
        self.assertTrue(Favorite.objects.filter(user=other, post=post).exists())

        client.post(reverse('add_comment', args=[post.pk]), {
            'content': 'Sách này còn slide không bạn?'
        })
        self.assertEqual(post.comments.count(), 1)

        # 7. Người bán trả lời
        client.force_login(post.seller)
        parent = post.comments.first()
        client.post(reverse('add_comment', args=[post.pk]), {
            'content': 'Dạ có đầy đủ nhé!',
            'parent_id': parent.pk,
        })
        self.assertEqual(parent.replies.count(), 1)

        # 8. Đánh giá uy tín
        client.force_login(other)
        client.post(reverse('add_review', args=['hao.nguyen']), {
            'rating': 5,
            'content': 'Giao dịch nhanh và dễ thương!',
        })
        review = Review.objects.get(seller=post.seller, reviewer=other)
        self.assertEqual(review.rating, 5)

        # 9. Người bán đánh dấu đã bán
        client.force_login(post.seller)
        client.post(reverse('toggle_sold', args=[post.pk]))
        post.refresh_from_db()
        self.assertTrue(post.is_sold)

        # 10. Bài đã bán không còn hiện trên trang chủ
        client.force_login(other)
        response = client.get(reverse('home'))
        self.assertNotContains(response, 'Giáo trình Đồ hoạ kỹ thuật')


# ===========================================================================
#  ĐẶT MUA - ĐƠN HÀNG
# ===========================================================================

class OrderModelTests(TestCase):
    """Kiểm thử model Order."""

    def setUp(self):
        self.seller = create_user('nguoiban')
        self.buyer = create_user('nguoimua')
        self.post = Post.objects.create(
            title='Bàn học gỗ chân sắt', price=250000, seller=self.seller,
        )

    def test_order_default_is_pending(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
        )
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertTrue(order.is_open)

    def test_price_snapshot_survives_post_price_edit(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            price_snapshot=250000,
        )
        self.post.price = 999000
        self.post.save()
        order.refresh_from_db()
        self.assertEqual(order.price_snapshot, 250000)

    def test_price_display_free(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller, price_snapshot=0,
        )
        self.assertEqual(order.price_display, 'Miễn phí')

    def test_price_display_formats_thousands(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            price_snapshot=1250000,
        )
        self.assertEqual(order.price_display, '1.250.000đ')

    def test_is_open_false_after_rejected(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.REJECTED,
        )
        self.assertFalse(order.is_open)

    def test_indexes_created_for_lookup(self):
        """Truy vấn đơn hàng theo người mua/người bán cần index."""
        index_names = {idx.name for idx in Order._meta.indexes}
        self.assertIn('idx_order_buyer_status', index_names)
        self.assertIn('idx_order_seller_status', index_names)

    def test_rejected_order_allows_new_request(self):
        """Sau khi bị từ chối, người mua được gửi yêu cầu lại."""
        Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.REJECTED,
        )
        order2 = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        self.assertEqual(order2.status, Order.Status.PENDING)


class OrderFormTests(TestCase):
    """Kiểm thử OrderForm."""

    def setUp(self):
        from .forms import OrderForm
        self.FormClass = OrderForm

    def test_valid_with_phone(self):
        form = self.FormClass(data={'contact': '0901234567', 'message': 'Xin chao'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_with_email(self):
        form = self.FormClass(data={'contact': 'ban@gmail.com'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_contact_without_phone_or_email_rejected(self):
        form = self.FormClass(data={'contact': 'gap nhau o san truong'})
        self.assertFalse(form.is_valid())
        self.assertIn('contact', form.errors)

    def test_blank_contact_allowed(self):
        form = self.FormClass(data={})
        self.assertTrue(form.is_valid(), form.errors)


class OrderFlowTests(TestCase):
    """Kiểm thử toàn bộ luồng đặt mua."""

    def setUp(self):
        self.seller = create_user('nguoiban')
        self.buyer = create_user('nguoimua')
        self.client_buyer = Client()
        self.client_buyer.force_login(self.buyer)
        self.post = Post.objects.create(
            title='Máy tính Casio fx-991ES Plus', price=450000, seller=self.seller,
        )

    def test_buy_post_requires_login(self):
        response = self.client.get(reverse('buy_post', args=[self.post.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dang-nhap/', response.url)

    def test_buy_post_get_shows_form(self):
        response = self.client_buyer.get(reverse('buy_post', args=[self.post.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Đặt mua')

    def test_buy_own_post_rejected(self):
        self.client_buyer.force_login(self.seller)
        response = self.client_buyer.get(reverse('buy_post', args=[self.post.pk]))
        self.assertRedirects(response, self.post.get_absolute_url())

    def test_buy_sold_post_rejected(self):
        self.post.status = Post.Status.SOLD
        self.post.is_sold = True
        self.post.save()
        response = self.client_buyer.get(reverse('buy_post', args=[self.post.pk]))
        self.assertRedirects(response, self.post.get_absolute_url())

    def test_create_order_success(self):
        response = self.client_buyer.post(reverse('buy_post', args=[self.post.pk]), {
            'message': 'Mình muốn mua, giao dịch tối nay được không?',
            'contact': '0901234567',
        })
        self.assertRedirects(response, reverse('my_orders'))
        order = Order.objects.get()
        self.assertEqual(order.buyer, self.buyer)
        self.assertEqual(order.seller, self.seller)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.price_snapshot, 450000)

    def test_duplicate_order_redirects_to_list(self):
        Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        response = self.client_buyer.post(reverse('buy_post', args=[self.post.pk]), {
            'contact': '0901234567',
        })
        self.assertRedirects(response, reverse('my_orders'))
        self.assertEqual(Order.objects.count(), 1)

    def test_seller_accept_order(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        self.client_buyer.force_login(self.seller)
        response = self.client_buyer.post(reverse('accept_order', args=[order.pk]))
        self.assertRedirects(response, reverse('order_detail', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)

    def test_buyer_cannot_accept_own_order(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        response = self.client_buyer.post(reverse('accept_order', args=[order.pk]))
        self.assertRedirects(response, reverse('my_orders'))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_buyer_cannot_reject_own_order(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        response = self.client_buyer.post(reverse('reject_order', args=[order.pk]))
        self.assertRedirects(response, reverse('my_orders'))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_seller_reject_order_saves_note(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        self.client_buyer.force_login(self.seller)
        self.client_buyer.post(reverse('reject_order', args=[order.pk]), {
            'seller_note': 'Xin lỗi, sản phẩm hỏng rồi.',
        })
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REJECTED)
        self.assertEqual(order.seller_note, 'Xin lỗi, sản phẩm hỏng rồi.')
        # Sản phẩm vẫn còn hiển thị
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_available)

    def test_complete_order_marks_post_sold(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.CONFIRMED,
        )
        self.client_buyer.post(reverse('complete_order', args=[order.pk]))
        order.refresh_from_db()
        self.post.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertEqual(self.post.status, Post.Status.SOLD)
        self.assertTrue(self.post.is_sold)

    def test_complete_rejected_order_not_allowed(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.REJECTED,
        )
        self.client_buyer.post(reverse('complete_order', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REJECTED)

    def test_buyer_cancel_order(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        response = self.client_buyer.post(reverse('cancel_order', args=[order.pk]))
        self.assertRedirects(response, reverse('my_orders'))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_state_change_views_reject_get(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        for name in ('accept_order', 'reject_order', 'complete_order', 'cancel_order'):
            response = self.client_buyer.get(reverse(name, args=[order.pk]))
            self.assertEqual(response.status_code, 405, name)

    def test_order_detail_only_for_buyer_and_seller(self):
        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        self.assertEqual(
            self.client_buyer.get(
                reverse('order_detail', args=[order.pk])
            ).status_code, 200
        )
        self.client_buyer.force_login(self.seller)
        self.assertEqual(
            self.client_buyer.get(
                reverse('order_detail', args=[order.pk])
            ).status_code, 200
        )
        self.client_buyer.force_login(create_user('nguoila'))
        response = self.client_buyer.get(reverse('order_detail', args=[order.pk]))
        self.assertRedirects(response, reverse('my_orders'))

    def test_my_orders_separates_buying_and_selling(self):
        Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        response = self.client_buyer.get(reverse('my_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['buying']), 1)
        self.assertEqual(len(response.context['selling']), 0)
        self.assertEqual(response.context['pending_sell_count'], 0)

        self.client_buyer.force_login(self.seller)
        response = self.client_buyer.get(reverse('my_orders'))
        self.assertEqual(len(response.context['buying']), 0)
        self.assertEqual(len(response.context['selling']), 1)
        self.assertEqual(response.context['pending_sell_count'], 1)

    def test_post_detail_shows_buy_button_then_order_link(self):
        response = self.client_buyer.get(self.post.get_absolute_url())
        self.assertContains(response, reverse('buy_post', args=[self.post.pk]))

        order = Order.objects.create(
            post=self.post, buyer=self.buyer, seller=self.seller,
            status=Order.Status.PENDING,
        )
        response = self.client_buyer.get(self.post.get_absolute_url())
        self.assertContains(response, reverse('order_detail', args=[order.pk]))


class OrderJourneyTests(TestCase):
    """Kịch bản đầu-cuối: mua → xác nhận → hoàn tất → sản phẩm ẩn khỏi sàn."""

    def test_full_purchase_journey(self):
        seller = create_user('nguoiban')
        buyer = create_user('nguoimua')
        client = Client()

        post = Post.objects.create(
            title='Giáo trình Giải tích cao cấp', price=90000, seller=seller,
        )

        # 1. Người mua đặt hàng
        client.force_login(buyer)
        client.post(reverse('buy_post', args=[post.pk]), {
            'message': 'Còn hàng không ạ?',
            'contact': '0987654321',
        })
        order = Order.objects.get()
        self.assertEqual(order.status, Order.Status.PENDING)

        # 2. Người bán xác nhận
        client.force_login(seller)
        client.post(reverse('accept_order', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)

        # 3. Hoàn tất giao dịch
        client.post(reverse('complete_order', args=[order.pk]))
        order.refresh_from_db()
        post.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertTrue(post.is_sold)

        # 4. Sản phẩm không còn xuất hiện trên trang chủ
        client.force_login(create_user('nguoikhac'))
        response = client.get(reverse('home'))
        self.assertNotContains(response, 'Giải tích cao cấp')
