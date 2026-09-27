import os
import re
import unicodedata
from pathlib import Path

import pandas as pd

from django.core.management.base import BaseCommand
from django.db import transaction

from dados_censo.models import Escola


# ==========================================================
# CONFIGURAÇÃO
# ==========================================================

ANO = 2025

BASE_DIR = Path(__file__).resolve().parents[4]

DIRETORIO_CENSO = (
    BASE_DIR
    / "dados"
    / "censo"
    / str(ANO)
)


# ==========================================================
# UTILIDADES
# ==========================================================

def normalizar_nome(valor):

    valor = str(valor)

    valor = unicodedata.normalize(
        "NFKD",
        valor
    )

    valor = "".join(
        c for c in valor
        if not unicodedata.combining(c)
    )

    valor = valor.upper()

    valor = re.sub(
        r"[^A-Z0-9]+",
        "_",
        valor
    )

    return valor.strip("_")


def normalizar_colunas(df):

    df = df.copy()

    df.columns = [
        normalizar_nome(c)
        for c in df.columns
    ]

    return df


def encontrar_coluna(df, candidatos):

    colunas = set(df.columns)

    for candidato in candidatos:

        candidato = normalizar_nome(
            candidato
        )

        if candidato in colunas:
            return candidato

    return None


def encontrar_coluna_por_parte(df, palavras):

    for coluna in df.columns:

        coluna_normalizada = normalizar_nome(
            coluna
        )

        if all(
            palavra in coluna_normalizada
            for palavra in palavras
        ):
            return coluna

    return None


def valor_int(valor):

    if pd.isna(valor):
        return 0

    try:
        return int(float(valor))
    except:
        return 0


def valor_bool(valor):

    if pd.isna(valor):
        return False

    texto = str(valor).strip().upper()

    return texto in [
        "1",
        "S",
        "SIM",
        "TRUE",
        "VERDADEIRO",
        "YES"
    ]


# ==========================================================
# LOCALIZAÇÃO DOS ARQUIVOS
# ==========================================================

def localizar_arquivo(pasta, palavras):

    arquivos = list(
        pasta.rglob("*.csv")
    )

    for arquivo in arquivos:

        nome = normalizar_nome(
            arquivo.name
        )

        if all(
            palavra in nome
            for palavra in palavras
        ):
            return arquivo

    return None


# ==========================================================
# LEITURA CSV
# ==========================================================

def ler_csv(arquivo):

    print()
    print("Lendo:")
    print(arquivo)

    tentativas = [
        (";", "latin1"),
        (";", "utf-8"),
        (",", "latin1"),
        (",", "utf-8"),
    ]

    ultimo_erro = None

    for sep, encoding in tentativas:

        try:

            df = pd.read_csv(
                arquivo,
                sep=sep,
                encoding=encoding,
                low_memory=False
            )

            if len(df.columns) > 1:

                return normalizar_colunas(
                    df
                )

        except Exception as erro:

            ultimo_erro = erro

    raise RuntimeError(
        f"Não foi possível ler {arquivo}: "
        f"{ultimo_erro}"
    )


# ==========================================================
# MOSTRA COLUNAS
# ==========================================================

def mostrar_colunas(df):

    print()
    print("=" * 70)
    print("COLUNAS ENCONTRADAS")
    print("=" * 70)

    for coluna in df.columns:
        print(coluna)

    print("=" * 70)


# ==========================================================
# COMANDO DJANGO
# ==========================================================

class Command(BaseCommand):

    help = (
        "Importa dados públicos do Censo Escolar "
        "para o banco do Palavreando."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--ano",
            type=int,
            default=2025
        )

        parser.add_argument(
            "--somente-colunas",
            action="store_true"
        )

        parser.add_argument(
            "--limite",
            type=int,
            default=None
        )

    def handle(self, *args, **options):

        ano = options["ano"]

        limite = options["limite"]

        somente_colunas = (
            options["somente_colunas"]
        )

        pasta = (
            BASE_DIR
            / "dados"
            / "censo"
            / str(ano)
        )

        if not pasta.exists():

            self.stdout.write(
                self.style.ERROR(
                    f"Pasta não encontrada:\n{pasta}"
                )
            )

            self.stdout.write(
                "Crie a pasta e coloque nela "
                "os microdados do Censo Escolar."
            )

            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Processando Censo Escolar {ano}"
            )
        )

        self.stdout.write(
            f"Pasta: {pasta}"
        )

        # ==================================================
        # LOCALIZAR ARQUIVOS
        # ==================================================

        arquivo_escola = localizar_arquivo(
            pasta,
            ["ESCOLA"]
        )

        arquivo_matricula = localizar_arquivo(
            pasta,
            ["MATRICULA"]
        )

        if arquivo_escola is None:

            self.stdout.write(
                self.style.ERROR(
                    "Arquivo de ESCOLA não encontrado."
                )
            )

            self.stdout.write(
                "Arquivos CSV encontrados:"
            )

            for arquivo in pasta.rglob("*.csv"):
                self.stdout.write(
                    str(arquivo)
                )

            return

        self.stdout.write(
            f"Escolas: {arquivo_escola}"
        )

        if arquivo_matricula:

            self.stdout.write(
                f"Matrículas: {arquivo_matricula}"
            )

        else:

            self.stdout.write(
                self.style.WARNING(
                    "Arquivo de matrículas não encontrado."
                )
            )

        # ==================================================
        # LER ESCOLAS
        # ==================================================

        escolas = ler_csv(
            arquivo_escola
        )

        mostrar_colunas(
            escolas
        )

        if somente_colunas:

            return

        # ==================================================
        # IDENTIFICAR CAMPOS
        # ==================================================

        coluna_codigo = encontrar_coluna(
            escolas,
            [
                "CO_ENTIDADE",
                "CODIGO_ESCOLA",
                "COD_ENTIDADE"
            ]
        )

        coluna_nome = encontrar_coluna(
            escolas,
            [
                "NO_ENTIDADE",
                "NOME_ESCOLA"
            ]
        )

        coluna_uf = encontrar_coluna(
            escolas,
            [
                "SG_UF",
                "UF"
            ]
        )

        coluna_municipio = encontrar_coluna(
            escolas,
            [
                "NO_MUNICIPIO",
                "MUNICIPIO"
            ]
        )

        if not coluna_codigo:

            raise RuntimeError(
                "Não encontrei a coluna do código INEP."
            )

        if not coluna_nome:

            raise RuntimeError(
                "Não encontrei a coluna do nome da escola."
            )

        # ==================================================
        # FILTRAR PARÁ
        # ==================================================

        if coluna_uf:

            escolas = escolas[
                escolas[coluna_uf]
                .astype(str)
                .str.upper()
                .isin(["PA", "15"])
            ].copy()

        self.stdout.write(
            self.style.SUCCESS(
                f"Escolas no Pará: {len(escolas):,}"
            )
        )

        # ==================================================
        # LIMITAR PARA TESTE
        # ==================================================

        if limite:

            escolas = escolas.head(
                limite
            )

            self.stdout.write(
                self.style.WARNING(
                    f"Executando somente {limite} escolas."
                )
            )

        # ==================================================
        # INFRAESTRUTURA
        # ==================================================

        coluna_internet = encontrar_coluna(
            escolas,
            [
                "IN_INTERNET",
                "IN_ACESSO_INTERNET"
            ]
        )

        if not coluna_internet:

            coluna_internet = (
                encontrar_coluna_por_parte(
                    escolas,
                    ["IN", "INTERNET"]
                )
            )

        coluna_agua = encontrar_coluna(
            escolas,
            [
                "IN_AGUA_POTAVEL",
                "IN_AGUA"
            ]
        )

        coluna_esgoto = encontrar_coluna(
            escolas,
            [
                "IN_ESGOTO_REDE_PUBLICA",
                "IN_ESGOTO"
            ]
        )

        coluna_computador = encontrar_coluna(
            escolas,
            [
                "QT_COMPUTADOR_PORTATIL_ALUNO",
                "QT_COMPUTADOR_PORTATIL"
            ]
        )

        # ==================================================
        # MATRÍCULAS
        # ==================================================

        matriculas = None

        if arquivo_matricula:

            matriculas = ler_csv(
                arquivo_matricula
            )

            mostrar_colunas(
                matriculas
            )

            coluna_mat_codigo = encontrar_coluna(
                matriculas,
                [
                    "CO_ENTIDADE",
                    "CODIGO_ESCOLA"
                ]
            )

            coluna_serie = encontrar_coluna(
                matriculas,
                [
                    "TP_ETAPA_ENSINO",
                    "TP_ETAPA",
                    "CO_ETAPA_ENSINO"
                ]
            )

            # --------------------------------------------------
            # IMPORTANTE:
            #
            # O Censo possui diferentes codificações
            # dependendo da base/ano.
            #
            # Por isso mostramos as colunas antes de
            # assumir uma codificação.
            # --------------------------------------------------

            if coluna_mat_codigo and coluna_serie:

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Coluna escola matrícula: "
                        f"{coluna_mat_codigo}"
                    )
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Coluna etapa/série: "
                        f"{coluna_serie}"
                    )
                )

                # ------------------------------------------
                # Normalizar código
                # ------------------------------------------

                matriculas[
                    coluna_mat_codigo
                ] = (
                    matriculas[
                        coluna_mat_codigo
                    ]
                    .astype(str)
                    .str.replace(
                        ".0",
                        "",
                        regex=False
                    )
                    .str.strip()
                )

                escolas[
                    coluna_codigo
                ] = (
                    escolas[
                        coluna_codigo
                    ]
                    .astype(str)
                    .str.replace(
                        ".0",
                        "",
                        regex=False
                    )
                    .str.strip()
                )

                # ------------------------------------------
                # Aqui NÃO vamos assumir que:
                #
                # 1 = primeiro ano
                # 2 = segundo ano
                #
                # até confirmar no dicionário do Censo.
                # ------------------------------------------

                self.stdout.write(
                    self.style.WARNING(
                        "A coluna de série foi encontrada."
                    )
                )

                self.stdout.write(
                    "Valores mais frequentes:"
                )

                print(
                    matriculas[
                        coluna_serie
                    ]
                    .value_counts()
                    .head(30)
                )

        # ==================================================
        # DADOS DAS ESCOLAS
        # ==================================================

        registros = []

        for _, linha in escolas.iterrows():

            codigo = str(
                linha[coluna_codigo]
            ).replace(
                ".0",
                ""
            ).strip()

            nome = str(
                linha[coluna_nome]
            ).strip()

            municipio = ""

            if coluna_municipio:

                municipio = str(
                    linha[coluna_municipio]
                ).strip()

            internet = False

            if coluna_internet:

                internet = valor_bool(
                    linha[coluna_internet]
                )

            agua = False

            if coluna_agua:

                agua = valor_bool(
                    linha[coluna_agua]
                )

            esgoto = False

            if coluna_esgoto:

                esgoto = valor_bool(
                    linha[coluna_esgoto]
                )

            computadores = 0

            if coluna_computador:

                computadores = valor_int(
                    linha[coluna_computador]
                )

            registros.append({

                "codigo_inep": codigo,

                "ano_censo": ano,

                "nome": nome,

                "municipio": municipio,

                "uf": "PA",

                "possui_internet": internet,

                "possui_agua_potavel": agua,

                "possui_esgoto": esgoto,

                "possui_saneamento": (
                    agua and esgoto
                ),

                "computadores_portateis": (
                    computadores
                ),

            })

        # ==================================================
        # SALVAR
        # ==================================================

        self.stdout.write(
            self.style.SUCCESS(
                f"Preparados {len(registros):,} registros."
            )
        )

        with transaction.atomic():

            for registro in registros:

                Escola.objects.update_or_create(

                    codigo_inep=(
                        registro[
                            "codigo_inep"
                        ]
                    ),

                    defaults=registro
                )

        self.stdout.write(
            self.style.SUCCESS(
                "======================================"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "IMPORTAÇÃO CONCLUÍDA"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Escolas importadas: "
                f"{len(registros):,}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "======================================"
            )
        )
