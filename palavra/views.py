import io
from datetime import timedelta
import os
import re
import difflib
import json

from django.contrib import messages
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
from .forms import PalavraForm, FraseForm
from .models import BlocoHistoria, Historia, Palavra, PartidaBatalha, RespostaCompreensao, SolicitacaoNivel, Frase, HistoricoDitado
from palavra.models import ResultadoOuvirEFalar

app_name = 'palavra'


@login_required
# 1. Tela para o aluno se identificar antes de iniciar
def selecionar_aluno(request):
    alunos = Aluno.objects.all().order_by('nome_completo')
    return render(request, 'palavra/selecionar_aluno.html', {'alunos': alunos})

@login_required
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

@login_required
def cadastrar_frase(request):
    if request.method == 'POST':
        texto = request.POST.get('texto')
        # Converte explicitamente para inteiro (garante valor padrão 1 se falhar)
        try:
            nivel = int(request.POST.get('nivel', 1))
        except (ValueError, TypeError):
            nivel = 1

        if texto:
            Frase.objects.create(
                texto=texto,
                nivel=nivel,
                professor=request.user
            )
            messages.success(request, 'Frase cadastrada com sucesso!')
            return redirect('palavra:cadastrar_frase')

    frases = Frase.objects.filter(professor=request.user).order_by('-criado_em')
    return render(request, 'palavra/cadastrar_frase.html', {'frases': frases})

@login_required
def excluir_frase(request, frase_id):
    # Garante que só encontra frases cadastradas (ou do professor logado)
    frase = get_object_or_404(Frase, id=frase_id)
    
    if request.method == 'POST':
        frase.delete()
        messages.success(request, 'Frase excluída com sucesso!')
        return redirect('palavra:cadastrar_frase')

    return redirect('palavra:cadastrar_frase')

@login_required
def modo(request):
  aluno_id_raw = request.GET.get('aluno_id')
  aluno = None

  try:
    if aluno_id_raw:
      aluno_id = int(aluno_id_raw)
      aluno = get_object_or_404(Aluno, pk=aluno_id)
  except (ValueError, TypeError):
    return redirect('palavra:selecionar_aluno')

  # Certifique-se de que o caminho do template coincide com o arquivo alterado
  return render(request, 'palavra/modo.html', {'aluno': aluno})

@login_required
def jogo_60s(request):
    aluno_id = request.GET.get('aluno_id')
    modo = request.GET.get('modo', '60s')
    nivel = request.GET.get('nivel')
    aluno = get_object_or_404(Aluno, pk=aluno_id) if aluno_id else None
    
    palavras_qs = Palavra.objects.all()
    if nivel:
      palavras_qs = palavras_qs.filter(dificuldade=nivel)
      
    palavras_lista = list(palavras_qs.values_list('texto', flat=True))
    
    context = {
     'aluno': aluno,
     'aluno_id': aluno_id,
     'modo': modo,
     'nivel': nivel,
     'palavras': palavras_lista,
     'palavras_json': json.dumps(palavras_lista),
    }
    return render(request, 'palavra/jogo_60s.html', context)

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

@login_required
def ouvir_falar(request):
    aluno_id = request.GET.get('aluno_id')
    nivel = request.GET.get('nivel', 1)
    modo = request.GET.get('modo', 'ouvir_falar')

    aluno = get_object_or_404(Aluno, id=aluno_id) if aluno_id else None

    # Busca palavras reais do nível ou fallback
    palavras_qs = Palavra.objects.filter(dificuldade=nivel, tipo='P')
    if not palavras_qs.exists():
        palavras_qs = Palavra.objects.filter(tipo='P')

    # Extrai estritamente dicionários simples
    palavras_lista = list(palavras_qs.values('id', 'texto', 'dificuldade'))

    context = {
        'aluno': aluno,
        'aluno_id': aluno_id,
        'nivel': nivel,
        'modo': modo,
        'palavras': palavras_lista,
        'palavras_json': json.dumps(palavras_lista, ensure_ascii=False),
    }
    return render(request, 'palavra/ouvir_falar.html', context)

def normalizar_texto(texto):
    """Remove pontuações extras e limpa espaços."""
    texto = re.sub(r'[^\w\s]', '', texto.lower())
    return texto.strip()

@login_required
def ditado(request):
    aluno_id = request.GET.get('aluno_id')
    nivel = request.GET.get('nivel', '1')
    
    aluno = get_object_or_404(Aluno, id=aluno_id) if aluno_id else None

    # Busca frases do nível ou todas as frases cadastradas
    frases_qs = Frase.objects.filter(nivel=nivel)
    if not frases_qs.exists():
        frases_qs = Frase.objects.all()

    frases_lista = list(frases_qs.values('id', 'texto', 'nivel'))

    context = {
        'aluno': aluno,
        'aluno_id': aluno_id,
        'nivel': nivel,
        'frases_json': json.dumps(frases_lista, ensure_ascii=False)
    }
    return render(request, 'palavra/ditado.html', context)

@csrf_exempt
def salvar_resultado_ditado(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            frase_id = data.get('frase_id')
            texto_digitado = data.get('texto_digitado', '')
            aluno_id = data.get('aluno_id')
            poulou = data.get('poulou', False)
            tempo_gasto = data.get('tempo_gasto', 0)  # Recebe o tempo em segundos

            if not frase_id or not aluno_id:
                return JsonResponse({'status': 'erro', 'mensagem': 'Dados incompletos'}, status=400)

            frase = get_object_or_404(Frase, id=frase_id)
            aluno = get_object_or_404(Aluno, id=aluno_id)

            original_bruto = frase.texto.strip()
            digitado_bruto = texto_digitado.strip()

            palavras_originais = normalizar_texto(original_bruto).split()
            palavras_digitadas = normalizar_texto(digitado_bruto).split()

            total_palavras = len(palavras_originais)
            relatorio_palavras = []
            palavras_com_erro = []

            if total_palavras == 0 or poulou:
                pontuacao_final = 0
                palavras_com_erro = palavras_originais.copy()
            else:
                valor_por_palavra = 100.0 / total_palavras
                pontos_acumulados = 0.0

                matcher = difflib.SequenceMatcher(None, palavras_originais, palavras_digitadas)
                status_originais = [None] * total_palavras
                usados_digitados = set()

                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag == 'equal':
                        for idx in range(i1, i2):
                            status_originais[idx] = {'digitado': palavras_originais[idx], 'status': 'correto'}
                            pontos_acumulados += valor_por_palavra
                            usados_digitados.add(j1 + (idx - i1))

                    elif tag in ('replace', 'delete', 'insert'):
                        orig_sub = palavras_originais[i1:i2]
                        dig_sub = palavras_digitadas[j1:j2]

                        for idx, orig in enumerate(orig_sub):
                            orig_index = i1 + idx
                            melhor_match_idx = -1
                            melhor_sim = 0.0

                            for d_idx, dig in enumerate(dig_sub):
                                real_d_idx = j1 + d_idx
                                if real_d_idx in usados_digitados:
                                    continue
                                sim = difflib.SequenceMatcher(None, orig, dig).ratio()
                                if sim > melhor_sim:
                                    melhor_sim = sim
                                    melhor_match_idx = real_d_idx

                            if melhor_match_idx != -1 and melhor_sim >= 0.85:
                                dig_palavra = palavras_digitadas[melhor_match_idx]
                                usados_digitados.add(melhor_match_idx)
                                status_originais[orig_index] = {'digitado': dig_palavra, 'status': 'ortografia'}
                                pontos_acumulados += (valor_por_palavra * 0.5)
                                palavras_com_erro.append(f"{orig} (grafia: {dig_palavra})")
                            else:
                                status_originais[orig_index] = {'digitado': '[omitida]', 'status': 'omissao'}
                                palavras_com_erro.append(f"{orig} (omitida)")

                # Monta lista de relatórios
                for i, orig in enumerate(palavras_originais):
                    item = status_originais[i]
                    if item:
                        relatorio_palavras.append({'original': orig, 'digitado': item['digitado'], 'status': item['status']})
                    else:
                        relatorio_palavras.append({'original': orig, 'digitado': '[omitida]', 'status': 'omissao'})

                pontuacao_final = round(pontos_acumulados)

            professor = request.user if request.user.is_authenticated else frase.professor

            # Salva o registro do ditado
            HistoricoDitado.objects.create(
                aluno=aluno,
                frase=frase,
                usuario_professor=professor,
                texto_original=original_bruto,
                texto_digitado=digitado_bruto if not poulou else "[PULOU]",
                pontuacao=pontuacao_final,
                erros_palavra=", ".join(palavras_com_erro) if palavras_com_erro else "Nenhum erro",
                tempo_gasto=tempo_gasto
            )

            return JsonResponse({
                'status': 'sucesso',
                'pontuacao': pontuacao_final,
                'texto_correto': original_bruto,
                'texto_digitado': digitado_bruto,
                'relatorio': relatorio_palavras
            })

        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)

    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido'}, status=400)

@login_required
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

@login_required
def checar_status_solicitacao(request, solicitacao_id):
  solicitacao = get_object_or_404(SolicitacaoNivel, pk=solicitacao_id)
  return JsonResponse({
      'status': solicitacao.status,
      'nivel': solicitacao.nivel,
      'aluno_id': solicitacao.aluno.id,
  })

@login_required
def checar_solicitacao_pendente(request):
    """ Retorna para o Dashboard do Professor a primeira solicitação pendente """
    solicitacao = SolicitacaoNivel.objects.filter(status='pendente').first()
    if solicitacao:
        return JsonResponse({
            'status': 'tem_solicitacao',
            'solicitacao_id': solicitacao.id,
            'aluno_nome': solicitacao.aluno.nome_completo,
            'nivel': solicitacao.nivel
        })
    return JsonResponse({'status': 'sem_solicitacao'})

@login_required
def responder_solicitacao(request, solicitacao_id):
    """ O professor aprova ou recusa a solicitação """
    if request.method == 'POST':
        data = json.loads(request.body)
        status_resposta = data.get('status') # 'aprovado' ou 'recusado'
        
        solicitacao = SolicitacaoNivel.objects.filter(id=solicitacao_id).first()
        if solicitacao:
            solicitacao.status = status_resposta
            solicitacao.save()
            return JsonResponse({'status': 'sucesso'})
            
    return JsonResponse({'status': 'erro'}, status=400)

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

@login_required
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

@login_required
@csrf_exempt
def registrar_resultado_ouvir_falar(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            aluno_id = data.get('aluno_id')
            
            if not aluno_id:
                return JsonResponse({'status': 'erro', 'mensagem': 'Aluno não informado.'}, status=400)

            aluno = get_object_or_404(Aluno, id=aluno_id)

            resultado = ResultadoOuvirEFalar.objects.create(
                aluno=aluno,
                pontuacao_total=data.get('pontuacao_total', 0),
                palavras_acertadas=data.get('palavras_acertadas', 0),
                palavras_ignoradas=len(data.get('palavras_puladas', [])),
                tempo_segundos=data.get('tempo_segundos', 60),
                palavras_com_demora=data.get('palavras_com_demora', []),
                palavras_puladas=data.get('palavras_puladas', []),
                palavras_erradas=data.get('palavras_erradas', [])
            )

            return JsonResponse({
                'status': 'sucesso',
                'mensagem': 'Resultado do Ouvir e Falar salvo com sucesso no novo modelo!',
                'id_resultado': resultado.id
            })

        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)

    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido.'}, status=405)

@login_required
@csrf_exempt
def registrar_resposta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            aluno_id = data.get('aluno_id')
            if not aluno_id:
                return JsonResponse({'status': 'erro', 'mensagem': 'Aluno não informado'}, status=400)

            aluno = get_object_or_404(Aluno, id=aluno_id)

            # Trata palavras com demora (extrai apenas os nomes se vier em formato objeto)
            raw_demora = data.get('palavras_com_demora', [])
            demora_lista = []
            for item in raw_demora:
                if isinstance(item, dict):
                    demora_lista.append(item.get('palavra', ''))
                elif item:
                    demora_lista.append(str(item))

            # Trata palavras puladas
            raw_puladas = data.get('palavras_puladas', []) or data.get('palavras_ignoradas', [])
            puladas_lista = []
            for item in raw_puladas:
                if isinstance(item, dict):
                    puladas_lista.append(item.get('palavra', ''))
                elif item:
                    puladas_lista.append(str(item))

            # Trata palavras erradas (real vs falada)
            raw_erradas = data.get('palavras_erradas', [])
            erradas_lista = []
            for item in raw_erradas:
                if isinstance(item, dict):
                    erradas_lista.append(f"{item.get('palavra_real', '')} (falou: {item.get('palavra_errada', '')})")
                elif item:
                    erradas_lista.append(str(item))

            # Cria o registro no banco de dados (atribuindo listas Python diretamente ao JSONField)
            resultado = ResultadoLeitura.objects.create(
                aluno=aluno,
                pontuacao_total=data.get('pontuacao_total', 0),
                palavras_acertadas=data.get('palavras_acertadas', 0),
                palavras_ignoradas=len(puladas_lista),
                tempo_segundos=data.get('tempo_segundos', 60),
                palavras_com_demora=list(set(filter(None, demora_lista))),
                palavras_puladas=list(set(filter(None, puladas_lista))),
                palavras_erradas=list(set(filter(None, erradas_lista)))
            )

            return JsonResponse({
                'status': 'sucesso',
                'mensagem': 'Resultado salvo com sucesso no banco de dados!',
                'id_resultado': resultado.id
            })

        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)

    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido'}, status=405)

@login_required
@csrf_exempt
def salvar_resultado(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            aluno = get_object_or_404(Aluno, id=data.get('aluno_id'))

            resultado = ResultadoLeitura.objects.create(
                aluno=aluno,
                pontuacao_total=data.get('pontuacao_total', 0),
                palavras_acertadas=data.get('palavras_acertadas', 0),
                palavras_ignoradas=data.get('palavras_ignoradas', 0),
                palavras_com_demora=json.dumps(
                    data.get('palavras_com_demora', [])
                ),
            )

            return JsonResponse({
                'status': 'sucesso',
                'mensagem': 'Resultado salvo com sucesso!',
                'id_resultado': resultado.id,
            })

        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)

    return JsonResponse({'status': 'erro', 'mensagem': 'Método não permitido.'}, status=405)

@login_required
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

#leitura de historia
@login_required
def iniciar_leitura_historia(request, aluno_id):
    nivel = request.GET.get('nivel', '1')
    historia_id = request.GET.get('historia_id')

    aluno = get_object_or_404(Aluno, id=aluno_id)

    if historia_id:
        historia = Historia.objects.filter(id=historia_id).first()
    else:
        historia = Historia.objects.filter(nivel=nivel).first()

    if not historia:
        return render(request, 'palavra/sem_historias.html', {'aluno': aluno})

    # Mapeia os blocos garantindo a extração do URL da imagem
    blocos_queryset = historia.blocos.all().order_by('ordem_bloco')
    blocos = []
    for b in historia.blocos.all().order_by('ordem_bloco'):
        blocos.append({
            'id': b.id,
            'ordem_bloco': b.ordem_bloco,
            'trecho_texto': b.trecho_texto,
            # Retorna o URL público da mídia
            'imagem_url': b.imagem.url if b.imagem else None
        })

    context = {
        'aluno': aluno,
        'aluno_id': aluno.id,
        'historia': historia,
        'blocos_json': json.dumps(blocos, ensure_ascii=False)
    }
    return render(request, 'palavra/leitura_historia.html', context)


@csrf_exempt
def salvar_resposta_historia(request):
    """
    Salva a resposta do aluno (texto ou transcrição de voz) para cada bloco lido.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            aluno_id = data.get('aluno_id')
            bloco_id = data.get('bloco_id')
            resposta = data.get('resposta', '').strip()
            tipo_resposta = data.get('tipo_resposta', 'texto')
            tempo_gasto = data.get('tempo_gasto', 0)

            if not aluno_id or not bloco_id or not resposta:
                return JsonResponse({'status': 'erro', 'mensagem': 'Preencha a resposta antes de prosseguir.'}, status=400)

            aluno = get_object_or_404(Aluno, id=aluno_id)
            bloco = get_object_or_404(BlocoHistoria, id=bloco_id)

            # Grava a resposta no banco de dados
            RespostaCompreensao.objects.create(
                aluno=aluno,
                bloco=bloco,
                tipo_resposta=tipo_resposta,
                resposta_aluno=resposta,
                tempo_resposta_segundos=tempo_gasto
            )

            return JsonResponse({'status': 'sucesso', 'mensagem': 'Resposta salva com sucesso!'})

        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=500)

    return JsonResponse({'status': 'erro', 'mensagem': 'Método inválido'}, status=400)


@login_required
def detalhe_resposta_historia_professor(request, resposta_id):
    """
    View para o professor analisar a resposta exata enviada pelo aluno relacionada ao trecho lido.
    """
    resposta_obj = get_object_or_404(RespostaCompreensao, id=resposta_id)
    
    context = {
        'resposta': resposta_obj,
        'aluno': resposta_obj.aluno,
        'bloco': resposta_obj.bloco,
        'historia': resposta_obj.bloco.historia
    }
    return render(request, 'palavra/detalhe_resposta_professor.html', context)

@login_required
def cadastrar_historia(request):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        nivel = request.POST.get('nivel', '1')

        # 1. Cria o registro principal da história (sem dependência de arquivo PDF)
        historia = Historia.objects.create(
            titulo=titulo,
            nivel=nivel
        )

        texto_completo_acumulado = []
        bloco_index = 1

        # 2. Varre os blocos enviados na requisição
        while f'trecho_texto_{bloco_index}' in request.POST:
            trecho = request.POST.get(f'trecho_texto_{bloco_index}', '').strip()
            imagem = request.FILES.get(f'imagem_bloco_{bloco_index}')

            if trecho:
                bloco = BlocoHistoria(
                    historia=historia,
                    ordem_bloco=bloco_index,
                    trecho_texto=trecho
                )
                if imagem:
                    bloco.imagem = imagem
                
                bloco.save()
                texto_completo_acumulado.append(trecho)

            bloco_index += 1

        # 3. Consolida o texto completo da história
        historia.texto_completo = "\n\n".join(texto_completo_acumulado)
        historia.save()

        return redirect('palavra:cadastrar_historia')

    historias = Historia.objects.all().order_by('-id')
    return render(request, 'palavra/cadastrar_historia.html', {'historias': historias})

@login_required
def listar_historias_por_nivel(request):
    nivel = request.GET.get('nivel', '1')
    historias = Historia.objects.filter(nivel=nivel).values('id', 'titulo')
    
    return JsonResponse({
        'status': 'sucesso',
        'historias': list(historias)
    })

@login_required
def editar_historia(request, historia_id):
    """
    Atualiza título, nível e opcionalmente substitui o arquivo PDF (refazendo os blocos).
    """
    historia = get_object_or_404(Historia, id=historia_id)

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        nivel = request.POST.get('nivel', '1')
        novo_pdf = request.FILES.get('arquivo_pdf')

        if not titulo:
            messages.error(request, 'O título da história não pode ficar em branco.')
            return redirect('palavra:cadastrar_historia')

        try:
            historia.titulo = titulo
            historia.nivel = nivel

            if novo_pdf:
                # Se enviou novo PDF, remove o antigo do disco e os blocos antigos
                if historia.arquivo_pdf and os.path.exists(historia.arquivo_pdf.path):
                    os.remove(historia.arquivo_pdf.path)
                
                historia.blocos.all().delete()
                historia.arquivo_pdf = novo_pdf

            historia.save()  # Dispara o signal de refatiamento se novo_pdf for salvo
            
            messages.success(request, f'História "{historia.titulo}" atualizada com sucesso!')
            return redirect('palavra:cadastrar_historia')

        except Exception as e:
            messages.error(request, f'Erro ao atualizar história: {e}')
            return redirect('palavra:cadastrar_historia')

    return redirect('palavra:cadastrar_historia')

@login_required
def excluir_historia(request, historia_id):
    if request.method == 'POST':
        historia = get_object_or_404(Historia, id=historia_id)
        
        # Elimina as imagens dos blocos salvas em disco se existirem
        for bloco in historia.blocos.all():
            if bloco.imagem:
                bloco.imagem.delete(save=False)
        
        # Apaga o registo no banco de dados (elimina em cascata os blocos)
        historia.delete()
        messages.success(request, "História eliminada com sucesso!")
        
    return redirect('palavra:cadastrar_historia')