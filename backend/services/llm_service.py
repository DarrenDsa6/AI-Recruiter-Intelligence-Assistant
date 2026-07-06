from openai import AsyncOpenAI
import json
import logging

logger = logging.getLogger(__name__)


class LLMRecruiterService:

    def _client(self, api_key, base_url):
        return AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def analyze_github_repos(self, github_data, api_key, base_url, model):
        prompt = f"""
            Analyze GitHub projects. Dont speak negatives on abandoned projects, just focus on the good ones.
            Just point out basic neagatives and nothing major. It should seem like even with negatives the candidate is still a good.
            In strong signals, include the most important skills and technologies that are relevant to the job description. In weak signals, include the skills and technologies that are missing or not well represented in the candidate's GitHub profile.
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

        return await self._call(prompt, api_key, base_url, model)

    async def generate_candidate_report(self, resume, jd, match_result, github_context, api_key, base_url, model):
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

        return await self._call(prompt, api_key, base_url, model)

    async def generate_interview_questions(self, resume, jd, missing_skills, github_context, api_key, base_url, model):
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

        return await self._call(prompt, api_key, base_url, model)

    async def _call(self, prompt, api_key, base_url, model):
        client = self._client(api_key, base_url)
        response = await client.chat.completions.create(
            model=model,
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
            first_brace = cleaned.index("{")
            last_brace = cleaned.rindex("}")
            json_str = cleaned[first_brace:last_brace + 1]
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"JSON parse failed: {e}, raw: {text[:200]}")
            return {
                "raw": text,
                "cleaned": cleaned,
                "error": f"JSON parse failed: {e}"
            }

    async def _stream(self, prompt, api_key, base_url, model):
        client = self._client(api_key, base_url)
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing candidate...'})}\n\n"

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a strict recruiter AI."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                stream=True
            )

            async for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)

                if content:
                    yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"

            yield f"data: {json.dumps({'type': 'final', 'result': {'summary': 'Analysis complete'}})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    async def _stream_chat(self, messages, api_key, base_url, model):
        client = self._client(api_key, base_url)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                stream=True
            )

            async for chunk in response:
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
