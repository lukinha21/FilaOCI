"""
app.py - Aplicação web (Flask) que expõe produtor e consumidor da fila OCI.
Equivalente ao app.js (Express) do exemplo original.

Rotas (mesmos nomes do original):
    GET  /               página com os formulários/botões
    POST /publicar       produtor, sem canal
    POST /publicarCanal  produtor, com canal
    GET  /consumir       consumidor, sem filtro de canal
    GET  /consumirCanal  consumidor, filtrando pelo canal

Execução:  python app.py   ->  http://localhost:3000
"""
import logging

from flask import Flask, jsonify, render_template, request

import services
from config import carregar_settings
from oci_http_request import OciApiError, OciHttpClient
from queue_client import QueueClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def criar_app(settings=None, fila=None) -> Flask:
    """Factory: permite injetar uma fila falsa nos testes."""
    settings = settings or carregar_settings()
    fila = fila or QueueClient(settings, OciHttpClient(settings.oci_config_file, settings.oci_profile))
    app = Flask(__name__)

    def _publicar(canal=None):
        dados = request.get_json(silent=True) or {}
        try:
            resultado = services.publicar_email(fila, dados.get("email", "").strip(),
                                                dados.get("msg", "").strip(), canal)
        except ValueError as erro:
            return jsonify(erro=str(erro)), 400
        except OciApiError as erro:
            log.error("Erro da OCI ao publicar: %s", erro)
            return jsonify(erro="Falha ao inserir na fila."), 502
        log.info("Publicado: %s", resultado)
        return jsonify(mensagem="Inserido na fila.")

    def _consumir(canal=None):
        try:
            r = services.consumir(settings, fila, canal)
        except OciApiError as erro:
            log.error("Erro da OCI ao consumir: %s", erro)
            return jsonify(erro="Falha ao ler a fila."), 502
        return jsonify(mensagem="Retirado da fila." if r.recebidas else "Nenhuma mensagem na fila.",
                       recebidas=r.recebidas, mensagens=r.mensagens,
                       processadas=r.processadas, devolvidas=r.devolvidas)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/publicar")
    def publicar():
        return _publicar()

    @app.post("/publicarCanal")
    def publicar_canal():
        return _publicar(settings.canal)

    @app.get("/consumir")
    def consumir():
        return _consumir()

    @app.get("/consumirCanal")
    def consumir_canal():
        return _consumir(settings.canal)

    return app


if __name__ == "__main__":
    criar_app().run(port=3000)
