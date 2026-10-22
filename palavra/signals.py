import fitz  # PyMuPDF
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.base import ContentFile
from .models import Historia, BlocoHistoria

@receiver(post_save, sender=Historia)
def processar_pdf_historia(sender, instance, created, **kwargs):
    if created and instance.arquivo_pdf:
        try:
            doc = fitz.open(instance.arquivo_pdf.path)
            texto_completo = ""
            bloco_num = 1

            for page_index in range(len(doc)):
                page = doc[page_index]
                texto_pagina_bruto = page.get_text("text")

                # TRATAMENTO DE TEXTO:
                # Trata quebras soltas de linha entre palavras
                paragrafos_brutos = texto_pagina_bruto.split('\n\n')
                paragrafos_limpos = []

                for p in paragrafos_brutos:
                    texto_paragrafo = " ".join(p.split())
                    if texto_paragrafo:
                        paragrafos_limpos.append(texto_paragrafo)

                texto_pagina_tratado = "\n\n".join(paragrafos_limpos)
                texto_completo += texto_pagina_tratado + "\n\n"

                # RENDERIZA A PÁGINA INTEIRA COMO IMAGEM (Garante captura de imagens do Google Docs)
                pix = page.get_pixmap(dpi=150) # Excelente qualidade para tela
                image_bytes = pix.tobytes("png")
                imagem_conteudo = ContentFile(image_bytes)
                nome_imagem = f"historia_{instance.id}_pag_{page_index + 1}.png"

                # Agrupa a cada 2 parágrafos por bloco de leitura
                for i in range(0, len(paragrafos_limpos), 2):
                    trecho = "\n\n".join(paragrafos_limpos[i:i+2])
                    
                    bloco = BlocoHistoria(
                        historia=instance,
                        ordem_bloco=bloco_num,
                        trecho_texto=trecho
                    )

                    # Salva a imagem da página renderizada no primeiro bloco da página
                    if i == 0:
                        bloco.imagem.save(nome_imagem, imagem_conteudo, save=False)

                    bloco.save()
                    bloco_num += 1

            instance.texto_completo = texto_completo.strip()
            instance.save(update_fields=['texto_completo'])

        except Exception as e:
            print(f"Erro ao processar PDF com PyMuPDF: {e}")