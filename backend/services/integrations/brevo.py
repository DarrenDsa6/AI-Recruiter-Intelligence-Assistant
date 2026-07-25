import logging
from string import Template

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

OTP_EMAIL_SUBJECT = "Your AI Resume Tailor Login Code"
OTP_EMAIL_HTML = Template("""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
  <div style="text-align: center; margin-bottom: 32px;">
    <h1 style="font-size: 24px; color: #1a1a1a; margin: 0;">AI Resume Tailor</h1>
  </div>
  <div style="background: #f8f9fa; border-radius: 12px; padding: 32px; text-align: center;">
    <p style="font-size: 16px; color: #555; margin: 0 0 16px;">Your verification code is</p>
    <div style="font-size: 48px; font-weight: bold; color: #2563eb; letter-spacing: 12px; margin: 16px 0;">$otp</div>
    <p style="font-size: 14px; color: #888; margin: 16px 0 0;">This code expires in 5 minutes.</p>
  </div>
  <p style="font-size: 13px; color: #999; text-align: center; margin-top: 24px;">
    If you didn't request this code, you can safely ignore this email.
  </p>
</body>
</html>
""")

REPORT_EMAIL_SUBJECT = Template("Your Resume Analysis is Ready - $score% ATS Match")
REPORT_EMAIL_HTML = Template("""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
  <div style="text-align: center; margin-bottom: 32px;">
    <h1 style="font-size: 24px; color: #1a1a1a; margin: 0;">AI Resume Tailor</h1>
  </div>
  <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 32px; text-align: center;">
    <p style="font-size: 16px; color: #166534; margin: 0 0 8px;">Your resume analysis is complete!</p>
    <div style="font-size: 48px; font-weight: bold; color: #16a34a; margin: 16px 0;">$score%</div>
    <p style="font-size: 14px; color: #555; margin: 0;">ATS Compatibility Score</p>
  </div>
  <div style="margin-top: 24px; text-align: center;">
    <a href="$dashboard_url" style="display: inline-block; background: #2563eb; color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">View Full Report</a>
  </div>
  <p style="font-size: 13px; color: #999; text-align: center; margin-top: 24px;">
    Includes: skill gap analysis, actionable rewrites, and interview prep questions.
  </p>
</body>
</html>
""")


class BrevoEmailService:
    def __init__(self):
        self.api_key = settings.brevo_api_key
        self.from_email = settings.brevo_from_email
        self.from_name = settings.brevo_from_name

    def _headers(self) -> dict:
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": self.api_key,
        }

    async def send_otp(self, to_email: str, otp: str) -> bool:
        payload = {
            "sender": {"email": self.from_email, "name": self.from_name},
            "to": [{"email": to_email}],
            "subject": OTP_EMAIL_SUBJECT,
            "htmlContent": OTP_EMAIL_HTML.substitute(otp=otp),
        }
        return await self._send(payload, to_email, "OTP")

    async def send_report_notification(
        self,
        to_email: str,
        score: float,
        report_id: str,
        dashboard_url: str,
    ) -> bool:
        subject = REPORT_EMAIL_SUBJECT.substitute(score=score)
        payload = {
            "sender": {"email": self.from_email, "name": self.from_name},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": REPORT_EMAIL_HTML.substitute(
                score=score, dashboard_url=dashboard_url
            ),
        }
        return await self._send(payload, to_email, "report notification")

    async def _send(self, payload: dict, to_email: str, label: str) -> bool:
        if not self.api_key:
            logger.warning(f"Brevo API key not configured, skipping {label} email to {to_email}")
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(BREVO_API_URL, json=payload, headers=self._headers())
                if resp.status_code in (200, 201):
                    logger.info(f"{label} email sent to {to_email}")
                    return True
                logger.error(f"Brevo API error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send {label} email to {to_email}: {e}")
            return False


brevo_email = BrevoEmailService()
