"""
oci_http_request.py
Equivalente em Python do ociHttpRequest.js do exemplo original.

Toda requisição à API da OCI precisa do cabeçalho "Authorization" assinado
(Request Signatures). O fluxo é o mesmo do exemplo em Node.js:
  1. carregar as credenciais do arquivo ~/.oci/config;
  2. criar um "signer" (assinador) com a chave privada;
  3. anexar a assinatura à requisição HTTP;
  4. enviar a requisição e converter a resposta JSON em dict.

Diferença importante (melhoria): o JS chamava response.json() sempre, mas
DELETE/PUT/POST podem retornar corpo vazio, o que gerava erro. Aqui o corpo
vazio é tratado, e erros HTTP viram exceções com mensagem clara.
"""
import logging
from typing import Any, Optional

import oci
import requests

log = logging.getLogger(__name__)


class OciApiError(Exception):
    """Erro devolvido pela API da OCI (status HTTP >= 400)."""

    def __init__(self, status: int, corpo: str):
        super().__init__(f"OCI respondeu HTTP {status}: {corpo}")
        self.status = status
        self.corpo = corpo


class OciHttpClient:
    def __init__(self, config_file: str, profile: str = "DEFAULT", timeout: int = 40):
        # 1. Carrega tenancy, user, fingerprint e caminho da chave privada
        config = oci.config.from_file(config_file, profile)
        # 2. O Signer implementa "requests.auth.AuthBase": assina cada requisição
        self._signer = oci.signer.Signer(
            tenancy=config["tenancy"],
            user=config["user"],
            fingerprint=config["fingerprint"],
            private_key_file_location=config["key_file"],
            pass_phrase=config.get("pass_phrase"),
        )
        self._timeout = timeout  # deve ser maior que o long polling da fila

    def request(
        self,
        metodo: str,
        url: str,
        corpo: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Optional[Any]:
        """Envia uma requisição assinada e devolve o JSON (dict) ou None."""
        resposta = requests.request(
            method=metodo.upper(),
            url=url,
            params=params,
            json=corpo,              # o 'requests' serializa e define o Content-Type
            auth=self._signer,       # 3. assinatura da requisição
            timeout=self._timeout,
        )
        if resposta.status_code >= 400:
            raise OciApiError(resposta.status_code, resposta.text)
        if not resposta.content:     # ex.: DELETE devolve 204 sem corpo
            return None
        return resposta.json()
