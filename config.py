"""
config.py
Centraliza TODA a configuração da aplicação.

Boa prática: nada de credenciais ou IDs fixos no código (no exemplo original
em Node.js a senha do e-mail e o OCID da fila estavam escritos direto no
arquivo). Aqui tudo vem de variáveis de ambiente (ou de um arquivo .env).
"""
import os
from dataclasses import dataclass
from pathlib import Path


def _carregar_dotenv(caminho: str = ".env") -> None:
    """Leitor mínimo de .env (evita depender de uma biblioteca extra)."""
    arquivo = Path(caminho)
    if not arquivo.exists():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        # variáveis já definidas no ambiente têm prioridade sobre o .env
        os.environ.setdefault(chave.strip(), valor.strip())


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise RuntimeError(f"Variável de ambiente obrigatória não definida: {nome}")
    return valor


@dataclass(frozen=True)
class Settings:
    # OCI
    oci_config_file: str
    oci_profile: str
    queue_id: str
    queue_endpoint: str
    # Fila / consumo
    canal: str                 # canal usado nos botões "- CANAL"
    batch_size: int            # mensagens por consumo (a OCI permite até 20)
    batch_size_canal: int
    retry_visibility: int      # segundos até a mensagem voltar à fila após falha
    # SMTP
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    enviar_email: bool = False  # se True, o consumo também dispara o e-mail


def carregar_settings() -> Settings:
    _carregar_dotenv()
    return Settings(
        oci_config_file=os.path.expanduser(os.getenv("OCI_CONFIG_FILE", ".oci/config")),
        oci_profile=os.getenv("OCI_PROFILE", "DEFAULT"),
        queue_id=_obrigatoria("OCI_QUEUE_ID"),
        queue_endpoint=_obrigatoria("OCI_QUEUE_ENDPOINT").rstrip("/"),
        canal=os.getenv("OCI_QUEUE_CHANNEL", "canal1"),
        batch_size=int(os.getenv("CONSUMER_BATCH_SIZE", "10")),
        batch_size_canal=int(os.getenv("CONSUMER_BATCH_SIZE_CANAL", "1")),
        retry_visibility=int(os.getenv("CONSUMER_RETRY_VISIBILITY", "30")),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        enviar_email=os.getenv("ENVIAR_EMAIL", "false").strip().lower() in ("1", "true", "sim"),
    )
