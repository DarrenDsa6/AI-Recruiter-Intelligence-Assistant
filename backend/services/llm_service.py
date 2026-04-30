from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import re


class LLMRecruiterService:

    def __init__(self, api_key: str):
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("MINIMAX_API_KEY")
        )

    def analyze_github_repos(self, github_data):

        prompt = f"""
            Analyze GitHub projects.

            Return ONLY JSON.

            DATA:
            {json.dumps(github_data, indent=2)}

            Return:
            {{
            "summary": "",
            "skill_level": "",
            "best_project": "",
            "signals": {{
                "strong": [],
                "weak": []
            }}
            }}
            """

        return self._call(prompt)

    def generate_candidate_report(self, resume, jd, match_result, github_context):

        prompt = f"""
            You are a recruiter.

            Resume:
            {resume}

            JD:
            {jd}

            Match:
            {match_result}

            GitHub:
            {github_context}

            Return ONLY JSON:
            {{
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "recommendation": "",
            "authenticity_score": 0
            }}
            """

        return self._call(prompt)

    def generate_interview_questions(self, resume, jd, missing_skills, github_context):

        prompt = f"""
            Generate interview questions.

            Resume:
            {resume}

            JD:
            {jd}

            Missing:
            {missing_skills}

            GitHub:
            {github_context}

            Return ONLY JSON:
            {{
            "technical": [],
            "behavioral": [],
            "gap_based": []
            }}
            """

        return self._call(prompt)

    def _call(self, prompt):

        response = self.client.chat.completions.create(
            model="minimaxai/minimax-m2.7",
            messages=[
                {"role": "system", "content": "You are a strict recruiter AI."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        text = response.choices[0].message.content

        # 🔥 REMOVE markdown ```json blocks
        cleaned = re.sub(r"```json|```", "", text).strip()

        try:
            return json.loads(cleaned)
        except Exception as e:
            return {
                "raw": text,
                "cleaned": cleaned,
                "error": str(e)
            }