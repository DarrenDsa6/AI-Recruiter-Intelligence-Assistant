import re
import logging

logger = logging.getLogger(__name__)


class HRAgent:
    """Analyzes resume for tenure, career progression, and educational background."""

    async def analyze(self, resume_text: str, llm_client, sections: dict = None) -> dict:
        if not resume_text:
            return self._empty_result("No resume text provided")

        basic = self._basic_analysis(resume_text, sections)
        llm_analysis = await self._llm_analysis(resume_text, llm_client)
        basic["llm_analysis"] = llm_analysis
        return basic

    def _basic_analysis(self, text: str, sections: dict = None) -> dict:
        tenure_years = self._estimate_tenure(text)
        progression = self._career_progression(text)
        education = self._extract_education(text, sections)
        experience_count = self._count_positions(text)

        return {
            "estimated_tenure_years": tenure_years,
            "career_progression_score": progression,
            "education": education,
            "positions_held": experience_count,
            "has_management_experience": self._has_management(text),
            "summary": f"Candidate has ~{tenure_years} years of experience across {experience_count} positions. "
                       f"Education: {education.get('highest_degree', 'unknown')}.",
        }

    def _estimate_tenure(self, text: str) -> int:
        year_pattern = re.compile(r"\b(19|20)\d{2}\b")
        years = [int(m.group()) for m in year_pattern.finditer(text)]
        years = [y for y in years if 1985 <= y <= 2030]
        if not years:
            return 0
        min_year = min(years)
        max_year = max(years)
        return max(0, max_year - min_year)

    def _career_progression(self, text: str) -> int:
        senior_indicators = [
            "senior", "lead", "principal", "staff", "manager", "director",
            "head", "vp", "vice president", "chief", "cto", "ceo", "architect",
        ]
        count = sum(1 for ind in senior_indicators if ind in text.lower())
        return min(100, count * 15)

    def _extract_education(self, text: str, sections: dict = None) -> dict:
        edu_text = ""
        if sections and "education" in sections:
            edu_text = sections["education"]
        else:
            edu_text = text

        degrees = {
            "phd": r"\b(ph\.?d\.?|doctorate|doctoral|philosophy doctor)\b",
            "master": r"\b(master|m\.?s\.?|m\.?a\.?|mba|m\.?eng\.?)\b",
            "bachelor": r"\b(bachelor|b\.?s\.?|b\.?a\.?|b\.?eng\.?|undergraduate)\b",
            "associate": r"\b(associate|a\.?s\.?|a\.?a\.?)\b",
        }

        highest = "unknown"
        for degree, pattern_str in degrees.items():
            if re.search(pattern_str, edu_text, re.IGNORECASE):
                highest = degree

        universities = re.findall(
            r"\b([A-Z][a-zA-Z]+ (?:University|College|Institute|School))\b",
            edu_text,
        )

        return {
            "highest_degree": highest,
            "universities_mentioned": list(set(universities))[:3],
        }

    def _count_positions(self, text: str) -> int:
        position_markers = [
            r"^(?:.*\bat\b.*)$",
            r"^(?:.*\bcompany\b.*)$",
            r"^(?:.*\bcorporation\b.*)$",
            r"^(?:.*\binc\.?\b.*)$",
            r"^(?:.*\bltd\.?\b.*)$",
            r"^(?:.*\bllc\.?\b.*)$",
        ]
        lines = text.split("\n")
        count = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            for marker in position_markers:
                if re.match(marker, line, re.IGNORECASE):
                    count += 1
                    break
        return max(count, 1)

    def _has_management(self, text: str) -> bool:
        management_indicators = [
            "managed", "management", "lead", "led", "supervised", "directed",
            "team lead", "team of", "reported to", "manager", "director",
        ]
        return any(ind in text.lower() for ind in management_indicators)

    async def _llm_analysis(self, resume_text: str, llm_client) -> dict:
        try:
            return await llm_client.analyze_career(resume_text[:8000])
        except Exception as e:
            logger.warning(f"HRAgent LLM analysis failed: {e}")
            return {"error": str(e)}

    def _empty_result(self, reason: str) -> dict:
        return {
            "estimated_tenure_years": 0,
            "career_progression_score": 0,
            "education": {"highest_degree": "unknown", "universities_mentioned": []},
            "positions_held": 0,
            "has_management_experience": False,
            "summary": reason,
            "llm_analysis": {},
        }
