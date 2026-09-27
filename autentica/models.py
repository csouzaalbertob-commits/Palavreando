# alunos/models.py
from django.db import models
from django.contrib.auth.models import User
import qrcode
from io import BytesIO
from django.core.files import File

class PerfilProfessor(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    matricula = models.CharField(max_length=20, unique=True, verbose_name="Matrícula")
    telefone = models.CharField(max_length=20, blank=True, null=True)
    disciplina = models.CharField(max_length=100, blank=True, null=True)
    escola = models.CharField(max_length=150, blank=True, null=True)
    foto = models.ImageField(upload_to='professores/', blank=True, null=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} ({self.matricula})"

