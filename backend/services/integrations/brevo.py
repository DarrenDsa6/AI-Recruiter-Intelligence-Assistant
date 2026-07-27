import base64
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


def _email_section(title, items, color="#555"):
    if not items:
        return ""
    lis = ""
    for item in items[:5]:
        text = item if isinstance(item, str) else item.get("text", item.get("description", item.get("suggested_rewrite", str(item))))
        lis += f'<li style="font-size:14px;color:#444;margin:6px 0;line-height:1.5;word-wrap:break-word;">{text}</li>\n'
    return f"""
  <div style="margin-top:20px;">
    <h3 style="font-size:15px;color:{color};margin:0 0 8px;">{title}</h3>
    <ul style="padding-left:18px;margin:0;">{lis}</ul>
  </div>"""


def _email_questions(questions):
    gap = questions.get("gap_focused", []) if isinstance(questions, dict) else []
    tech = questions.get("technical", []) if isinstance(questions, dict) else []
    if not gap and not tech:
        return ""
    items = ""
    for i, q in enumerate(gap[:3], 1):
        if isinstance(q, dict):
            items += f'<li style="font-size:14px;color:#444;margin:8px 0;line-height:1.5;word-wrap:break-word;"><strong>{q.get("question","")}</strong>'
            if q.get("prep_tips"):
                items += f'<br/><span style="font-size:12px;color:#888;word-wrap:break-word;">Tip: {q["prep_tips"]}</span>'
            items += '</li>'
    for i, q in enumerate(tech[:3], 1):
        text = q if isinstance(q, str) else q.get("question", str(q))
        items += f'<li style="font-size:14px;color:#444;margin:8px 0;line-height:1.5;word-wrap:break-word;">{text}</li>'
    return f"""
  <div style="margin-top:20px;">
    <h3 style="font-size:15px;color:#b45309;margin:0 0 8px;">Interview Prep</h3>
    <ul style="padding-left:18px;margin:0;">{items}</ul>
  </div>"""


def _email_rewrites(rewrites):
    rw_list = rewrites.get("rewrites", []) if isinstance(rewrites, dict) else []
    if not rw_list:
        return ""
    items = ""
    for rw in rw_list[:3]:
        if isinstance(rw, dict):
            orig = rw.get("original_chunk", rw.get("original", ""))
            opts = rw.get("rewrite_options", rw.get("rewrites", []))
            suggestion = opts[0] if isinstance(opts, list) and opts else ""
            items += f'<li style="font-size:14px;color:#444;margin:8px 0;line-height:1.5;word-wrap:break-word;">'
            if orig:
                items += f'<span style="color:#999;text-decoration:line-through;font-size:12px;word-wrap:break-word;">{orig[:200]}</span><br/>'
            if suggestion:
                items += f'<span style="color:#0e7490;word-wrap:break-word;">{suggestion[:300]}</span>'
            items += '</li>'
    return f"""
  <div style="margin-top:20px;">
    <h3 style="font-size:15px;color:#0e7490;margin:0 0 8px;">Suggested Rewrites</h3>
    <ul style="padding-left:18px;margin:0;">{items}</ul>
  </div>"""


REPORT_EMAIL_HTML = Template("""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px; word-wrap: break-word; overflow-wrap: break-word;">
  <div style="text-align: center; margin-bottom: 24px;">
    <h1 style="font-size: 24px; color: #1a1a1a; margin: 0;">AI Resume Tailor</h1>
  </div>
  <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 28px; text-align: center;">
    <p style="font-size: 16px; color: #166534; margin: 0 0 8px;">Your resume analysis is complete!</p>
    <div style="font-size: 48px; font-weight: bold; color: #16a34a; margin: 12px 0;">$score%</div>
    <p style="font-size: 14px; color: #555; margin: 0;">ATS Compatibility Score</p>
  </div>

  $summary_section
  $strengths_section
  $gaps_section
  $keywords_section
  $rewrites_section
  $questions_section

  <div style="margin-top:28px; text-align: center;">
    <a href="$dashboard_url" style="display: inline-block; background: #2563eb; color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">View Full Report</a>
  </div>
  <p style="font-size: 12px; color: #999; text-align: center; margin-top: 20px;">
    Full report includes detailed scoring breakdown and PDF export.
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
        pdf_bytes: bytes = None,
        report: dict = None,
        questions: dict = None,
        rewrites: dict = None,
    ) -> bool:
        report = report or {}
        questions = questions or {}
        rewrites = rewrites or {}

        summary_text = report.get("summary", "")
        summary_section = f'<div style="margin-top:20px;"><h3 style="font-size:15px;color:#2563eb;margin:0 0 8px;">Summary</h3><p style="font-size:14px;color:#444;line-height:1.6;margin:0;word-wrap:break-word;">{summary_text}</p></div>' if summary_text else ""

        strengths = report.get("strengths", [])
        gaps = report.get("improvement_areas", report.get("gaps", []))
        keywords = report.get("keyword_suggestions", report.get("recommendations", []))

        html = REPORT_EMAIL_HTML.substitute(
            score=score,
            dashboard_url=dashboard_url,
            summary_section=summary_section,
            strengths_section=_email_section("Strengths", strengths, "#16a34a"),
            gaps_section=_email_section("Areas for Improvement", gaps, "#ea580c"),
            keywords_section=_email_section("Keyword Suggestions", keywords, "#7c3aed"),
            rewrites_section=_email_rewrites(rewrites),
            questions_section=_email_questions(questions),
        )

        subject = REPORT_EMAIL_SUBJECT.substitute(score=score)
        payload = {
            "sender": {"email": self.from_email, "name": self.from_name},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html,
        }
        if pdf_bytes:
            encoded = base64.b64encode(pdf_bytes).decode("utf-8")
            payload["attachment"] = [
                {
                    "name": f"resume-analysis-{report_id}.pdf",
                    "content": encoded,
                }
            ]
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
