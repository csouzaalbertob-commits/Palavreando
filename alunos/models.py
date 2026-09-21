from io import BytesIO
from django.core.files import File
from django.db import models
from django.db.models import Avg, Max
import qrcode

NIVEIS_ENSINO = [
    ('EF1', 'Ensino Fundamental I'),
    ('EF2', 'Ensino Fundamental II'),
    ('EM', 'Ensino Médio'),
]


class Aluno(models.Model):
  nome_completo = models.CharField(max_length=150)
  turma = models.CharField(max_length=50)
  serie = models.CharField(max_length=50, blank=True, null=True)
  foto = models.ImageField(upload_to='fotos_alunos/', blank=True, null=True)
  qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

  def save(self, *args, **kwargs):
    super().save(*args, **kwargs)

    if not self.qr_code:
      dados_qr = f"Aluno: {self.nome_completo}\nSérie: {self.serie or ''}\nTurma: {self.turma}"
      qr_img = qrcode.make(dados_qr)
      buffer = BytesIO()
      qr_img.save(buffer, format='PNG')

      filename = f"qr_aluno_{self.id}.png"
      self.qr_code.save(filename, File(buffer), save=False)
      super().save(*args, **kwargs)

  def __str__(self):
    return f"{self.nome_completo} - {self.turma}"


class ResultadoLeitura(models.Model):
  aluno = models.ForeignKey(
      Aluno, on_delete=models.CASCADE, related_name='resultados'
  )
  pontuacao_total = models.IntegerField(default=0)
  palavras_acertadas = models.IntegerField(default=0)
  palavras_ignoradas = models.IntegerField(default=0)

  # Métricas de Fluência
  tempo_segundos = models.IntegerField(
      default=60
  )  # Tempo total que levou na leitura
  ppm = models.IntegerField(default=0)  # Palavras por Minuto
  precisao = models.FloatField(default=0.0)  # Porcentagem de acerto

  # Listas de palavras para o diagnóstico (Salvas em JSON)
  palavras_com_demora = models.JSONField(
      default=list
  )  # ex: ["SUBSTANTIVO", "PARALELEPIPEDO"]
  palavras_puladas = models.JSONField(default=list)  # ex: ["ENTRETANTO"]
  palavras_erradas = models.JSONField(default=list)  # ex: ["PISCINA"]

  data_realizacao = models.DateTimeField(auto_now_add=True)

  def save(self, *args, **kwargs):
    # Cálculo do PPM: (Palavras lidas / Tempo em seg) * 60
    if self.tempo_segundos > 0:
      self.ppm = int((self.palavras_acertadas / self.tempo_segundos) * 60)

    # Cálculo da Precisão: (Acertos / Total de palavras) * 100
    total_palavras = (
        self.palavras_acertadas
        + self.palavras_ignoradas
        + len(self.palavras_erradas)
    )
    if total_palavras > 0:
      self.precisao = round(
          (self.palavras_acertadas / total_palavras) * 100, 1
      )

    super().save(*args, **kwargs)

  def __str__(self):
    return f"Resultado: {self.aluno.nome_completo} ({self.pontuacao_total} pts)"