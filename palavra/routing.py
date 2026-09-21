from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Altere de <partida_id> ou <pk> para <sala_id>
    re_path(
        r'ws/batalha/(?P<sala_id>\d+)/$', consumers.BatalhaConsumer.as_asgi()
    ),
]