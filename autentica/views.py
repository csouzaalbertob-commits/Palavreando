import json
from collections import Counter, defaultdict
from django.db.models import Count

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum, Value, Avg, Max, Prefetch
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.http import JsonResponse

from alunos.models import Aluno, ResultadoLeitura
from palavra.models import HistoricoDitado, ResultadoOuvirEFalar, RespostaCompreensao, Historia
from .forms import (
    AtualizarProfessorForm,
    CadastroProfessorForm,
    PerfilProfessorForm,
)
from .models import PerfilProfessor, DRE, Escola

app_name = 'autentica'


@login_required
def editar_perfil_professor(request):
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
    professor = request.user

    # 1. Total de Alunos Cadastrados do Professor Logado
    alunos = Aluno.objects.filter(professor=professor)
    total_alunos = alunos.count()

    # 2. Top 10 Alunos do Professor Logado para o Gráfico Combinado
    # Considera tanto o Desafio 60s quanto o Ouvir e Falar
    top_alunos = alunos[:10]

    labels_grafico = []
    dados_60s = []
    dados_ouvir_falar = []
    dados_projecao = []

    for aluno in top_alunos:
        nome_curto = aluno.nome_completo.split()[0] if getattr(aluno, 'nome_completo', None) else str(aluno)
        labels_grafico.append(nome_curto)

        # Maior pontuação em cada modalidade
        max_60s = ResultadoLeitura.objects.filter(aluno=aluno).aggregate(Max('pontuacao_total'))['pontuacao_total__max'] or 0
        max_ouvir_falar = ResultadoOuvirEFalar.objects.filter(aluno=aluno).aggregate(Max('pontuacao_total'))['pontuacao_total__max'] or 0

        dados_60s.append(max_60s)
        dados_ouvir_falar.append(max_ouvir_falar)

        # Projeção de evolução estimada em +15% sobre o melhor desempenho combinado
        maior_combinado = max(max_60s, max_ouvir_falar)
        projecao = round(maior_combinado * 1.15, 1)
        dados_projecao.append(projecao)

    # 3. Lista de Recordes de Leitura com Cálculo Real de Tendência
    alunos_recordes = []
    for aluno in alunos:
        # Busca histórico do Desafio 60s
        historico_60s = list(ResultadoLeitura.objects.filter(aluno=aluno).order_by('data_realizacao'))
        # Busca histórico do Ouvir e Falar
        historico_of = list(ResultadoOuvirEFalar.objects.filter(aluno=aluno).order_by('data_realizacao'))

        total_t_60s = len(historico_60s)
        total_t_of = len(historico_of)
        total_testes = total_t_60s + total_t_of

        # Maior pontuação global e data do recorde
        res_60s_max = ResultadoLeitura.objects.filter(aluno=aluno).order_by('-pontuacao_total').first()
        res_of_max = ResultadoOuvirEFalar.objects.filter(aluno=aluno).order_by('-pontuacao_total').first()

        pts_60s = res_60s_max.pontuacao_total if res_60s_max else 0
        pts_of = res_of_max.pontuacao_total if res_of_max else 0

        if pts_of > pts_60s:
            maior_pontuacao = pts_of
            data_recorde = res_of_max.data_realizacao
        else:
            maior_pontuacao = pts_60s
            data_recorde = res_60s_max.data_realizacao if res_60s_max else None

        # --- Lógica de Cálculo de Tendência Real ---
        # Une todos os testes de ambas as modalidades por data de realização
        todos_testes = sorted(
            [{'pts': r.pontuacao_total, 'data': r.data_realizacao} for r in historico_60s] +
            [{'pts': r.pontuacao_total, 'data': r.data_realizacao} for r in historico_of],
            key=lambda x: x['data']
        )

        tendencia = 'sem_dados'
        taxa_evolucao = 0

        if len(todos_testes) >= 2:
            ultimo = todos_testes[-1]['pts']
            penultimo = todos_testes[-2]['pts']

            if penultimo > 0:
                variacao = round(((ultimo - penultimo) / penultimo) * 100)
            else:
                variacao = 100 if ultimo > 0 else 0

            taxa_evolucao = abs(variacao)
            if variacao > 0:
                tendencia = 'subindo'
            elif variacao < 0:
                tendencia = 'caindo'
            else:
                tendencia = 'estavel'
        elif len(todos_testes) == 1:
            tendencia = 'inicial'

        alunos_recordes.append({
            'aluno': aluno,
            'total_testes': total_testes,
            'maior_pontuacao': maior_pontuacao,
            'data_recorde': data_recorde,
            'tendencia': tendencia,
            'taxa_evolucao': taxa_evolucao,
        })

    # Ordenar lista de recordes pela maior pontuação
    alunos_recordes.sort(key=lambda x: x['maior_pontuacao'], reverse=True)

    # 4. Melhor Aluno e Aluno com Dificuldade do Professor Logado
    melhor_aluno = None
    aluno_dificuldade = None

    if alunos_recordes:
        melhor_item = alunos_recordes[0]
        if melhor_item['maior_pontuacao'] > 0:
            melhor_aluno = {
                'nome_completo': melhor_item['aluno'].nome_completo,
                'maior_pontuacao': melhor_item['maior_pontuacao'],
                'data_recorde': melhor_item['data_recorde'],
            }

        pior_item = alunos_recordes[-1]
        aluno_dificuldade = {
            'nome_completo': pior_item['aluno'].nome_completo,
            'menor_pontuacao': pior_item['maior_pontuacao'],
            'data_recorde': pior_item['data_recorde'],
        }

    # 5. Ranking de Batalhas apenas dos Alunos do Professor Logado
    ranking_alunos = Aluno.objects.filter(professor=professor).annotate(
        pontuacao_total=Coalesce(Sum('resultados__pontuacao_total'), Value(0))
    ).order_by('-pontuacao_total')[:5]

    # 6. Palavras com Maior Demora (Consolida registros do 60s e do Ouvir e Falar)
    contador_demora = Counter()

    # Leitura do modelo de 60s
    resultados_60s = ResultadoLeitura.objects.filter(aluno__professor=professor).exclude(palavras_com_demora='')
    for res in resultados_60s:
        if res.palavras_com_demora:
            try:
                palavras = json.loads(res.palavras_com_demora) if isinstance(res.palavras_com_demora, str) else res.palavras_com_demora
                for p in palavras:
                    texto_p = p.get('palavra', '') if isinstance(p, dict) else str(p)
                    if texto_p:
                        contador_demora[texto_p.upper()] += 1
            except Exception:
                pass

    # Leitura do modelo de Ouvir e Falar
    resultados_of = ResultadoOuvirEFalar.objects.filter(aluno__professor=professor).exclude(palavras_com_demora=[])
    for res in resultados_of:
        if res.palavras_com_demora:
            try:
                palavras = json.loads(res.palavras_com_demora) if isinstance(res.palavras_com_demora, str) else res.palavras_com_demora
                for p in palavras:
                    texto_p = p.get('palavra', '') if isinstance(p, dict) else str(p)
                    if texto_p:
                        contador_demora[texto_p.upper()] += 1
            except Exception:
                pass

    palavras_dificuldade = [
        {'texto': p, 'total_atrasos': qtd} for p, qtd in contador_demora.most_common(5)
    ]

    # 7. Histórico de Ditados Aninhado por Aluno
    alunos_ditado = (
        Aluno.objects.filter(professor=professor, historicos_ditado__isnull=False)
        .prefetch_related(
            Prefetch(
                'historicos_ditado',
                queryset=HistoricoDitado.objects.select_related('frase').order_by('-data_registro')
            )
        )
        .distinct()
    )

    cards_alunos_ditado = []
    for aluno in alunos_ditado:
        historicos = list(aluno.historicos_ditado.all())
        qtd_ditados = len(historicos)
        
        if qtd_ditados > 0:
            total_pontos = sum(h.pontuacao for h in historicos)
            total_tempo = sum(getattr(h, 'tempo_gasto', 0) for h in historicos)
            media_pontos = round(total_pontos / qtd_ditados)

            cards_alunos_ditado.append({
                'aluno': aluno,
                'historicos': historicos,
                'qtd_ditados': qtd_ditados,
                'media_pontos': media_pontos,
                'tempo_total': total_tempo,
            })

    #8. Leitura Dinamica de Compreensão (Histórias)
    # Busca leituras realizadas e agrupa os blocos lidos por aluno/história
    leituras_recentes = RespostaCompreensao.objects.select_related('aluno', 'bloco__historia')\
        .order_by('-data_realizacao')
    # Estrutura os dados agrupando por Aluno e História
    historico_leituras = {}
    for resp in leituras_recentes:
        aluno = resp.aluno
        historia = resp.bloco.historia
        chave = (aluno.id, historia.id)

        if chave not in historico_leituras:
            historico_leituras[chave] = {
                'aluno_nome': aluno.nome_completo,
                'historia_titulo': historia.titulo,
                'total_blocos_historia': historia.blocos.count(),
                'blocos_lidos': 0,
                'respostas': [],
                'ultima_data': resp.data_realizacao
            }

        historico_leituras[chave]['blocos_lidos'] += 1
        historico_leituras[chave]['respostas'].append({
            'ordem_bloco': resp.bloco.ordem_bloco,
            'trecho_texto': resp.bloco.trecho_texto,
            'resposta_aluno': resp.resposta_aluno,
            'tipo_resposta': resp.tipo_resposta,
            'tempo': resp.tempo_resposta_segundos
        })

    # Contexto Completo
    context = {
        'total_alunos': total_alunos,
        'melhor_aluno': melhor_aluno,
        'aluno_dificuldade': aluno_dificuldade,
        'alunos_recordes': alunos_recordes,
        'ranking_alunos': ranking_alunos,
        'palavras_dificuldade': palavras_dificuldade,
        'cards_alunos_ditado': cards_alunos_ditado,
        'labels_grafico_json': json.dumps(labels_grafico),
        'dados_60s_json': json.dumps(dados_60s),
        'dados_ouvir_falar_json': json.dumps(dados_ouvir_falar),
        'dados_projecao_json': json.dumps(dados_projecao),
        'leituras': list(historico_leituras.values()),
    }

    return render(request, 'autentica/dashboard.html', context)

def buscar_dres_por_cidade(request):
    cidade_id = request.GET.get('cidade_id')
    dres = DRE.objects.filter(cidade_id=cidade_id).values('id', 'nome')
    return JsonResponse(list(dres), safe=False)

def buscar_escolas_por_dre(request):
    dre_id = request.GET.get('dre_id')
    escolas = Escola.objects.filter(dre_id=dre_id).values('id', 'nome')
    return JsonResponse(list(escolas), safe=False)

def cadastro_professor(request):
    if request.user.is_authenticated:
        return redirect('autentica:dashboard')

    if request.method == 'POST':
        form = CadastroProfessorForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(
                request,
                f'Conta criada com sucesso! Bem-vindo, Prof.'
                f' {user.first_name or user.username}.',
            )
            return redirect('autentica:dashboard')
        else:
            messages.error(request, 'Por favor, corrija os erros apontados no formulário.')
    else:
        form = CadastroProfessorForm()

    return render(request, 'autentica/cadastro_professor.html', {'form': form})