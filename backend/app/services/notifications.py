import logging
import os
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def _smtp_config() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": int(os.getenv("SMTP_PORT", "587") or 587),
        "username": os.getenv("SMTP_USERNAME", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", "").strip(),
        "from_email": os.getenv("SMTP_FROM_EMAIL", "").strip(),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").strip().lower() not in {"0", "false", "no"},
    }


def notify_admin_event(subject: str, body: str) -> bool:
    settings = get_settings()
    admin_email = (os.getenv("PARTNER_NOTIFY_EMAIL") or settings.ADMIN_EMAIL or "").strip()
    config = _smtp_config()
    if not admin_email or not config["host"] or not config["from_email"]:
        logger.info("admin notification skipped: %s", subject)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config["from_email"]
    message["To"] = admin_email
    message.set_content(body)

    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=10) as smtp:
            if config["use_tls"]:
                smtp.starttls()
            if config["username"] and config["password"]:
                smtp.login(config["username"], config["password"])
            smtp.send_message(message)
        return True
    except Exception:
        logger.exception("admin notification failed: %s", subject)
        return False

