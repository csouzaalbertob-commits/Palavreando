from django.contrib import admin
from .models import HistoricoDitado

#app_name = "palavra"
@admin.register(HistoricoDitado)
class HistoricoDitadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario_professor', 'aluno', 'frase', 'pontuacao', 'data_envio')
    list_filter = ('usuario_professor', 'data_envio', 'pontuacao')
    search_fields = ('texto_original', 'texto_digitado', 'aluno__nome')