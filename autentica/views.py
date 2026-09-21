from collections import Counter
import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render

from alunos.models import Aluno, ResultadoLeitura

from .forms import (
    AtualizarProfessorForm,
    CadastroProfessorForm,
    PerfilProfessorForm,
)
from .models import PerfilProfessor

app_name = 'autentica'


@login_required
def editar_perfil_professor(request):
  # Garante que o objeto PerfilProfessor exista para o usuário atual
  perfil, _ = PerfilProfessor.objects.get_or_create(usuario=request.user)

  if request.method == 'POST':
    form = AtualizarProfessorForm(request.POST, instance=request.user)
    form_perfil = PerfilProfessorForm(
        request.POST, request.FILES, instance=perfil
    )

    if form.is_valid() and form_perfil.is_valid():
      form.save()
      form_perfil.save()
      messages.success(request, 'Seus dados foram atualizados com sucesso!')
      return redirect('autentica:editar_perfil')
  else:
    form = AtualizarProfessorForm(instance=request.user)
    form_perfil = PerfilProfessorForm(instance=perfil)

  return render(
      request,
      'autentica/atualiza_professor.html',
      {'form': form, 'form_perfil': form_perfil},
  )


@login_required
def dashboard(request):
  total_alunos = Aluno.objects.count()

  # Traz todos os alunos e todos os resultados do banco de uma só vez
  alunos = list(Aluno.objects.all().order_by('nome_completo'))
  todos_resultados = list(ResultadoLeitura.objects.select_related('aluno').all())

  alunos_recordes = []

  for aluno in alunos:
    # Filtra os resultados deste aluno em memória usando Python
    resultados_aluno = [r for r in todos_resultados if r.aluno_id == aluno.id]
    total_testes = len(resultados_aluno)

    if total_testes > 0:
      # Ordena: maior pontuação primeiro, data mais recente como segundo critério
      resultados_aluno.sort(
          key=lambda r: (r.pontuacao_total, r.data_realizacao), reverse=True
      )
      melhor_resultado = resultados_aluno[0]
      maior_pontuacao = melhor_resultado.pontuacao_total
      data_recorde = melhor_resultado.data_realizacao

      # Ordena por data para determinar a tendência de crescimento
      resultados_cronologicos = sorted(
          resultados_aluno, key=lambda r: r.data_realizacao
      )
      if len(resultados_cronologicos) >= 2:
        penultimo = resultados_cronologicos[-2].pontuacao_total
        ultimo = resultados_cronologicos[-1].pontuacao_total
        if ultimo > penultimo:
          tendencia = 'subindo'
        elif ultimo < penultimo:
          tendencia = 'caindo'
        else:
          tendencia = 'estavel'
      else:
        tendencia = 'subindo'
    else:
      maior_pontuacao = 0
      data_recorde = None
      tendencia = 'estavel'

    alunos_recordes.append({
        'aluno': aluno,
        'maior_pontuacao': maior_pontuacao,
        'data_recorde': data_recorde,
        'total_testes': total_testes,
        'tendencia': tendencia,
    })

  # CRITÉRIO DE ORDENAÇÃO DO RANKING DA TABELA PRINCIPAL
  for item in alunos_recordes:
    item['media_eficiencia'] = (
        item['maior_pontuacao'] / item['total_testes']
        if item['total_testes'] > 0
        else 0
    )

  alunos_recordes.sort(
      key=lambda x: (
          0 if x['total_testes'] > 0 else 1,
          -x['media_eficiencia'],
          x['total_testes'],
          x['aluno'].nome_completo,
      )
  )

  top_10_alunos = alunos_recordes[:10]

  # Ranking de Batalhas/Desafios (Soma dos pontos de J1 + J2)
  ranking_alunos = (
      Aluno.objects.annotate(
          pontos_j1=Coalesce(Sum('partidas_j1__pontos_j1'), Value(0)),
          pontos_j2=Coalesce(Sum('partidas_j2__pontos_j2'), Value(0)),
      )
      .annotate(pontuacao_total=F('pontos_j1') + F('pontos_j2'))
      .order_by('-pontuacao_total')[:10]
  )

  # Prepara dados para o Chart.js (Envio de TODOS os alunos para o gráfico)
  labels_grafico = []
  pontuacoes_grafico = []
  predicoes_grafico = []

  for item in top_10_alunos:
    aluno = item['aluno']
    labels_grafico.append(aluno.nome_completo)
    pontuacoes_grafico.append(item['maior_pontuacao'])

    # Histórico em ordem cronológica para projeção/regressão linear
    historico_aluno = [r for r in todos_resultados if r.aluno_id == aluno.id]
    historico_aluno.sort(key=lambda r: r.data_realizacao)
    historico = [r.pontuacao_total for r in historico_aluno]

    if len(historico) >= 2:
      n = len(historico)
      x = list(range(1, n + 1))
      y = historico
      sum_x = sum(x)
      sum_y = sum(y)
      sum_xy = sum(i * j for i, j in zip(x, y))
      sum_x2 = sum(i**2 for i in x)

      denom = n * sum_x2 - sum_x**2
      inclinacao = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else 0
      intercepto = (sum_y - inclinacao * sum_x) / n

      proxima_pontuacao = max(0, round(inclinacao * (n + 1) + intercepto, 1))
      predicoes_grafico.append(proxima_pontuacao)
    elif len(historico) == 1:
      predicoes_grafico.append(historico[0])
    else:
      predicoes_grafico.append(0)

  # Destaques da Tela (Melhor e Pior Global)
  resultados_com_pontos = [
      r for r in todos_resultados if r.pontuacao_total > 0
  ]

  if resultados_com_pontos:
    resultados_com_pontos.sort(
        key=lambda r: (r.pontuacao_total, r.data_realizacao), reverse=True
    )
    melhor_global = resultados_com_pontos[0]
    pior_global = resultados_com_pontos[-1]

    melhor_aluno = {
        'nome_completo': melhor_global.aluno.nome_completo,
        'maior_pontuacao': melhor_global.pontuacao_total,
        'data_recorde': melhor_global.data_realizacao,
    }

    aluno_dificuldade = {
        'nome_completo': pior_global.aluno.nome_completo,
        'menor_pontuacao': pior_global.pontuacao_total,
        'data_recorde': pior_global.data_realizacao,
    }
  else:
    melhor_aluno = None
    aluno_dificuldade = None

  # Contagem de palavras com demora
  contador_demoradas = Counter()
  for res in todos_resultados:
    if res.palavras_com_demora:
      try:
        demoradas = (
            json.loads(res.palavras_com_demora)
            if isinstance(res.palavras_com_demora, str)
            else res.palavras_com_demora
        )
        if isinstance(demoradas, list):
          for item in demoradas:
            palavra_texto = (
                item.get('palavra') if isinstance(item, dict) else item
            )
            if palavra_texto:
              contador_demoradas[str(palavra_texto).upper()] += 1
      except Exception:
        continue

  palavras_mais_demoradas = contador_demoradas.most_common(5)
  palavras_dificuldade = [
      {'texto': palavra, 'total_atrasos': quantidade}
      for palavra, quantidade in contador_demoradas.most_common(5)
  ]

  context = {
      'total_alunos': total_alunos,
      'alunos': alunos,
      'alunos_recordes': alunos_recordes,
      'melhor_aluno': melhor_aluno,
      'aluno_dificuldade': aluno_dificuldade,
      # Compatibilidade com as chaves exigidas no HTML atualizado do Dashboard:
      'nomes_alunos_json': json.dumps(labels_grafico),
      'pontos_atuais_json': json.dumps(pontuacoes_grafico),
      'chart_predicoes': json.dumps(predicoes_grafico),
      'palavras_mais_demoradas': palavras_mais_demoradas,
      'palavras_dificuldade': palavras_dificuldade,
      'ranking_alunos': ranking_alunos,
  }

  return render(request, 'autentica/dashboard.html', context)


def cadastro_professor(request):
  if request.user.is_authenticated:
    return redirect('autentica:login')

  if request.method == 'POST':
    form = CadastroProfessorForm(request.POST)
    if form.is_valid():
      user = form.save()
      login(request, user)  # Faz login automático após cadastrar
      messages.success(
          request,
          f'Conta criada com sucesso! Bem-vindo, Prof. {user.first_name}.',
      )
      return redirect('autentica:login')
    else:
      messages.error(request, 'Por favor, corrija os erros abaixo.')
  else:
    form = CadastroProfessorForm()

  return render(request, 'autentica/cadastro_professor.html', {'form': form})