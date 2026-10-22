from django.db import models
from django.contrib.auth.models import User

# --- Estruturas de Gestão Territorial e Escolar ---
class Cidade(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Cidade")
    uf = models.CharField(max_length=2, default='PA', verbose_name="UF")

    class Meta:
        verbose_name = "Cidade"
        verbose_name_plural = "Cidades"

    def __str__(self):
        return f"{self.nome} - {self.uf}"


class DRE(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome da DRE")
    cidade = models.ForeignKey(Cidade, on_delete=models.CASCADE, related_name='dres', verbose_name="Cidade")

    class Meta:
        verbose_name = "DRE"
        verbose_name_plural = "DREs"

    def __str__(self):
        return self.nome


class Escola(models.Model):
    nome = models.CharField(max_length=150, verbose_name="Nome da Escola")
    dre = models.ForeignKey(DRE, on_delete=models.SET_NULL, null=True, blank=True, related_name='escolas', verbose_name="DRE")
    cidade = models.ForeignKey(Cidade, on_delete=models.CASCADE, related_name='escolas', verbose_name="Cidade")

    class Meta:
        verbose_name = "Escola"
        verbose_name_plural = "Escolas"

    def __str__(self):
        return f"{self.nome} ({self.cidade.nome})"


# --- Perfil do Professor / Usuário ---

class PerfilProfessor(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    matricula = models.CharField(max_length=20, unique=True, verbose_name="Matrícula")
    telefone = models.CharField(max_length=20, blank=True, null=True)
    disciplina = models.CharField(max_length=100, blank=True, null=True)

    # Novos relacionamentos
    escola = models.ForeignKey(Escola, on_delete=models.SET_NULL, null=True, blank=True, related_name='professores', verbose_name="Escola")
    dre = models.ForeignKey(DRE, on_delete=models.SET_NULL, null=True, blank=True, related_name='professores', verbose_name="DRE")
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True, blank=True, related_name='professores', verbose_name="Cidade")

    foto = models.ImageField(upload_to='professores/', blank=True, null=True)

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} ({self.matricula})"

