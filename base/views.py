from django.shortcuts import render

app_name = 'base'

def landing(request):
    return render(request, 'base/base.html')

def home(request):
    return render(request, 'base/index.html')

def sobre(request):
    return render(request, 'base/sobre.html')

