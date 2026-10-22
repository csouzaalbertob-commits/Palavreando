from django.core.management.base import BaseCommand
from autentica.populate_data import popular_dados_iniciais


class Command(BaseCommand):
  help = 'Popula Cidades, DREs e Escolas a partir do CSV'

  def handle(self, *args, **kwargs):
    popular_dados_iniciais()
    self.stdout.write(
        self.style.SUCCESS('Processo de povoamento executado!')
    )