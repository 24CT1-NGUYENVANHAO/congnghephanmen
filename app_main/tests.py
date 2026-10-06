"""
Bộ kiểm thử tự động (Unit Tests) cho ứng dụng SáchGóc Uni.
Kiểm tra tính đúng đắn của Models, Views, và Định tuyến URL.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Category, Post, Comment

class ModelTests(TestCase):
    """Kiểm tra hoạt động của các Model."""

    def setUp(self):
        self.user = User.objects.create_user(username='teststudent', password='Password123')
        self.category = Category.objects.create(name='Giáo trình CNTT', slug='giao-trinh-cntt')

    def test_category_creation(self):
        self.assertEqual(str(self.category), 'Giáo trình CNTT')

    def test_post_creation(self):
        post = Post.objects.create(
            title='Giáo trình Python Cơ bản',
            seller=self.user,
            category=self.category,
            price=0,
            is_free=True,
            condition='LIKE_NEW',
            description='Sách tặng miễn phí cho tân sinh viên'
        )
        self.assertEqual(post.title, 'Giáo trình Python Cơ bản')
        self.assertTrue(post.is_free)
        self.assertEqual(post.seller.username, 'teststudent')

class ViewTests(TestCase):
    """Kiểm tra phản hồi của các Views và HTTP status codes."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='teststudent', password='Password123')
        self.category = Category.objects.create(name='Dụng cụ học tập', slug='dung-cu-hoc-tap')
        self.post = Post.objects.create(
            title='Thước kẻ vẽ kỹ thuật A3',
            seller=self.user,
            category=self.category,
            price=20000,
            description='Thước vẽ kiến trúc'
        )

    def test_home_page_status(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Thước kẻ vẽ kỹ thuật A3')

    def test_post_detail_page_status(self):
        response = self.client.get(reverse('post_detail', args=[self.post.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Thước vẽ kiến trúc')
