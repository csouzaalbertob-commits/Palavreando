from django.apps import AppConfig

class AutenticaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'autentica'

    def ready(self):
        # Executa apenas na inicialização principal do servidor
        import os, sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv or 'wsgi' in sys.argv:
            from autentica.populate_data import popular_dados_iniciais
            popular_dados_iniciais()

        if os.environ.get('RUN_MAIN') == 'true':
            from apscheduler.schedulers.background import BackgroundScheduler
            from sistema.backup import realizar_backup_banco

            scheduler = BackgroundScheduler()
            
            # Agenda o backup para todo DOMINGO (sun) às 10h00
            scheduler.add_job(
                realizar_backup_banco, 
                'cron', 
                day_of_week='sun', 
                hour=10, 
                minute=0
            )
            
            scheduler.start()