from django.shortcuts import render
from django.contrib.auth.decorators import login_required

app_name = 'base'

@login_required
def landing(request):
    return render(request, 'base/base.html')

@login_required
def home(request):
    return render(request, 'base/index.html')

def sobre(request):
    return render(request, 'base/sobre.html')

