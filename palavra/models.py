from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import os

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

class ResultadoOuvirEFalar(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='resultados_ouvir_falar')
    pontuacao_total = models.IntegerField(default=0)
    palavras_acertadas = models.IntegerField(default=0)
    palavras_ignoradas = models.IntegerField(default=0)
    tempo_segundos = models.IntegerField(default=60)
    
    # Granularidade diagnóstica (JSON)
    palavras_com_demora = models.JSONField(default=list)  # ex: [{"palavra": "SAPO", "tempo": 6}]
    palavras_puladas = models.JSONField(default=list)     # ex: [{"palavra": "CASA", "tempo": 3}]
    palavras_erradas = models.JSONField(default=list)     # ex: [{"palavra_real": "SAPO", "palavra_errada": "PIPA"}]
    
    data_realizacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ouvir e Falar: {self.aluno.nome_completo} ({self.pontuacao_total} pts)"
    
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

  professor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='frases')

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

User = get_user_model()

class HistoricoDitado(models.Model):
    # Use 'nome_do_app.Aluno' em vez da classe importada
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE, related_name='historicos_ditado')
    frase = models.ForeignKey('Frase', on_delete=models.CASCADE)
    usuario_professor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    texto_original = models.TextField()
    texto_digitado = models.TextField()
    pontuacao = models.IntegerField(default=0)
    erros_palavra = models.TextField(blank=True, null=True)
    tempo_gasto = models.IntegerField(default=0)
    data_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.aluno} - {self.pontuacao} pts"


#app de leitura de historia
#signal processamento de pdf
from django.db.models.signals import post_save
from django.dispatch import receiver
import pypdf

@receiver(post_save, sender='palavra.Historia')
def processar_pdf_historia(sender, instance, created, **kwargs):
    if created and instance.arquivo_pdf:
        try:
            # 1. Extrai o texto do arquivo PDF
            reader = pypdf.PdfReader(instance.arquivo_pdf.path)
            texto_extraido = ""
            for page in reader.pages:
                texto_extraido += page.extract_text() + "\n\n"

            instance.texto_completo = texto_extraido.strip()

            # 2. Divide em parágrafos válidos (ignorando linhas em branco)
            paragrafos = [p.strip() for p in texto_extraido.split('\n\n') if p.strip()]

            # 3. Agrupa a cada 2 parágrafos por bloco
            bloco_num = 1
            for i in range(0, len(paragrafos), 2):
                trecho = "\n\n".join(paragrafos[i:i+2])
                BlocoHistoria.objects.create(
                    historia=instance,
                    ordem_bloco=bloco_num,
                    trecho_texto=trecho
                )
                bloco_num += 1

        except Exception as e:
            print(f"Erro ao processar PDF da História: {e}")

#app de leitura de historia
NIVEL_DIFICULDADE = [
    ('1', 'Nível 1 - Iniciante'),
    ('2', 'Nível 2 - Intermediário'),
    ('3', 'Nível 3 - Avançado'),
]
class Historia(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="Título da História")
    arquivo_pdf = models.FileField(upload_to='historias_pdf/', verbose_name="Arquivo PDF")
    nivel = models.CharField(max_length=1, choices=NIVEL_DIFICULDADE, default='1', verbose_name="Nível de Dificuldade")
    texto_completo = models.TextField(blank=True, null=True, verbose_name="Texto Extraído")
    professor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} (Nível {self.nivel})"

class BlocoHistoria(models.Model):
    historia = models.ForeignKey(Historia, on_delete=models.CASCADE, related_name='blocos')
    ordem_bloco = models.PositiveIntegerField()
    trecho_texto = models.TextField(verbose_name="Trecho da História (2 Parágrafos)")
    imagem = models.ImageField(upload_to='historias_imagens/', blank=True, null=True, verbose_name="Imagem da Página/Bloco")

    class Meta:
        ordering = ['ordem_bloco']

class RespostaCompreensao(models.Model):
    TIPO_RESPOSTA = [
        ('texto', 'Digitado'),
        ('voz', 'Voz Transcrita'),
    ]

    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='respostas_historias')
    bloco = models.ForeignKey(BlocoHistoria, on_delete=models.CASCADE, related_name='respostas')
    tipo_resposta = models.CharField(max_length=10, choices=TIPO_RESPOSTA, default='texto')
    resposta_aluno = models.TextField(verbose_name="Resposta do Aluno (O que entendeu)")
    tempo_resposta_segundos = models.IntegerField(default=0)
    data_realizacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.aluno.nome_completo} - {self.bloco.historia.titulo} (Bloco {self.bloco.ordem_bloco})"