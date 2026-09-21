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