# alunos/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'alunos'

urlpatterns = [     
    path('', views.lista_alunos, name='lista_alunos'),
    path('aluno/novo/', views.cadastrar_aluno, name='cadastrar_aluno'),
    path('aluno/<int:aluno_id>/carteirinha/', views.carteirinha, name='carteirinha'),
    path('salvar-resultado/', views.salvar_resultado, name='salvar_resultado'),
    path('api/ficha/<int:aluno_id>/', views.api_ficha_aluno, name='api_ficha_aluno'),
]