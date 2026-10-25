"""Notification channels and the factory that builds them from configuration.

`SENT` means "handed to the channel". For IN_APP that means the message is in
the learner's inbox; for EMAIL it means the provider accepted it. Neither means
the learner has read it (that is `read_at`).
"""
import logging
from collections.abc import Callable

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings
from app.core.exceptions import NotificationDeliveryError
from app.domain.enums import NotificationChannelType
from app.domain.interfaces import NotificationChannel, NotificationRecipient

logger = logging.getLogger("campus.notifications")


class InAppChannel:
    """The notification row itself is the in-app message, so there is nothing to push."""

    channel_type = NotificationChannelType.IN_APP

    def send(self, recipient: NotificationRecipient, title: str, message: str) -> None:
        return None


class ConsoleEmailChannel:
    """Development stand-in for an email provider: writes the email to the log."""

    channel_type = NotificationChannelType.EMAIL

    def send(self, recipient: NotificationRecipient, title: str, message: str) -> None:
        if not recipient.email:
            raise NotificationDeliveryError("recipient has no email address")
        logger.info("EMAIL to=%s subject=%r body=%r", recipient.email, title, message)


class SmtpEmailChannel:
    """Production SMTP email channel with fail-safe error isolation."""

    channel_type = NotificationChannelType.EMAIL

    def __init__(self, settings=None) -> None:  # noqa: ANN001
        self._settings = settings or get_settings()

    def send(self, recipient: NotificationRecipient, title: str, message: str) -> None:
        if not recipient.email:
            raise NotificationDeliveryError("recipient has no email address")
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = self._settings.smtp_from
            msg["To"] = recipient.email
            msg.attach(MIMEText(message, "plain"))

            if self._settings.smtp_port == 465:
                server = smtplib.SMTP_SSL(self._settings.smtp_host, self._settings.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=10)
                if self._settings.smtp_tls:
                    server.starttls()

            if self._settings.smtp_user and self._settings.smtp_password:
                server.login(self._settings.smtp_user, self._settings.smtp_password)

            server.sendmail(self._settings.smtp_from, [recipient.email], msg.as_string())
            server.quit()
            logger.info("SMTP EMAIL delivered to=%s subject=%r", recipient.email, title)
        except Exception as exc:
            logger.error("Failed to send SMTP email to %s: %s", recipient.email, exc)
            raise NotificationDeliveryError(f"SMTP delivery failed: {exc}") from exc


class NotificationChannelFactory:
    """Maps configuration names to channel classes (Factory pattern).

    Adding SMS later = write SmsChannel and `register("sms", SmsChannel)`.
    """

    def __init__(self) -> None:
        self._registry: dict[str, Callable[[], NotificationChannel]] = {}

    def register(self, name: str, builder: Callable[[], NotificationChannel]) -> None:
        self._registry[name] = builder

    def create(self, name: str) -> NotificationChannel:
        try:
            return self._registry[name]()
        except KeyError as exc:
            raise ValueError(f"Unknown notification channel '{name}'. Known: {sorted(self._registry)}") from exc

    def create_many(self, names: list[str]) -> list[NotificationChannel]:
        return [self.create(n) for n in names]


channel_factory = NotificationChannelFactory()
channel_factory.register("in_app", InAppChannel)
channel_factory.register("console_email", ConsoleEmailChannel)
channel_factory.register("smtp_email", SmtpEmailChannel)
channel_factory.register("smtp", SmtpEmailChannel)
