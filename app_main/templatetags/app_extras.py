"""Bộ lọc (filter) và thẻ (tag) tùy chỉnh cho template."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def price_display(value):
    """Định dạng giá theo kiểu Việt Nam: 45000 -> 45.000đ"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return value
    if number == 0:
        return "Miễn phí"
    return f"{number:,}".replace(",", ".") + "đ"


@register.filter
def stars(rating):
    """Trả về chuỗi 5 ngôi sao (vàng/Trắng) theo điểm đánh giá."""
    try:
        value = int(rating or 0)
    except (TypeError, ValueError):
        value = 0
    value = max(0, min(5, value))
    filled = "★" * value
    empty = "☆" * (5 - value)
    return mark_safe(f'<span class="text-amber-400">{filled}</span><span class="text-slate-300">{empty}</span>')


@register.filter
def get_item(dictionary, key):
    """dict[key] an toàn trong template: trả về '' nếu thiếu."""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return ''


@register.simple_tag(takes_context=True)
def querystring(context, **kwargs):
    """
    Giữ nguyên tham số GET hiện tại khi thay đổi một vài tham số.

    Dùng cho phân trang & sắp xếp: <a href="?{% querystring page=2 %}"> để không mất bộ lọc.
    Trả về chuỗi KHÔNG bao gồm dấu '?' đầu tiên (template đã có sẵn).
    """
    request = context.get('request')
    params = request.GET.copy() if request else {}

    for key, value in kwargs.items():
        if value is None or value == '':
            params.pop(key, None)
        else:
            params[key] = value

    if 'page' not in kwargs:
        params.pop('page', None)

    return params.urlencode()


@register.filter
def add_class(field, css):
    """Gắn thêm class CSS vào field của Django form."""
    try:
        return field.as_widget(attrs={'class': f"{field.field.widget.attrs.get('class', '')} {css}".strip()})
    except AttributeError:
        return field


@register.simple_tag
def field_icon(name):
    """Trả về icon SVG theo tên, dùng để tái sử dụng icon trong template."""
    icons = {
        'book': 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
        'search': 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
        'tag': 'M7 7h10M7 7L3 11v8h8l4-4m0 0l4-4m-4 4V3',
        'user': 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
        'location': 'M17.657 16.657L13.414 20.9a2 2 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0zM15 11a3 3 0 11-6 0 3 3 0 016 0z',
        'clock': 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
        'heart': 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
    }
    path = icons.get(name, icons['tag'])
    return mark_safe(
        f'<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" '
        f'viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" '
        f'stroke-width="2" d="{path}"/></svg>'
    )
