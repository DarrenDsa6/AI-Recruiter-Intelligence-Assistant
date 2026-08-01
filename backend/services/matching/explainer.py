import re


class MatchExplainer:
    def generate_explanation(
        self, matched_skills: list[str], missing_skills: list[str], match_score: float
    ) -> dict:
        strong_matches = matched_skills[:5]
        recommendations = [f"Consider learning {s}" for s in missing_skills[:5]]

        if match_score > 80:
            summary = "Your resume strongly matches this job description."
        elif match_score > 60:
            summary = "Your resume partially matches this job description."
        else:
            summary = "Your resume has limited match with this job description."

        return {
            "summary": summary,
            "strong_matches": strong_matches,
            "recommendations": recommendations,
        }

    def generate_pros_cons(
        self,
        matched_skills: list[str],
        missing_skills: list[str],
        resume_text: str = "",
        jd_text: str = "",
        matched_chunks: list[dict] = None,
    ) -> dict:
        pros = []
        cons = []
        citations = []

        for skill in matched_skills[:8]:
            citation = self._find_citation(skill, resume_text)
            pros.append({
                "skill": skill,
                "reason": f"Candidate has '{skill}' which is required for the role.",
                "citation": citation,
            })
            if citation:
                citations.append(citation)

        for skill in missing_skills[:8]:
            jd_citation = self._find_citation(skill, jd_text)
            cons.append({
                "skill": skill,
                "reason": f"Candidate is missing '{skill}' which is listed in the job description.",
                "citation": jd_citation,
            })

        if matched_chunks:
            for chunk in matched_chunks[:3]:
                chunk_text = chunk.get("text", "")[:200]
                chunk_section = chunk.get("section", "unknown")
                citations.append({
                    "type": "resume_chunk",
                    "section": chunk_section,
                    "text": chunk_text,
                    "relevance": chunk.get("score", 0),
                })

        return {
            "pros": pros,
            "cons": cons,
            "citations": citations,
        }

    def _find_citation(self, skill: str, text: str) -> dict | None:
        if not text or not skill:
            return None
        pattern = re.compile(re.escape(skill), re.IGNORECASE)
        match = pattern.search(text)
        if match:
            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 60)
            context = text[start:end]
            line_num = text[:match.start()].count("\n") + 1
            return {
                "skill": skill,
                "context": context.strip(),
                "line": line_num,
            }
        return None
