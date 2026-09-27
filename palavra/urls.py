from django.urls import path
from . import views

app_name = 'palavra'

urlpatterns = [
    #path('avaliacao/', views.tela_avaliacao, name='tela_avaliacao'),
    path('palavras/deletar/<int:palavra_id>/', views.deletar_palavra, name='deletar_palavra'),
    path('gerenciar/', views.gerenciar_palavras, name='gerenciar_palavras'),
    path('selecionar/', views.selecionar_aluno, name='selecionar_aluno'),
    path('exibir_palavras/', views.exibir_palavras, name='exibir_palavras'),
    path('registrar-resultado/', views.registrar_resposta, name='registrar_resposta'),
    path('ranking/', views.ranking_recordes, name='ranking'),
    path('qrcode/<int:aluno_id>/<int:prof_id>/', views.gerar_qrcode_aluno, name='gerar_qrcode_aluno'),
    path('modo/', views.modo, name='modo'),
    path('batalha/', views.modo_batalha, name='iniciar_batalha'),
    #solicitacao de nivel
    path('api/solicitacao/criar/', views.criar_solicitacao, name='criar_solicitacao'),
    path('api/solicitacao/checar/<int:solicitacao_id>/', views.checar_status_solicitacao, name='checar_status_solicitacao'),
    path('api/solicitacao/pendentes/', views.buscar_solicitacoes_pendentes, name='buscar_solicitacoes_pendentes'),
    path('api/solicitacao/responder/', views.responder_solicitacao, name='responder_solicitacao'),
    #leitura e escrita
    path('leitura-escrita/', views.leitura_escrita, name='leitura_escrita'),
    #ditado
    path('ditado/', views.ditado, name='ditado'),
    path('ditado/gerenciar/', views.cadastrar_frase, name='cadastrar_frase'),
    path('ditado/eliminar/<int:frase_id>/', views.eliminar_frase, name='eliminar_frase'),
]