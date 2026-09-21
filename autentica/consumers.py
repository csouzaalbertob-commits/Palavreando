import json
from channels.generic.websocket import AsyncWebsocketConsumer


class SolicitacaoNivelConsumer(AsyncWebsocketConsumer):

  async def connect(self):
    self.room_group_name = 'solicitacoes_nivel'

    # Adiciona o websocket ao grupo global de solicitações
    await self.channel_layer.group_add(
        self.room_group_name, self.channel_name
    )
    await self.accept()

  async def disconnect(self, close_code):
    await self.channel_layer.group_discard(
        self.room_group_name, self.channel_name
    )

  async def receive(self, text_data):
    data = json.loads(text_data)

    # Transmite o payload para todos conectados no grupo
    await self.channel_layer.group_send(
        self.room_group_name, {'type': 'notificar_evento', 'payload': data}
    )

  async def notificar_evento(self, event):
    payload = event['payload']
    # Envia o payload desempacotado diretamente no WebSocket
    await self.send(text_data=json.dumps(payload))