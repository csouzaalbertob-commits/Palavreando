import sys
from django.apps import AppConfig

class PalavraConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'palavra'

    def ready(self):
        # Garante que roda apenas no servidor (evita comandos como makemigrations/shell)
        is_server = any(cmd in sys.argv for cmd in ['runserver', 'gunicorn', 'uwsgi', 'daphne']) or 'gunicorn' in sys.argv[0]

        if is_server:
            from .seguranca import validar_arquivos_e_ambiente, verificar_banco_assincrono
            
            # 1. Checa variáveis/pastas
            validar_arquivos_e_ambiente()
            
            # 2. Testa banco em segundo plano sem emitir RuntimeWarning
            verificar_banco_assincrono()