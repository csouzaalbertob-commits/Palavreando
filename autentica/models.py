# alunos/models.py
from django.db import models
from django.contrib.auth.models import User
import qrcode
from io import BytesIO
from django.core.files import File

# 1. MODELO DO PROFESSOR (Perfil Estendido)
class PerfilProfessor(models.Model):
    # Conecta este perfil a um usuário nativo do Django
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    
    # Campos extras específicos do professor
    matricula = models.CharField("Matrícula", max_length=20, unique=True)
    telefone = models.CharField("Telefone/WhatsApp", max_length=20, blank=True, null=True)
    disciplina = models.CharField("Disciplina / Área de Atuação", max_length=100, blank=True, null=True)
    escola = models.CharField(max_length=150, blank=True)
    foto = models.ImageField(upload_to='professores/', blank=True, null=True)
    
    def __str__(self):
        return f"Prof. {self.usuario.get_full_name() or self.usuario.username}"

