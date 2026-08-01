import logging

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

MAX_REPOS = 20


class GitHubService:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        effective_token = token or settings.github_token
        if effective_token:
            self.headers["Authorization"] = f"Bearer {effective_token}"

    async def get_repositories(self, username: str) -> list[dict]:
        async with httpx.AsyncClient(headers=self.headers, timeout=15) as client:
            repos = []
            page = 1
            while page <= 2 and len(repos) < MAX_REPOS:
                resp = await client.get(
                    f"{self.BASE_URL}/users/{username}/repos",
                    params={"page": page, "per_page": 100, "sort": "updated", "direction": "desc"},
                )
                if resp.status_code != 200:
                    logger.warning(f"GitHub repos fetch failed: {resp.status_code}")
                    break
                data = resp.json()
                if not data:
                    break
                repos.extend(data)
                if len(data) < 100:
                    break
                page += 1

            repos = repos[:MAX_REPOS]
            result = []
            for repo in repos:
                try:
                    readme = await self._get_readme(client, username, repo["name"])
                    languages = await self._get_languages(client, repo.get("languages_url", ""))
                    result.append({
                        "name": repo["name"],
                        "description": repo.get("description") or "",
                        "url": repo["html_url"],
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "languages": languages,
                        "readme": readme[:1500],
                    })
                except Exception as e:
                    logger.warning(f"Skipping repo {repo.get('name')}: {e}")
                    continue

            return result

    async def iter_repositories(self, username: str):
        """Async generator that yields repos one by one to avoid loading everything at once."""
        async with httpx.AsyncClient(headers=self.headers, timeout=15) as client:
            page = 1
            fetched = 0
            while page <= 2 and fetched < MAX_REPOS:
                resp = await client.get(
                    f"{self.BASE_URL}/users/{username}/repos",
                    params={"page": page, "per_page": 100, "sort": "updated", "direction": "desc"},
                )
                if resp.status_code != 200:
                    logger.warning(f"GitHub repos fetch failed: {resp.status_code}")
                    break

                for repo in resp.json():
                    if fetched >= MAX_REPOS:
                        return
                    try:
                        readme = await self._get_readme(client, username, repo["name"])
                        languages = await self._get_languages(client, repo.get("languages_url", ""))
                        yield {
                            "name": repo["name"],
                            "description": repo.get("description") or "",
                            "url": repo["html_url"],
                            "stars": repo.get("stargazers_count", 0),
                            "forks": repo.get("forks_count", 0),
                            "languages": languages,
                            "readme": readme[:1500],
                        }
                        fetched += 1
                    except Exception as e:
                        logger.warning(f"Skipping repo {repo.get('name')}: {e}")
                        continue

                if len(list(resp.json())) < 100:
                    break
                page += 1

    async def _get_languages(self, client: httpx.AsyncClient, url: str) -> dict:
        if not url:
            return {}
        resp = await client.get(url)
        return resp.json() if resp.status_code == 200 else {}

    async def _get_readme(self, client: httpx.AsyncClient, username: str, repo_name: str) -> str:
        url = f"{self.BASE_URL}/repos/{username}/{repo_name}/readme"
        resp = await client.get(url, headers={**self.headers, "Accept": "application/vnd.github.v3.raw"})
        return resp.text if resp.status_code == 200 else ""
