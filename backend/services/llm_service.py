from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import re
import logging

logger = logging.getLogger(__name__)


class LLMRecruiterService:

    def __init__(self):
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("LLM_API_KEY") or os.getenv("MINIMAX_API_KEY")
        )
        self.model = "mistralai/mistral-large-3-675b-instruct-2512"

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
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a strict recruiter AI."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        text = response.choices[0].message.content

        cleaned = (
            text.replace("```json", "")
                .replace("```", "")
                .strip()
        )

        try:
            return json.loads(cleaned)
        except Exception:
            return {
                "raw": text,
                "cleaned": cleaned,
                "error": "JSON parse failed"
            }

    def _stream(self, prompt):
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing candidate...'})}\n\n"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a strict recruiter AI."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                stream=True
            )

            for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)

                if content:
                    yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"

            yield f"data: {json.dumps({'type': 'final', 'result': {'summary': 'Analysis complete'}})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    def _stream_chat(self, messages):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                stream=True
            )

            for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)

                if content:
                    yield content

        except Exception as e:
            logger.error(f"Chat stream failed: {e}")
            raise


llm_service = LLMRecruiterService()
