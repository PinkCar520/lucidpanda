import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger


def send_email_via_smtp(to_email:
    str, subject: str, body: str):
    """传统 SMTP 发送逻辑"""
    if not settings.SMTP_SERVER or not settings.EMAIL_SENDER or not settings.EMAIL_PASSWORD:
        logger.warning("SMTP settings are incomplete. Cannot send email.")
        return False

    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_SENDER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_SENDER, settings.EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"SMTP Failed: {e}")
        return False

def send_email_via_resend(to_email:
    str, subject: str, body: str):
    """现代 Resend API 发送逻辑"""
    import resend

    if not settings.RESEND_API_KEY:
        logger.error("RESEND_API_KEY is not set.")
        return False

    resend.api_key = settings.RESEND_API_KEY

    try:
        params = {
            "from": settings.EMAIL_SENDER or "LucidPanda <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": body,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        logger.error(f"Resend API Failed: {e}")
        return False

def send_email(to_email:
    str, subject: str, body: str):
    """
    统一邮件发送入口
    根据环境变量 EMAIL_PROVIDER 选择具体实现
    """
    provider = settings.EMAIL_PROVIDER.lower()

    logger.info(f"📧 Sending email via {provider} to {to_email}...")

    if provider == "resend":
        success = send_email_via_resend(to_email, subject, body)
    elif provider == "smtp":
        success = send_email_via_smtp(to_email, subject, body)
    else:
        logger.error(f"Unknown email provider: {provider}")
        return False

    if success:
        logger.info(f"✅ Email sent successfully using {provider}")
    return success
