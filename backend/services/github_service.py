import requests

class GitHubService:
    def __init__(self):
        self.base_url = "https://api.github.com"

    # -----------------------------
    # 1. Get repositories (enriched)
    # -----------------------------
    def get_repositories(self, username):

        url = f"{self.base_url}/users/{username}/repos"
        response = requests.get(url)

        if response.status_code != 200:
            raise Exception("Failed to fetch repositories")

        repos = response.json()

        repo_data = []

        for repo in repos:

            languages = self.get_languages(repo["languages_url"])

            readme = self.get_readme(username, repo["name"])

            repo_data.append({
                "name": repo["name"],
                "description": repo["description"],
                "url": repo["html_url"],

                # 🔥 important signals
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "size_kb": repo["size"],
                "last_updated": repo["updated_at"],

                # 🔥 skill signals
                "languages": languages,

                # 🔥 content signal
                "readme": readme[:2000]  # limit for LLM
            })

        return repo_data

    # -----------------------------
    # 2. Languages API
    # -----------------------------
    def get_languages(self, languages_url):
        response = requests.get(languages_url)

        if response.status_code != 200:
            return {}

        return response.json()

    # -----------------------------
    # 3. README fetch
    # -----------------------------
    def get_readme(self, username, repo_name):

        url = f"{self.base_url}/repos/{username}/{repo_name}/readme"

        headers = {
            "Accept": "application/vnd.github.v3.raw"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.text

        return ""