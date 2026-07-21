from __future__ import annotations

import logging
import random

logger = logging.getLogger(__name__)


class EmailService:

    def send_verification_email(self, email: str, code: str) -> bool:
        logger.info("=" * 60)
        logger.info("EMAIL SERVICE (simulated)")
        logger.info("To: %s", email)
        logger.info("Subject: Verify your Bloomberg Terminal account")
        logger.info("Body:")
        logger.info("  Welcome to Secure Bloomberg Terminal!")
        logger.info("  Your verification code is: %s", code)
        logger.info("  This code expires in 15 minutes.")
        logger.info("=" * 60)
        return True

    def send_welcome_email(self, email: str) -> bool:
        logger.info("=" * 60)
        logger.info("EMAIL SERVICE (simulated)")
        logger.info("To: %s", email)
        logger.info("Subject: Welcome to Bloomberg Terminal")
        logger.info("Body:")
        logger.info("  Your email has been verified successfully.")
        logger.info("  You can now log in and start trading.")
        logger.info("=" * 60)
        return True

    @staticmethod
    def generate_verification_code() -> str:
        return f"{random.randint(0, 999999):06d}"


email_service = EmailService()
