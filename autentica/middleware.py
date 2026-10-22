from .populate_data import popular_dados_iniciais


class AutoPopulateMiddleware:
  _populado = False

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    if not AutoPopulateMiddleware._populado:
      AutoPopulateMiddleware._populado = True
      try:
        popular_dados_iniciais()
      except Exception as e:
        print(f'[ERRO MIDDLEWARE]: {e}')

    return self.get_response(request)