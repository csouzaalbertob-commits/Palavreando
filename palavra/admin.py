from django.contrib import admin
from .models import HistoricoDitado, Historia, BlocoHistoria, RespostaCompreensao

#app_name = "palavra"

class BlocoHistoriaInline(admin.TabularInline):
    model = BlocoHistoria
    extra = 0
    readonly_fields = ('ordem_bloco', 'trecho_texto')

@admin.register(Historia)
class HistoriaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'nivel', 'data_cadastro', 'professor')
    list_filter = ('nivel', 'data_cadastro')
    search_fields = ('titulo', 'texto_completo')
    inlines = [BlocoHistoriaInline]

@admin.register(RespostaCompreensao)
class RespostaCompreensaoAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'get_historia', 'get_bloco', 'tipo_resposta', 'tempo_resposta_segundos', 'data_realizacao')
    list_filter = ('tipo_resposta', 'data_realizacao', 'bloco__historia')
    search_fields = ('aluno__nome_completo', 'resposta_aluno')

    def get_historia(self, obj):
        return obj.bloco.historia.titulo
    get_historia.short_description = "História"

    def get_bloco(self, obj):
        return f"Bloco {obj.bloco.ordem_bloco}"
    get_bloco.short_description = "Bloco"
@admin.register(HistoricoDitado)
class HistoricoDitadoAdmin(admin.ModelAdmin):
    list_display = (
        'aluno',
        'frase',
        'pontuacao',
        'erros_palavra',
        'tempo_gasto',
        'data_registro'
    )
    list_filter = (
        'aluno',
        'data_registro'
    )
    search_fields = ('aluno__nome', 'texto_original', 'texto_digitado')