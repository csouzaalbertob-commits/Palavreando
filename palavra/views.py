import io
import json
import qrcode
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import models, transaction 
from django.db.models import Count, Max
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from django.utils import timezone

from alunos.models import Aluno, ResultadoLeitura
from .forms import PalavraForm
from .models import Palavra, PartidaBatalha, SolicitacaoNivel

app_name = 'palavra'


# 1. Tela para o aluno se identificar antes de iniciar
def selecionar_aluno(request):
    alunos = Aluno.objects.all().order_by('nome_completo')
    return render(request, 'palavra/selecionar_aluno.html', {'alunos': alunos})


# 2. Tela da atividade
def exibir_palavras(request):
  aluno_id = request.GET.get('aluno_id')
  modo = request.GET.get('modo', '60s')
  nivel = request.GET.get('nivel')

  # 1. Busca os dados do aluno para exibir no cabeçalho
  aluno = get_object_or_404(Aluno, pk=aluno_id) if aluno_id else None

  # 2. Filtra as palavras
  palavras_qs = Palavra.objects.all()
  if nivel:
    palavras_qs = palavras_qs.filter(dificuldade=nivel)

  # 3. Converte o QuerySet para uma lista de dicionários serializável
  palavras_lista = list(
      palavras_qs.values('id', 'texto', 'dificuldade', 'tipo')
  )

  context = {
      'aluno': aluno,
      'aluno_id': aluno_id,
      'modo': modo,
      'nivel': nivel,
      'palavras': palavras_lista,
      'palavras_json': json.dumps(
          palavras_lista
      ),  # Para ser consumido facilmente pelo JS
  }

  return render(request, 'palavra/exibir_palavras.html', context)


def modo(request):
    aluno_id_raw = request.GET.get('aluno_id')
    aluno = None

    # Validação e conversão segura para inteiro
    try:
        if aluno_id_raw:
            aluno_id = int(aluno_id_raw)
            aluno = get_object_or_404(Aluno, pk=aluno_id)
    except (ValueError, TypeError):
        # Se aluno_id vier malformado, redireciona para seleção
        return redirect('palavra:selecionar_aluno')

    return render(request, 'palavra/modo.html', {'aluno': aluno})

def modo_batalha(request):
  aluno_id = request.GET.get('aluno_id')
  aluno = get_object_or_404(Aluno, id=aluno_id)

  with transaction.atomic():
    tempo_limite = timezone.now() - timedelta(seconds=60)

    # 1. Limpa salas "aguardando" sem oponente que expiraram (mais de 60s)
    PartidaBatalha.objects.filter(
        status='aguardando', jogador_2__isnull=True, criado_em__lt=tempo_limite
    ).delete()

    # 2. SE O PRÓPRIO ALUNO JÁ TIVER UMA SALA ATIVA/AGUARDANDO, MANTÉM NA MESMA
    partida = (
        PartidaBatalha.objects.select_for_update()
        .filter(
            models.Q(jogador_1=aluno) | models.Q(jogador_2=aluno),
            status__in=['aguardando', 'em_andamento'],
            criado_em__gte=tempo_limite,
        )
        .order_by('-id')
        .first()
    )

    # 3. Se ele não estiver em nenhuma sala, procura uma sala aberta de outro jogador
    if not partida:
      partida = (
          PartidaBatalha.objects.select_for_update()
          .filter(
              status='aguardando',
              jogador_2__isnull=True,
              criado_em__gte=tempo_limite,
          )
          .exclude(jogador_1=aluno)
          .order_by('id')
          .first()
      )

      if partida:
        partida.jogador_2 = aluno
        partida.status = 'em_andamento'
        partida.save()
      else:
        # 4. Caso não encontre nenhuma, aí sim cria uma nova sala
        partida = PartidaBatalha.objects.create(
            jogador_1=aluno, jogador_2=None, status='aguardando'
        )

  oponente = (
      partida.jogador_2 if partida.jogador_1 == aluno else partida.jogador_1
  )

  palavras_dict = {
      1: list(
          Palavra.objects.filter(dificuldade=1).values('id', 'texto', 'tipo')
      ),
      2: list(
          Palavra.objects.filter(dificuldade=2).values('id', 'texto', 'tipo')
      ),
      3: list(
          Palavra.objects.filter(dificuldade=3).values('id', 'texto', 'tipo')
      ),
  }

  context = {
      'aluno': aluno,
      'partida': partida,
      'oponente': oponente,
      'palavras_json': json.dumps(palavras_dict),
  }

  return render(request, 'palavra/batalha.html', context)

@csrf_exempt
def criar_solicitacao(request):
  if request.method == 'POST':
    data = json.loads(request.body)
    aluno_id = data.get('aluno_id')
    nivel = data.get('nivel')

    aluno = get_object_or_404(Aluno, pk=aluno_id)

    # Cancela solicitações pendentes anteriores do mesmo aluno
    SolicitacaoNivel.objects.filter(
        aluno=aluno, status='pendente'
    ).delete()

    solicitacao = SolicitacaoNivel.objects.create(
        aluno=aluno, nivel=nivel, status='pendente'
    )

    return JsonResponse(
        {'status': 'sucesso', 'solicitacao_id': solicitacao.id}
    )

  return JsonResponse({'error': 'Método inválido'}, status=400)


def checar_status_solicitacao(request, solicitacao_id):
  solicitacao = get_object_or_404(SolicitacaoNivel, pk=solicitacao_id)
  return JsonResponse({
      'status': solicitacao.status,
      'nivel': solicitacao.nivel,
      'aluno_id': solicitacao.aluno.id,
  })


def buscar_solicitacoes_pendentes(request):
  # Busca a solicitação pendente mais recente
  solicitacao = (
      SolicitacaoNivel.objects.filter(status='pendente')
      .order_by('-criado_em')
      .first()
  )

  if solicitacao:
    return JsonResponse({
        'tem_solicitacao': True,
        'solicitacao_id': solicitacao.id,
        'id': solicitacao.id,  # Garantia para ambas as chamadas JS
        'aluno_nome': solicitacao.aluno.nome_completo,
        'nivel': solicitacao.nivel,
    })

  return JsonResponse({'tem_solicitacao': False})


@csrf_exempt
def responder_solicitacao(request):
  if request.method == 'POST':
    try:
      data = json.loads(request.body)
      solicitacao_id = data.get('solicitacao_id') or data.get('id')

      # Suporta tanto a chave 'resposta' quanto 'status' enviadas pelo JS
      resposta = data.get('resposta') or data.get('status')

      solicitacao = get_object_or_404(SolicitacaoNivel, pk=solicitacao_id)
      solicitacao.status = resposta

      if request.user.is_authenticated:
        solicitacao.professor = request.user

      solicitacao.save()

      return JsonResponse(
          {'status': 'sucesso', 'message': f'Solicitação marcada como {resposta}'}
      )
    except Exception as e:
      return JsonResponse({'error': str(e)}, status=400)

  return JsonResponse({'error': 'Método inválido'}, status=400)

@login_required
def deletar_palavra(request, palavra_id):
    palavra = Palavra.objects.filter(id=palavra_id).first()

    if palavra:
        palavra.delete()

    return redirect('palavra:gerenciar_palavras')


@login_required
def gerenciar_palavras(request):
    if request.method == 'POST':
        form = PalavraForm(request.POST)
        if form.is_valid():
            palavra = form.save(commit=False)
            palavra.professor = request.user
            palavra.save()
            return redirect('palavra:gerenciar_palavras')
    else:
        form = PalavraForm()

    palavras = Palavra.objects.all()
    return render(
        request,
        'palavra/gerenciar_palavras.html',
        {'form': form, 'palavras': palavras},
    )


def gerar_qrcode_aluno(request, aluno_id, prof_id):
    domain = request.build_absolute_uri('/')[:-1]

    caminho_avaliacao = reverse('palavra:exibir_palavras')
    url_avaliacao = (
        f'{domain}{caminho_avaliacao}?aluno_id={aluno_id}&prof_id={prof_id}'
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url_avaliacao)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return HttpResponse(buffer.getvalue(), content_type='image/png')


@csrf_exempt
def registrar_resposta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            aluno_id = data.get('aluno_id')
            if not aluno_id:
                return JsonResponse({'status': 'erro', 'mensagem': 'Aluno não informado'}, status=400)

            aluno = get_object_or_404(Aluno, id=aluno_id)

            # Garante que salva arrays serializados em JSON
            resultado = ResultadoLeitura.objects.create(
                aluno=aluno,
                pontuacao_total=data.get('pontuacao_total', data.get('pontuacao', 0)),
                palavras_acertadas=data.get('palavras_acertadas', data.get('acertos', 0)),
                palavras_ignoradas=data.get('palavras_ignoradas', data.get('erros', 0)),
                palavras_com_demora=json.dumps(data.get('palavras_com_demora', data.get('demoradas', []))),
                palavras_puladas=json.dumps(data.get('palavras_puladas', data.get('puladas', []))),
                palavras_erradas=json.dumps(data.get('palavras_erradas', data.get('erradas', []))),
            )

            return JsonResponse({
                'status': 'sucesso',
                'mensagem': 'Resultado salvo com sucesso no banco de dados!',
                'id_resultado': resultado.id,
            })

        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)

    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido'}, status=405)


@csrf_exempt
def salvar_resultado(request):
  if request.method == 'POST':
    try:
      data = json.loads(request.body)

      aluno = get_object_or_404(Aluno, id=data.get('aluno_id'))

      resultado = ResultadoLeitura.objects.create(
          aluno=aluno,
          pontuacao_total=data.get('pontuacao_total', data.get('pontuacao', 0)),
          palavras_acertadas=data.get('palavras_acertadas', data.get('acertos', 0)),
          palavras_ignoradas=data.get('palavras_ignoradas', data.get('erros', 0)),
          palavras_com_demora=json.dumps(data.get('palavras_com_demora', data.get('demoradas', []))),
          palavras_puladas=json.dumps(data.get('palavras_puladas', data.get('puladas', []))),
          palavras_erradas=json.dumps(data.get('palavras_erradas', data.get('erradas', []))),
      )

      return JsonResponse({
          'status': 'sucesso',
          'mensagem': 'Resultado salvo com sucesso!',
          'id_resultado': resultado.id,
      })

    except Exception as e:
      return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)

  return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido.'}, status=405)


def ranking_recordes(request):
    ranking = (
        Aluno.objects.annotate(
            maior_pontuacao=Max('resultadoleitura__pontuacao_total'),
            total_testes=Count('resultadoleitura'),
        )
        .filter(maior_pontuacao__isnull=False)
        .order_by('-maior_pontuacao', 'total_testes')
    )

    return render(request, 'palavra/ranking.html', {'ranking': ranking})