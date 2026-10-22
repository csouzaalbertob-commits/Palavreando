import base64
import json
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Avg, Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from autentica.models import Escola
from .forms import AlunoForm
from .models import Aluno, ResultadoLeitura

app_name = 'alunos'

@login_required
def lista_alunos(request):
  # 1. Identifica a escola vinculada ao perfil do professor logado
  perfil_prof = getattr(request.user, 'perfilprofessor', None)
  escola_professor = perfil_prof.escola if perfil_prof else None

  # 2. Filtra os alunos de acordo com a escola e professor
  if escola_professor:
    queryset = Aluno.objects.filter(
        escola=escola_professor, professor=request.user
    )
  elif request.user.is_superuser:
    queryset = Aluno.objects.all()
  else:
    queryset = Aluno.objects.none()

  # 3. Aplica busca por nome ou turma
  query = request.GET.get('q')
  if query:
    queryset = queryset.filter(
        Q(nome_completo__icontains=query) | Q(turma__icontains=query)
    )

  alunos = queryset.select_related('escola').order_by('nome_completo')

  return render(request, 'alunos/lista_alunos.html', {'alunos': alunos})


@login_required
def cadastrar_aluno(request):
  
  escola_prof = None
  if (
      hasattr(request.user, 'perfilprofessor')
      and request.user.perfilprofessor.escola_id
  ):
    escola_prof = request.user.perfilprofessor.escola
  else:
    escola_prof = Escola.objects.first()
  if not escola_prof:
    messages.error(
      request,
      "Nenhuma escola cadastrada no sistema. Cadastre uma escola antes de"
      " Criar alunos.",
    )
    return redirect("autentica:dashboard")
  
  if request.method == 'POST':
    form = AlunoForm(request.POST, request.FILES)
    if form.is_valid():
      aluno = form.save(commit=False)

      aluno.professor = request.user
      aluno.escola = escola_prof

      foto_base64 = request.POST.get('foto_webcam')
      if foto_base64 and 'data:image' in foto_base64:
        format, imgstr = foto_base64.split(';base64,')
        ext = format.split('/')[-1]
        data = ContentFile(
            base64.b64decode(imgstr), name=f'aluno_{aluno.nome_completo}.{ext}'
        )
        aluno.foto = data

      aluno.save()
      messages.success(request, f'Aluno {aluno.nome_completo} cadastrado com sucesso!')
      return redirect('alunos:carteirinha', aluno_id=aluno.id)
  else:
    form = AlunoForm()

  return render(request, 'alunos/cadastrar_aluno.html', {'form': form})


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
    if not valor_campo:
        return []

    dados = valor_campo
    if isinstance(valor_campo, str):
        valor_str = valor_campo.strip()
        if not valor_str or valor_str == '[]':
            return []
        try:
            dados = json.loads(valor_str)
        except (json.JSONDecodeError, TypeError):
            return [p.strip().upper() for p in valor_str.split(',') if p.strip()]

    palavras_extraidas = []

    if isinstance(dados, list):
        for item in dados:
            if isinstance(item, dict):
                palavra = (
                    item.get('palavra')
                    or item.get('palavra_real')
                    or item.get('texto')
                )
                if palavra:
                    errada = item.get('palavra_errada')
                    if errada:
                        palavras_extraidas.append(f"{str(palavra).upper()} (falou: {errada})")
                    else:
                        palavras_extraidas.append(str(palavra).strip().upper())
            elif item:
                palavras_extraidas.append(str(item).strip().upper())

    return palavras_extraidas


@login_required
def api_ficha_aluno(request, aluno_id):
    try:
        aluno = Aluno.objects.get(pk=aluno_id)
        resultados = ResultadoLeitura.objects.filter(aluno=aluno).order_by('data_realizacao')

        total_testes = resultados.count()
        media_ppm = resultados.aggregate(Avg('ppm'))['ppm__avg'] or 0
        media_precisao = resultados.aggregate(Avg('precisao'))['precisao__avg'] or 0
        maior_pontuacao = resultados.aggregate(Max('pontuacao_total'))['pontuacao_total__max'] or 0

        labels_datas = []
        pontuacoes_historico = []
        
        for res in resultados:
            labels_datas.append(res.data_realizacao.strftime('%d/%m %H:%M'))
            pontuacoes_historico.append(res.pontuacao_total)

        predicao = []
        tendencia_texto = "Estável"

        if len(pontuacoes_historico) >= 2:
            ultimo = pontuacoes_historico[-1]
            penultimo = pontuacoes_historico[-2]
            diferenca = ultimo - penultimo
            labels_datas.extend(['Prox. 1', 'Prox. 2'])
            predicao = [None] * (len(pontuacoes_historico) - 1)
            predicao.append(ultimo)
            p1 = max(0, round(ultimo + diferenca))
            p2 = max(0, round(p1 + diferenca))
            predicao.extend([p1, p2])

            if diferenca > 0:
                tendencia_texto = f"Crescimento (+{diferenca} pts)"
            elif diferenca < 0:
                tendencia_texto = f"Apoio necessário ({diferenca} pts)"
        else:
            predicao = pontuacoes_historico.copy()

        # Consolidação unificada de dados de diagnósticos
        palavras_demoradas, palavras_ignoradas, palavras_errou = [], [], []
        for res in resultados:
            palavras_demoradas.extend(_extrair_lista_palavras(res.palavras_com_demora))
            palavras_ignoradas.extend(_extrair_lista_palavras(res.palavras_puladas))
            palavras_errou.extend(_extrair_lista_palavras(res.palavras_erradas))

        data = {
            'sucesso': True,
            'nome': aluno.nome_completo,
            'serie': getattr(aluno, 'serie', ''),
            'turma': getattr(aluno, 'turma', ''),
            'foto_url': aluno.foto.url if aluno.foto else None,
            'total_testes': total_testes,
            'ppm': round(media_ppm, 1),
            'precisao': round(media_precisao, 1),
            'maior_pontuacao': maior_pontuacao,
            'labels_datas': labels_datas,
            'historico': pontuacoes_historico,
            'predicao': predicao,
            'tendencia_texto': tendencia_texto,
            'palavras_demoradas': list(set(palavras_demoradas)),
            'palavras_ignoradas': list(set(palavras_ignoradas)),
            'palavras_errou': list(set(palavras_errou)),
        }
        return JsonResponse(data)

    except Aluno.DoesNotExist:
        return JsonResponse({'sucesso': False, 'erro': 'Aluno não encontrado'}, status=404)