import logging

logger = logging.getLogger(__name__)


def send_approval_email(to: str, full_name: str) -> None:
    logger.info(f"[EMAIL STUB] Approval email → {to} ({full_name})")


def send_rejection_email(to: str, reason: str) -> None:
    logger.info(f"[EMAIL STUB] Rejection email → {to}: {reason}")


def send_registration_email(to: str, full_name: str) -> None:
    logger.info(f"[EMAIL STUB] Registration received email → {to} ({full_name})")
