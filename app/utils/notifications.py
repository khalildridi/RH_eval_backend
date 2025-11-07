import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from typing import List

async def send_notification_email(to_emails: List[str], subject: str, body: str):
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"Notifications désactivées. SMTP non configuré. Sujet: {subject}")
        return
    
    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_USER
    msg['To'] = ", ".join(to_emails)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(settings.SMTP_USER, to_emails, text)
        server.quit()
        print(f"Email envoyé à {to_emails}")
    except Exception as e:
        print(f"Erreur envoi email: {e}")

# Exemple d'usage : await send_notification_email(["manager@email.com"], "Nouvelle campagne", "Évaluez vos collaborateurs...")