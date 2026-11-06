def global_version(request):
    """
    Retorna a versão global do Palavreando para exibição no rodapé e templates.
    """
    return {
        'APP_VERSION': '2.0.0',
        'APP_NAME': 'Palavreando'
    }