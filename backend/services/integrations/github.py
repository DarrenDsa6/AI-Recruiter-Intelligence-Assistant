import logging

import requests

from config.settings import settings

logger = logging.getLogger(__name__)


class GitHubService:
    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.session = requests.Session()
        effective_token = token or settings.github_token
        if effective_token:
            self.session.headers.update({"Authorization": f"Bearer {effective_token}"})

    def get_repositories(self, username: str) -> list[dict]:
        response = self.session.get(f"{self.BASE_URL}/users/{username}/repos")
        if response.status_code != 200:
            raise Exception("Failed to fetch repositories")

        repos = response.json()
        return [
            {
                "name": repo["name"],
                "description": repo["description"],
                "url": repo["html_url"],
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "size_kb": repo["size"],
                "last_updated": repo["updated_at"],
                "languages": self.get_languages(repo["languages_url"]),
                "readme": self.get_readme(username, repo["name"])[:2000],
            }
            for repo in repos
        ]

    def get_languages(self, languages_url: str) -> dict:
        response = self.session.get(languages_url)
        return response.json() if response.status_code == 200 else {}

    def get_readme(self, username: str, repo_name: str) -> str:
        url = f"{self.BASE_URL}/repos/{username}/{repo_name}/readme"
        response = self.session.get(url, headers={"Accept": "application/vnd.github.v3.raw"})
        return response.text if response.status_code == 200 else ""
