"""
services.py
Regra de negócio, independente do Flask (pode ser testada sem servidor web).

No exemplo original em Node.js, as quatro rotas repetiam o mesmo código
(publicar/publicarCanal e consumir/consumirCanal eram quase idênticas).
Aqui cada par vira UMA função que recebe o canal como parâmetro opcional.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from config import Settings
from email_sender import enviar_email
from oci_http_request import OciApiError
from queue_client import Mensagem, QueueClient

log = logging.getLogger(__name__)

ASSUNTO_PADRAO = "Teste Fila OCI"


@dataclass
class ResultadoConsumo:
    """Resumo de uma chamada de consumo (devolvido ao navegador)."""
    recebidas: int = 0
    mensagens: List[dict] = field(default_factory=list)   # o que será exibido na tela
    processadas: List[str] = field(default_factory=list)  # ids apagados da fila
    devolvidas: List[str] = field(default_factory=list)   # ids devolvidos p/ nova tentativa


# ---------------------------------------------------------------- Produtor
def publicar_email(fila: QueueClient, email: str, msg: str, canal: Optional[str] = None) -> dict:
    """Valida os dados e publica na fila (opcionalmente em um canal)."""
    if not email or not msg:
        raise ValueError("Informe todos os dados (e-mail e mensagem).")
    return fila.publicar({"email": email, "msg": msg}, canal=canal)


# -------------------------------------------------------------- Consumidor
def _interpretar(msg: Mensagem) -> dict:
    """
    Aceita os dois formatos que podem existir na fila:
      - JSON {"email": ..., "msg": ...}  (publicado por esta aplicação)
      - texto simples                    (ex.: "Enviar mensagem" do console da OCI)
    """
    try:
        dados = msg.como_json()
        if isinstance(dados, dict):
            return dados
    except ValueError:
        pass
    return {"msg": msg.content}


def _processar(settings: Settings, dados: dict) -> None:
    """Passo extra do consumo: enviar o e-mail (somente se ENVIAR_EMAIL=true)."""
    if not settings.enviar_email:
        return
    email, corpo = dados.get("email"), dados.get("msg")
    if not email or not corpo:
        raise ValueError("Mensagem sem 'email' e 'msg': não dá para enviar o e-mail.")
    enviar_email(settings, ASSUNTO_PADRAO, email, corpo)
    log.info("E-mail enviado para %s", email)


def consumir(settings: Settings, fila: QueueClient, canal: Optional[str] = None) -> ResultadoConsumo:
    """
    GetMessages -> para cada mensagem: sucesso => DeleteMessage;
                                       falha   => UpdateMessage (volta à fila).
    """
    limite = settings.batch_size_canal if canal else settings.batch_size
    mensagens = fila.receber(limite=limite, canal=canal)
    resultado = ResultadoConsumo(recebidas=len(mensagens))

    for msg in mensagens:
        log.info("Mensagem recebida (id=%s, entrega nº %s): %s", msg.id, msg.delivery_count, msg.content)
        try:
            dados = _interpretar(msg)
            _processar(settings, dados)
            fila.apagar(msg)  # só apaga DEPOIS do sucesso; senão ela voltaria sozinha à fila
            resultado.processadas.append(msg.id)
            resultado.mensagens.append({
                "id": msg.id,
                "email": dados.get("email"),
                "msg": dados.get("msg"),
                "conteudo": msg.content,
                "entrega": msg.delivery_count,
            })
        except Exception as erro:  # noqa: BLE001 - qualquer falha deve devolver a mensagem
            log.error("Falha ao processar %s: %s. Devolvendo à fila em %ss.",
                      msg.id, erro, settings.retry_visibility)
            try:
                fila.devolver(msg, settings.retry_visibility)
                resultado.devolvidas.append(msg.id)
            except OciApiError as erro_update:
                # O visibility timeout natural fará a mensagem voltar mesmo assim.
                log.error("Não foi possível devolver %s: %s", msg.id, erro_update)
    return resultado
