import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class BatalhaConsumer(AsyncWebsocketConsumer):

  async def connect(self):
    # Previne KeyError verificando sala_id, partida_id ou pk na rota
    kwargs = self.scope.get('url_route', {}).get('kwargs', {})
    self.sala_id = (
        kwargs.get('sala_id') or kwargs.get('partida_id') or kwargs.get('pk')
    )

    if not self.sala_id:
      await self.close()
      return

    self.room_group_name = f'batalha_{self.sala_id}'

    await self.channel_layer.group_add(
        self.room_group_name, self.channel_name
    )
    await self.accept()

  async def disconnect(self, close_code):
    if hasattr(self, 'room_group_name'):
      await self.channel_layer.group_discard(
          self.room_group_name, self.channel_name
      )

  async def receive(self, text_data):
    data = json.loads(text_data)
    tipo = data.get('type')

    if tipo == 'atualizar_pontos':
      aluno_id = data.get('aluno_id')
      pontos = data.get('pontos')

      await self.salvar_pontuacao_parcial(aluno_id, pontos)

      await self.channel_layer.group_send(
          self.room_group_name,
          {
              'type': 'atualizar_pontos_broadcast',
              'aluno_id': aluno_id,
              'pontos': pontos,
          },
      )

    elif tipo == 'finalizar_partida':
      await self.finalizar_partida_no_banco()

      await self.channel_layer.group_send(
          self.room_group_name, {'type': 'partida_finalizada_broadcast'}
      )

    else:
      # Reencaminha mensagens dinâmicas (aluno_entrou, iniciar_contagem_5s, desafio_recusado, etc.)
      await self.channel_layer.group_send(
          self.room_group_name, {'type': 'generic_broadcast', 'payload': data}
      )

  # Handlers de envio aos clientes
  async def generic_broadcast(self, event):
    await self.send(text_data=json.dumps(event['payload']))

  async def atualizar_pontos_broadcast(self, event):
    await self.send(
        text_data=json.dumps({
            'type': 'atualizar_pontos',
            'aluno_id': event['aluno_id'],
            'pontos': event['pontos'],
        })
    )

  async def partida_finalizada_broadcast(self, event):
    await self.send(text_data=json.dumps({'type': 'partida_finalizada'}))

  # OPERAÇÕES DE BANCO DE DADOS (ORM)
  @database_sync_to_async
  def salvar_pontuacao_parcial(self, aluno_id, pontos):
    from .models import PartidaBatalha

    partida = PartidaBatalha.objects.filter(id=self.sala_id).first()
    if partida:
      if partida.jogador_1_id == aluno_id:
        partida.pontos_j1 = pontos
      elif partida.jogador_2_id == aluno_id:
        partida.pontos_j2 = pontos
      partida.save(update_fields=['pontos_j1', 'pontos_j2'])

  @database_sync_to_async
  def finalizar_partida_no_banco(self):
    from .models import PartidaBatalha

    partida = PartidaBatalha.objects.filter(id=self.sala_id).first()
    if partida and partida.status != 'finalizada':
      partida.status = 'finalizada'

      if partida.pontos_j1 > partida.pontos_j2:
        partida.vencedor = partida.jogador_1
      elif partida.pontos_j2 > partida.pontos_j1:
        partida.vencedor = partida.jogador_2
      else:
        partida.vencedor = None  # Empate fica gravado como NULL (0)

      partida.save(update_fields=['status', 'vencedor'])