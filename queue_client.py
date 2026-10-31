"""
queue_client.py
Camada que conhece os ENDPOINTS da API de Filas (Queue) da OCI.

Separar isso do restante do código (boa prática: responsabilidade única)
deixa producer.py e consumer.py muito mais limpos: eles falam "publicar",
"receber", "apagar", "devolver" em vez de montar URLs.

Endpoints usados (API versão 20210201):
  POST   /queues/{id}/messages            -> PutMessages   (produtor)
  GET    /queues/{id}/messages            -> GetMessages   (consumidor)
  DELETE /queues/{id}/messages/{receipt}  -> DeleteMessage (confirma o processamento)
  PUT    /queues/{id}/messages/{receipt}  -> UpdateMessage (devolve à fila)
"""
import json
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

from config import Settings
from oci_http_request import OciHttpClient

API_VERSION = "20210201"


@dataclass(frozen=True)
class Mensagem:
    """Mensagem recebida da fila."""
    id: str
    content: str          # payload (aqui: um JSON em texto)
    receipt: str          # comprovante necessário para apagar/atualizar
    delivery_count: int   # quantas vezes foi entregue (ao passar do máximo -> DLQ)

    def como_json(self) -> dict:
        """Converte o payload em dict. Lança ValueError se não for JSON válido."""
        return json.loads(self.content)


class QueueClient:
    def __init__(self, settings: Settings, http: OciHttpClient):
        self._http = http
        self._queue_id = settings.queue_id
        self._base = f"{settings.queue_endpoint}/{API_VERSION}/queues/{settings.queue_id}"

    # ---------------- Produtor ----------------
    def publicar(self, conteudo: dict, canal: Optional[str] = None) -> dict:
        """
        PutMessages: coloca uma mensagem (dict -> JSON) na fila.
        Se `canal` for informado, a mensagem é marcada com metadata.channelId;
        assim só um consumidor que filtre por esse canal consegue retirá-la.
        """
        mensagem = {"content": json.dumps(conteudo, ensure_ascii=False)}
        if canal:
            mensagem["metadata"] = {"channelId": canal}
        return self._http.request("POST", f"{self._base}/messages", corpo={"messages": [mensagem]})

    # ---------------- Consumidor ----------------
    def receber(
        self, limite: int = 10, timeout_s: int = 0, canal: Optional[str] = None
    ) -> List[Mensagem]:
        """
        GetMessages: retira até `limite` mensagens (máx. 20).
        As mensagens ficam INVISÍVEIS para outros consumidores durante o
        'visibility timeout' da fila.
        `timeout_s` > 0 ativa o long polling (a OCI segura a conexão até chegar
        mensagem); 0 devolve na hora, o que combina com um botão "CONSUMIR".
        `canal` filtra somente as mensagens daquele canal (channelFilter).
        """
        params = {"limit": limite, "timeoutInSeconds": timeout_s}
        if canal:
            params["channelFilter"] = canal
        retorno = self._http.request("GET", f"{self._base}/messages", params=params) or {}
        return [
            Mensagem(
                id=str(m.get("id")),
                content=m.get("content", ""),
                receipt=m["receipt"],
                delivery_count=int(m.get("deliveryCount", 0)),
            )
            for m in retorno.get("messages", [])
        ]

    def apagar(self, msg: Mensagem) -> None:
        """DeleteMessage: remove definitivamente a mensagem (processada com sucesso)."""
        self._http.request("DELETE", f"{self._base}/messages/{self._receipt(msg)}")

    def devolver(self, msg: Mensagem, visibilidade_s: int) -> None:
        """
        UpdateMessage: ajusta 'visibilityInSeconds'. A mensagem volta a ficar
        disponível após esse tempo. Se estourar o 'máximo de tentativas de
        entrega' da fila, ela vai para a DLQ (fila de mensagens inativas).
        """
        self._http.request(
            "PUT",
            f"{self._base}/messages/{self._receipt(msg)}",
            corpo={"visibilityInSeconds": visibilidade_s},
        )

    @staticmethod
    def _receipt(msg: Mensagem) -> str:
        # O receipt contém caracteres especiais: precisa ser codificado na URL
        return quote(msg.receipt, safe="")
