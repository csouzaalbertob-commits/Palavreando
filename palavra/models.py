from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from alunos.models import Aluno, ResultadoLeitura


TIPO_PALAVRA = [
    ('P', 'Palavra Real'),
    ('PP', 'Pseudopalavra'),
]

DIFICULDADE_CHOICES = [
    (1, 'Fácil (100 pts)'),
    (2, 'Média (200 pts)'),
    (3, 'Difícil (300 pts)'),
]


class Palavra(models.Model):
  texto = models.CharField('Palavra / Pseudopalavra', max_length=100)
  tipo = models.CharField(
      'Tipo', max_length=2, choices=TIPO_PALAVRA, default='P'
  )
  dificuldade = models.IntegerField(
      'Dificuldade', choices=DIFICULDADE_CHOICES, default=1
  )
  criado_em = models.DateTimeField(auto_now_add=True)
  professor = models.ForeignKey(
      'auth.User', on_delete=models.CASCADE, null=True, blank=True
  )

  def get_pontos_base(self):
    return self.dificuldade * 100


class AvaliacaoLeitura(models.Model):
  aluno_id = models.CharField(max_length=50)
  professor_id = models.CharField(max_length=50)
  data = models.DateTimeField(auto_now_add=True)
  etapa = models.IntegerField(default=1)  # 1: Palavras, 2: Pseudopalavras


class RespostaPalavra(models.Model):
  STATUS_CHOICES = [
      ('CORRETO', 'Leu Corretamente'),
      ('TROCA', 'Substituiu/Omitiu'),
      ('AUTOCORRECAO', 'Autocorregiou'),
  ]
  # Usa a referência direta à classe do modelo já importado
  avaliacao = models.ForeignKey(
      ResultadoLeitura,
      on_delete=models.CASCADE,
      related_name='respostas_palavras',
  )
  palavra = models.ForeignKey(Palavra, on_delete=models.CASCADE)
  status = models.CharField(max_length=15, choices=STATUS_CHOICES)
  tempo_resposta_segundos = models.IntegerField(default=0)


class PartidaBatalha(models.Model):
  jogador_1 = models.ForeignKey(
      Aluno, on_delete=models.CASCADE, related_name='partidas_j1'
  )
  jogador_2 = models.ForeignKey(
      Aluno,
      on_delete=models.CASCADE,
      related_name='partidas_j2',
      null=True,
      blank=True,
  )
  vencedor = models.ForeignKey(
      Aluno,
      on_delete=models.SET_NULL,
      null=True,
      blank=True,
      related_name='vitorias',
  )
  status = models.CharField(max_length=20, default='aguardando')
  nivel_atual = models.IntegerField(default=1)
  pontos_j1 = models.IntegerField(default=0)
  pontos_j2 = models.IntegerField(default=0)
  criado_em = models.DateTimeField(auto_now_add=True)


class SolicitacaoNivel(models.Model):
  STATUS_CHOICES = (
      ('pendente', 'Pendente'),
      ('aprovado', 'Aprovado'),
      ('recusado', 'Recusado'),
      ('cancelado', 'Cancelado'),  # Adicionado
  )

  aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE)
  professor = models.ForeignKey(
      User, on_delete=models.SET_NULL, null=True, blank=True
  )
  nivel = models.IntegerField(default=1)
  status = models.CharField(
      max_length=10, choices=STATUS_CHOICES, default='pendente'
  )
  criado_em = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return f'{self.aluno.nome_completo} - Nível {self.nivel} ({self.status})'

#ditado
class Frase(models.Model):
  """Modelo para armazenar as frases/textos do Ditado."""

  NIVEL_CHOICES = [
      ('1', 'Nível 1 - Fácil (Palavras simples)'),
      ('2', 'Nível 2 - Médio (Frases curtas)'),
      ('3', 'Nível 3 - Difícil (Pontuação e acentuação)'),
  ]

  texto = models.TextField(
      verbose_name='Texto do Ditado',
      help_text='Insira a frase ou pequeno texto que o computador lerá para o aluno.',
  )
  nivel = models.CharField(
      max_length=1,
      choices=NIVEL_CHOICES,
      default='1',
      verbose_name='Nível de Dificuldade',
  )
  criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

  class Meta:
    verbose_name = 'Frase de Ditado'
    verbose_name_plural = 'Frases de Ditado'

  def __str__(self):
    return f'[{self.get_nivel_display()}] {self.texto[:40]}...'
  
class ResultadoDitado(models.Model):
  """Modelo para registrar o resultado e a pontuação do aluno no ditado."""

  aluno = models.ForeignKey(
      Aluno,
      on_delete=models.CASCADE,
      related_name='resultados_ditado',
      verbose_name='Aluno',
  )
  frase = models.ForeignKey(
      Frase,
      on_delete=models.CASCADE,
      related_name='resultados',
      verbose_name='Frase Ditada',
  )
  texto_digitado = models.TextField(verbose_name='Texto Digitado pelo Aluno')
  pontuacao = models.IntegerField(
      default=0,
      verbose_name='Pontuação (0-100)',
      help_text='Nota calculada por similaridade com a frase original.',
  )
  erros_acentuacao = models.IntegerField(
      default=0, verbose_name='Erros de Acentuação/Pontuação'
  )
  erros_palavras = models.IntegerField(
      default=0, verbose_name='Palavras Erradas/Faltando'
  )
  data_realizacao = models.DateTimeField(
      auto_now_add=True, verbose_name='Data de Realização'
  )

  class Meta:
    verbose_name = 'Resultado do Ditado'
    verbose_name_plural = 'Resultados dos Ditados'
    ordering = ['-data_realizacao']

  def __str__(self):
    return (
        f'{self.aluno.nome_completo} - Nota: {self.pontuacao} pts em'
        f' {self.data_realizacao.strftime("%d/%m/%Y")}'
    )

class HistoricoDitado(models.Model):
    usuario_professor = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Professor/Usuário")
    aluno = models.ForeignKey(Aluno, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Aluno")
    frase = models.ForeignKey(Frase, on_delete=models.CASCADE, verbose_name="Frase Exibida")
    texto_original = models.TextField(verbose_name="Texto Original")
    texto_digitado = models.TextField(verbose_name="Texto Digitado")
    pontuacao = models.IntegerField(verbose_name="Pontuação (0-100)")
    erros_acentuacao = models.IntegerField(default=0, verbose_name="Erros de Acentuação")
    erros_palavra = models.IntegerField(default=0, verbose_name="Erros de Palavra")
    palavras_erradas = models.JSONField(default=list, verbose_name="Lista de Palavras Erradas")
    data_envio = models.DateTimeField(auto_now_add=True, verbose_name="Data do Envio")

    def __str__(self):
        return f"Ditado #{self.id} - {self.usuario_professor.username} - {self.pontuacao} pts"