import requests

class GitHubService:
    def __init__(self):
        self.base_url = "https://api.github.com"

    def get_repositories(self, username):
        url = f"{self.base_url}/users/{username}/repos"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Failed to fetch repositories")
        repos = response.json()
        repo_data = []
        for repo in repos:
            repo_data.append({
                "name": repo["name"],
                "description": repo["description"],
                "url": repo["html_url"]
            })
        return repo_data

    def get_readme(self, username, repo_name):
        url = f"{self.base_url}/repos/{username}/{repo_name}/readme"
        headers = {
            "Accept": "application/vnd.github.v3.raw"
        }
        response = requests.get(
            url,
            headers=headers
        )
        if response.status_code == 200:
            return response.text
        return ""