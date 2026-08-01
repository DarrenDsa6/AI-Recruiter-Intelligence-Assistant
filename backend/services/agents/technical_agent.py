import logging

logger = logging.getLogger(__name__)


class TechnicalAgent:
    """Analyzes GitHub profile: commit frequency, languages used, repo complexity.
    Processes repos one by one to avoid overwhelming the LLM API."""

    async def analyze(self, github_context: dict, llm_client) -> dict:
        if not github_context or not isinstance(github_context, dict):
            return self._empty_result("No GitHub data provided")

        repos = github_context.get("repos", [])
        if not repos:
            return self._empty_result("No repositories found")

        result = self._basic_analysis(repos)
        llm_analysis = await self._llm_analysis(repos, llm_client)
        result["llm_analysis"] = llm_analysis

        logger.info(f"TechnicalAgent: analyzed {len(repos)} repos one by one")
        return result

    def _basic_analysis(self, repos: list[dict]) -> dict:
        total_stars = sum(r.get("stars", 0) for r in repos)
        total_forks = sum(r.get("forks", 0) for r in repos)
        languages: dict[str, int] = {}
        for r in repos:
            for lang, bytes_count in (r.get("languages") or {}).items():
                languages[lang] = languages.get(lang, 0) + bytes_count

        top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        has_readme = sum(1 for r in repos if r.get("readme"))

        projects_with_desc = [r for r in repos if r.get("description")]

        return {
            "repo_count": len(repos),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "top_languages": [lang for lang, _ in top_languages],
            "projects_with_descriptions": len(projects_with_desc),
            "has_readme_ratio": f"{has_readme}/{len(repos)}",
            "summary": f"Candidate has {len(repos)} repositories with {total_stars} stars. "
                       f"Top languages: {', '.join(lang for lang, _ in top_languages)}.",
        }

    async def _llm_analysis(self, repos: list[dict], llm_client) -> dict:
        """Process each repo individually via the LLM to avoid token limits."""
        try:
            repo_summaries = []
            for r in repos[:20]:
                repo_summaries.append({
                    "name": r.get("name", ""),
                    "description": (r.get("description") or "")[:200],
                    "stars": r.get("stars", 0),
                    "forks": r.get("forks", 0),
                    "languages": (r.get("languages") or {}),
                    "readme": (r.get("readme") or "")[:1000],
                })
            return await llm_client.analyze_github(repo_summaries)
        except Exception as e:
            logger.warning(f"TechnicalAgent LLM analysis failed: {e}")
            return {"error": str(e)}

    def _empty_result(self, reason: str) -> dict:
        return {
            "repo_count": 0,
            "total_stars": 0,
            "total_forks": 0,
            "top_languages": [],
            "projects_with_descriptions": 0,
            "has_readme_ratio": "0/0",
            "summary": reason,
            "llm_analysis": {},
        }
