import sys
from django.apps import AppConfig

class PalavraConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'palavra'

    def ready(self):
        # 1. Comandos de gerenciamento que NÃO devem executar a validação
        comandos_desativados = {
            'makemigrations', 'migrate', 'collectstatic', 
            'createsuperuser', 'shell', 'test', 'check'
        }

        # 2. Verifica se algum desses comandos foi passado no terminal
        is_management = any(arg in comandos_desativados for arg in sys.argv)

        # 3. Só importa e executa a validação se for a subida do servidor (runserver/gunicorn/daphne)
        if not is_management:
            from sistema.seguranca import validar_arquivos_e_ambiente
            validar_arquivos_e_ambiente()