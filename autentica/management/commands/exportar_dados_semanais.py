from django.core.management.base import BaseCommand
from sistema.exportacao_dados import realizar_backup_banco

class Command(BaseCommand):
    help = 'Executa a rotina semanal de exportação de dados acadêmicos por e-mail'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando exportação semanal de dados...')
        try:
            realizar_backup_banco()
            self.stdout.write(self.style.SUCCESS('Exportação concluída e enviada com sucesso!'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Falha na execução da rotina: {e}'))