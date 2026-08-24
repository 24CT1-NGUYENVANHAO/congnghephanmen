from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse

def home(request):
    return HttpResponse("""
        <div style='text-align: center; margin-top: 15%; font-family: Arial, sans-serif;'>
            <h1 style='color: #0b4f30; font-size: 55px; font-weight: bold; margin-bottom: 30px;'>django</h1>
            <h2 style='color: #0b4f30; font-size: 32px; font-weight: bold;'>Chào bạn khóa 24CT đến với học phần CNPM-DAU</h2>
        </div>
    """)