from openai import AsyncOpenAI
import json
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "You are a career coach helping candidates optimize their resume for a specific job description."


class LLMService:

    def _client(self, api_key, base_url):
        return AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate_candidate_report(self, resume, jd, match_result, github_context, api_key, base_url, model):
        prompt = f"""You are a career coach. Analyze this candidate's resume against the job description.

1. Identify missing keywords that ATS (Applicant Tracking Systems) would look for
2. Suggest how to rephrase existing experience to better match this JD
3. Rate the ATS compatibility (not "fit" -- "compatibility")

Resume:
{resume}

Job Description:
{jd}

Match Analysis:
{json.dumps(match_result, indent=2)}

GitHub:
{json.dumps(github_context, indent=2)}

Return ONLY JSON:
{{
  "ats_score": 0,
  "missing_keywords": [],
  "keyword_suggestions": [
    {{"original": "", "suggested_rewrite": ""}}
  ],
  "summary": "",
  "strengths": [],
  "improvement_areas": []
}}"""
        return await self._call(prompt, api_key, base_url, model)

    async def generate_interview_questions(self, resume, jd, missing_skills, github_context, api_key, base_url, model):
        prompt = f"""You are a mock interview coach. Given this candidate's resume and the job description,
generate interview questions that target the candidate's EXACT skill gaps.

Focus on questions the candidate is LIKELY to be asked about their weak areas.
Provide preparation tips for each question.

Resume:
{resume}

Job Description:
{jd}

Missing Skills:
{json.dumps(missing_skills)}

GitHub:
{json.dumps(github_context)}

Return ONLY JSON:
{{
  "technical": [],
  "behavioral": [],
  "gap_focused": [
    {{"question": "", "why_likely": "", "prep_tips": ""}}
  ]
}}"""
        return await self._call(prompt, api_key, base_url, model)

    async def generate_actionable_rewrites(self, low_scoring_chunks, jd_text, api_key, base_url, model):
        if not low_scoring_chunks:
            return {"rewrites": []}

        chunks_text = "\n\n".join(
            f"Chunk {c['chunk_index']} (score: {c['score']}):\n{c['text']}"
            for c in low_scoring_chunks
        )

        prompt = f"""You are a resume optimization coach. These resume sections scored lowest
against the target job description. Generate 3 optimized rewrite alternatives for each.

Low-scoring resume chunks:
{chunks_text}

Job Description:
{jd_text}

Return ONLY JSON:
{{
  "rewrites": [
    {{
      "original_chunk": "",
      "rewrite_options": ["", "", ""]
    }}
  ]
}}"""
        return await self._call(prompt, api_key, base_url, model)

    async def _call(self, prompt, api_key, base_url, model):
        client = self._client(api_key, base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        text = response.choices[0].message.content
        cleaned = text.replace("```json", "").replace("```", "").strip()

        try:
            first_brace = cleaned.index("{")
            last_brace = cleaned.rindex("}")
            return json.loads(cleaned[first_brace : last_brace + 1])
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"JSON parse failed: {e}, raw: {text[:200]}")
            return {"raw": text, "cleaned": cleaned, "error": f"JSON parse failed: {e}"}

    async def _stream_chat(self, messages, api_key, base_url, model):
        client = self._client(api_key, base_url)
        response = await client.chat.completions.create(
            model=model, messages=messages, temperature=0.2, stream=True
        )
        async for chunk in response:
            if not chunk.choices:
                continue
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                yield content


llm_service = LLMService()
