import os
from django.core.asgi import get_asgi_application

# 1. Defina a variável de ambiente do Django ANTES de importar o routing ou channels
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema.settings')

# 2. Inicialize o app ASGI do Django
django_asgi_app = get_asgi_application()

# 3. Importe os Channels e o seu routing APÓS chamar get_asgi_application()
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import palavra.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            palavra.routing.websocket_urlpatterns
        )
    ),
})