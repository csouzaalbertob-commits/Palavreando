from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'^/?ws/solicitacao_nivel/$', consumers.SolicitacaoNivelConsumer.as_asgi()
    ),
    re_path(
        r'^/?ws/batalha/(?P<partida_id>\d+)/$', consumers.BatalhaConsumer.as_asgi()
    ),
]