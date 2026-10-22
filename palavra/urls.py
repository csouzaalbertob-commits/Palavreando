from django.urls import path
from . import views

app_name = 'palavra'

urlpatterns = [
    #path('avaliacao/', views.tela_avaliacao, name='tela_avaliacao'),
    path('palavras/deletar/<int:palavra_id>/', views.deletar_palavra, name='deletar_palavra'),
    path('gerenciar/', views.gerenciar_palavras, name='gerenciar_palavras'),
    path('selecionar/', views.selecionar_aluno, name='selecionar_aluno'),
    path('exibir_palavras/', views.exibir_palavras, name='exibir_palavras'),
    path('frases/cadastrar/', views.cadastrar_frase, name='cadastrar_frase'),
    path('frases/excluir/<int:frase_id>/', views.excluir_frase, name='excluir_frase'),
    path('registrar-resultado/', views.registrar_resposta, name='registrar_resposta'),
    path('ranking/', views.ranking_recordes, name='ranking'),
    path('qrcode/<int:aluno_id>/<int:prof_id>/', views.gerar_qrcode_aluno, name='gerar_qrcode_aluno'),

    #Modos
    path('modo/', views.modo, name='modo'),
    path('60s/', views.jogo_60s, name='l60s'),
    path('batalha/', views.modo_batalha, name='iniciar_batalha'),
    path('ouvir-falar/', views.ouvir_falar, name='ouvir_falar'),
    path('registrar-ouvir-falar/', views.registrar_resultado_ouvir_falar, name='registrar_resultado_ouvir_falar'),
    path('ditado/', views.ditado, name='ditado'),
    path('salvar-ditado/', views.salvar_resultado_ditado, name='salvar_resultado_ditado'),

    #solicitacao de nivel
    path('api/solicitacao/criar/', views.criar_solicitacao, name='criar_solicitacao'),
    path('api/solicitacao/checar/<int:solicitacao_id>/', views.checar_status_solicitacao, name='checar_status_solicitacao'),
    path('api/solicitacao/pendente/', views.checar_solicitacao_pendente, name='api_solicitacao_pendente'),
    path('api/solicitacao/responder/<int:solicitacao_id>/', views.responder_solicitacao, name='api_solicitacao_responder'),

    # Leitura de Histórias e Compreensão
    path('historia/cadastrar/', views.cadastrar_historia, name='cadastrar_historia'),
    path('historia/excluir/<int:historia_id>/', views.excluir_historia, name='excluir_historia'),
    path('api/historias/por-nivel/', views.listar_historias_por_nivel, name='api_historias_por_nivel'),
    path('historia/editar/<int:historia_id>/', views.editar_historia, name='editar_historia'),
    path('historia/leitura/<int:aluno_id>/', views.iniciar_leitura_historia, name='iniciar_leitura_historia'),
    path('historia/salvar-resposta/', views.salvar_resposta_historia, name='salvar_resposta_historia'),
    path('historia/resposta/<int:resposta_id>/', views.detalhe_resposta_historia_professor, name='detalhe_resposta_professor'),
]