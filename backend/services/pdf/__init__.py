import io
import json
import logging

from fpdf import FPDF

logger = logging.getLogger(__name__)


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(37, 99, 235)
        self.cell(0, 10, "AI Resume Tailor - Analysis Report", new_x="LMARGIN", new_y="NEXT", align="C")
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
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def bullet_list(self, items):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        for item in items:
            if isinstance(item, dict):
                text = json.dumps(item, indent=2)
            else:
                text = str(item)
            self.cell(5)
            self.multi_cell(0, 5, f"  {text}")
        self.ln(2)

    def key_value(self, key, value):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(50, 50, 50)
        self.cell(50, 6, f"{key}:")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, str(value), new_x="LMARGIN", new_y="NEXT")


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

    score = match_result.get("final_score", 0)
    pdf.key_value("ATS Match Score", f"{score}%")
    pdf.ln(3)

    category_breakdown = match_result.get("category_breakdown", {})
    if category_breakdown:
        pdf.section_title("Score Breakdown")
        for cat, val in category_breakdown.items():
            pdf.key_value(cat.replace("_", " ").title(), f"{val}%")
        pdf.ln(3)

    summary = report.get("summary", "")
    if summary:
        pdf.section_title("Summary")
        pdf.body_text(summary)

    ats_score = report.get("ats_score")
    if ats_score is not None:
        pdf.key_value("ATS Compatibility", f"{ats_score}/100")

    strengths = report.get("strengths", [])
    if strengths:
        pdf.section_title("Strengths")
        pdf.bullet_list(strengths)

    gaps = report.get("improvement_areas", report.get("gaps", []))
    if gaps:
        pdf.section_title("Areas for Improvement")
        pdf.bullet_list(gaps)

    missing = report.get("missing_keywords", [])
    if missing:
        pdf.section_title("Missing Keywords")
        pdf.bullet_list(missing)

    suggestions = report.get("keyword_suggestions", report.get("recommendations", []))
    if suggestions:
        pdf.section_title("Keyword Suggestions")
        for s in suggestions:
            if isinstance(s, dict):
                orig = s.get("original", s.get("keyword", ""))
                suggested = s.get("suggested_rewrite", s.get("suggestion", ""))
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(5)
                pdf.multi_cell(0, 5, f"{orig} -> {suggested}")
            else:
                pdf.bullet_list([str(s)])
        pdf.ln(2)

    gap_questions = questions.get("gap_focused", [])
    if gap_questions:
        pdf.section_title("Gap-Focused Interview Questions")
        for i, q in enumerate(gap_questions, 1):
            if isinstance(q, dict):
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(5)
                pdf.multi_cell(0, 5, f"{i}. {q.get('question', '')}")
                why = q.get("why_likely", "")
                if why:
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(8)
                    pdf.multi_cell(0, 5, f"Why likely: {why}")
                tips = q.get("prep_tips", "")
                if tips:
                    pdf.set_font("Helvetica", "", 9)
                    pdf.cell(8)
                    pdf.multi_cell(0, 5, f"Prep tips: {tips}")
                pdf.ln(2)

    tech_questions = questions.get("technical", [])
    if tech_questions:
        pdf.section_title("Technical Questions")
        for i, q in enumerate(tech_questions, 1):
            text = q if isinstance(q, str) else q.get("question", json.dumps(q))
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(5)
            pdf.multi_cell(0, 5, f"{i}. {text}")
        pdf.ln(2)

    rewrite_list = rewrites.get("rewrites", [])
    if rewrite_list:
        pdf.section_title("Actionable Resume Rewrites")
        for rw in rewrite_list:
            if isinstance(rw, dict):
                original = rw.get("original_chunk", rw.get("original", ""))
                options = rw.get("rewrite_options", rw.get("rewrites", []))
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(5)
                pdf.multi_cell(0, 5, f"Original: {original}")
                for j, opt in enumerate(options, 1):
                    pdf.set_font("Helvetica", "", 9)
                    pdf.set_text_color(37, 99, 235)
                    pdf.cell(8)
                    pdf.multi_cell(0, 5, f"Option {j}: {opt}")
                pdf.ln(3)

    if jd_text:
        pdf.add_page()
        pdf.section_title("Job Description (Reference)")
        pdf.body_text(jd_text[:3000])

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
