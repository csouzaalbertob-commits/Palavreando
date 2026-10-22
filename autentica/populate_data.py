import csv
import os
from django.conf import settings
from django.db import transaction
from autentica.models import DRE, Cidade, Escola


def popular_dados_iniciais():
  if Cidade.objects.exists() and Escola.objects.exists():
    return

  csv_path = os.path.join(settings.BASE_DIR, 'escolas_para.csv')

  if not os.path.exists(csv_path):
    print(f'\n[ERRO POPULATE] Arquivo CSV não encontrado em: {csv_path}\n')
    return

  # Identifica automaticamente o nome do campo de código INEP no Model Escola
  campos_escola = [f.name for f in Escola._meta.get_fields()]
  campo_inep = None
  for possivel_nome in [
      'codigo_inep',
      'inep',
      'cod_inep',
      'codigo',
      'inep_code',
  ]:
    if possivel_nome in campos_escola:
      campo_inep = possivel_nome
      break

  print('\n[INICIANDO POVOAMENTO] Lendo escolas_para.csv...')

  try:
    cidades_criadas = 0
    dres_criadas = 0
    escolas_criadas = 0
    total_linhas = 0

    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
      reader = csv.DictReader(file)

      with transaction.atomic():
        for row in reader:
          total_linhas += 1

          # 1. Filtra apenas escolas do Pará (PA)
          uf = row.get('UF', '').strip().upper()
          if uf != 'PA':
            continue

          nome_municipio = row.get('Município', '').strip()
          nome_escola = row.get('Escola', '').strip()
          codigo_inep_val = row.get('Código INEP', '').strip()

          if not nome_municipio or not nome_escola:
            continue

          # 2. Cadastra/Obtém a Cidade (PA)
          cidade_obj, created_c = Cidade.objects.get_or_create(
              nome=nome_municipio.title(), defaults={'uf': 'PA'}
          )
          if created_c:
            cidades_criadas += 1

          # 3. Define/Cadastra a DRE vinculada à Cidade
          nome_dre = f'DRE - {nome_municipio.title()}'
          dre_obj, created_d = DRE.objects.get_or_create(
              nome=nome_dre, cidade=cidade_obj
          )
          if created_d:
            dres_criadas += 1

          # 4. Monta os valores do objeto Escola (passando tanto DRE quanto Cidade)
          defaults_escola = {}
          if campo_inep and codigo_inep_val:
            defaults_escola[campo_inep] = codigo_inep_val

          # Passa cidade e DRE explicitamente para a Escola
          params_busca = {'nome': nome_escola, 'dre': dre_obj}
          if 'cidade' in campos_escola:
            params_busca['cidade'] = cidade_obj

          _, created_e = Escola.objects.get_or_create(
              **params_busca, defaults=defaults_escola
          )
          if created_e:
            escolas_criadas += 1

    print('\n==========================================')
    print(' Cidade/DRE/Escola populados com sucesso!')
    print(f' - Total de linhas analisadas: {total_linhas}')
    print(f' - Cidades cadastradas (PA): {cidades_criadas}')
    print(f' - DREs cadastradas: {dres_criadas}')
    print(f' - Escolas do PA cadastradas: {escolas_criadas}')
    print('==========================================\n')

  except Exception as e:
    print(f'\n[ERRO AO POPULAR BANCO]: {e}\n')