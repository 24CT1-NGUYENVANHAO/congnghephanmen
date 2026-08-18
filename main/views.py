from django.http import HttpResponse

def home(request):
    html_content = """
    <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
        <img src="https://static.djangoproject.com/img/logos/django-logo-positive.png" alt="Django Logo" width="250" style="margin-bottom: 20px;">
        <h1 style="color: #0c4b33;">Chào bạn khóa 24CT đến với học phần CNPM-DAU</h1>
    </div>
    """
    return HttpResponse(html_content)