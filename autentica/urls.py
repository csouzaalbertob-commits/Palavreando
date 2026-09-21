from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .models import PerfilProfessor

app_name = 'autentica'

urlpatterns = [
    # Cadastro e Autenticação
    path('cadastro/', views.cadastro_professor, name='cadastro_professor'),
    path('login/', auth_views.LoginView.as_view(template_name='autentica/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='autentica:login'), name='logout'),
    path('dash/', views.dashboard, name='dashboard'),
    path('perfil/editar/', views.editar_perfil_professor, name='editar_perfil'),

    path('alterar-senha/', auth_views.PasswordChangeView.as_view(
        template_name='autentica/alterar_senha.html',
        success_url='/autentica/perfil/editar/'
    ), name='password_change'),
]