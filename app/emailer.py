"""
Invio email astratto: send_email(to, subject, html_body).
Implementazione di default via SMTP (es. Gmail con App Password), cosi'
da non dipendere da un servizio terzo a pagamento. Per cambiare provider
in futuro basta riscrivere questa funzione: il resto dell'app non cambia.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM


class EmailError(Exception):
    pass


def send_email(to: str, subject: str, html_body: str, retries: int = 2) -> bool:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD and to):
        raise EmailError("Configurazione email incompleta (SMTP_* / EMAIL_TO).")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText("Il tuo client email non supporta l'HTML.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    last_error = None
    for attempt in range(1, retries + 2):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(EMAIL_FROM, [to], msg.as_string())
            return True
        except Exception as e:
            last_error = e
    raise EmailError(f"Invio email fallito dopo {retries + 1} tentativi: {last_error}")
