import io
import json
import logging
import re

from fpdf import FPDF

logger = logging.getLogger(__name__)

def _sanitize(text):
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    text = text.replace('\u2026', '...')
    text = text.replace('\u2022', '-')
    text = text.replace('\u00a0', ' ')
    return text.strip()


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(37, 99, 235)
        self.cell(0, 10, _sanitize("AI Resume Tailor - Analysis Report"), new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_draw_color(37, 99, 235)
        self.set_line_width(0.5)
        self.line(20, self.get_y(), self.w - 20, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(30, 30, 30)
        self.cell(0, 8, _sanitize(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5, _sanitize(text))
        self.ln(2)

    def bullet_list(self, items):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        for item in items:
            if isinstance(item, dict):
                text = item.get("text", item.get("description", item.get("suggestion", json.dumps(item))))
            else:
                text = str(item)
            self.multi_cell(0, 5, _sanitize(f"  - {text}"))
        self.ln(2)

    def key_value(self, key, value):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(50, 50, 50)
        safe_key = _sanitize(str(key))
        safe_val = _sanitize(str(value))
        self.cell(55, 6, safe_key + ":")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, safe_val, new_x="LMARGIN", new_y="NEXT")


def generate_report_pdf(
    match_result: dict,
    report: dict,
    questions: dict,
    rewrites: dict,
    jd_text: str = "",
) -> bytes:
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    def _safe(label, fn):
        try:
            fn()
        except Exception as e:
            logger.warning(f"PDF section '{label}' skipped: {e}")

    _safe("score", lambda: (
        pdf.key_value("ATS Match Score", f"{match_result.get('final_score', 0)}%"),
        pdf.ln(3),
    ))

    def _score_breakdown():
        category_breakdown = match_result.get("category_breakdown", {})
        if category_breakdown:
            pdf.section_title("Score Breakdown")
            for cat, val in category_breakdown.items():
                display = f"{val}%" if isinstance(val, (int, float)) else str(val)
                pdf.key_value(_sanitize(cat.replace("_", " ").title()), display)
            pdf.ln(3)
    _safe("score_breakdown", _score_breakdown)

    def _summary():
        summary = report.get("summary", "")
        if summary:
            pdf.section_title("Summary")
            pdf.body_text(summary)
    _safe("summary", _summary)

    def _ats_compat():
        ats_score = report.get("ats_score")
        if ats_score is not None:
            pdf.key_value("ATS Compatibility", f"{ats_score}/100")
    _safe("ats_compat", _ats_compat)

    def _strengths():
        strengths = report.get("strengths", [])
        if strengths:
            pdf.section_title("Strengths")
            pdf.bullet_list(strengths)
    _safe("strengths", _strengths)

    def _gaps():
        gaps = report.get("improvement_areas", report.get("gaps", []))
        if gaps:
            pdf.section_title("Areas for Improvement")
            pdf.bullet_list(gaps)
    _safe("gaps", _gaps)

    def _missing():
        missing = report.get("missing_keywords", [])
        if missing:
            pdf.section_title("Missing Keywords")
            pdf.bullet_list(missing)
    _safe("missing", _missing)

    def _keywords():
        suggestions = report.get("keyword_suggestions", report.get("recommendations", []))
        if suggestions:
            pdf.section_title("Keyword Suggestions")
            for s in suggestions:
                if isinstance(s, dict):
                    orig = _sanitize(s.get("original", s.get("keyword", "")))
                    suggested = _sanitize(s.get("suggested_rewrite", s.get("suggestion", "")))
                    pdf.set_font("Helvetica", "", 10)
                    pdf.set_text_color(50, 50, 50)
                    pdf.multi_cell(0, 5, _sanitize(f"  {orig} -> {suggested}"))
                else:
                    pdf.bullet_list([str(s)])
            pdf.ln(2)
    _safe("keywords", _keywords)

    def _gap_questions():
        gap_questions = questions.get("gap_focused", [])
        if gap_questions:
            pdf.section_title("Gap-Focused Interview Questions")
            for i, q in enumerate(gap_questions, 1):
                if isinstance(q, dict):
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.set_text_color(50, 50, 50)
                    pdf.multi_cell(0, 5, _sanitize(f"  {i}. {q.get('question', '')}"))
                    why = q.get("why_likely", "")
                    if why:
                        pdf.set_font("Helvetica", "I", 9)
                        pdf.set_text_color(100, 100, 100)
                        pdf.multi_cell(0, 5, _sanitize(f"    Why likely: {why}"))
                    tips = q.get("prep_tips", "")
                    if tips:
                        pdf.set_font("Helvetica", "", 9)
                        pdf.multi_cell(0, 5, _sanitize(f"    Prep tips: {tips}"))
                    pdf.ln(2)
    _safe("gap_questions", _gap_questions)

    def _tech_questions():
        tech_questions = questions.get("technical", [])
        if tech_questions:
            pdf.section_title("Technical Questions")
            for i, q in enumerate(tech_questions, 1):
                text = q if isinstance(q, str) else q.get("question", json.dumps(q))
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 5, _sanitize(f"  {i}. {text}"))
            pdf.ln(2)
    _safe("tech_questions", _tech_questions)

    def _rewrites():
        rewrite_list = rewrites.get("rewrites", [])
        if rewrite_list:
            pdf.section_title("Actionable Resume Rewrites")
            for rw in rewrite_list:
                if isinstance(rw, dict):
                    original = _sanitize(rw.get("original_chunk", rw.get("original", "")))
                    options = rw.get("rewrite_options", rw.get("rewrites", []))
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.set_text_color(50, 50, 50)
                    pdf.multi_cell(0, 5, _sanitize(f"  Original: {original}"))
                    for j, opt in enumerate(options, 1):
                        pdf.set_font("Helvetica", "", 9)
                        pdf.set_text_color(37, 99, 235)
                        pdf.multi_cell(0, 5, _sanitize(f"    Option {j}: {opt}"))
                    pdf.ln(3)
    _safe("rewrites", _rewrites)

    def _jd_ref():
        if jd_text:
            pdf.add_page()
            pdf.section_title("Job Description (Reference)")
            pdf.body_text(_sanitize(jd_text[:3000]))
    _safe("jd_ref", _jd_ref)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
