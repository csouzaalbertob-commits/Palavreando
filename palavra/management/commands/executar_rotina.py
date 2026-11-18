from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Executa as rotinas automáticas diárias do sistema Palavreando'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando rotina automática...')
        try:
            # Chame aqui a função exata que o seu agendador antigo chamava
            # enviar_relatorio_diario()
            
            self.stdout.write(self.style.SUCCESS('Rotina concluída com sucesso!'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erro ao executar rotina: {e}'))