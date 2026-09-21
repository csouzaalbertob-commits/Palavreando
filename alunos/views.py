import base64
import json

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Avg, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from .forms import AlunoForm
from .models import Aluno, ResultadoLeitura

app_name = 'alunos'


@login_required
def cadastrar_aluno(request):
  if request.method == 'POST':
    form = AlunoForm(request.POST, request.FILES)
    if form.is_valid():
      aluno = form.save(commit=False)

      # Captura foto da WebCam (Base64) se enviada
      foto_base64 = request.POST.get('foto_webcam')
      if foto_base64 and 'data:image' in foto_base64:
        try:
          format, imgstr = foto_base64.split(';base64,')
          ext = format.split('/')[-1]
          data = ContentFile(
              base64.b64decode(imgstr),
              name=f'aluno_{aluno.nome_completo}.{ext}',
          )
          aluno.foto = data
        except Exception as e:
          print(f'Erro ao processar foto webcam: {e}')

      aluno.save()
      return redirect('alunos:carteirinha', aluno_id=aluno.id)
  else:
    form = AlunoForm()

  return render(request, 'alunos/cadastrar_aluno.html', {'form': form})


@login_required
def lista_alunos(request):
  alunos = Aluno.objects.all()
  return render(request, 'alunos/lista_alunos.html', {'alunos': alunos})


@login_required
def carteirinha(request, aluno_id):
  aluno = get_object_or_404(Aluno, id=aluno_id)
  return render(request, 'alunos/carteirinha.html', {'aluno': aluno})


@csrf_exempt
def salvar_resultado(request):
  if request.method == 'POST':
    try:
      data = json.loads(request.body)
      aluno_id = data.get('aluno_id')

      aluno = Aluno.objects.get(id=aluno_id)
      ResultadoLeitura.objects.create(
          aluno=aluno,
          pontuacao_total=data.get('pontuacao', 0),
          palavras_acertadas=data.get('acertos', 0),
          palavras_ignoradas=data.get('erros', 0),
          palavras_com_demora=data.get('demoradas', []),
          palavras_puladas=data.get('puladas', []),
          palavras_erradas=data.get('erradas', []),
      )
      return JsonResponse(
          {'status': 'sucesso', 'message': 'Resultado salvo com sucesso!'}
      )
    except Aluno.DoesNotExist:
      return JsonResponse(
          {'status': 'erro', 'message': 'Aluno não encontrado.'}, status=404
      )
    except json.JSONDecodeError:
      return JsonResponse(
          {'status': 'erro', 'message': 'JSON inválido.'}, status=400
      )
    except Exception as e:
      return JsonResponse({'status': 'erro', 'message': str(e)}, status=500)

  return JsonResponse(
      {'status': 'erro', 'message': 'Método inválido.'}, status=400
  )


def _extrair_lista_palavras(valor_campo):
    """
    Extrai e normaliza uma lista de textos de palavras a partir de:
    - Strings JSON (listas de strings ou de dicionários)
    - Listas Python (com strings ou dicionários)
    - Strings separadas por vírgula
    """
    if not valor_campo:
        return []

    dados = valor_campo

    # 1. Se for string, tenta fazer parse de JSON
    if isinstance(valor_campo, str):
        valor_str = valor_campo.strip()
        if not valor_str or valor_str == '[]':
            return []
        try:
            dados = json.loads(valor_str)
        except (json.JSONDecodeError, TypeError):
            # Caso seja string simples delimitada por vírgulas
            return [p.strip().upper() for p in valor_str.split(',') if p.strip()]

    palavras_extraidas = []

    # 2. Se for uma lista
    if isinstance(dados, list):
        for item in dados:
            if isinstance(item, dict):
                # Extrai apenas o texto da palavra, independente da chave usada
                palavra = item.get('palavra') or item.get('PALAVRA') or item.get('texto') or item.get('word')
                if palavra:
                    palavras_extraidas.append(str(palavra).strip().upper())
            elif item:
                palavras_extraidas.append(str(item).strip().upper())

    # 3. Se for um dicionário isolado
    elif isinstance(dados, dict):
        palavra = dados.get('palavra') or dados.get('PALAVRA') or dados.get('texto') or dados.get('word')
        if palavra:
            palavras_extraidas.append(str(palavra).strip().upper())

    return palavras_extraidas


@login_required
def api_ficha_aluno(request, aluno_id):
  try:
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    resultados = aluno.resultados.all().order_by('data_realizacao')

    if not resultados.exists():
      return JsonResponse({
          'nome_completo': aluno.nome_completo,
          'serie': aluno.serie or '',
          'turma': aluno.turma or '',
          'foto_url': aluno.foto.url if aluno.foto else None,
          'total_testes': 0,
          'ppm_medio': 0,
          'precisao_media': 0,
          'maior_pontuacao': 0,
          'palavras_demoradas': [],
          'palavras_puladas': [],
          'palavras_erradas': [],
          'historico_rotulos': [],
          'historico_pontos': [],
          'historico_ppm': [],
      })

    # Métricas Agregadas
    ppm_medio = int(resultados.aggregate(Avg('ppm'))['ppm__avg'] or 0)
    precisao_media = round(
        resultados.aggregate(Avg('precisao'))['precisao__avg'] or 0, 1
    )
    maior_pontuacao = (
        resultados.aggregate(Max('pontuacao_total'))['pontuacao_total__max']
        or 0
    )

    # Coleta de palavras com falhas de leitura
    demoradas, puladas, erradas = set(), set(), set()

    for r in resultados:
      demoradas.update(_extrair_lista_palavras(r.palavras_com_demora))
      puladas.update(
          _extrair_lista_palavras(getattr(r, 'palavras_puladas', []))
      )
      erradas.update(
          _extrair_lista_palavras(getattr(r, 'palavras_erradas', []))
      )

    # Histórico de até 10 avaliações para os gráficos
    ultimos_resultados = list(resultados[:10])
    labels = [
        f'Teste {idx + 1}' for idx, _ in enumerate(ultimos_resultados)
    ]
    pontos = [r.pontuacao_total or 0 for r in ultimos_resultados]
    ppms = [r.ppm or 0 for r in ultimos_resultados]

    return JsonResponse({
        'nome_completo': aluno.nome_completo,
        'serie': aluno.serie or '',
        'turma': aluno.turma or '',
        'foto_url': aluno.foto.url if aluno.foto else None,
        'total_testes': resultados.count(),
        'ppm_medio': ppm_medio,
        'precisao_media': precisao_media,
        'maior_pontuacao': maior_pontuacao,
        'palavras_demoradas': sorted(list(demoradas)),
        'palavras_puladas': sorted(list(puladas)),
        'palavras_erradas': sorted(list(erradas)),
        'historico_rotulos': labels,
        'historico_pontos': pontos,
        'historico_ppm': ppms,
    })

  except Exception as e:
    # Retorna o erro em formato JSON estruturado para depuração direta
    return JsonResponse({'status': 'erro', 'message': str(e)}, status=500)