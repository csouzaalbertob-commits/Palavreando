from django.apps import AppConfig

class PalavraConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'palavra'

    def ready(self):
        import palavra.signals  # <--- Essencial para ativar os sinais ao subir o servidor