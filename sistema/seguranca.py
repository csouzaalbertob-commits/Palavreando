import os
import sys
import threading
import time
from django.conf import settings

def validar_arquivos_e_ambiente():
    """Valida configurações, diretórios e ambiente sem tocar no ORM/Banco."""
    alertas = []
    erros = []

    if settings.DEBUG:
        alertas.append("DEBUG está ativado! Desative em ambiente de produção (aprendi.arvity.com.br).")

    if getattr(settings, 'SECRET_KEY', '') in ['', 'django-insecure-dummy-key', 'sua_chave_padrao']:
        erros.append("SECRET_KEY é insegura!")

    diretorios_criticos = [
        ('MEDIA_ROOT', getattr(settings, 'MEDIA_ROOT', None)),
        ('STATIC_ROOT', getattr(settings, 'STATIC_ROOT', None)),
    ]

    for nome, caminho in diretorios_criticos:
        if not caminho:
            alertas.append(f"{nome} não está configurado.")
        elif not os.path.exists(caminho):
            try:
                os.makedirs(caminho, exist_ok=True)
                print(f"  📁 Diretório {nome} criado: {caminho}")
            except Exception as e:
                erros.append(f"Não foi possível criar {nome}: {str(e)}")

    if alertas:
        for a in alertas:
            print(f"  ⚠️ {a}")

    if erros and not settings.DEBUG:
        print("\n❌ ERROS CRÍTICOS DE AMBIENTE DETECTADOS!")
        sys.exit(1)


def verificar_banco_assincrono():
    """Executa o teste de banco de dados após o carregamento completo do Django."""
    def _testar():
        time.sleep(0.5)  # Aguarda o encerramento do ciclo ready()
        try:
            from django.db import connection
            connection.ensure_connection()
            print("  ✅ Conexão com o Banco de Dados verificada com sucesso.\n")
        except Exception as e:
            print(f"  ❌ Falha de conexão com o banco de dados: {e}")

    # Roda em thread separada para não bloquear o ciclo de inicialização do AppConfig
    thread = threading.Thread(target=_testar, daemon=True)
    thread.start()