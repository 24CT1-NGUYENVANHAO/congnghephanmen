/* ==========================================================================
   SáchGóc Uni — JavaScript chính
   Xử lý menu, tìm kiếm, yêu thích AJAX, xác nhận hành động.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

    // ----- Đóng menu khi click ra ngoài -----
    document.addEventListener('click', function (event) {
        const userMenu = document.getElementById('user-menu');
        const dropdown = document.getElementById('user-menu-dropdown');

        if (userMenu && dropdown && !userMenu.contains(event.target)) {
            dropdown.classList.add('hidden');
        }
    });

    // ----- Tự ẩn thông báo sau 6 giây -----
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert, index) {
        setTimeout(function () {
            if (index === 0) {
                alert.style.transition = 'opacity 0.4s, transform 0.4s';
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-10px)';
                setTimeout(() => alert.remove(), 400);
            }
        }, 6000);
    });

    // ----- Tự tắt thanh lọc thu gọn trên màn hình nhỏ -----
    const filterPanel = document.getElementById('filter-panel');
    const filterToggle = document.getElementById('filter-toggle');
    if (filterToggle && filterPanel) {
        if (window.innerWidth < 1024) filterPanel.classList.add('hidden');
        filterToggle.addEventListener('click', function () {
            filterPanel.classList.toggle('hidden');
        });
    }

    // ----- Thư viện ảnh trang chi tiết -----
    const mainImage = document.getElementById('main-image');
    const thumbs = document.querySelectorAll('[data-gallery-thumb]');

    thumbs.forEach(function (thumb) {
        thumb.addEventListener('click', function () {
            if (mainImage && thumb.dataset.src) {
                mainImage.style.opacity = '0';
                setTimeout(function () {
                    mainImage.src = thumb.dataset.src;
                    mainImage.alt = thumb.dataset.alt || '';
                    mainImage.style.opacity = '1';
                }, 150);
            }
            thumbs.forEach(t => t.classList.remove('ring-2', 'ring-indigo-500'));
            thumb.classList.add('ring-2', 'ring-indigo-500');
        });
    });

    // ----- Yêu thích bằng AJAX (không tải lại trang) -----
    const favButton = document.getElementById('favorite-button');
    if (favButton) {
        favButton.addEventListener('click', function (event) {
            event.preventDefault();

            const form = favButton.closest('form');
            const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;
            const url = favButton.dataset.url;

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(response => response.json())
                .then(data => {
                    // Cập nhật biểu tượng
                    favButton.querySelector('[data-icon]').textContent =
                        data.favorited ? '♥' : '♡';
                    favButton.classList.toggle('text-rose-500', data.favorited);
                    favButton.classList.toggle('text-slate-400', !data.favorited);

                    // Cập nhật số lượng
                    const counter = document.getElementById('favorite-count');
                    if (counter) counter.textContent = data.count;

                    showToast(data.message);
                })
                .catch(() => {
                    window.location.reload();
                });
        });
    }

    // ----- Mật khẩu: hiện/ẩn -----
    document.querySelectorAll('[data-toggle-password]').forEach(function (button) {
        button.addEventListener('click', function () {
            const input = document.getElementById(button.dataset.target);
            if (!input) return;
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            button.textContent = isPassword ? '🙈' : '👁️';
        });
    });

    // ----- Kiểm tra mật khẩu khớp ở form đăng ký -----
    const pass1 = document.getElementById('id_password1');
    const pass2 = document.getElementById('id_password2');
    if (pass1 && pass2) {
        const hint = document.getElementById('password-match-hint');
        pass2.addEventListener('input', function () {
            if (!hint) return;
            if (pass2.value === '') {
                hint.textContent = '';
            } else if (pass1.value === pass2.value) {
                hint.textContent = '✅ Hai mật khẩu khớp';
                hint.style.color = '#059669';
            } else {
                hint.textContent = '❌ Hai mật khẩu không khớp';
                hint.style.color = '#dc2626';
            }
        });
    }

    // ----- Chống gửi form nhiều lần -----
    document.querySelectorAll('form[data-once]').forEach(function (form) {
        form.addEventListener('submit', function () {
            const button = form.querySelector('button[type=submit]');
            if (button) {
                setTimeout(function () {
                    button.disabled = true;
                    button.textContent = 'Đang xử lý...';
                }, 0);
            }
        });
    });

    // ----- Thanh tiến độ cuộn trang -----
    const progress = document.getElementById('scroll-progress');
    if (progress) {
        window.addEventListener('scroll', function () {
            const scrollTop = window.pageYOffset;
            const height = document.documentElement.scrollHeight - window.innerHeight;
            const progressPercent = height > 0 ? (scrollTop / height) * 100 : 0;
            progress.style.width = progressPercent + '%';
        }, { passive: true });
    }
});

/* ----- Menu tài khoản ----- */
function toggleUserMenu() {
    const dropdown = document.getElementById('user-menu-dropdown');
    const isHidden = dropdown.classList.contains('hidden');
    dropdown.classList.toggle('hidden');
    document.querySelector('#user-menu button').setAttribute('aria-expanded', isHidden);
}

/* ----- Menu mobile ----- */
function toggleMobileMenu() {
    document.getElementById('mobile-menu').classList.toggle('hidden');
}

/* ----- Xác nhận trước khi thực hiện ----- */
function confirmAction(message) {
    return window.confirm(message);
}

/* ----- Hiển thị thông báo nổi (toast) ----- */
function showToast(message) {
    // Xoá toast cũ nếu có
    const existing = document.getElementById('toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'toast';
    toast.textContent = message;
    toast.style.cssText = `
        position:fixed;bottom:1.5rem;left:50%;transform:translateX(-50%);
        background:var(--slate-900);color:#fff;padding:0.75rem 1.5rem;
        border-radius:0.75rem;font-size:0.875rem;font-weight:500;
        box-shadow:var(--shadow-lg);z-index:9999;
        animation:toastIn 0.3s ease-out;max-width:90vw;
    `;
    document.body.appendChild(toast);

    setTimeout(function () {
        toast.style.transition = 'opacity 0.3s, transform 0.3s';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

/* ----- Thêm animation cho toast ----- */
const style = document.createElement('style');
style.textContent = `
    @keyframes toastIn {
        from { opacity:0; transform:translateX(-50%) translateY(20px); }
        to   { opacity:1; transform:translateX(-50%) translateY(0); }
    }
`;
document.head.appendChild(style);
