"""
email_sender.py
Envio de e-mail via SMTP usando apenas a biblioteca padrão (smtplib).

Diferença para o original: lá o envio usava callback e NÃO era aguardado,
então um erro de e-mail nunca caía no 'catch' e a mensagem era apagada da
fila mesmo sem ter sido enviada. Aqui o envio é síncrono: se falhar, lança
exceção e o consumidor consegue devolver a mensagem à fila.
"""
import smtplib
from email.message import EmailMessage

from config import Settings


def enviar_email(settings: Settings, assunto: str, destinatario: str, corpo_html: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg.set_content("Seu cliente de e-mail não suporta HTML.")  # alternativa em texto
    msg.add_alternative(corpo_html, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
