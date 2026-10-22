import os
import json
from datetime import datetime
from django.core.management import call_command
from django.core.mail import EmailMessage
from django.conf import settings

def realizar_backup_banco():
    """Gera o dump em JSON apenas dos dados de desempenho dos alunos nos módulos."""
    data_atual = datetime.now().strftime('%Y-%m-%d_%H-%M')
    nome_arquivo = f"desempenho_alunos_{data_atual}.json"
    caminho_arquivo = os.path.join(settings.BASE_DIR, nome_arquivo)

    # Lista apenas os models relacionados ao desempenho acadêmico/módulos
    modelos_desempenho = [
        'alunos.aluno',
        'alunos.resultadoleitura',     # Desafio 60s
        'palavra.resultadoouvirefalar', # Ouvir e Falar
        'palavra.historicoditado',      # Ditado Eletrônico
    ]

    try:
        # 1. Gera o arquivo JSON filtrado apenas pelos modelos informados
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            call_command('dumpdata', *modelos_desempenho, '--indent', '2', stdout=f)

        print(f"[{datetime.now()}] Dump de desempenho gerado com sucesso: {nome_arquivo}")

        # 2. Envia por e-mail
        assunto = f"📊 [Palavreando Mestrado] Relatório de Desempenho dos Alunos - {data_atual}"
        mensagem = (
            "Olá Carlos,\n\n"
            "Segue em anexo o arquivo JSON contendo exclusivamente os dados de desempenho "
            "dos alunos registrados nos 3 módulos (Desafio 60s, Ouvir e Falar, Ditado Eletrônico) "
            "para sua análise no Mestrado.\n\n"
            "Atenciosamente,\nSistema Palavreando"
        )

        email = EmailMessage(
            subject=assunto,
            body=mensagem,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=['prof.carlospopo@gmail.com'],
        )

        email.attach_file(caminho_arquivo)
        email.send()

        print(f"[{datetime.now()}] Backup de desempenho enviado com sucesso por e-mail!")

    except Exception as e:
        print(f"Erro ao processar backup de desempenho: {e}")

    finally:
        # 3. Remove o arquivo temporário após o envio
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)